# AidFi/urls.py

from django.urls import path
from AidFi.views import (
    v_afase,
    v_regie,
    v_cap,
    v_generique,
)

app_name = "AidFi"

urlpatterns = [
    # ==========================================================
    # DASHBOARD UNIFIÉ (ENTRÉE PRINCIPALE)
    # ==========================================================
    path(
        "beneficiaire/<int:beneficiaire_id>/dashboard/",
        v_generique.dashboard_aidfi_beneficiaire,
        name="dashboard_beneficiaire",
    ),

    # ==========================================================
    # AFASE (Aide Financière ASE)
    # ==========================================================
    # CRÉATION (depuis le dashboard)
    path(
        "beneficiaire/<int:beneficiaire_id>/afase/nouvelle/",
        v_afase.afase_creer_ou_modifier,
        name="afase_creer",
    ),
    
    # MODIFICATION
    path(
        "afase/<int:demande_id>/modifier/",
        v_afase.afase_creer_ou_modifier,
        name="afase_modifier",
    ),
    
    # DÉTAIL (utilisé depuis le dashboard)
    path(
        "afase/<int:demande_id>/",
        v_afase.afase_detail,
        name="afase_detail",
    ),
    
    # ÉVALUATION
    path(
        "afase/<int:demande_id>/evaluation/",
        v_afase.afase_evaluation,
        name="afase_evaluation",
    ),
    
    # DÉCISION
    path(
        "afase/<int:demande_id>/decision/",
        v_afase.afase_decision,
        name="afase_decision",
    ),
    
    # PDF
    path(
        "afase/<int:demande_id>/pdf/",
        v_afase.afase_pdf,
        name="afase_pdf",
    ),

    # ==========================================================
    # RÉGIE D'URGENCE
    # ==========================================================
    # CRÉATION (depuis le dashboard)
    path(
        "beneficiaire/<int:beneficiaire_id>/regie/nouvelle/",
        v_regie.regie_urgence_create,
        name="regie_urgence_create",
    ),
    
    # DÉTAIL (à créer dans v_regie.py)
    path(
        "regie/<int:demande_id>/",
        v_regie.regie_detail,
        name="regie_detail",
    ),

    # ==========================================================
    # CAP (Chèque d'Accompagnement Personnalisé)
    # ==========================================================
    # CRÉATION (depuis le dashboard)
    path(
        "beneficiaire/<int:beneficiaire_id>/cap/nouvelle/",
        v_cap.cap_attribution,
        name="cap_attribution",
    ),
    
    # DÉTAIL (à créer dans v_cap.py)
    path(
        "cap/<int:demande_id>/",
        v_cap.cap_detail,
        name="cap_detail",
    ),
]
