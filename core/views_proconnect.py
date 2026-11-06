# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/views_proconnect.py
"""Connexion et déconnexion ProConnect (désactivées sans identifiants : voir core/proconnect.py)."""
import logging

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from . import proconnect as pc

log = logging.getLogger(__name__)


class Connexion(LoginView):
    """Page de connexion habituelle, avec le bouton ProConnect quand il est configuré."""
    template_name = "login.html"

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "proconnect_actif": pc.actif()}


def _redirect_uri(request):
    return request.build_absolute_uri(reverse("proconnect_retour"))


def connexion(request):
    if not pc.actif():
        raise Http404("ProConnect n'est pas configuré.")
    try:
        return redirect(pc.url_autorisation(request, _redirect_uri(request)))
    except Exception:  # noqa: BLE001
        log.exception("ProConnect indisponible")
        messages.error(request, "ProConnect est momentanément indisponible. Connectez-vous avec votre identifiant CID.")
        return redirect("login")


def retour(request):
    if not pc.actif():
        raise Http404("ProConnect n'est pas configuré.")
    try:
        identite, id_token = pc.retour(request, _redirect_uri(request))
    except pc.ErreurProConnect as e:
        messages.error(request, f"Connexion ProConnect refusée : {e}")
        return redirect("login")
    except Exception:  # noqa: BLE001
        log.exception("ProConnect : retour")
        messages.error(request, "ProConnect est momentanément indisponible.")
        return redirect("login")
    user = pc.trouver_compte(identite)
    if user is None:
        messages.error(request, f"Aucun compte CID actif n'est associé à {identite.get('email') or 'cette identité'}. "
                                "Demandez à un administrateur de CID de créer votre compte avec ce courriel professionnel.")
        return redirect("login")
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    request.session["proconnect_id_token"] = id_token
    user.identites_proconnect.filter(sub=identite["sub"]).update(derniere_connexion=timezone.now())
    return redirect(request.session.pop("proconnect_suivant", None) or "/")


def deconnexion(request):
    """Déconnexion de CID ; si la session venait de ProConnect, fermeture aussi chez ProConnect."""
    id_token = request.session.get("proconnect_id_token")
    if request.method == "POST" and id_token and pc.actif():
        logout(request)
        try:
            url = pc.url_deconnexion(id_token, request.build_absolute_uri(reverse("login")))
            if url:
                return redirect(url)
        except Exception:  # noqa: BLE001
            log.exception("ProConnect : déconnexion")
        return redirect("login")
    return LogoutView.as_view(template_name="logout.html")(request)
