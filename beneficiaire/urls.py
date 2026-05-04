# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

"""
URLs pour l'application bénéficiaire
Fichier : beneficiaire/urls.py
AMELIORE : Ajout URLs sortie et décès
"""

from django.urls import path
from . import views

app_name = 'beneficiaire'

urlpatterns = [
    # Liste et recherche
    path('', views.liste_beneficiaires, name='liste'),
    
    # CRUD Bénéficiaire
    path('ajouter/', views.ajouter_beneficiaire, name='ajouter_beneficiaire'),
    path('<str:code_interne>/', views.detail_beneficiaire, name='detail_beneficiaire'),
    path('<str:code_interne>/modifier/', views.modifier_beneficiaire, name='modifier_beneficiaire'),
    
    # Ayant droit
    path('<str:code_interne>/ayant-droit/ajouter/', views.ajouter_ayant_droit, name='ajouter_ayant_droit'),
    
    # NOUVEAU : Gestion sortie et décès
    path('<str:code_interne>/sortir/', views.sortir_beneficiaire, name='sortir_beneficiaire'),
    path('<str:code_interne>/deces/', views.declarer_deces, name='declarer_deces'),
    path('<str:code_interne>/supprimer/', views.supprimer_beneficiaire, name='supprimer_beneficiaire'),
    
    # AJAX
    path('ajax/load-referents/', views.load_referents, name='load_referents'),
]
