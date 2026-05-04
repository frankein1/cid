# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
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
