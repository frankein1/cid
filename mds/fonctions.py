# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

# mds/fonctions.py

"""Fonction d'un agent telle qu'elle s'écrit sous sa signature (« Directrice de la MDS de territoire … »).

Elle est saisie une fois, sur le rattachement de l'agent à sa MDS (gestion des agents de la MDS), et reprise dans
les courriers et PDF. Rien n'est affiché quand elle n'est pas renseignée."""

from .models import UserMDSProfile


def fonction_de(user, mds=None):
    if not user:
        return ""
    profils = UserMDSProfile.objects.filter(user=user, actif=True).select_related('mds', 'herite_de__mds')
    p = None
    if mds is not None:
        p = profils.filter(mds=mds).first()
    if p is None or not p.intitule:
        p = profils.filter(principale=True).first() or p
    return p.intitule if p else ""


def nom_et_fonction(user, mds=None, separateur=" – "):
    if not user:
        return "-"
    nom = user.get_full_name() or user.username
    f = fonction_de(user, mds)
    return f"{nom}{separateur}{f}" if f else nom
