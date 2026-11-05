# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/urls.py
from django.urls import path

from . import views, views_simulation

app_name = 'connecteurs'

urlpatterns = [
    path('usager/<str:code_interne>/simulation-droits/', views_simulation.simuler_droits, name='simuler_droits'),
    path('usager/<str:code_interne>/situation/actualiser/', views.actualiser_situation,
         name='actualiser_situation'),
    # Passerelle RDV Service Public (désactivée par défaut)
    path('rdv-service-public/', views.rdvsp_etat, name='rdvsp_etat'),
    path('rdv-service-public/connexion/', views.rdvsp_connexion, name='rdvsp_connexion'),
    path('rdv-service-public/retour/', views.rdvsp_retour, name='rdvsp_retour'),
    path('usager/<str:code_interne>/rdv-service-public/', views.rdvsp_planifier, name='rdvsp_planifier'),
]
