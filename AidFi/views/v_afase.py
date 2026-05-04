from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from AidFi.forms.afase_workflow_form import AFASEWorkflowForm
from AidFi.forms.f_afase import EvaluationSocialeAFASEForm, DecisionAFASEForm
from AidFi.models.m_afase import DemandeAFASE
from AidFi.services.afase_pdf import generer_pdf_afase
from ged.services import stocker_pdf_afase

from beneficiaire.models import Beneficiaire


@login_required
def afase_creer_ou_modifier(request, beneficiaire_id=None, demande_id=None):
    demande = None
    beneficiaire = None
    budget = None

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

    if action == "création":
        if not request.user.peut_agir_sur_objet(beneficiaire, "peut_creer"):
            return HttpResponseForbidden("Accès refusé")
    else:
        if not request.user.peut_agir_sur_objet(demande, "peut_modifier"):
            return HttpResponseForbidden("Accès refusé")

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
        messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = AFASEWorkflowForm(
            beneficiaire=beneficiaire,
            user=request.user,
            demande=demande,
        )
        if not demande and beneficiaire.numero_genesis:
            form.fields["numero_genesis"].initial = beneficiaire.numero_genesis

    context_budget = {
        "ressources": budget.ressources,
        "charges": budget.charges,
    } if budget else {"ressources": {}, "charges": {}}

    nb_personnes_foyer = 1
    for lien in beneficiaire.liens_familiaux.all():
        if lien.vit_au_foyer:
            nb_personnes_foyer += 1

    return render(
        request,
        "AidFi/f_afase.html",
        {
            "form": form,
            "beneficiaire": beneficiaire,
            "demande": demande,
            "action": action,
            "context_budget": context_budget,
            "nb_personnes_foyer": nb_personnes_foyer,
        },
    )


@login_required
def afase_detail(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.a_la_capacite("peut_voir"):
        return HttpResponseForbidden("Accès refusé")

    decision = getattr(demande, "decision", None)

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


@login_required
def afase_evaluation(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.a_la_capacite("peut_instruire"):
        return HttpResponseForbidden("Accès refusé")

    if demande.statut not in ["EN_INSTRUCTION", "BROUILLON"]:
        messages.error(request, "Cette demande n’est pas modifiable.")
        return redirect("AidFi:afase_detail", demande_id=demande.id)

    if request.method == "POST":
        form = EvaluationSocialeAFASEForm(request.POST, instance=getattr(demande, "evaluation_afase", None))
        if form.is_valid():
            form.save()
            demande.statut = "DEPOSEE"
            demande.save(update_fields=["statut"])
            messages.success(request, "Instruction finalisée et demande transmise au cadre.")
            return redirect("AidFi:afase_detail", demande_id=demande.id)
    else:
        form = EvaluationSocialeAFASEForm(instance=getattr(demande, "evaluation_afase", None))

    return render(request, "AidFi/afase_evaluation.html", {"demande": demande, "form": form, "beneficiaire": demande.beneficiaire})


@login_required
def afase_decision(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.a_la_capacite("peut_decider"):
        return HttpResponseForbidden("Accès refusé")

    if demande.statut != "DEPOSEE":
        messages.error(request, "Cette demande n’est pas en attente de décision.")
        return redirect("AidFi:afase_detail", demande_id=demande.id)

    decision = getattr(demande, "decision", None)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "RETOUR_INSTRUCTION":
            demande.statut = "EN_INSTRUCTION"
            demande.save(update_fields=["statut"])
            messages.success(request, "La demande a été retournée en instruction.")
            return redirect("AidFi:afase_detail", demande_id=demande.id)

        form = DecisionAFASEForm(request.POST, instance=decision)
        if form.is_valid():
            with transaction.atomic():
                decision = form.save(commit=False)
                decision.demande = demande
                decision.decide_par = request.user
                decision.save()

                demande.statut = "ACCORDEE" if decision.type_decision == "ACCORD" else "REFUSEE"
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


@login_required
def afase_pdf(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.a_la_capacite("peut_voir"):
        return HttpResponseForbidden("Accès refusé")

    buffer = generer_pdf_afase(demande)
    return FileResponse(buffer, as_attachment=True, filename=f"afase_{demande.id}.pdf")
