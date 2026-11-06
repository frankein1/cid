# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

# core/models/__init__.py
"""
Modèles CORE - Point d'entrée centralisé
"""

# Modèles de base
from .user import User, CustomUserManager
from .profil import Profil
from .capacite import Capacite
from .organisation import Service
from .configuration import Configuration
from .audit import AuditLog
from .modele_courrier import ModeleCourrier

# Export explicite pour star imports
__all__ = [
    # Users
    'User',
    'CustomUserManager',
    
    # Sécurité
    'Profil',
    'Capacite',
    
    # Structure
    'Service',
    
    # Configuration
    'Configuration',
    
    # Audit
    'AuditLog',
    'ModeleCourrier',
    'IdentiteProConnect',
]
from .proconnect import IdentiteProConnect  # noqa: E402,F401
