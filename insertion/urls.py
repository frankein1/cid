# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/urls.py
from django.urls import path

from insertion import views, views_contrats as vc, views_prescriptions as vp

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
    # Contrats
    path('contrats/', vc.contrats_liste, name='contrats_liste'),
    path('beneficiaire/<str:code_interne>/contrats/', vc.contrats_beneficiaire, name='contrats_beneficiaire'),
    path('beneficiaire/<str:code_interne>/contrats/nouveau/', vc.contrat_nouveau, name='contrat_nouveau'),
    path('contrats/<int:pk>/', vc.contrat_detail, name='contrat_detail'),
    path('contrats/<int:pk>/modifier/', vc.contrat_modifier, name='contrat_modifier'),
    path('contrats/<int:pk>/transmettre/', vc.contrat_transmettre, name='contrat_transmettre'),
    path('contrats/<int:pk>/annuler/', vc.contrat_annuler, name='contrat_annuler'),
    path('contrats/<int:pk>/renouveler/', vc.contrat_renouveler, name='contrat_renouveler'),
    path('contrats/<int:pk>/receptionner/', vc.contrat_receptionner, name='contrat_receptionner'),
    path('contrats/<int:pk>/avis/', vc.contrat_avis, name='contrat_avis'),
    path('contrats/<int:pk>/decision/', vc.contrat_decision, name='contrat_decision'),
    path('contrats/<int:pk>/contrat.pdf', vc.contrat_pdf, name='contrat_pdf'),
    path('contrats/<int:pk>/certificat-medical.pdf', vc.contrat_courrier_medecin, name='contrat_courrier_medecin'),
    path('contrats/<int:pk>/notification.pdf', vc.contrat_notification, name='contrat_notification'),
    # Prescriptions
    path('prescriptions/', vp.prescriptions_liste, name='prescriptions_liste'),
    path('beneficiaire/<str:code_interne>/prescriptions/nouvelle/', vp.prescription_nouvelle, name='prescription_nouvelle'),
    path('prescriptions/<int:pk>/', vp.prescription_detail, name='prescription_detail'),
    path('prescriptions/<int:pk>/modifier/', vp.prescription_modifier, name='prescription_modifier'),
    path('prescriptions/<int:pk>/adresser/', vp.prescription_adresser, name='prescription_adresser'),
    path('prescriptions/<int:pk>/annuler/', vp.prescription_annuler, name='prescription_annuler'),
    path('prescriptions/<int:pk>/valider/', vp.prescription_valider, name='prescription_valider'),
    path('prescriptions/<int:pk>/retour/', vp.prescription_retour, name='prescription_retour'),
    path('prescriptions/<int:pk>/fiche.pdf', vp.prescription_pdf, name='prescription_pdf'),
    path('actions/<int:pk>/questions/', vp.action_questions, name='action_questions'),
]
