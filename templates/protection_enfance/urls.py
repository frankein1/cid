# protection_enfance/urls.py - NOUVEAU FICHIER
from django.urls import path
from . import views

app_name = 'protection_enfance'

urlpatterns = [
    # Tableaux de bord
    path('', views.dashboard_ase, name='dashboard_ase'),
    path('crip/', views.dashboard_crip, name='dashboard_crip'),
    
    # Informations Préoccupantes
    path('ip/', views.ip_liste, name='ip_liste'),
    path('ip/<int:ip_id>/', views.ip_detail, name='ip_detail'),
    path('ip/nouvelle/', views.ip_creation, name='ip_creation'),
    
    # Placements
    path('placements/', views.placements_liste, name='placements_liste'),
    path('placements/<int:placement_id>/', views.placement_detail, name='placement_detail'),
]
