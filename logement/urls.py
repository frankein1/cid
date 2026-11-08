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
    path('expulsions/', views.expulsion_liste, name='expulsion_liste'),
    path('expulsions/nouveau/', views.expulsion_nouveau, name='expulsion_nouveau'),
    path('expulsions/statistiques/', views.expulsion_stats, name='expulsion_stats'),
    path('expulsions/secteur/', views.expulsion_secteur, name='expulsion_secteur'),
    path('expulsions/<int:pk>/', views.expulsion_detail, name='expulsion_detail'),
    path('expulsions/<int:pk>/modifier/', views.expulsion_modifier, name='expulsion_modifier'),
    path('expulsions/<int:pk>/action/', views.expulsion_action, name='expulsion_action'),
    path('expulsions/<int:pk>/fiche.pdf', views.expulsion_pdf, name='expulsion_pdf'),
    path('expulsions/<int:pk>/convoquer/', views.expulsion_convoquer, name='expulsion_convoquer'),
    path('expulsions/convocation/<int:pk>/courrier.pdf', views.convocation_pdf, name='convocation_pdf'),
    path('expulsions/convocation/<int:pk>/noter/', views.convocation_noter, name='convocation_noter'),
    path('expulsions/<int:pk>/questionnaire/', views.questionnaire_preparer, name='questionnaire_preparer'),
    path('expulsions/<int:pk>/questionnaire.pdf', views.questionnaire_pdf, name='questionnaire_pdf'),
    path('expulsions/<int:pk>/questionnaire/recu/', views.questionnaire_recu, name='questionnaire_recu'),
    path('expulsions/<int:pk>/diagnostic/', views.diagnostic_nouveau, name='diagnostic_nouveau'),
    path('expulsions/diagnostic/<int:pk>/', views.diagnostic_detail, name='diagnostic_detail'),
    path('expulsions/diagnostic/<int:pk>/modifier/', views.diagnostic_modifier, name='diagnostic_modifier'),
    path('expulsions/diagnostic/<int:pk>/document.pdf', views.diagnostic_pdf, name='diagnostic_pdf'),
    path('expulsions/diagnostic/<int:pk>/action/', views.diagnostic_action, name='diagnostic_action'),
]
