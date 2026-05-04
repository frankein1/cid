# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# mds/urls.py
from django.urls import path
from .views import base_views, user_views, reception_views, api_views, salle_views 

app_name = 'mds'

urlpatterns = [
    # BASE / MDS
    path('', base_views.liste_mds, name='liste_mds'),
    path('creer/', base_views.creer_mds, name='creer_mds'),
    path('<int:mds_id>/', base_views.detail_mds, name='detail_mds'),
    path('<int:mds_id>/modifier/', base_views.modifier_mds, name='modifier_mds'),
    path('<int:mds_id>/statistiques/', base_views.statistiques_mds, name='statistiques_mds'),
    
    # UTILISATEURS
    path('<int:mds_id>/utilisateurs/', user_views.gestion_utilisateurs_mds, name='gestion_utilisateurs_mds'),
    path('<int:mds_id>/utilisateurs/ajouter/', user_views.ajouter_utilisateur_mds, name='ajouter_utilisateur_mds'),
    path('<int:mds_id>/utilisateurs/<int:user_id>/modifier/', user_views.modifier_profil_utilisateur, name='modifier_profil_utilisateur'),
    path('<int:mds_id>/utilisateurs/<int:user_id>/supprimer/', user_views.supprimer_utilisateur_mds, name='supprimer_utilisateur_mds'),
    
    # RÉCEPTION
    path('mes-demi-journees/', reception_views.mes_demi_journees, name='mes_demi_journees'),
    path('gestion-demi-journees/', reception_views.mes_demi_journees, name='gestion_demi_journees'),
    path('toggle-demi-journee/', reception_views.toggle_demi_journee, name='toggle_demi_journee'),
    
    # SALLES (Pointent désormais vers salle_views)
    path('<int:mds_id>/salles/', salle_views.gestion_salles_mds, name='gestion_salles_mds'),
    path('<int:mds_id>/salles/creer/', salle_views.creer_salle_mds, name='creer_salle_mds'),
    path('<int:mds_id>/salles/<int:salle_id>/modifier/', salle_views.modifier_salle_mds, name='modifier_salle_mds'),
    path('<int:mds_id>/salles/<int:salle_id>/supprimer/', salle_views.supprimer_salle_mds, name='supprimer_salle_mds'),
    
    # API JSON
    path('ajax/ville-par-cp/', api_views.ajax_get_ville_from_cp, name='get_ville_by_cp'),
    path('<int:mds_id>/utilisateurs/json/', api_views.get_utilisateurs_mds_json, name='get_utilisateurs_mds_json'),
    path('<int:mds_id>/salles/json/', api_views.get_salles_mds_json, name='get_salles_mds_json'),
]
