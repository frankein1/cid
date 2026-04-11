# AidFi/views/v_generique.py

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from beneficiaire.models import Beneficiaire
from AidFi.models.m_generique import DemandeAide
from AidFi.models.m_afase import DemandeAFASE

@login_required
def dashboard_aidfi_beneficiaire(request, beneficiaire_id):
    beneficiaire = get_object_or_404(Beneficiaire, id=beneficiaire_id)

    # 🔒 Sécurité minimale
    if not request.user.a_la_capacite("peut_voir"):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Accès refusé")

    # 🎭 Rôles (simples, explicites)
    is_ts = request.user.a_la_capacite("peut_instruire") or request.user.a_la_capacite("peut_creer")
    is_cadre = request.user.a_la_capacite("peut_decider")

    # ➕ Actions globales possibles
    actions = {
        "can_create_afase": request.user.a_la_capacite("peut_creer"),
        "can_create_cap": request.user.a_la_capacite("peut_gerer_finance"),
        "can_create_regie": request.user.a_la_capacite("peut_gerer_finance"),
    }

    # 📦 Récupérer toutes les demandes (socle commun)
    demandes = (
        DemandeAide.objects
        .filter(beneficiaire=beneficiaire)
        .select_related("type_aide")
        .order_by("-date_creation")
    )

    aides = []

    for demande in demandes:
        type_code = demande.type_aide.code  # ex: AFASE, CAP, REGIE

        aide = {
            "id": demande.id,
            "type": type_code,
            "type_label": demande.type_aide.nom,
            "date": demande.date_creation,
            "montant": getattr(demande, "montant_sollicite", None),
            "statut": demande.get_statut_display(),
            "badge_classes": getattr(demande, "statut_badge_classes", "bg-gray-200 text-gray-800"),
            "urls": {},
            "can": {
                "voir": request.user.a_la_capacite("peut_voir"),
                "modifier": False,
                "decider": False,
                "pdf": False,
            },
        }

        # ==========================
        # 🔹 CAS AFASE (complet)
        # ==========================
        if type_code == "AFASE":
            afase = DemandeAFASE.objects.get(pk=demande.pk)
            print(f"=== DASHBOARD DEBUG: demande #{demande.id} - montant_sollicite = {demande.montant_sollicite} ===")

            aide["urls"]["detail"] = "AidFi:afase_detail"
            aide["urls"]["detail_args"] = [afase.id]

            if request.user.peut_agir_sur_objet(afase, "peut_modifier"):
                aide["can"]["modifier"] = True
                aide["urls"]["modifier"] = "AidFi:afase_modifier"

            if is_cadre and afase.statut in ["EVALUATION", "EN_INSTRUCTION"]:
                aide["can"]["decider"] = True
                aide["urls"]["decision"] = "AidFi:afase_decision"

            if hasattr(afase, "decision"):
                aide["can"]["pdf"] = True
                aide["urls"]["pdf"] = "AidFi:afase_pdf"

        # ==========================
        # 🔹 CAS CAP (partiel)
        # ==========================
        elif type_code == "CAP":
            aide["urls"]["detail"] = "AidFi:cap_detail"
            aide["urls"]["detail_args"] = [demande.id]
            # Décision / PDF : à venir plus tard

        # ==========================
        # 🔹 CAS RÉGIE (partiel)
        # ==========================
        elif type_code == "REGIE":
            aide["urls"]["detail"] = "AidFi:regie_detail"
            aide["urls"]["detail_args"] = [demande.id]

        print(f"=== APRES CONSTRUCTION: demande #{demande.id} - aide.montant = {aide['montant']} | type = {type(aide['montant'])} ===")
        aides.append(aide)

    context = {
        "beneficiaire": beneficiaire,
        "roles": {
            "is_ts": is_ts,
            "is_cadre": is_cadre,
        },
        "actions": actions,
        "aides": aides,
    }

    return render(request, "AidFi/dashboard_beneficiaire.html", context)
