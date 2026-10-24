# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/urls.py
from django.urls import path

from . import views

app_name = 'connecteurs'

urlpatterns = [
    path('usager/<str:code_interne>/situation/actualiser/', views.actualiser_situation,
         name='actualiser_situation'),
]
