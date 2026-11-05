# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

"""
URLs pour l'application bénéficiaire
Fichier : beneficiaire/urls.py
AMELIORE : Ajout URLs sortie et décès
"""

from django.urls import path
from . import views, views_rgpd

app_name = 'beneficiaire'

urlpatterns = [
    # Liste et recherche
    path('', views.liste_beneficiaires, name='liste'),

    # Archivage RGPD (avant les routes <code_interne>/)
    path('rgpd/archivage/', views_rgpd.rgpd_archivage, name='rgpd_archivage'),
    path('rgpd/archiver/', views_rgpd.rgpd_archiver, name='rgpd_archiver'),
    path('rgpd/effacement/', views_rgpd.rgpd_effacement, name='rgpd_effacement'),
    path('rgpd/dossier/<str:code_interne>/', views_rgpd.rgpd_dossier, name='rgpd_dossier'),
    
    # CRUD Bénéficiaire
    path('ajouter/', views.ajouter_beneficiaire, name='ajouter_beneficiaire'),
    path('<str:code_interne>/', views.detail_beneficiaire, name='detail_beneficiaire'),
    path('<str:code_interne>/modifier/', views.modifier_beneficiaire, name='modifier_beneficiaire'),
    
    # Ayant droit
    #path('<str:code_interne>/ayant-droit/ajouter/', views.ajouter_ayant_droit, name='ajouter_ayant_droit'),
    path('<str:code_interne>/lien/ajouter/', views.ajouter_lien_beneficiaire, name='ajouter_lien_beneficiaire'),
    
    # NOUVEAU : Gestion sortie et décès
    path('<str:code_interne>/sortir/', views.sortir_beneficiaire, name='sortir_beneficiaire'),
    path('<str:code_interne>/transferer/', views.transferer_beneficiaire, name='transferer_beneficiaire'),
    path('<str:code_interne>/deces/', views.declarer_deces, name='declarer_deces'),
    path('<str:code_interne>/reactiver/', views.reactiver_beneficiaire, name='reactiver_beneficiaire'),
    path('<str:code_interne>/supprimer/', views.supprimer_beneficiaire, name='supprimer_beneficiaire'),
    
    # AJAX
    path('ajax/load-referents/', views.load_referents, name='load_referents'),
]
