# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/urls.py
from django.urls import path

from protection_enfance.views import v_evaluation, v_ip, v_pief, v_stats

app_name = 'protection_enfance'

urlpatterns = [
    # IP : liste, saisie CRIP, fiche
    path('ip/', v_ip.ip_liste, name='ip_liste'),
    path('ip/nouvelle/', v_ip.ip_saisie, name='ip_creation'),
    path('ip/statistiques/', v_stats.statistiques_ip, name='statistiques_ip'),
    path('ip/<str:ip_id>/', v_ip.ip_detail, name='ip_detail'),
    path('ip/<str:ip_id>/modifier/', v_ip.ip_saisie, name='ip_modifier'),
    path('ip/<str:ip_id>/transmettre/', v_ip.ip_transmettre, name='ip_transmettre'),
    path('ip/<str:ip_id>/binome/', v_ip.ip_binome, name='ip_binome'),
    path('ip/<str:ip_id>/piece/', v_ip.ip_piece, name='ip_piece'),

    # Évaluation
    path('ip/<str:ip_id>/demarche/', v_evaluation.action_ajouter, name='action_ajouter'),
    path('demarche/<int:action_id>/suivi/', v_evaluation.action_suivi, name='action_suivi'),
    path('demarche/<int:action_id>/courrier.pdf', v_evaluation.courrier_pdf, name='courrier_pdf'),
    path('ip/<str:ip_id>/rapport/', v_evaluation.rapport, name='rapport'),
    path('ip/<str:ip_id>/rapport/viser/', v_evaluation.rapport_viser, name='rapport_viser'),
    path('ip/<str:ip_id>/rapport/renvoyer/', v_evaluation.rapport_renvoyer, name='rapport_renvoyer'),
    path('ip/<str:ip_id>/rapport.pdf', v_evaluation.rapport_pdf, name='rapport_pdf'),

    # Saisine du procureur
    path('ip/<str:ip_id>/saisine/', v_evaluation.saisine_proposer, name='saisine_proposer'),
    path('saisine/<int:saisine_id>/cadre/', v_evaluation.saisine_cadre, name='saisine_cadre'),
    path('saisine/<int:saisine_id>/effectuee/', v_evaluation.saisine_effectuee, name='saisine_effectuee'),
    path('saisine/<int:saisine_id>/courrier.pdf', v_evaluation.saisine_pdf, name='saisine_pdf'),

    # Inspecteur enfance famille
    path('ip/<str:ip_id>/avis/', v_pief.avis_rapport, name='avis_rapport'),
    path('saisine/<int:saisine_id>/inspecteur/', v_pief.saisine_pief, name='saisine_pief'),
]
