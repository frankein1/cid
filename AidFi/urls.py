# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

# AidFi/urls.py 

from django.urls import path
from AidFi.views import v_stats
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
    path("beneficiaire/<int:beneficiaire_id>/dashboard/",v_generique.dashboard_aidfi_beneficiaire,name="dashboard_beneficiaire",),

    # ==========================================================
    # AFASE (Aide Financière ASE)
    # ==========================================================
    path("beneficiaire/<int:beneficiaire_id>/afase/nouvelle/", v_afase.afase_creer_ou_modifier, name="afase_creer",),

    path("afase/<int:demande_id>/modifier/", v_afase.afase_creer_ou_modifier, name="afase_modifier", ),

    path("afase/<int:demande_id>/", v_afase.afase_detail, name="afase_detail",),

    # ✅ ÉVALUATION TS 
    path("afase/<int:demande_id>/evaluation/", v_afase.afase_evaluation, name="afase_evaluation",),

    # ✅ DÉCISION CADRE
     path("afase/<int:demande_id>/decision/", v_afase.afase_decision, name="afase_decision",),

    # ✅ prévisualisation 
    path("afase/<int:demande_id>/previsualisation/", v_afase.afase_previsualisation, name="afase_previsualisation",),
    # ✅ ajout documents 
path("afase/<int:demande_id>/ajouter-document/", v_afase.ajouter_document_afase, name="afase_ajouter_document",),

    # ✅ PDF OFFICIEL
    path("afase/<int:demande_id>/pdf/", v_afase.afase_pdf, name="afase_pdf",),
    path("afase/<int:demande_id>/paiement/", v_afase.afase_paiement, name="afase_paiement",),

    # ==========================================================
    # RÉGIE D'URGENCE
    # ==========================================================
    path("beneficiaire/<int:beneficiaire_id>/regie/nouvelle/", v_regie.regie_urgence_create, name="regie_urgence_create",),

    path("regie/<int:demande_id>/", v_regie.regie_detail, name="regie_detail",),

    # ==========================================================
    # CAP
    # ==========================================================
    # Demande (AS) → décision → remise → feuille → clôture
    path("beneficiaire/<int:beneficiaire_id>/cap/nouvelle/", v_cap.cap_creer, name="cap_creer",),
    path("cap/<int:demande_id>/", v_cap.cap_detail, name="cap_detail",),
    path("cap/<int:demande_id>/decision/", v_cap.cap_decision, name="cap_decision",),
    path("cap/<int:demande_id>/remise/", v_cap.cap_remise, name="cap_remise",),
    path("cap/<int:demande_id>/remise-paierie/", v_cap.cap_remise_paierie, name="cap_remise_paierie",),
    path("cap/<int:demande_id>/feuille.pdf", v_cap.cap_feuille_pdf, name="cap_feuille_pdf",),
    path("cap/<int:demande_id>/cloturer/", v_cap.cap_cloturer, name="cap_cloturer",),

    # Coffre et réception (régisseur de la MDS)
    path("cap/coffres/", v_cap.cap_coffres, name="cap_coffres",),
    path("cap/coffre/<int:mds_id>/", v_cap.cap_coffre, name="cap_coffre",),
    path("cap/coffre/<int:mds_id>/regisseur/", v_cap.cap_designer_regisseur, name="cap_designer_regisseur",),
    path("cap/coffre/<int:mds_id>/reception/", v_cap.cap_reception_nouvelle, name="cap_reception_nouvelle",),
    path("cap/reception/<int:reception_id>/", v_cap.cap_reception, name="cap_reception",),
    path("cap/reception/<int:reception_id>/bordereau.pdf", v_cap.cap_reception_pdf, name="cap_reception_pdf",),
    path("cap/titre/<int:titre_id>/incident/", v_cap.cap_titre_incident, name="cap_titre_incident",),
    path("cap/coffre/<int:mds_id>/inventaire/", v_cap.cap_inventaire_nouveau, name="cap_inventaire_nouveau",),
    path("cap/inventaire/<int:inventaire_id>/", v_cap.cap_inventaire, name="cap_inventaire",),
    path("cap/inventaire/<int:inventaire_id>/proces-verbal.pdf", v_cap.cap_inventaire_pdf, name="cap_inventaire_pdf",),

    # Régie centrale (paierie départementale)
    path("cap/paierie/", v_cap.cap_paierie, name="cap_paierie",),

    # ==========================================================
    # DASHBOARD CADRE
    # ==========================================================
    path("cadre/dashboard/", v_cadre.dashboard_cadre, name="dashboard_cadre",),
    path("statistiques/", v_stats.statistiques_aides, name="statistiques_aides",),
]
