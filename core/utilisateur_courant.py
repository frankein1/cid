# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/utilisateur_courant.py
"""
Mémorise l'utilisateur connecté pendant une requête, pour que les modèles
(AuditedMixin) puissent remplir 'cree_par' et 'modifie_par' sans que chaque
vue ait à le faire.

- CurrentUserMiddleware : à déclarer dans settings.MIDDLEWARE,
  APRÈS AuthenticationMiddleware.
- get_utilisateur_courant() : renvoie l'utilisateur connecté, ou None
  (scripts, commandes init2/install, tâches sans requête).

contextvars : chaque requête a sa propre valeur, même si le serveur
en traite plusieurs en parallèle.
"""

from contextvars import ContextVar

_utilisateur = ContextVar('cid_utilisateur_courant', default=None)


def get_utilisateur_courant():
    user = _utilisateur.get()
    if user is not None and getattr(user, 'is_authenticated', False):
        return user
    return None


class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        jeton = _utilisateur.set(getattr(request, 'user', None))
        try:
            return self.get_response(request)
        finally:
            _utilisateur.reset(jeton)  # rien ne « fuit » vers la requête suivante
