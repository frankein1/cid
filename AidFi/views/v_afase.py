# AidFi/views/v_afase.py — VERSION STABLE NETTOYÉE

from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from AidFi.forms.afase_workflow_form import AFASEWorkflowForm
from AidFi.forms.f_afase import EvaluationSocialeAFASEForm, DecisionAFASEForm
from AidFi.models.m_afase import DemandeAFASE, DecisionAFASE
from AidFi.services.afase_pdf import generer_pdf_afase
from ged.services import stocker_pdf_afase

from beneficiaire.models import Beneficiaire

# ==========================================================
# CRÉATION / MODIFICATION AFASE
# ==========================================================

@login_required
def afase_creer_ou_modifier(request, beneficiaire_id=None, demande_id=None):

    demande = None
    beneficiaire = None
    budget = None

    # ------------------------------
    # CONTEXTE
    # ------------------------------
    if demande_id:
        demande = get_object_or_404(DemandeAFASE, pk=demande_id)
        beneficiaire = demande.beneficiaire
        action = "modification"
        budget = DemandeAFASE.objects.select_related("budget") \
         .get(pk=demande.id).budget if demande else None

    elif beneficiaire_id:
        beneficiaire = get_object_or_404(Beneficiaire, pk=beneficiaire_id)
        action = "création"

    else:
        return HttpResponseForbidden("Paramètres manquants")

    # ------------------------------
    # SÉCURITÉ
    # ------------------------------
    if action == "création":
        if not request.user.peut_agir_sur_objet(beneficiaire, "peut_creer"):
            return HttpResponseForbidden("Accès refusé")
    else:
        if not request.user.peut_agir_sur_objet(demande, "peut_modifier"):
            return HttpResponseForbidden("Accès refusé")

    # ------------------------------
    # FORMULAIRE
    # ------------------------------
    if request.method == "POST":
        form = AFASEWorkflowForm(
            data=request.POST,
            beneficiaire=beneficiaire,
            user=request.user,
            demande=demande,
        )
        if form.is_valid():
            demande = form.save()
            messages.success(request, "Demande AFASE enregistrée avec succès.")
            return redirect("AidFi:afase_detail", demande_id=demande.id)
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = AFASEWorkflowForm(
            beneficiaire=beneficiaire,
            user=request.user,
            demande=demande,
        )

    # ------------------------------
    # CONTEXTE BUDGET (CLÉ DU BUG)
    # ------------------------------
    context_budget = {
        "ressources": budget.ressources,
        "charges": budget.charges,
    } if budget else {"ressources": {}, "charges": {}}


    print("=== FIELDS DU FORMULAIRE ===", list(form.fields.keys()))                        
    # ------------------------------
    # RENDER
    # ------------------------------
    return render(
        request,
        "AidFi/f_afase.html",
        {
            "form": form,
            "beneficiaire": beneficiaire,
            "demande": demande,
            "action": action,
            "context_budget": context_budget,
        },
    )

# ==========================================================
# DÉTAIL AFASE
# ==========================================================

@login_required
def afase_detail(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.a_la_capacite("peut_voir"):
        return HttpResponseForbidden("Accès refusé")

    decision = getattr(demande, "decisionafase", None)

    return render(
        request,
        "AidFi/afase_detail.html",
        {
            "demande": demande,
            "decision": decision,
            "beneficiaire": demande.beneficiaire,
            "can_modifier": request.user.peut_agir_sur_objet(demande, "peut_modifier"),
            "can_decider": request.user.a_la_capacite("peut_decider"),
            "can_instruire": request.user.a_la_capacite("peut_instruire"),
        },
    )

# ==========================================================
# ÉVALUATION
# ==========================================================

@login_required
def afase_evaluation(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.a_la_capacite("peut_instruire"):
        return HttpResponseForbidden("Accès refusé")

    if demande.statut not in ["EN_INSTRUCTION", "BROUILLON"]:
        messages.error(request, "Cette demande n’est pas modifiable.")
        return redirect("AidFi:afase_detail", demande_id=demande.id)

    if request.method == "POST":
        form = EvaluationSocialeAFASEForm(request.POST, instance=demande.evaluation_afase)
        if form.is_valid():
            form.save()

            # ✅ RELAI TS → CADRE
            demande.statut = "DEPOSEE"
            demande.save(update_fields=["statut"])

            messages.success(
                request,
                "Instruction finalisée et demande transmise au cadre."
            )
            return redirect("AidFi:afase_detail", demande_id=demande.id)
    else:
        form = EvaluationSocialeAFASEForm(
            instance=getattr(demande, "evaluation_afase", None)
        )

    return render(
        request,
        "AidFi/afase_evaluation.html",
        {
            "demande": demande,
            "form": form,
            "beneficiaire": demande.beneficiaire,
        },
    )

# ==========================================================
# DÉCISION
# ==========================================================


@login_required
def afase_decision(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.a_la_capacite("peut_decider"):
        return HttpResponseForbidden("Accès refusé")

    # ✅ Le cadre ne décide QUE si la demande est déposée
    if demande.statut != "DEPOSEE":
        messages.error(request, "Cette demande n’est pas en attente de décision.")
        return redirect("AidFi:afase_detail", demande_id=demande.id)

    decision = getattr(demande, "decision", None)

    if request.method == "POST":
        action = request.POST.get("action")

        # 🔁 RETOUR EN INSTRUCTION
        if action == "RETOUR_INSTRUCTION":
            demande.statut = "EN_INSTRUCTION"
            demande.save(update_fields=["statut"])
            messages.success(request, "La demande a été retournée en instruction.")
            return redirect("AidFi:afase_detail", demande_id=demande.id)

        # ✅ DÉCISION FINALE
        form = DecisionAFASEForm(request.POST, instance=decision)
        if form.is_valid():
            with transaction.atomic():
                decision = form.save(commit=False)
                decision.demande = demande
                decision.decide_par = request.user
                decision.save()

                if decision.type_decision == "ACCORD":
                    demande.statut = "ACCORDEE"
                else:
                    demande.statut = "REFUSEE"

                demande.save(update_fields=["statut"])

                buffer = generer_pdf_afase(demande)
                stocker_pdf_afase(demande, buffer, request.user)

                messages.success(request, "Décision enregistrée.")
                return redirect("AidFi:afase_detail", demande_id=demande.id)

    else:
        form = DecisionAFASEForm(instance=decision)

    return render(
        request,
        "AidFi/afase_decision.html",
        {
            "demande": demande,
            "beneficiaire": demande.beneficiaire,
            "form": form,
        },
    )


# ==========================================================
# PDF
# ==========================================================

@login_required
def afase_pdf(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.a_la_capacite("peut_voir"):
        return HttpResponseForbidden("Accès refusé")

    buffer = generer_pdf_afase(demande)
    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f"afase_{demande.id}.pdf",
    )

# Alias compatibilité
afase_creer = afase_creer_ou_modifier
