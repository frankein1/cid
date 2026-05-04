# core/__init__.py
"""
Application CORE - Fondation du SI DITAS
"""
default_app_config = 'core.apps.CoreConfig'

from .models.user import User
from .models.organisation import Service
from .models.profil import Profil
from .models.capacite import Capacite

__all__ = ['User', 'Service', 'Profil', 'Capacite']
