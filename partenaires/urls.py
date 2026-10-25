# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# partenaires/urls.py
from django.urls import path

from . import views

app_name = 'partenaires'

urlpatterns = [
    path('', views.liste, name='liste'),
    path('ajouter/', views.ajouter, name='ajouter'),
    path('<int:pk>/modifier/', views.modifier, name='modifier'),
    path('<int:pk>/actif/', views.basculer_actif, name='basculer_actif'),
]
