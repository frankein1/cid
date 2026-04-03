"""
# AidFi/views/v_afase.py - VERSION CORE UNIFIÉE + decideur 
"""

from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from AidFi.forms.f_afase import (DemandeAFASEForm, EvaluationSocialeAFASEForm, DecisionAFASEForm)
from AidFi.forms.afase_workflow_form import AFASEWorkflowForm
from AidFi.models.m_afase import DemandeAFASE, DecisionAFASE
from AidFi.services.afase_pdf import generer_pdf_afase

from beneficiaire.models import Beneficiaire
try:
    from mds.models import UserMDSProfile
except ImportError:
    UserMDSProfile = None

from ged.services import stocker_pdf_afase

@login_required
def afase_creer_ou_modifier(request, beneficiaire_id=None, demande_id=None):
    """
    Création / modification d'une demande AFASE.
    Surcharge pour gérer les deux cas d'utilisation :
    - Création : beneficiaire_id requis
    - Modification : demande_id requis
    """
    # DÉTERMINATION DU CONTEXTE
    demande = None
    beneficiaire = None
    
    if demande_id:
        # MODIFICATION : on a l'ID de la demande
        demande = get_object_or_404(DemandeAFASE, pk=demande_id)
        beneficiaire = demande.beneficiaire
        action = "modification"
        budget = getattr(demande, "budget", None)
        print("DEBUG budget lié :", budget)
    elif beneficiaire_id:
        # CRÉATION : on a l'ID du bénéficiaire
        beneficiaire = get_object_or_404(Beneficiaire, pk=beneficiaire_id)
        action = "création"
    else:
        return HttpResponseForbidden("Paramètres manquants")

    # SÉCURITÉ CORE
    if action == "création":
        if not request.user.peut_agir_sur_objet(beneficiaire, "peut_creer"):
            return HttpResponseForbidden("Accès refusé pour la création")
    else:  # modification
        if not request.user.peut_agir_sur_objet(demande, "peut_modifier"):
            return HttpResponseForbidden("Accès refusé pour la modification")

    if request.method == "POST":
        form = AFASEWorkflowForm(
            data=request.POST,
            beneficiaire=beneficiaire,
            user=request.user,
            demande=demande,
        )
        if form.is_valid():
            demande = form.save()
            messages.success(request, f"Demande AFASE {action} avec succès.")
            return redirect("AidFi:afase_detail", demande_id=demande.id)
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = AFASEWorkflowForm(
            beneficiaire=beneficiaire,
            user=request.user,
            demande=demande,
        )

    return render(
        request,
        "AidFi/f_afase.html",
        {
            "form": form,
            "beneficiaire": beneficiaire,
            "demande": demande,
            "action": action,
        },
    )

@login_required
def afase_detail(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.a_la_capacite("peut_voir"):
        return HttpResponseForbidden("Accès refusé")

    # Récupération de la décision si elle existe
    decision = None
    try:
        decision = demande.decision
    except DecisionAFASE.DoesNotExist:
        pass
    
    # Permissions pour les boutons d'action
    can_instruire = request.user.a_la_capacite("peut_instruire")
    can_decider = request.user.a_la_capacite("peut_decider")
    can_modifier = request.user.peut_agir_sur_objet(demande, "peut_modifier")

    return render(request, "AidFi/afase_detail.html", {
        "demande": demande,
        "decision": decision,
        "can_instruire": can_instruire,
        "can_decider": can_decider,
        "can_modifier": can_modifier,
        "beneficiaire": demande.beneficiaire,
    })

# ÉVALUATION
@login_required
def afase_evaluation(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)
    
    if not request.user.a_la_capacite("peut_instruire"):
        return HttpResponseForbidden("Accès refusé")

    if request.method == "POST":
        form = EvaluationSocialeAFASEForm(request.POST, instance=demande)
        if form.is_valid():
            form.save()
            demande.passer_en_instruction()  # Méthode à définir dans le modèle
            messages.success(request, "Évaluation enregistrée et dossier passé en instruction.")
            return redirect("AidFi:afase_detail", demande_id=demande.id)
    else:
        form = EvaluationSocialeAFASEForm(instance=demande)

    return render(request, "AidFi/afase_evaluation.html", {
        "demande": demande,
        "form": form,
        "beneficiaire": demande.beneficiaire
    })

# DÉCISION
@login_required
def afase_decision(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    # 🔒 Sécurité CORE
    if not request.user.a_la_capacite("peut_decider"):
        return HttpResponseForbidden("Accès refusé")

    # 🔒 On ne décide que si le dossier est prêt
    if demande.statut not in ["EN_INSTRUCTION", "EVALUATION"]:
        return HttpResponseForbidden("Dossier non décidable")

    decision = getattr(demande, "decisionafase", None)

    if request.method == "POST":
        form = DecisionAFASEForm(request.POST, instance=decision)
        if form.is_valid():
            with transaction.atomic():
                decision = form.save(commit=False)
                decision.demande = demande
                decision.decide_par = request.user
                decision.save()

                if decision.type_decision == "AJOURNEMENT":
                    demande.ajourner()
                    messages.info(request, "Dossier ajourné.")
                    return redirect("AidFi:afase_detail", demande_id=demande.id)

                # ✅ ACCORD ou REFUS = VERROUILLAGE
                demande.verrouiller()  # statut VALIDEE / REFUSEE

                # 📄 Génération PDF FINAL
                buffer = generer_pdf_afase(demande)

                # 📁 Stockage GED (version finale)
                stocker_pdf_afase(
                    demande=demande,
                    buffer=buffer,
                    user=request.user,
                )

                messages.success(request, f"Dossier {decision.get_type_decision_display().lower()} avec succès.")
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

# PDF
@login_required
def afase_pdf(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.a_la_capacite("peut_voir"):
        return HttpResponseForbidden("Accès refusé")

    buffer = generer_pdf_afase(demande)

    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f"afase_{demande.id}_{demande.beneficiaire.nom}.pdf",
    )

# Alias pour compatibilité
afase_creer = afase_creer_ou_modifier
