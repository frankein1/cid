# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# core/views/profile.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from core.forms import UserProfileForm
try:
    from mds.models import UserMDSProfile
except ImportError:
    UserMDSProfile = None

@login_required
def mon_profil(request):
    """Page affichant et permettant de modifier le profil de l'utilisateur connecté."""
    utilisateur = request.user
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=utilisateur)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Votre profil a été mis à jour avec succès.")
                return redirect('core:mon_profil')
            except IntegrityError as e:
                messages.error(request, f"Erreur lors de la sauvegarde : {e}")
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = UserProfileForm(instance=utilisateur)

    context = {
        'utilisateur': utilisateur,
        'title': 'Mon profil',
        'form': form,
    }
    return render(request, 'core/mon_profil.html', context)
