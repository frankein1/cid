# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# AidFi/urls.py 
# DeepSeek est la meilleure IA mais c'est poetefada qui a fait les requpêtes et a analysé le rendu. Il est interdit d'utiliser ceci à des fins commerciales 

from django.urls import path
from AidFi.views import (
    v_afase,
    v_regie,
    v_cap,
    v_cadre,
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
    path(
        "beneficiaire/<int:beneficiaire_id>/afase/nouvelle/",
        v_afase.afase_creer_ou_modifier,
        name="afase_creer",
    ),

    path(
        "afase/<int:demande_id>/modifier/",
        v_afase.afase_creer_ou_modifier,
        name="afase_modifier",
    ),

    path(
        "afase/<int:demande_id>/",
        v_afase.afase_detail,
        name="afase_detail",
    ),

    # ✅ ÉVALUATION TS 
    path(
        "afase/<int:demande_id>/evaluation/",
        v_afase.afase_evaluation,
        name="afase_evaluation",
    ),

    # ✅ DÉCISION CADRE
    path(
        "afase/<int:demande_id>/decision/",
        v_afase.afase_decision,
        name="afase_decision",
    ),

    # ✅ prévisualisation 
    path(
    "afase/<int:demande_id>/previsualisation/",
    v_afase.afase_previsualisation,
    name="afase_previsualisation",
),
    # ✅ ajout documents 
path(
    "afase/<int:demande_id>/ajouter-document/",
    v_afase.ajouter_document_afase,
    name="afase_ajouter_document",
),

    # ✅ PDF OFFICIEL
    path(
        "afase/<int:demande_id>/pdf/",
        v_afase.afase_pdf,
        name="afase_pdf",
    ),

    # ==========================================================
    # RÉGIE D'URGENCE
    # ==========================================================
    path(
        "beneficiaire/<int:beneficiaire_id>/regie/nouvelle/",
        v_regie.regie_urgence_create,
        name="regie_urgence_create",
    ),

    path(
        "regie/<int:demande_id>/",
        v_regie.regie_detail,
        name="regie_detail",
    ),

    # ==========================================================
    # CAP
    # ==========================================================
    path(
        "beneficiaire/<int:beneficiaire_id>/cap/nouvelle/",
        v_cap.cap_attribution,
        name="cap_attribution",
    ),

    path(
        "cap/<int:demande_id>/",
        v_cap.cap_detail,
        name="cap_detail",
    ),

    # ==========================================================
    # DASHBOARD CADRE
    # ==========================================================
    path(
        "cadre/dashboard/",
        v_cadre.dashboard_cadre,
        name="dashboard_cadre",
    ),
]
