# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# ru/rendez_vous.py
"""Rendez-vous RU posé dans l'agenda : le courrier de convocation ne part que s'il est lié à un rendez-vous.
Le lieu du courrier est le mémo du rendez-vous (MDS par défaut) ; la salle choisie est réservée."""
from datetime import datetime, timedelta

from planning.agenda import dans_heures_ouverture, salle_occupee
from planning.forms import memo_mds
from planning.models import CreneauRdv

DUREE_RDV_RU_MINUTES = 40


def poser_rdv_ru(demande, rang, user, salle=None):
    """Crée ou met à jour le rendez-vous de la demande pour le rang donné (1 ou 2). Lève ValueError si l'horaire
    n'est pas saisi par pas de 10 minutes ou si la salle est déjà réservée."""
    date_rdv = demande.date_premier_rendez_vous if rang == 1 else demande.date_second_rendez_vous
    heure = demande.heure_premier_rendez_vous if rang == 1 else demande.heure_second_rendez_vous
    lien = 'creneau_premier_rdv' if rang == 1 else 'creneau_second_rdv'
    if not date_rdv or not heure:
        raise ValueError("Renseignez la date et l'heure du rendez-vous avant de poser le rendez-vous.")
    if isinstance(heure, str):
        heure = datetime.strptime(heure.strip(), "%H:%M").time()
    if heure.minute % 10:
        raise ValueError("Les horaires se posent par pas de 10 minutes.")
    debut = heure
    fin = (datetime.combine(date_rdv, heure) + timedelta(minutes=DUREE_RDV_RU_MINUTES)).time()
    if salle is not None and salle_occupee(salle, date_rdv, debut, fin, 'HORS_PERMANENCE',
                                           exclure_id=getattr(getattr(demande, lien), 'pk', None)):
        raise ValueError(f"{salle.nom} est réservée sur cet horaire : choisissez une autre salle ou un autre "
                         f"horaire. Le courrier n'est pas parti.")
    rdv = getattr(demande, lien) or CreneauRdv(cree_par=user, reserve_par=user)
    rdv.date, rdv.heure_debut, rdv.heure_fin = date_rdv, debut, fin
    rdv.duree_minutes = DUREE_RDV_RU_MINUTES
    rdv.mds, rdv.salle, rdv.agent = demande.mds, salle, demande.agent_assigne or user
    rdv.nature, rdv.domaine, rdv.type_rdv = 'HORS_PERMANENCE', 'SOCIAL', 'HORS_PERMANENCE'
    rdv.modalite = 'MDS'
    rdv.lieu_precis = memo_mds(demande.mds, salle)[:200]
    if not dans_heures_ouverture(debut, fin):
        raise ValueError("À la MDS, les rendez-vous se prennent aux heures d'ouverture (9 h - 12 h, 13 h 30 - 17 h).")
    rdv.statut = 'RESERVE'
    rdv.description = f"Relation usager – 1er rendez-vous ({demande.reference})" if rang == 1 \
        else f"Relation usager – 2e rendez-vous ({demande.reference})"
    rdv.save()
    setattr(demande, lien, rdv)
    demande.save(update_fields=[lien])
    return rdv
