# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# adultevul/services.py
"""Circuit de l'information préoccupante adulte vulnérable. Chaque étape est journalisée et contrôlée."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import CelluleEvaluation, HistoriqueAV, MesureMASP, PROPOSITIONS


def journaliser(situation, user, action, detail=""):
    HistoriqueAV.objects.create(situation=situation, auteur=user if user and user.is_authenticated else None,
                                action=action, detail=detail)


def peut_recevoir(user, mds):
    return bool(user.is_authenticated and mds and user.a_la_capacite("peut_voir") and user.a_acces_mds(mds))


def peut_piloter(user, situation):
    return bool(situation.mds_id and user.is_authenticated and user.a_la_capacite("av_piloter")
                and user.a_acces_mds(situation.mds))


def peut_evaluer(user, situation):
    if not (situation.mds_id and user.is_authenticated and user.a_acces_mds(situation.mds)):
        return False
    if peut_piloter(user, situation):
        return True
    cellule = getattr(situation, 'cellule', None)
    return bool(user.a_la_capacite("av_evaluer") and cellule and cellule.referents.filter(pk=user.pk).exists())


def peut_decider(user, situation):
    return bool(situation.mds_id and user.is_authenticated and user.a_la_capacite("peut_decider")
                and user.a_acces_mds(situation.mds))


def _verifier(condition, message):
    if not condition:
        raise PermissionDenied(message)


@transaction.atomic
def creer_situation(situation, user):
    """Enregistre le recueil (annexe 1). La situation est à qualifier par le cadre."""
    _verifier(peut_recevoir(user, situation.mds), "Vous ne pouvez pas enregistrer de recueil pour cette MDS.")
    situation.recue_par = user
    situation.cree_par = user
    situation.statut = 'RECUE'
    situation.save()
    journaliser(situation, user, "RECUEIL", "Recueil de l'information enregistré")
    return situation


@transaction.atomic
def qualifier(situation, user, qualifiee, motif):
    """Le cadre qualifie (ou non) l'information. Qualifiée : la cellule d'évaluation doit être constituée."""
    _verifier(peut_piloter(user, situation), "Seul le cadre de la MDS peut qualifier l'information.")
    _verifier(situation.statut == 'RECUE', "Cette information a déjà été qualifiée.")
    if not motif.strip():
        raise ValidationError("Indiquez le motif de la qualification.")
    situation.statut = 'QUALIFIEE' if qualifiee else 'NON_QUALIFIEE'
    situation.date_qualification = timezone.now()
    situation.qualifiee_par = user
    situation.motif_qualification = motif
    situation.save()
    journaliser(situation, user, "QUALIFICATION" if qualifiee else "NON_QUALIFICATION", motif)
    return situation


@transaction.atomic
def constituer_cellule(situation, user, cellule_data, referents):
    """Met en place la cellule d'évaluation (annexe 2) et désigne les référents."""
    _verifier(peut_piloter(user, situation), "Seul le cadre de la MDS peut constituer la cellule.")
    _verifier(situation.statut == 'QUALIFIEE', "La situation doit être qualifiée avant de constituer la cellule.")
    cellule = CelluleEvaluation.objects.create(situation=situation, **cellule_data)
    cellule.referents.set(referents)
    situation.statut = 'EVALUATION'
    situation.save(update_fields=['statut', 'date_modification'])
    journaliser(situation, user, "CELLULE", f"Cellule du {cellule.date_cellule:%d/%m/%Y}, urgence {cellule.get_urgence_display()}")
    return cellule


@transaction.atomic
def enregistrer_cellule(situation, user, cellule_data, referents):
    """Met à jour le plan d'action et les propositions tant que le rapport n'est pas soumis au visa."""
    _verifier(peut_evaluer(user, situation), "Vous ne pouvez pas modifier cette évaluation.")
    cellule = situation.cellule
    _verifier(not cellule.verrouillee, "Le rapport est déjà soumis au visa : l'évaluation est figée.")
    for champ, valeur in cellule_data.items():
        setattr(cellule, champ, valeur)
    cellule.save()
    cellule.referents.set(referents)
    journaliser(situation, user, "EVALUATION", "Évaluation mise à jour")
    return cellule


def controler_rapport(situation):
    """Liste ce qui manque avant la soumission au visa. Vide = rapport complet."""
    manques = []
    cellule = getattr(situation, 'cellule', None)
    if not cellule:
        return ["la cellule d'évaluation n'est pas constituée"]
    if not cellule.referents.exists():
        manques.append("le référent de la situation")
    if not cellule.plan_action.strip():
        manques.append("le plan d'action")
    if not cellule.propositions:
        manques.append("au moins une proposition")
    codes = {code for code, _ in PROPOSITIONS}
    if any(p not in codes for p in cellule.propositions):
        manques.append("une proposition non reconnue")
    if "CLASSEMENT" in cellule.propositions and len(cellule.propositions) > 1:
        manques.append("le classement sans suite ne peut pas être combiné à une autre proposition")
    if "CLASSEMENT" in cellule.propositions and not cellule.argumentation.strip():
        manques.append("l'argumentation du classement sans suite")
    if "PROTECTION_JURIDIQUE" in cellule.propositions:
        manques.extend(pieces_protection_manquantes(situation))
    return manques


def pieces_protection_manquantes(situation):
    """Pièces exigées par le parquet pour une demande de protection (annexe 9, sous peine d'irrecevabilité)."""
    manques = []
    if not situation.tribunal:
        manques.append("le parquet compétent")
    if not situation.mesure_protection:
        manques.append("la mesure demandée (tutelle, curatelle ou sauvegarde)")
    if not situation.pj_acte_naissance:
        manques.append("la copie de l'acte de naissance ou d'un justificatif d'état civil")
    if not situation.pj_fiche:
        manques.append("la fiche de renseignements complétée")
    if not situation.pj_certificat and not situation.pj_certificat_absence.strip():
        manques.append("le certificat médical circonstancié, ou le motif de son absence")
    return manques


@transaction.atomic
def enregistrer_protection(situation, user, donnees):
    """Parquet, mesure et pièces jointes (annexe 9). Modifiable tant que le rapport n'est pas visé."""
    _verifier(peut_evaluer(user, situation), "Vous ne pouvez pas modifier ces informations.")
    _verifier(situation.statut in ('EVALUATION', 'RAPPORT', 'VALIDEE'), "Cette étape n'est plus modifiable.")
    if situation.statut != 'EVALUATION':
        _verifier(peut_piloter(user, situation), "Seul le cadre peut modifier le rapport après soumission.")
    for champ, valeur in donnees.items():
        setattr(situation, champ, valeur)
    situation.save()
    journaliser(situation, user, "PROTECTION", "Informations de protection juridique mises à jour")
    return situation


@transaction.atomic
def enregistrer_masp(situation, user, donnees):
    """Suivi MASP dans CID (annexe 6), une fois la mesure proposée et décidée."""
    _verifier(peut_piloter(user, situation) or peut_evaluer(user, situation), "Accès refusé au suivi MASP.")
    _verifier("MASP" in situation.cellule.propositions, "Aucun MASP n'a été proposé dans cette situation.")
    mesure, _ = MesureMASP.objects.get_or_create(situation=situation, defaults={'niveau': donnees['niveau']})
    for champ, valeur in donnees.items():
        setattr(mesure, champ, valeur)
    mesure.save()
    journaliser(situation, user, "MASP", f"Suivi MASP niveau {mesure.niveau}")
    return mesure


@transaction.atomic
def soumettre_rapport(situation, user):
    """Soumet le rapport au visa de l'adjoint Cohésion sociale. Refus avec la liste des éléments manquants."""
    _verifier(peut_evaluer(user, situation), "Vous ne pouvez pas soumettre le rapport de cette situation.")
    _verifier(situation.statut == 'EVALUATION', "Le rapport n'est pas attendu à cette étape.")
    manques = controler_rapport(situation)
    if manques:
        raise ValidationError("Transmission impossible : il manque " + ", ".join(manques) + ".")
    situation.cellule.date_rapport = timezone.now()
    situation.cellule.save(update_fields=['date_rapport'])
    situation.statut = 'RAPPORT'
    situation.save(update_fields=['statut', 'date_modification'])
    journaliser(situation, user, "RAPPORT", "Rapport soumis au visa")
    return situation


@transaction.atomic
def valider_rapport(situation, user):
    """Visa technique du cadre (adjoint Cohésion sociale ou responsable de MDS de proximité)."""
    _verifier(peut_piloter(user, situation), "Seul le cadre de la MDS peut viser le rapport.")
    _verifier(situation.statut == 'RAPPORT', "Aucun rapport n'est en attente de visa.")
    situation.statut = 'VALIDEE'
    situation.save(update_fields=['statut', 'date_modification'])
    journaliser(situation, user, "VISA", "Rapport visé")
    return situation


@transaction.atomic
def renvoyer_rapport(situation, user, motif):
    """Le cadre renvoie le rapport pour compléments : l'évaluation redevient modifiable."""
    _verifier(peut_piloter(user, situation), "Seul le cadre de la MDS peut renvoyer le rapport.")
    _verifier(situation.statut == 'RAPPORT', "Aucun rapport n'est en attente de visa.")
    if not motif.strip():
        raise ValidationError("Indiquez le motif du renvoi.")
    situation.statut = 'EVALUATION'
    situation.save(update_fields=['statut', 'date_modification'])
    journaliser(situation, user, "RENVOI", motif)
    return situation


@transaction.atomic
def decider(situation, user, commentaire):
    """Décision administrative du directeur de MDS."""
    _verifier(peut_decider(user, situation), "Seul le directeur de la MDS peut prendre la décision.")
    _verifier(situation.statut == 'VALIDEE', "Le rapport doit être visé avant la décision.")
    situation.decision_commentaire = commentaire
    situation.decideur = user
    situation.date_decision = timezone.now()
    situation.statut = 'DECIDEE'
    situation.save()
    journaliser(situation, user, "DECISION", commentaire)
    return situation


@transaction.atomic
def cloturer(situation, user):
    _verifier(peut_piloter(user, situation), "Seul le cadre de la MDS peut clôturer la situation.")
    _verifier(situation.statut in ('DECIDEE', 'NON_QUALIFIEE'), "La situation ne peut pas être clôturée à cette étape.")
    situation.statut = 'CLOTUREE'
    situation.date_cloture = timezone.now()
    situation.save(update_fields=['statut', 'date_cloture', 'date_modification'])
    journaliser(situation, user, "CLOTURE")
    return situation
