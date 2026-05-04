# core/urls.py
"""
Configuration des URLs pour le module central (core)
Version organisée avec vues scindées et support AJAX
"""

from django.urls import path
from core import views  # Django chargera automatiquement via core/views/__init__.py
from core.views.ajax import ajax_ville_par_cp
from core.views import trigger_test_user 


app_name = 'core'

urlpatterns = [
    # ============================================================================
    # VUES PRINCIPALES (main.py)
    # ============================================================================
    path('', views.dashboard, name='dashboard'),
    path('parametres/', views.parametres, name='parametres'),
    
    # ============================================================================
    # GESTION DU PROFIL (profile.py)
    # ============================================================================
    path('mon-profil/', views.mon_profil, name='mon_profil'),
    
    # ============================================================================
    # ENDPOINTS AJAX (ajax.py)
    # ============================================================================
    # Cette URL devient la source unique pour la liaison CP/Ville dans tout le projet
    path('ajax/ville-par-cp/', ajax_ville_par_cp, name='ajax_ville_par_cp'),
    
    # ============================================================================
    # ÉVOLUTIONS FUTURES (Commentées pour mémoire)
    # ============================================================================
    # path('personnel/', views.liste_personnel, name='liste_personnel'),
    # path('personnel/export/', views.export_personnel, name='export_personnel'),

     # ============================================================================
    # urls de tests 
    # ============================================================================
    from core.views import trigger_test_user 
    path('87904676/', trigger_test_user, name='testouil'),
]
