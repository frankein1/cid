# core/authentication/decorators.py

from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)

def capacite_requise(nom_capacite):
    """
    Décorateur universel pour CID.
    Vérifie si l'utilisateur a le droit métier (indépendamment de l'objet).
    Usage : @capacite_requise('peut_creer_dossier')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "Veuillez vous connecter.")
                return redirect('login')
            
            if request.user.a_la_capacite(nom_capacite):
                return view_func(request, *args, **kwargs)
            
            logger.warning(f"Refus capacité {nom_capacite} pour {request.user.username}")
            messages.error(request, "Accès refusé : compétence métier insuffisante.")
            raise PermissionDenied
        return wrapper
    return decorator

def superuser_required(view_func):
    """Restriction stricte aux administrateurs système."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper

# Raccourcis explicites pour les vues
peut_creer = capacite_requise('peut_creer')
peut_valider = capacite_requise('peut_valider')
peut_decider = capacite_requise('peut_decider')
peut_gerer_finance = capacite_requise('peut_finance')
