# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# protection_enfance/urls.py

from django.urls import path
from . import views

app_name = 'protection_enfance'

urlpatterns = [
    # Dashboards
    #path('dashboard/ase/', views.dashboard_ase, name='dashboard_ase'),
    #path('dashboard/crip/', views.dashboard_crip, name='dashboard_crip'),
    
    # Informations Préoccupantes
    path('ip/', views.ip_liste, name='ip_liste'),
    path('ip/creation/', views.ip_creation, name='ip_creation'),
    path('ip/<str:ip_id>/', views.ip_detail, name='ip_detail'),
    path('ip/<str:ip_id>/modifier/', views.ip_modifier, name='ip_modifier'),
    path('ip/<str:ip_id>/transmettre-parquet/', views.ip_transmettre_parquet, name='ip_transmettre_parquet'),
    path('ip/<str:ip_id>/assigner-referents/', views.ip_assigner_referents, name='ip_assigner_referents'),
    
    # Placements (à développer)
    #path('placements/', views.placements_liste, name='placements_liste'),
    #path('placements/<int:placement_id>/', views.placement_detail, name='placement_detail'),
]
