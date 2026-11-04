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


# =============================================================================
# Contrats
# =============================================================================
# Référent (agent de la MDS du bénéficiaire, capacité peut_creer) : rédige, signe, transmet, renouvelle.
# Pôle insertion (contrats des MDS de son pôle) : l'administratif réceptionne, le médecin donne son avis sur les
# contrats santé, le cadre décide en commission. Les agents du pôle ne voient pas le reste du dossier social.

def poles_de(user):
    from insertion.models import PoleInsertion
    return PoleInsertion.objects.filter(membres=user, actif=True)


def pole_de_mds(mds):
    from insertion.models import PoleInsertion
    return PoleInsertion.objects.filter(mds=mds, actif=True).order_by('code').first() if mds else None


def contrats_visibles(user):
    from insertion.models import ContratInsertion
    from mds.models import UserMDSProfile
    qs = ContratInsertion.objects.select_related('beneficiaire', 'mds', 'pole', 'referent')
    if user.a_la_capacite('peut_administrer'):
        return qs
    filtre = Q(pk__in=[])
    if user.a_la_capacite('peut_voir'):
        filtre |= Q(mds_id__in=UserMDSProfile.objects.filter(user=user, actif=True).values('mds_id'))
    if est_agent_pole(user):
        filtre |= Q(pole__in=poles_de(user))
    return qs.filter(filtre)


def peut_rediger(user, beneficiaire):
    """Créer ou reprendre un contrat : agent de la MDS du bénéficiaire qui peut créer des dossiers."""
    return beneficiaire.peut_etre_modifie_par(user)


def _du_pole(user, contrat, capacite):
    if user.is_superuser:
        return True
    return (user.a_la_capacite(capacite) and contrat.pole_id is not None
            and poles_de(user).filter(pk=contrat.pole_id).exists())


def est_admin_pole(user, contrat):
    return _du_pole(user, contrat, 'rsa_pole_admin')


def est_cadre_pole(user, contrat):
    return _du_pole(user, contrat, 'rsa_pole_cadre')


def est_medecin_pole(user, contrat):
    return _du_pole(user, contrat, 'rsa_pole_medecin')
