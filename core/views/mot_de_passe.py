# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/views/mot_de_passe.py
"""Mot de passe oublié, réinitialisation par l'administration, changement (obligatoire après réinitialisation)."""
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core import mot_de_passe as mdp


def mot_de_passe_oublie(request):
    """Page publique. La réponse est la même que le compte existe ou non (pas d'indice sur les identifiants)."""
    envoye = False
    if request.method == "POST":
        identifiant = (request.POST.get("identifiant") or "").strip()
        user = get_user_model().objects.filter(username__iexact=identifiant, is_active=True).first() if identifiant else None
        if user:
            mdp.signaler_oubli(user)
        envoye = bool(identifiant)
    return render(request, "core/mdp_oublie.html", {"envoye": envoye})


@login_required
def reinitialiser_mot_de_passe(request, user_id):
    cible = get_object_or_404(get_user_model(), pk=user_id)
    if not mdp.peut_reinitialiser(request.user, cible):
        return HttpResponseForbidden("Réinitialisation réservée au super-administrateur et au gestionnaire des accès.")
    provisoire = None
    if request.method == "POST":
        provisoire = mdp.reinitialiser(cible)
        messages.success(request, f"Mot de passe de {cible.get_full_name() or cible.username} réinitialisé.")
    return render(request, "core/mdp_reinitialiser.html", {
        "cible": cible, "provisoire": provisoire, "exemple": mdp.mot_de_passe_provisoire(cible)})


@login_required
def changer_mot_de_passe(request):
    force = request.user.force_change_password
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            user.force_change_password = False
            user.date_dernier_changement_mdp = timezone.localdate()
            user.save(update_fields=["force_change_password", "date_dernier_changement_mdp"])
            update_session_auth_hash(request, user)
            messages.success(request, "Votre mot de passe a été changé.")
            return redirect("/")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "core/mdp_changer.html", {"form": form, "force": force})
