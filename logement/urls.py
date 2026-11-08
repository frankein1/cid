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
    path('demande/<str:code_interne>/', views.logement_social, name='logement_social'),
    path('copp/nouvelle/<str:code_interne>/', views.copp_nouvelle, name='copp_nouvelle'),
    path('copp/<int:pk>/', views.copp_detail, name='copp_detail'),
    path('copp/<int:pk>/modifier/', views.copp_modifier, name='copp_modifier'),
    path('copp/<int:pk>/fiche.pdf', views.copp_pdf, name='copp_pdf'),
    path('copp/<int:pk>/action/', views.copp_action, name='copp_action'),
    path('envoi/<str:nature>/<int:pk>/', views.envoi_dossier, name='envoi_dossier'),
    path('papier-economise/', views.papier_economise, name='papier_economise'),
]
