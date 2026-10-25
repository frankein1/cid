# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/services/afase_circuit.py
"""
Circuit du paiement d'une AFASE accordée :

  cadre (ou secrétariat) ──► SERVICE DE CONTRÔLE ──► logiciel comptable (service finances) ──► paierie
  « transmettre »            « paiement demandé »                                      « payé » → clôture

- La transmission est BLOQUÉE tant que le dossier est incomplet (évite les allers-retours) :
  identité(s), livret de famille, RIB du destinataire du paiement, facture ou devis.
- Le service de contrôle voit le dossier complet (pièces comprises) ; les finances ne reçoivent,
  via le logiciel comptable, que le nom, le RIB et la somme : rien n'en passe par CID.
- Le contrôle peut renvoyer le dossier à la MDS avec un motif.
- Chaque étape prévient le suivant par message CID ; le paiement prévient l'AS et le cadre.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from AidFi.models.m_generique import PIECES_REQUISES_AFASE, PieceJustificative

STATUTS_CONTROLE = ('TRANSMISE_CONTROLE', 'PAIEMENT_DEMANDE', 'CLOTUREE')


class CircuitErreur(Exception):
    pass


# -----------------------------------------------------------------------------
# Droits
# -----------------------------------------------------------------------------

def est_controle(user):
    return user.is_authenticated and user.a_la_capacite('afase_controle')


def controle_peut_voir(user, demande):
    """Le service de contrôle voit les dossiers qui lui ont été transmis (toutes MDS)."""
    decision = getattr(demande, 'decision', None)
    return (est_controle(user) and demande.statut in STATUTS_CONTROLE
            and decision is not None and decision.date_transmission_controle is not None)


def peut_transmettre(user, demande):
    decision = getattr(demande, 'decision', None)
    if demande.statut != 'ACCORDEE' or not decision or decision.type_decision != 'ACCORD':
        return False
    return any(user.peut_agir_sur_objet(demande, cap) for cap in ('peut_decider', 'peut_valider_cheque_aidfi'))


# -----------------------------------------------------------------------------
# Complétude du dossier
# -----------------------------------------------------------------------------

def etat_pieces(demande):
    """[(code, libellé, nombre de pièces jointes)] pour les pièces exigées."""
    pieces = PieceJustificative.objects.filter(demande_id=demande.pk, document_ged__isnull=False)
    return [(code, libelle, pieces.filter(type_piece=code).count()) for code, libelle in PIECES_REQUISES_AFASE]


def pieces_manquantes(demande):
    return [libelle for code, libelle, n in etat_pieces(demande) if n == 0]


# -----------------------------------------------------------------------------
# Messages
# -----------------------------------------------------------------------------

def _agent_depot(demande):
    from AidFi.models.m_generique import SuiviDemande
    depot = SuiviDemande.objects.filter(demande_id=demande.pk, statut_nouveau="DEPOSEE").order_by('-id').first()
    return (depot.agent if depot and depot.agent else None) or demande.cree_par


def _prevenir(expediteur, destinataires, demande, objet, texte):
    from AidFi.signals import _envoyer
    for d in {u for u in destinataires if u and u.pk != expediteur.pk}:
        _envoyer(expediteur, d, demande, objet=objet, contenu=texte + "\n\nMessage automatique de CID.",
                 motif='suivi_dossier', priorite='importante')


def _titre(demande):
    b = demande.beneficiaire
    return f"{b.prenom} {b.nom.upper()} (dossier {demande.pk})"


# -----------------------------------------------------------------------------
# Étapes
# -----------------------------------------------------------------------------

@transaction.atomic
def transmettre(demande, user, paiement_a, organisme, identites_confirmees):
    from core.models import User
    if not peut_transmettre(user, demande):
        raise CircuitErreur("Ce dossier ne peut pas être transmis.")
    manque = pieces_manquantes(demande)
    if manque:
        raise CircuitErreur("Dossier incomplet : " + " ; ".join(manque) + ".")
    if not identites_confirmees:
        raise CircuitErreur("Confirmez que les pièces d'identité de toutes les personnes concernées sont jointes.")
    if paiement_a not in ('FAMILLE', 'ORGANISME'):
        raise CircuitErreur("Indiquez à qui le paiement doit être fait.")
    if paiement_a == 'ORGANISME' and not organisme.strip():
        raise CircuitErreur("Indiquez l'organisme qui recevra le paiement.")
    d = demande.decision
    d.paiement_a, d.organisme_paiement = paiement_a, organisme.strip() if paiement_a == 'ORGANISME' else ""
    d.date_transmission_controle, d.transmis_par, d.motif_renvoi = timezone.now(), user, ""
    d.save(update_fields=['paiement_a', 'organisme_paiement', 'date_transmission_controle', 'transmis_par',
                          'motif_renvoi'])
    demande.statut, demande._acteur = 'TRANSMISE_CONTROLE', user
    demande.save(update_fields=['statut'])
    controleurs = User.objects.filter(is_active=True, profils__code='SERVICE_CONTROLE_AFASE',
                                      profils__actif=True).distinct()
    _prevenir(user, controleurs, demande, f"AFASE à contrôler : {_titre(demande)}",
              f"La MDS {demande.mds} transmet l'AFASE n° {demande.pk} accordée pour "
              f"{d.montant_accorde} € (paiement à : {d.get_paiement_a_display()}"
              f"{' – ' + d.organisme_paiement if d.organisme_paiement else ''}).\n"
              f"Le dossier est complet. Transmis par {user.get_full_name() or user.username}.")


@transaction.atomic
def demander_paiement(demande, user, date, reference):
    if not est_controle(user) or demande.statut != 'TRANSMISE_CONTROLE':
        raise CircuitErreur("Action réservée au service de contrôle, sur un dossier transmis.")
    d = demande.decision
    d.date_demande_paiement = date or timezone.localdate()
    d.reference_comptable, d.controle_par = (reference or "").strip()[:60], user
    d.save(update_fields=['date_demande_paiement', 'reference_comptable', 'controle_par'])
    demande.statut, demande._acteur = 'PAIEMENT_DEMANDE', user
    demande.save(update_fields=['statut'])


@transaction.atomic
def enregistrer_paiement(demande, user, date, montant):
    if not est_controle(user) or demande.statut != 'PAIEMENT_DEMANDE':
        raise CircuitErreur("Action réservée au service de contrôle, après la demande de paiement.")
    d = demande.decision
    d.date_delivrance = date or timezone.localdate()
    d.montant_delivre = montant if montant is not None else d.montant_accorde
    if d.montant_delivre < 0 or d.montant_delivre > d.montant_accorde:
        raise CircuitErreur("Le montant payé doit être compris entre 0 et le montant accordé.")
    d.save(update_fields=['date_delivrance', 'montant_delivre'])
    demande.statut, demande._acteur = 'CLOTUREE', user
    demande.save(update_fields=['statut'])
    partiel = d.montant_delivre < d.montant_accorde
    _prevenir(user, [_agent_depot(demande), d.decide_par, d.transmis_par], demande,
              f"AFASE payée : {_titre(demande)}",
              f"L'AFASE n° {demande.pk} a été payée le {d.date_delivrance:%d/%m/%Y} : {d.montant_delivre} €"
              f"{' (paiement partiel, accordé : ' + str(d.montant_accorde) + ' €)' if partiel else ''}"
              f" à {d.get_paiement_a_display().lower()}{' – ' + d.organisme_paiement if d.organisme_paiement else ''}.\n"
              f"Le dossier est clôturé.")


@transaction.atomic
def renvoyer(demande, user, motif):
    if not est_controle(user) or demande.statut != 'TRANSMISE_CONTROLE':
        raise CircuitErreur("Seul un dossier en attente de contrôle peut être renvoyé.")
    if not (motif or "").strip():
        raise CircuitErreur("Indiquez le motif du renvoi.")
    d = demande.decision
    d.motif_renvoi, d.date_transmission_controle, d.controle_par = motif.strip(), None, user
    d.save(update_fields=['motif_renvoi', 'date_transmission_controle', 'controle_par'])
    demande.statut, demande._acteur = 'ACCORDEE', user
    demande.save(update_fields=['statut'])
    _prevenir(user, [d.transmis_par, d.decide_par, _agent_depot(demande)], demande,
              f"AFASE renvoyée par le contrôle : {_titre(demande)}",
              f"Le service de contrôle renvoie l'AFASE n° {demande.pk} à la MDS.\nMotif : {motif.strip()}\n"
              f"Complétez le dossier puis transmettez-le à nouveau.")


def lire_montant(texte):
    texte = (texte or "").replace(",", ".").replace("€", "").strip()
    return Decimal(texte) if texte else None
