# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/acces.py
"""
Droits du module RSA – Insertion (un seul endroit, pour les vues comme pour l'import CSV).

Capacités : rsa_referentiel (actions départementales), rsa_actions_locales (actions de sa MDS),
rsa_pole_admin, rsa_pole_cadre, rsa_pole_medecin (agents d'un pôle insertion, module RSA uniquement).
"""
from django.db.models import Q

CAPACITES_POLE = ('rsa_pole_admin', 'rsa_pole_cadre', 'rsa_pole_medecin')


def est_agent_pole(user):
    return any(user.a_la_capacite(c) for c in CAPACITES_POLE)


def peut_voir_module(user):
    return user.is_authenticated and (user.a_la_capacite('peut_voir') or est_agent_pole(user)
                                      or user.a_la_capacite('rsa_referentiel'))


def peut_gerer_departemental(user):
    return user.a_la_capacite('rsa_referentiel')


def mds_gerables(user):
    """MDS dont l'utilisateur peut gérer les actions locales."""
    from mds.models import MDS
    if user.a_la_capacite('peut_administrer'):
        return MDS.objects.all()
    if not user.a_la_capacite('rsa_actions_locales'):
        return MDS.objects.none()
    return MDS.objects.filter(profils_utilisateurs__user=user, profils_utilisateurs__actif=True).distinct()


def peut_gerer(user, action):
    if action.niveau == action.DEPARTEMENTAL:
        return peut_gerer_departemental(user)
    return action.mds_id is not None and mds_gerables(user).filter(pk=action.mds_id).exists()


def mds_visibles_ids(user):
    """MDS dont l'utilisateur voit les actions locales : les siennes, et celles de ses pôles insertion."""
    from mds.models import MDS
    if user.a_la_capacite('peut_administrer') or user.a_la_capacite('rsa_referentiel'):
        return None   # toutes
    return set(MDS.objects.filter(Q(profils_utilisateurs__user=user, profils_utilisateurs__actif=True)
                                  | Q(poles_insertion__membres=user)).values_list('pk', flat=True))


def actions_visibles(user):
    from insertion.models import ActionInsertion
    qs = ActionInsertion.objects.select_related('type_action', 'mds').prefetch_related('poles')
    ids = mds_visibles_ids(user)
    if ids is None:
        return qs
    return qs.filter(Q(niveau=ActionInsertion.DEPARTEMENTAL) | Q(mds_id__in=ids))
