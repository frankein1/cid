# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/urls.py
from django.urls import path

from insertion import views

app_name = 'insertion'

urlpatterns = [
    path('', views.accueil, name='accueil'),
    path('actions/', views.actions_liste, name='actions_liste'),
    path('actions/nouvelle/', views.action_saisie, name='action_creation'),
    path('actions/modele.csv', views.actions_modele_csv, name='actions_modele_csv'),
    path('actions/export.csv', views.actions_export_csv, name='actions_export_csv'),
    path('actions/importer/', views.actions_import, name='actions_import'),
    path('actions/<int:pk>/', views.action_detail, name='action_detail'),
    path('actions/<int:pk>/modifier/', views.action_saisie, name='action_modifier'),
]
