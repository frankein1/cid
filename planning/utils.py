# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

"""
planning/utils.py
Utilitaires pour la gestion des créneaux de rendez-vous
VERSION CORRIGÉE - Plus d'erreur usermdsprofile
"""

from datetime import datetime, timedelta, time, date
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import CreneauRdv, JourBloque
from mds.models import DemiJourneeReception, MDSReception, UserMDSProfile

User = get_user_model()

# =============================================================================
# CONSTANTES GLOBALES
# =============================================================================
HEURE_DEBUT_MATIN = time(9, 0)
HEURE_FIN_MATIN = time(12, 0)
HEURE_DEBUT_APRES_MIDI = time(13, 30)
HEURE_FIN_APRES_MIDI = time(17, 0)
DUREE_CRENEAU_MINUTES = 30

DERNIER_DEBUT_AUTORISE = (
    HEURE_FIN_APRES_MIDI.hour * 60 + HEURE_FIN_APRES_MIDI.minute
) - DUREE_CRENEAU_MINUTES


# =============================================================================
# 1. FONCTIONS DE VÉRIFICATION
# =============================================================================

def salle_est_disponible(salle, date_obj):
    if JourBloque.objects.filter(date=date_obj, salle=salle).exists():
        return False
    if JourBloque.objects.filter(date=date_obj, salle__isnull=True).exists():
        return False
    return True


def agent_est_disponible(agent, date_obj, heure_debut, heure_fin):
    if JourBloque.objects.filter(date=date_obj, agent=agent).exists():
        return False
    if CreneauRdv.objects.filter(
        agent=agent,
        date=date_obj,
        heure_debut__lt=heure_fin,
        heure_fin__gt=heure_debut
    ).exists():
        return False
    return True


# =============================================================================
# 2. GÉNÉRATION DE CRÉNEAUX
# =============================================================================

def generer_creneaux_agent_demi_journee(
    date_obj, salle, agent, heure_debut, heure_fin, type_rdv
):
    creneaux_crees = []

    if heure_debut < HEURE_DEBUT_MATIN:
        heure_debut = HEURE_DEBUT_MATIN

    if heure_fin > HEURE_FIN_MATIN and heure_debut < HEURE_FIN_MATIN:
        heure_fin = HEURE_FIN_MATIN

    if heure_debut >= time(12, 0) and heure_debut < HEURE_DEBUT_APRES_MIDI:
        heure_debut = HEURE_DEBUT_APRES_MIDI

    if heure_fin > HEURE_FIN_APRES_MIDI:
        heure_fin = HEURE_FIN_APRES_MIDI

    debut_minutes = heure_debut.hour * 60 + heure_debut.minute
    fin_minutes = heure_fin.hour * 60 + heure_fin.minute

    if fin_minutes <= debut_minutes:
        return creneaux_crees

    for minute_depart in range(debut_minutes, fin_minutes, DUREE_CRENEAU_MINUTES):

        if minute_depart > DERNIER_DEBUT_AUTORISE:
            continue

        minute_fin = minute_depart + DUREE_CRENEAU_MINUTES

        h_debut = time(minute_depart // 60, minute_depart % 60)
        h_fin = time(minute_fin // 60, minute_fin % 60)

        if CreneauRdv.objects.filter(
            date=date_obj,
            salle=salle,
            agent=agent,
            heure_debut=h_debut
        ).exists():
            continue

        creneau = CreneauRdv.objects.create(
            date=date_obj,
            heure_debut=h_debut,
            heure_fin=h_fin,
            salle=salle,
            agent=agent,
            type_rdv=type_rdv,
            statut='DISPONIBLE',
            description="Créneau généré automatiquement"
        )
        creneaux_crees.append(creneau)

    return creneaux_crees


def generer_creneaux_depuis_permanences_externes(date_debut, date_fin, mds):
    """Génère les créneaux pour les permanences externes actives de la MDS"""
    from .models import PermanenceExterne
    creneaux_crees = []
    
    perms = PermanenceExterne.objects.filter(
        actif=True,
        salle__mds_origine=mds,
        date_debut__lte=date_fin
    ).filter(
        Q(date_fin__isnull=True) | Q(date_fin__gte=date_debut)
    )
    
    for perm in perms:
        current_date = date_debut
        while current_date <= date_fin:
            if perm.recurrence == 'HEBDO' and current_date.weekday() == perm.jour_semaine:
                pass
            elif perm.recurrence == 'MENSUEL':
                semaine_num = (current_date.day - 1) // 7 + 1
                if semaine_num != 1:
                    current_date += timedelta(days=1)
                    continue
                if current_date.weekday() != perm.jour_semaine:
                    current_date += timedelta(days=1)
                    continue
            else:
                current_date += timedelta(days=1)
                continue
            
            creneau = CreneauRdv.objects.create(
                date=current_date,
                heure_debut=perm.heure_debut,
                heure_fin=perm.heure_fin,
                salle=perm.salle,
                agent=perm.agent,
                type_rdv='PERMANENCE',
                statut='DISPONIBLE',
                description=f"Permanence externe : {perm.salle.nom}"
            )
            creneaux_crees.append(creneau)
            current_date += timedelta(days=1)
    
    return creneaux_crees


def generer_creneaux_permanences(
    date_debut, nombre_semaines, mds, type_rdv='PERMANENCE'
):
    creneaux_crees = []
    salles = MDSReception.objects.filter(mds=mds, actif=True)

    # ✅ Récupération des IDs des agents de la MDS (une seule fois)
    ids_agents_mds = UserMDSProfile.objects.filter(
        mds=mds, actif=True
    ).values_list('user_id', flat=True)

    for i in range(nombre_semaines * 7):
        current_date = date_debut + timedelta(days=i)

        if current_date.weekday() >= 5:
            continue

        if JourBloque.objects.filter(date=current_date, salle__isnull=True).exists():
            continue

        if est_jour_ferie(current_date):
            continue

        demi_journees = [
            {'heure_debut': HEURE_DEBUT_MATIN, 'heure_fin': HEURE_FIN_MATIN},
            {'heure_debut': HEURE_DEBUT_APRES_MIDI, 'heure_fin': HEURE_FIN_APRES_MIDI},
        ]

        dj_perso = DemiJourneeReception.objects.filter(
            mds=mds,
            jour_semaine=current_date.weekday(),
            actif=True
        )

        if dj_perso.exists():
            demi_journees = [
                {
                    'heure_debut': d.heure_debut,
                    'heure_fin': d.heure_fin,
                    'agent': d.agent
                }
                for d in dj_perso
            ]

        for salle in salles:
            if not salle_est_disponible(salle, current_date):
                continue

            dispo = [
                salle.disponible_lundi,
                salle.disponible_mardi,
                salle.disponible_mercredi,
                salle.disponible_jeudi,
                salle.disponible_vendredi
            ]
            if not dispo[current_date.weekday()]:
                continue

            for dj in demi_journees:
                if dj.get('agent'):
                    agents = [dj['agent']]
                else:
                    # ✅ FILTRAGE CORRECT : on utilise les IDs des agents de la MDS
                    agents = User.objects.filter(
                        id__in=ids_agents_mds,
                        is_active=True,
                        profils__capacites__code='peut_creer'
                    ).distinct()

                for agent in agents:
                    if agent_est_disponible(
                        agent,
                        current_date,
                        dj['heure_debut'],
                        dj['heure_fin']
                    ):
                        creneaux_crees.extend(
                            generer_creneaux_agent_demi_journee(
                                current_date,
                                salle,
                                agent,
                                dj['heure_debut'],
                                dj['heure_fin'],
                                type_rdv
                            )
                        )

    return creneaux_crees


# =============================================================================
# 3. JOURS FÉRIÉS
# =============================================================================

def est_jour_ferie(date_val):
    if not isinstance(date_val, date):
        date_val = date_val.date()

    fixes = {
        (1, 1), (1, 5), (8, 5), (14, 7),
        (15, 8), (1, 11), (11, 11), (25, 12)
    }
    if (date_val.month, date_val.day) in fixes:
        return True

    y = date_val.year
    a = y % 19
    b = y // 100
    c = y % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mois = (h + l - 7 * m + 114) // 31
    jour = ((h + l - 7 * m + 114) % 31) + 1
    paques = date(y, mois, jour)

    return date_val in {
        paques + timedelta(days=1),
        paques + timedelta(days=39),
        paques + timedelta(days=50)
    }
