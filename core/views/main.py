# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

# core/views/main.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
try:
    from mds.models import UserMDSProfile
except ImportError:
    UserMDSProfile = None

User = get_user_model()

@login_required
def dashboard(request):
    """Page d'accueil du système : tableau de bord simple."""
    total_utilisateurs = User.objects.filter(is_active=True).count()
    context = {
        'title': 'Tableau de bord',
        'total_utilisateurs': total_utilisateurs,
        'service_actif': getattr(request, 'service_actif', None),
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def parametres(request):
    """Page contenant les paramètres utilisateur."""
    context = {'title': 'Paramètres utilisateur'}
    return render(request, 'core/parametres.html', context)


def accueil(request):
    """
    Page d'accueil. L'« Aperçu du système » n'est affiché qu'aux agents connectés, limité à leurs MDS
    (toutes les MDS pour l'administration).
    """
    stats = None
    if request.user.is_authenticated:
        from django.utils import timezone
        from beneficiaire.models import Beneficiaire
        from mds.models import MDS
        from planning.models import CreneauRdv
        user = request.user
        tout = user.is_superuser or user.a_la_capacite('peut_administrer')
        mds_ids = None if tout else list(UserMDSProfile.objects.filter(user=user, actif=True).values_list('mds_id', flat=True))
        benefs = Beneficiaire.objects.filter(statut='ACTIF')
        rdv = CreneauRdv.objects.filter(date=timezone.localdate(), beneficiaire__isnull=False).exclude(
            statut__in=('ANNULE_USAGER', 'ANNULE_MDS', 'DISPONIBLE'))
        agents = User.objects.filter(is_active=True)
        if mds_ids is not None:
            benefs = benefs.filter(mds_id__in=mds_ids)
            rdv = rdv.filter(mds_id__in=mds_ids)
            agents = agents.filter(profils_mds__mds_id__in=mds_ids, profils_mds__actif=True).distinct()
        stats = {
            'perimetre': "toutes les MDS" if tout else ("ma MDS" if len(mds_ids) == 1 else "mes MDS"),
            'total_beneficiaires': benefs.count(),
            'total_mds': MDS.objects.filter(active=True).count() if tout else len(mds_ids),
            'rdv_aujourdhui': rdv.count(),
            'utilisateurs_actifs': agents.count(),
        }
    return render(request, 'accueil.html', {'stats': stats})
