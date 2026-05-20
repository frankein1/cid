# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# planning/urls.py
"""
URLs pour le module planning
VERSION COMPLÈTE avec accueil et exports
"""

from django.urls import path
from . import views

app_name = 'planning'

urlpatterns = [
    # ==========================
    # CALENDRIER PRINCIPAL
    # ==========================
    path('calendrier/<int:beneficiaire_id>/', views.calendrier_rdv, name='calendrier_rdv'),    
    path('api/creneaux/', views.api_creneaux, name='api_creneaux'),
    path('', views.calendrier_rdv, name='calendrier_rdv'),
    
    # ==========================
    # GESTION DES CRÉNEAUX
    # ==========================
    path('reserver/<int:creneau_id>/<int:beneficiaire_id>/', views.reserver_rdv, name='reserver_rdv'),
    path('reserver/<int:creneau_id>/', views.reserver_rdv, name='reserver_rdv_simple'),
    path('annuler/<int:creneau_id>/', views.annuler_rdv, name='annuler_rdv'),
    path('generer/', views.generer_creneaux, name='generer_creneaux'),
    
    # ==========================
    # JOURS BLOQUÉS
    # ==========================
    path('bloquer-jour/', views.ajouter_jour_bloque, name='ajouter_jour_bloque'),
    
    # ==========================
    # PLANNING ACCUEIL (NOUVEAU)
    # ==========================
    path('accueil/', views.planning_accueil_jour, name='planning_accueil_jour'),
    path('accueil/<str:date_str>/', views.planning_accueil_jour, name='planning_accueil_jour_date'),
    path('accueil/semaine/', views.planning_accueil_semaine, name='planning_accueil_semaine'),
    path('accueil/semaine/<str:date_str>/', views.planning_accueil_semaine, name='planning_accueil_semaine_date'),
    path('mes-permanences/', views.mes_permanences_semaine, name='mes_permanences'),
    path('mes-permanences/<str:date_str>/', views.mes_permanences_semaine, name='mes_permanences_date'),
    path('permanences/externes/', views.gerer_permanences_externes, name='gerer_permanences_externes'),
    path('permanences/externes/supprimer/<int:pk>/', views.supprimer_permanence_externe, name='supprimer_permanence_externe'),
    path('creer-rdv/<int:beneficiaire_id>/', views.creer_rdv_depuis_beneficiaire, name='creer_rdv_depuis_beneficiaire'),
    path('choisir-creneau/<int:beneficiaire_id>/', views.choisir_creneau, name='choisir_creneau'),

    
    # ==========================
    # EXPORTS OUTLOOK (NOUVEAU)
    # ==========================
    path('export/ical/', views.export_planning_ical, name='export_ical'),
    path('export/agent/<int:agent_id>/outlook/', views.exporter_planning_agent_outlook, name='export_agent_outlook'),
    path('export/mes-permanences/ics/', views.exporter_mes_permanences_ics, name='export_mes_permanences_ics'),
    
    # ==========================
    # IMPRESSION PDF (NOUVEAU)
    # ==========================
    path('imprimer/<str:date_str>/pdf/', views.imprimer_planning_jour_pdf, name='imprimer_planning_pdf'),


    # ==========================
    # recherche beneficiaire
    # ==========================
    path('api/recherche-beneficiaire/', views.api_recherche_beneficiaire, name='api_recherche_beneficiaire'),

    
    # ==========================
    # FUTURE: SYNC MICROSOFT GRAPH
    # ==========================
    # path('sync/outlook/auth/', views.outlook_auth, name='outlook_auth'),
    # path('sync/outlook/callback/', views.outlook_callback, name='outlook_callback'),
    # path('sync/outlook/sync/', views.outlook_sync, name='outlook_sync'),
]
