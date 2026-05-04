# core/views/__init__.py

"""
Exports des vues pour l'application core
Permet d'accéder aux vues via core.views.nom_vue
"""

from .main import dashboard, parametres
from .profile import mon_profil
from .tests import trigger_test_user
# Ne pas exporter ajax_ville_par_cp ici pour éviter la confusion
# Il est importé directement depuis core.views.ajax dans urls.py
