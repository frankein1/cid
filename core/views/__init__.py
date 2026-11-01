# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

# core/views/__init__.py

"""
Exports des vues pour l'application core
Permet d'accéder aux vues via core.views.nom_vue
"""

from .main import dashboard, parametres, accueil
from .profile import mon_profil
from .gubed import trigger_test_user
from .demo import demo_reinitialiser
from .aide import aide
from .mot_de_passe import mot_de_passe_oublie, reinitialiser_mot_de_passe, changer_mot_de_passe
# Ne pas exporter ajax_ville_par_cp ici pour éviter la confusion
# Il est importé directement depuis core.views.ajax dans urls.py
