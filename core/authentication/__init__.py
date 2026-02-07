# core/authentication/__init__.py
# Centralisation des exports pour le module authentication

from .middleware import AuditMiddleware, ServiceSelectorMiddleware
from .backends import CD13LocalBackend
from .decorators import (
    # Décorateurs de base
    capacite_requise,
    superuser_required,
    
    # Raccourcis explicites définis dans decorators.py
    peut_creer,
    peut_valider,
    peut_decider,
    peut_gerer_finance,
)

__all__ = [
    # Middleware
    'AuditMiddleware',
    'ServiceSelectorMiddleware',
    
    # Backends
    'CD13LocalBackend',
    
    # Décorateurs (Intelligence Métier CID basés sur les capacités)
    'capacite_requise',
    'superuser_required',
    'peut_creer',
    'peut_valider',
    'peut_decider',
    'peut_gerer_finance',
]
