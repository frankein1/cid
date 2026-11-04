# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/services/contrat_circuit.py
"""
Circuit du contrat RSA, de la rédaction à la décision :

  En préparation ──(référent : transmettre)──▶ Transmis au pôle ──(administratif : réceptionner)──▶ Reçu
       ▲                                                                                          │
       └──────────── Ajourné ◀──(cadre : décision de la commission)───────────────────────────────┤
                                 Validé · Validé sauf action · Non validé ◀───────────────────────┘

Contrat santé d'une personne de moins de 60 ans (paramétrable) : le médecin traitant adresse un certificat
au médecin du pôle (sous pli cacheté ou par MSSanté). CID n'enregistre que les dates, l'avis (favorable ou
défavorable) et une motivation sans détail médical ; la commission ne décide qu'une fois l'avis donné.
Chaque étape est tracée (HistoriqueContrat) et prévient la personne qui doit agir ensuite (messagerie).
"""
from django.db import transaction
from django.utils import timezone

from insertion import acces
from insertion.models import ContratInsertion, HistoriqueContrat, LigneActionContrat, ParametresRSA

C = ContratInsertion


class ErreurCircuit(ValueError):
    pass


def nom(u):
    return (u.get_full_name() or u.username) if u else "-"


def journal(contrat, user, action, commentaire=""):
    return HistoriqueContrat.objects.create(contrat=contrat, user=user, action=action[:200], commentaire=commentaire)


# ---------------------------------------------------------------------- messages
def _envoyer(expediteur, destinataire, contrat, objet, contenu, avec_usager):
    from django.contrib.contenttypes.models import ContentType
    from messagerie.models import Message, StatutLecture
    msg = Message.objects.create(
        expediteur=expediteur, destinataire=destinataire,
        # Les agents du pôle n'ont pas accès au dossier social : pas de lien vers la fiche de l'usager
        beneficiaire=contrat.beneficiaire if avec_usager else None,
        objet=objet[:255], contenu=contenu + "\n\nMessage automatique de CID.", motif='suivi_dossier',
        priorite='normale', content_type=ContentType.objects.get_for_model(contrat), object_id=contrat.pk,
        reference=contrat.numero)
    StatutLecture.objects.create(message=msg, utilisateur=destinataire, type_reception='destinataire')


def prevenir(expediteur, destinataires, contrat, objet, contenu, avec_usager=False):
    vus = set()
    for d in destinataires:
        if d is None or not d.is_active or (expediteur and d.pk == expediteur.pk) or d.pk in vus:
            continue
        _envoyer(expediteur, d, contrat, objet, contenu, avec_usager)
        vus.add(d.pk)
    return vus


def agents_pole(contrat, capacite):
    if not contrat.pole_id:
        return []
    return [u for u in contrat.pole.membres.filter(is_active=True) if u.a_la_capacite(capacite)]


def _usager(contrat):
    b = contrat.beneficiaire
    return f"{b.prenom} {b.nom.upper()}"


# ---------------------------------------------------------------------- création
def _conjoint(beneficiaire):
    from beneficiaire.models import LienFamilial
    lien = (LienFamilial.objects.filter(personne_a=beneficiaire, type_lien='CONJOINT', date_fin__isnull=True)
            .select_related('personne_b').first())
    return lien.personne_b if lien else None


CHAMPS_REPRIS = [
    'nature', 'conjoint', 'conjoint_situation', 'conjoint_operateur', 'conjoint_referent', 'inscrit_france_travail',
    'identifiant_france_travail', 'niveau_etudes', 'formation', 'experience', 'dernier_emploi', 'dernier_emploi_annee',
    'dernier_emploi_duree', 'emploi_recherche', 'francais_parle', 'francais_lu', 'francais_ecrit', 'permis_b',
    'autres_permis', 'vehicule', 'couverture_base', 'couverture_complementaire', 'logement', 'logement_precision',
    'heures_activite_hebdo',
]


@transaction.atomic
def creer(beneficiaire, user, type_contrat=C.OUVERTURE, precedent=None):
    """Nouveau contrat prérempli : à partir du dossier (MDS, pôle, conjoint, identifiant France Travail) et,
    pour un prolongement ou un rétablissement, du contrat précédent (diagnostic et actions en cours)."""
    p = ParametresRSA.courant()
    c = C(beneficiaire=beneficiaire, mds=beneficiaire.mds, pole=acces.pole_de_mds(beneficiaire.mds),
          referent=user, type_contrat=type_contrat, precedent=precedent, date_etablissement=timezone.localdate(),
          duree_proposee_mois=p.duree_defaut_mois, heures_activite_hebdo=p.heures_hebdo_min,
          conjoint=_conjoint(beneficiaire), identifiant_france_travail=beneficiaire.numero_france_travail or "",
          inscrit_france_travail=bool(beneficiaire.numero_france_travail))
    if precedent:
        for champ in CHAMPS_REPRIS:
            setattr(c, champ, getattr(precedent, champ))
        c.parole_deja_fait = precedent.parole_souhaits
    c.save()
    if precedent:
        for l in precedent.lignes.filter(date_sortie__isnull=True, non_retenue=False):
            LigneActionContrat.objects.create(contrat=c, action=l.action, libelle=l.libelle, date_entree=l.date_entree)
    journal(c, user, f"Contrat créé ({c.get_type_contrat_display().lower()})",
            f"Suite du contrat {precedent.numero}" if precedent else "")
    return c


# ---------------------------------------------------------------------- référent
@transaction.atomic
def transmettre(contrat, user):
    if contrat.statut not in C.MODIFIABLES:
        raise ErreurCircuit("Ce contrat a déjà été transmis.")
    if not contrat.pole_id:
        contrat.pole = acces.pole_de_mds(contrat.mds)
    manques = contrat.manques_transmission()
    if manques:
        raise ErreurCircuit("Avant de transmettre, renseignez : " + ", ".join(manques) + ".")
    reprise = contrat.statut == C.AJOURNE
    contrat.statut, contrat.date_transmission = C.TRANSMIS, timezone.localdate()
    contrat.date_reception = contrat.recu_par = None
    contrat.decision, contrat.date_decision, contrat.decide_par = "", None, None
    contrat.save()
    journal(contrat, user, "Transmis au pôle insertion" + (" (après ajournement)" if reprise else ""))
    texte = (f"Le contrat {contrat.numero} de {_usager(contrat)} ({contrat.mds}) vient d'être transmis au pôle"
             f"{' après ajournement' if reprise else ''}. Merci de le réceptionner.")
    if contrat.certificat_obligatoire:
        texte += (f"\nContrat santé : certificat médical transmis "
                  f"{contrat.get_certificat_mode_display().lower()}.")
    prevenir(user, agents_pole(contrat, 'rsa_pole_admin'), contrat, f"Contrat {contrat.numero} à réceptionner", texte)


@transaction.atomic
def annuler(contrat, user, motif=""):
    if contrat.statut not in C.MODIFIABLES:
        raise ErreurCircuit("Seul un contrat en préparation ou ajourné peut être annulé.")
    contrat.statut = C.ANNULE
    contrat.save(update_fields=['statut', 'modifie_le'])
    journal(contrat, user, "Contrat annulé", motif)


# ---------------------------------------------------------------------- pôle : administratif
@transaction.atomic
def receptionner(contrat, user, le=None):
    if contrat.statut != C.TRANSMIS:
        raise ErreurCircuit("Seul un contrat transmis au pôle peut être réceptionné.")
    contrat.statut, contrat.date_reception, contrat.recu_par = C.RECU, le or timezone.localdate(), user
    contrat.save()
    journal(contrat, user, "Reçu au pôle insertion")
    texte = f"Le contrat {contrat.numero} de {_usager(contrat)} ({contrat.mds}) est reçu : il peut passer en commission."
    if contrat.attend_avis_medical:
        texte += "\nContrat santé : la commission attend l'avis du médecin du pôle."
        prevenir(user, agents_pole(contrat, 'rsa_pole_medecin'), contrat,
                 f"Contrat santé {contrat.numero} : avis attendu",
                 f"Le contrat santé {contrat.numero} de {_usager(contrat)} attend votre avis. Le certificat du médecin "
                 f"traitant est adressé {contrat.get_certificat_mode_display().lower()}.")
    prevenir(user, agents_pole(contrat, 'rsa_pole_cadre'), contrat, f"Contrat {contrat.numero} à présenter en commission",
             texte)


# ---------------------------------------------------------------------- pôle : médecin
@transaction.atomic
def donner_avis(contrat, user, *, certificat_recu_le, avis, motivation):
    if contrat.statut not in (C.TRANSMIS, C.RECU):
        raise ErreurCircuit("L'avis se donne sur un contrat transmis au pôle, avant la commission.")
    if avis not in dict(C.AVIS):
        raise ErreurCircuit("Choisissez un avis favorable ou défavorable.")
    if avis == 'DEFAVORABLE' and not motivation.strip():
        raise ErreurCircuit("Un avis défavorable est motivé (sans détail médical).")
    contrat.certificat_recu_le, contrat.avis_medical, contrat.avis_motivation = certificat_recu_le, avis, motivation
    contrat.avis_le, contrat.avis_par = timezone.localdate(), user
    contrat.save()
    journal(contrat, user, f"Avis du médecin du pôle : {contrat.get_avis_medical_display().lower()}")
    texte = (f"Avis du médecin du pôle sur le contrat santé {contrat.numero} de {_usager(contrat)} : "
             f"{contrat.get_avis_medical_display().lower()}." + (f"\nMotivation : {motivation}" if motivation else ""))
    prevenir(user, agents_pole(contrat, 'rsa_pole_cadre'), contrat, f"Contrat {contrat.numero} : avis médical donné", texte)


# ---------------------------------------------------------------------- pôle : cadre (commission)
@transaction.atomic
def decider(contrat, user, *, decision, date_decision, date_debut=None, duree_mois=None, motif="",
            decision_transport="", motif_transport="", commentaire="", non_retenues=None):
    """non_retenues : {ligne_pk: motif} des actions non retenues (décision « validé sauf action »)."""
    p = ParametresRSA.courant()
    if contrat.statut not in (C.TRANSMIS, C.RECU):
        raise ErreurCircuit("La commission décide sur un contrat transmis au pôle.")
    if decision not in dict(C.DECISIONS):
        raise ErreurCircuit("Choisissez une décision.")
    if decision in (C.VALIDE, C.VALIDE_SAUF_ACTION) and contrat.attend_avis_medical:
        raise ErreurCircuit("Contrat santé : la commission attend l'avis du médecin du pôle.")
    non_retenues = {int(k): (v or "").strip() for k, v in (non_retenues or {}).items()}
    if decision == C.VALIDE_SAUF_ACTION:
        if not non_retenues:
            raise ErreurCircuit("« Validé sauf action » : cochez l'action non retenue.")
        if not all(non_retenues.values()):
            raise ErreurCircuit("Indiquez le motif de chaque action non retenue.")
        duree_mois = p.duree_sauf_action_mois
    if decision in (C.VALIDE, C.VALIDE_SAUF_ACTION):
        if not date_debut:
            raise ErreurCircuit("Indiquez la date de début du contrat.")
        if not duree_mois or duree_mois < 1 or duree_mois > p.duree_max_mois:
            raise ErreurCircuit(f"La durée validée va de 1 à {p.duree_max_mois} mois.")
        contrat.date_debut, contrat.duree_validee_mois = date_debut, duree_mois
        contrat.date_fin = contrat.date_fin_pour(date_debut, duree_mois)
    else:
        if not motif.strip():
            raise ErreurCircuit("Indiquez le motif de l'ajournement ou de la non-validation.")
        contrat.date_debut = contrat.date_fin = contrat.duree_validee_mois = None
    if decision_transport == 'NON' and motif_transport not in ('DUREE_MAX', 'CONDITIONS'):
        raise ErreurCircuit("Indiquez le motif du refus de l'aide aux transports.")
    for ligne in contrat.lignes.all():
        motif_ligne = non_retenues.get(ligne.pk) if decision == C.VALIDE_SAUF_ACTION else None
        ligne.non_retenue, ligne.motif_non_retenue = bool(motif_ligne), motif_ligne or ""
        ligne.save(update_fields=['non_retenue', 'motif_non_retenue'])
    if not contrat.date_reception:
        contrat.date_reception, contrat.recu_par = date_decision, user
    contrat.statut = contrat.decision = decision
    contrat.date_decision, contrat.decide_par = date_decision, user
    contrat.motif_decision, contrat.commentaire_commission = motif, commentaire
    contrat.decision_transport = decision_transport
    contrat.motif_transport = motif_transport if decision_transport else ""
    contrat.save()
    libelle = contrat.get_decision_display()
    journal(contrat, user, f"Décision de la commission : {libelle.lower()}", motif)
    texte = f"Décision de la commission du {date_decision:%d/%m/%Y} sur le contrat {contrat.numero} de {_usager(contrat)} : {libelle.lower()}."
    if contrat.date_fin:
        texte += f"\nContrat en vigueur du {contrat.date_debut:%d/%m/%Y} au {contrat.date_fin:%d/%m/%Y}."
    if decision == C.VALIDE_SAUF_ACTION:
        texte += "\nAction(s) non retenue(s) : " + "; ".join(
            f"{l.intitule} ({l.motif_non_retenue})" for l in contrat.lignes.filter(non_retenue=True)) + "."
    if motif:
        texte += f"\nMotif : {motif}"
    if decision == C.AJOURNE:
        texte += "\nLe contrat est de nouveau modifiable : reprenez-le puis transmettez-le de nouveau."
    prevenir(user, [contrat.referent], contrat, f"Contrat {contrat.numero} : {libelle.lower()}", texte, avec_usager=True)
