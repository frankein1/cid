# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/urls.py
from django.urls import path

from . import views, views_invitations, views_rdvsp_synchro, views_simulation

app_name = 'connecteurs'

from . import views_droits, views_inclusion  # noqa: E402

urlpatterns = [
    path('inclusion/', views_inclusion.recherche, name='inclusion_recherche'),
    path('inclusion/<int:pk>/ajouter-annuaire/', views_inclusion.ajouter_annuaire, name='inclusion_ajouter'),
    path('inclusion/mise-a-jour/', views_inclusion.etat, name='inclusion_etat'),
    path('usager/<str:code_interne>/simulation-droits/', views_simulation.simuler_droits, name='simuler_droits'),
    path('usager/<str:code_interne>/situation/actualiser/', views.actualiser_situation,
         name='actualiser_situation'),
    path('usager/<str:code_interne>/situation/ecart/<int:pk>/regle/', views_droits.regler_ecart, name='regler_ecart'),
    path('usager/<str:code_interne>/situation/aides/', views_droits.relever_prestations, name='relever_prestations'),
    # Passerelle RDV Service Public (désactivée par défaut)
    path('rdv-service-public/', views.rdvsp_etat, name='rdvsp_etat'),
    path('rdv-service-public/connexion/', views.rdvsp_connexion, name='rdvsp_connexion'),
    path('rdv-service-public/retour/', views.rdvsp_retour, name='rdvsp_retour'),
    path('rdv-service-public/avis/', views_rdvsp_synchro.avis, name='rdvsp_avis'),
    path('rdv-service-public/synchroniser/', views_rdvsp_synchro.synchroniser, name='rdvsp_synchroniser'),
    path('rdv-service-public/declarer/', views_rdvsp_synchro.declarer, name='rdvsp_declarer'),
    path('invitations-rsa/', views_invitations.invitations_rsa, name='invitations_rsa'),
    path('invitations-rsa/<int:pk>/courrier.pdf', views_invitations.invitation_courrier, name='invitation_courrier'),
    path('usager/<str:code_interne>/reservation-en-ligne/', views_invitations.reservation_en_ligne,
         name='reservation_en_ligne'),
    path('usager/<str:code_interne>/rdv-service-public/', views.rdvsp_planifier, name='rdvsp_planifier'),
]
