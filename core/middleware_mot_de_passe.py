# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/middleware_mot_de_passe.py
"""Après une réinitialisation, l'agent doit changer son mot de passe avant d'utiliser CID."""
from django.shortcuts import redirect
from django.urls import reverse

LIBRES = ("/logout/", "/static/", "/media/", "/aide/")


class ChangementMotDePasseObligatoire:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and getattr(user, "force_change_password", False):
            page = reverse("core:changer_mot_de_passe")
            if request.path != page and not request.path.startswith(LIBRES):
                return redirect(page)
        return self.get_response(request)
