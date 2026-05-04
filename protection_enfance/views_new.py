# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# VUES TABLEAU DE BORD
@login_required
def dashboard_ase(request):
    """Tableau de bord ASE"""
    return render(request, 'protection_enfance/dashboard/ase.html')

@login_required
def dashboard_crip(request):
    """Tableau de bord CRIP"""
    return render(request, 'protection_enfance/dashboard/crip.html')

# VUES INFORMATIONS PRÉOCCUPANTES
@login_required
def ip_liste(request):
    """Liste des Informations Préoccupantes"""
    return render(request, 'protection_enfance/informations_preoccupantes/liste.html')

@login_required
def ip_creation(request):
    """Création d'une IP"""
    return render(request, 'protection_enfance/informations_preoccupantes/creation.html')

@login_required
def ip_detail(request, ip_id):
    """Détail d'une IP"""
    return render(request, 'protection_enfance/informations_preoccupantes/detail.html')

# VUES PLACEMENTS
@login_required
def placements_liste(request):
    """Liste des placements"""
    return render(request, 'protection_enfance/placements/liste.html')

@login_required
def placement_detail(request, placement_id):
    """Détail d'un placement"""
    return render(request, 'protection_enfance/placements/detail.html')
