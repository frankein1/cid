# /AidFi/views/v_afase.py

from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from AidFi.forms.afase_workflow_form import AFASEWorkflowForm
from AidFi.forms.f_afase import (
    EvaluationSocialeAFASEForm,
    DecisionAFASEForm
)
from AidFi.models.m_afase import DemandeAFASE
from AidFi.services.afase_pdf import generer_pdf_afase
from ged.services import stocker_pdf_afase

from beneficiaire.models import Beneficiaire

# ==========================================================
# CRÉATION / MODIFICATION AFASE (TS)
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
        budget = getattr(demande, "budget", None)

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
    # CONTEXTE BUDGET
    # ------------------------------
    context_budget = {
        "ressources": budget.ressources,
        "charges": budget.charges,
    } if budget else {"ressources": {}, "charges": {}}

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

afase_creer = afase_creer_ou_modifier  # alias compatibilité

# ==========================================================
# DÉTAIL AFASE (DASHBOARD TS / CADRE)
# ==========================================================

@login_required
def afase_detail(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.a_la_capacite("peut_voir"):
        return HttpResponseForbidden("Accès refusé")

    decision = getattr(demande, "decision", None)
    evaluation = getattr(demande, "evaluation_afase", None)

    form_instruction = None
    if request.user.a_la_capacite("peut_instruire"):
        form_instruction = EvaluationSocialeAFASEForm(instance=evaluation)

    return render(
        request,
        "AidFi/afase_detail.html",
        {
            "demande": demande,
            "beneficiaire": demande.beneficiaire,
            "decision": decision,
            "form_instruction": form_instruction,
            "can_modifier": request.user.peut_agir_sur_objet(demande, "peut_modifier"),
            "can_decider": request.user.a_la_capacite("peut_decider"),
            "can_instruire": request.user.a_la_capacite("peut_instruire"),
        },
    )

# ==========================================================
# INSTRUCTION AFASE (TS)
# ==========================================================

@login_required
def afase_instruire(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.a_la_capacite("peut_instruire"):
        return HttpResponseForbidden("Accès refusé")

    evaluation = getattr(demande, "evaluation_afase", None)

    if request.method == "POST":
        form = EvaluationSocialeAFASEForm(request.POST, instance=evaluation)
        if form.is_valid():
            form.save()
            messages.success(request, "Instruction AFASE enregistrée.")
        else:
            messages.error(request, "Erreur dans l’instruction.")

    return redirect("AidFi:afase_detail", demande_id=demande.id)

# ==========================================================
# ENVOI AU CADRE (FIN INSTRUCTION TS)
# ==========================================================

@login_required
def afase_envoyer_cadre(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.a_la_capacite("peut_instruire"):
        return HttpResponseForbidden("Accès refusé")

    demande.statut = "EVALUATION"
    demande.save()

    messages.success(request, "Demande AFASE transmise au cadre.")
    return redirect("AidFi:afase_detail", demande_id=demande.id)

# ==========================================================
# DÉCISION (CADRE)
# ==========================================================

@login_required
def afase_decision(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.a_la_capacite("peut_decider"):
        return HttpResponseForbidden("Accès refusé")

    decision = getattr(demande, "decision", None)

    if request.method == "POST":
        form = DecisionAFASEForm(request.POST, instance=decision)
        if form.is_valid():
            with transaction.atomic():
                decision = form.save(commit=False)
                decision.demande = demande
                decision.decide_par = request.user
                decision.save()

                demande.verrouiller()

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

# ==========================================================
# ÉVALUATION SOCIALE (LEGACY / COMPATIBILITÉ)
# ==========================================================

@login_required
def afase_evaluation(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.a_la_capacite("peut_instruire"):
        return HttpResponseForbidden("Accès refusé")

    if demande.est_verrouillee:
        messages.error(request, "Demande verrouillée. Évaluation impossible.")
        return redirect("AidFi:afase_detail", demande_id=demande.id)

    evaluation = getattr(demande, "evaluation_afase", None)

    if request.method == "POST":
        form = EvaluationSocialeAFASEForm(request.POST, instance=evaluation)
        if form.is_valid():
            form.save()
            messages.success(request, "Évaluation sociale enregistrée.")
            return redirect("AidFi:afase_detail", demande_id=demande.id)
    else:
        form = EvaluationSocialeAFASEForm(instance=evaluation)

    return render(
        request,
        "AidFi/afase_evaluation.html",
        {
            "demande": demande,
            "beneficiaire": demande.beneficiaire,
            "form": form,
        },
    )
