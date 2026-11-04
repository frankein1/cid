# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/services/prescription_circuit.py
"""
Circuit d'une prescription vers une action d'insertion (fiche de liaison / d'orientation) :

  En préparation ──(prescripteur : adresser)──▶ [À valider par le pôle ──▶ Refusée]
                                               ──▶ Adressée au porteur, en attente d'intégration
                                                     ├─▶ Non intégrée (motif)
                                                     ├─▶ Réorientée
                                                     └─▶ Intégrée, en cours ──▶ Terminée · Arrêtée · Réorientée

Le passage par le pôle dépend de l'action (« Prescription validée par le pôle insertion »).
Le retour du porteur (premier rendez-vous, intégration, sortie) est noté par le prescripteur ou par
l'administratif du pôle ; il met à jour, sans ressaisie, la ligne de l'action dans le contrat.
"""
from django.db import transaction
from django.utils import timezone

from insertion import acces
from insertion.models import (ContratInsertion, HistoriquePrescription, LigneActionContrat, PrescriptionInsertion,
                              ReponseQuestion)
from insertion.services.contrat_circuit import ErreurCircuit, agents_pole, prevenir

P = PrescriptionInsertion
C = ContratInsertion


def journal(p, user, action, commentaire=""):
    return HistoriquePrescription.objects.create(prescription=p, user=user, action=action[:200], commentaire=commentaire)


def _usager(p):
    return f"{p.beneficiaire.prenom} {p.beneficiaire.nom.upper()}"


def contrat_courant(beneficiaire):
    """Contrat auquel rattacher une prescription : celui en préparation, sinon le dernier validé en vigueur."""
    qs = beneficiaire.contrats_insertion
    en_prep = qs.filter(statut__in=C.MODIFIABLES).order_by('-pk').first()
    if en_prep:
        return en_prep
    aujourd_hui = timezone.localdate()
    return (qs.filter(statut__in=(C.VALIDE, C.VALIDE_SAUF_ACTION), date_fin__gte=aujourd_hui)
            .order_by('-date_fin').first()
            or qs.filter(statut__in=(C.TRANSMIS, C.RECU)).order_by('-pk').first())


# ---------------------------------------------------------------------- création
@transaction.atomic
def creer(beneficiaire, user, action):
    """Prescription préremplie à partir du dossier et du contrat courant."""
    c = contrat_courant(beneficiaire)
    p = P(beneficiaire=beneficiaire, mds=beneficiaire.mds, pole=acces.pole_de_mds(beneficiaire.mds),
          prescripteur=user, action=action, contrat=c, date_prescription=timezone.localdate(),
          identifiant_france_travail=beneficiaire.numero_france_travail or "",
          inscrit_france_travail=bool(beneficiaire.numero_france_travail),
          pieces_fournies=[])
    if c:
        p.inscrit_france_travail = c.inscrit_france_travail
        p.identifiant_france_travail = c.identifiant_france_travail or p.identifiant_france_travail
        p.qualification = " – ".join(x for x in [c.get_niveau_etudes_display() if c.niveau_etudes else "",
                                                  c.formation] if x)
        p.objectifs = c.objectifs
    p.save()
    journal(p, user, f"Prescription créée vers « {action.libelle} »",
            f"Rattachée au contrat {c.numero}" if c else "Aucun contrat en cours")
    return p


def enregistrer_reponses(p, donnees):
    """donnees : {question_pk: texte}."""
    for q in p.action.questions.all():
        if q.pk in donnees:
            ReponseQuestion.objects.update_or_create(prescription=p, question=q,
                                                     defaults={"valeur": (donnees[q.pk] or "").strip()})


# ---------------------------------------------------------------------- tableau des actions du contrat
def synchroniser_contrat(p):
    """La ligne de l'action dans le contrat suit la prescription (entrée, sortie, motif)."""
    # La ligne n'apparaît qu'une fois la prescription adressée au porteur (pas en attente de validation, ni refusée)
    if not p.contrat_id or p.statut in (P.BROUILLON, P.ANNULEE, P.A_VALIDER, P.REFUSEE):
        return
    lignes = list(p.lignes_contrat.all())
    if not lignes:
        ligne = p.contrat.lignes.filter(action=p.action, prescription__isnull=True).first()
        if ligne:
            ligne.prescription = p
            lignes = [ligne]
        elif p.contrat.modifiable:
            lignes = [LigneActionContrat(contrat=p.contrat, action=p.action, prescription=p)]
    motif = p.motif_sortie or (f"Non intégrée : {p.motif_non_integration}" if p.motif_non_integration else "")
    if p.reorientation:
        motif = (motif + " – " if motif else "") + f"réorientée : {p.get_reorientation_display()}"
    for l in lignes:
        l.date_entree = p.date_entree
        l.date_sortie = p.date_sortie
        l.motif_sortie = motif[:200]
        l.save()


# ---------------------------------------------------------------------- prescripteur
@transaction.atomic
def adresser(p, user):
    if p.statut != P.BROUILLON:
        raise ErreurCircuit("Cette prescription a déjà été adressée.")
    manques = p.manques_envoi()
    if manques:
        raise ErreurCircuit("Avant d'adresser la prescription, renseignez : " + ", ".join(manques) + ".")
    if not p.date_signature:
        p.date_signature = timezone.localdate()
    if not p.pole_id:
        p.pole = acces.pole_de_mds(p.mds)
    if p.action.validation_pole:
        if not p.pole_id:
            raise ErreurCircuit("Cette action passe par le pôle insertion, et aucun pôle ne couvre la MDS.")
        p.statut = P.A_VALIDER
        p.save()
        journal(p, user, "Adressée au pôle insertion pour validation")
        prevenir(user, agents_pole(p, 'rsa_pole_admin') + agents_pole(p, 'rsa_pole_cadre'), p,
                 f"Prescription {p.numero} à valider",
                 f"Prescription de {_usager(p)} ({p.mds}) vers « {p.action.libelle} » : elle attend la validation "
                 "du pôle avant d'être adressée au porteur.")
    else:
        p.statut, p.date_envoi = P.EN_ATTENTE, timezone.localdate()
        p.save()
        journal(p, user, "Adressée au porteur" + (f" ({p.action.porteur})" if p.action.porteur else ""))
    synchroniser_contrat(p)


@transaction.atomic
def annuler(p, user, motif=""):
    if p.statut not in (P.BROUILLON, P.A_VALIDER):
        raise ErreurCircuit("Seule une prescription en préparation ou en attente de validation peut être annulée.")
    p.statut = P.ANNULEE
    p.save(update_fields=['statut', 'modifie_le'])
    journal(p, user, "Prescription annulée", motif)


# ---------------------------------------------------------------------- pôle
@transaction.atomic
def valider(p, user, accepte, motif=""):
    if p.statut != P.A_VALIDER:
        raise ErreurCircuit("Cette prescription n'attend pas de validation.")
    if not accepte and not motif.strip():
        raise ErreurCircuit("Indiquez le motif du refus.")
    p.valide_par, p.date_validation = user, timezone.localdate()
    if accepte:
        p.statut, p.date_envoi, p.motif_refus = P.EN_ATTENTE, timezone.localdate(), ""
        texte = f"La prescription de {_usager(p)} vers « {p.action.libelle} » est validée par le pôle : elle est adressée au porteur."
    else:
        p.statut, p.motif_refus = P.REFUSEE, motif
        texte = f"La prescription de {_usager(p)} vers « {p.action.libelle} » est refusée par le pôle.\nMotif : {motif}"
    p.save()
    journal(p, user, "Validée par le pôle" if accepte else "Refusée par le pôle", motif)
    prevenir(user, [p.prescripteur], p, f"Prescription {p.numero} : {'validée' if accepte else 'refusée'}", texte,
             avec_usager=True)
    synchroniser_contrat(p)


# ---------------------------------------------------------------------- retour du porteur
ISSUES = {'': None, P.INTEGREE: (P.EN_ATTENTE,), P.NON_INTEGREE: (P.EN_ATTENTE,),
          P.TERMINEE: (P.INTEGREE,), P.ARRETEE: (P.INTEGREE,), P.REORIENTEE: (P.EN_ATTENTE, P.INTEGREE)}


@transaction.atomic
def noter_retour(p, user, *, issue="", premier_rdv_le=None, premier_rdv_issue="", diagnostic_finalise=False,
                 date_entree=None, motif_non_integration="", date_sortie=None, motif_sortie="", reorientation="",
                 reorientation_precision="", commentaire_porteur=""):
    if p.statut not in (P.EN_ATTENTE, P.INTEGREE):
        raise ErreurCircuit("Le retour du porteur se note sur une prescription adressée ou en cours.")
    if issue not in ISSUES:
        raise ErreurCircuit("Issue inconnue.")
    if issue and p.statut not in ISSUES[issue]:
        raise ErreurCircuit(f"Passage impossible : {p.get_statut_display().lower()} → {dict(P.STATUTS)[issue].lower()}.")
    if issue == P.INTEGREE and not date_entree:
        raise ErreurCircuit("Indiquez la date d'entrée dans l'action.")
    if issue == P.NON_INTEGREE and not motif_non_integration.strip():
        raise ErreurCircuit("Indiquez le motif de non-intégration.")
    if issue in (P.TERMINEE, P.ARRETEE, P.REORIENTEE) and not date_sortie:
        raise ErreurCircuit("Indiquez la date de sortie.")
    if issue == P.ARRETEE and not motif_sortie.strip():
        raise ErreurCircuit("Indiquez le motif de l'arrêt.")
    if issue == P.REORIENTEE and not reorientation:
        raise ErreurCircuit("Indiquez vers quoi la personne est réorientée.")
    p.premier_rdv_le, p.premier_rdv_issue = premier_rdv_le, premier_rdv_issue
    p.diagnostic_finalise, p.commentaire_porteur = diagnostic_finalise, commentaire_porteur
    if issue == P.INTEGREE or p.statut == P.INTEGREE:
        p.date_entree = date_entree or p.date_entree
    if issue == P.NON_INTEGREE:
        p.motif_non_integration = motif_non_integration
    if issue in (P.TERMINEE, P.ARRETEE, P.REORIENTEE):
        p.date_sortie, p.motif_sortie = date_sortie, motif_sortie
        if issue == P.REORIENTEE:
            p.reorientation, p.reorientation_precision = reorientation, reorientation_precision
    ancien = p.get_statut_display().lower()
    if issue:
        p.statut = issue
    p.save()
    journal(p, user, f"Retour du porteur : {p.get_statut_display().lower()}" if issue else "Retour du porteur noté",
            commentaire_porteur)
    if issue and p.prescripteur_id and p.prescripteur_id != user.pk:
        prevenir(user, [p.prescripteur], p, f"Prescription {p.numero} : {p.get_statut_display().lower()}",
                 f"Retour du porteur pour {_usager(p)} (« {p.action.libelle} ») : {ancien} → "
                 f"{p.get_statut_display().lower()}.", avec_usager=True)
    synchroniser_contrat(p)
