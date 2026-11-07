# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/urls.py
from django.urls import path

from . import views

app_name = 'logement'
urlpatterns = [
    path('fsl/nouvelle/<str:code_interne>/', views.fsl_nouvelle, name='fsl_nouvelle'),
    path('fsl/<int:pk>/', views.fsl_detail, name='fsl_detail'),
    path('fsl/<int:pk>/modifier/', views.fsl_modifier, name='fsl_modifier'),
    path('fsl/<int:pk>/dossier.pdf', views.fsl_pdf, name='fsl_pdf'),
    path('fsl/<int:pk>/action/', views.fsl_action, name='fsl_action'),
]
