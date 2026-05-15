# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: Perplexity / DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/views/v_afase.py - Version complète et corrigée
# Gestion complète du workflow AFASE : création, instruction, décision,
# prévisualisation, gestion des documents GED et génération PDF
# =============================================================================

from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
import base64

from AidFi.forms.afase_workflow_form import AFASEWorkflowForm
from AidFi.forms.f_afase import EvaluationSocialeAFASEForm, DecisionAFASEForm
from AidFi.models.m_afase import DemandeAFASE
from AidFi.models.m_generique import PieceJustificative
from AidFi.services.afase_pdf import generer_pdf_afase
from ged.services import stocker_pdf_afase
from ged.forms import DocumentGEDForm
from beneficiaire.models import Beneficiaire


# =============================================================================
# CRÉATION / MODIFICATION D'UNE DEMANDE AFASE
# =============================================================================

@login_required
def afase_creer_ou_modifier(request, beneficiaire_id=None, demande_id=None):
    """
    Vue unifiée pour la création et la modification d'une demande AFASE.
    - Si demande_id est fourni : édition d'une demande existante
    - Sinon : création d'une nouvelle demande pour le bénéficiaire
    """
    demande = None
    beneficiaire = None
    budget = None

    # Récupération du contexte
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

    # Vérification des droits
    if action == "création":
        if not request.user.peut_agir_sur_objet(beneficiaire, "peut_creer"):
            return HttpResponseForbidden("Accès refusé")
    else:
        if not request.user.peut_agir_sur_objet(demande, "peut_modifier"):
            return HttpResponseForbidden("Accès refusé")

    # Traitement du formulaire
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

    # Préparation du contexte pour le template
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


# =============================================================================
# DÉTAIL D'UNE DEMANDE AFASE
# =============================================================================

@login_required
def afase_detail(request, demande_id):
    """
    Affichage du détail d'une demande AFASE.
    Visible par les agents et cadres selon leurs droits.
    """
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


# =============================================================================
# ÉVALUATION SOCIALE (TRAVAILLEUR SOCIAL)
# =============================================================================

@login_required
def afase_evaluation(request, demande_id):
    """
    Phase d'instruction par le travailleur social.
    Remplit l'évaluation sociale et transmet au cadre.
    """
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.a_la_capacite("peut_instruire"):
        return HttpResponseForbidden("Accès refusé")

    if demande.statut not in ["EN_INSTRUCTION", "BROUILLON"]:
        messages.error(request, "Cette demande n'est pas modifiable.")
        return redirect("AidFi:afase_detail", demande_id=demande.id)

    if request.method == "POST":
        form = EvaluationSocialeAFASEForm(
            request.POST, 
            instance=getattr(demande, "evaluation_afase", None)
        )
        if form.is_valid():
            form.save()
            demande.statut = "DEPOSEE"
            demande.save(update_fields=["statut"])
            messages.success(request, "Instruction finalisée et demande transmise au cadre.")
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
            "beneficiaire": demande.beneficiaire
        }
    )


# =============================================================================
# DÉCISION CADRE
# =============================================================================

@login_required
def afase_decision(request, demande_id):
    """
    Phase de décision par le cadre.
    - Peut retourner la demande en instruction
    - Peut accorder ou refuser avec motif
    """
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.a_la_capacite("peut_decider"):
        return HttpResponseForbidden("Accès refusé")

    if demande.statut != "DEPOSEE":
        messages.error(request, "Cette demande n'est pas en attente de décision.")
        return redirect("AidFi:afase_detail", demande_id=demande.id)

    decision = getattr(demande, "decision", None)

    if request.method == "POST":
        action = request.POST.get("action")

        # Retour en instruction
        if action == "RETOUR_INSTRUCTION":
            demande.statut = "EN_INSTRUCTION"
            demande.save(update_fields=["statut"])
            messages.success(request, "La demande a été retournée en instruction.")
            return redirect("AidFi:afase_detail", demande_id=demande.id)

        # Décision finale (accord ou refus)
        form = DecisionAFASEForm(request.POST, instance=decision)
        if form.is_valid():
            with transaction.atomic():
                decision = form.save(commit=False)
                decision.demande = demande
                decision.decide_par = request.user
                decision.save()

                demande.statut = "ACCORDEE" if decision.type_decision == "ACCORD" else "REFUSEE"
                demande.save(update_fields=["statut"])

                # Génération et archivage du PDF
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


# =============================================================================
# PRÉVISUALISATION AVANT VALIDATION FINALE
# =============================================================================

@login_required
def afase_previsualisation(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    # ✅ N'importe quel agent MDS peut prévisualiser (pas besoin de "peut_decider")
    if not request.user.a_la_capacite("peut_voir"):
        return HttpResponseForbidden()

    buffer = generer_pdf_afase(demande)
    b64_pdf = base64.b64encode(buffer.getvalue()).decode('utf-8')
    buffer.close()

    return render(request, "AidFi/afase_previsualisation.html", {
        "demande": demande,
        "pdf_data": b64_pdf,
    })


# =============================================================================
# AJOUT DE DOCUMENT GED À LA VOLÉE
# =============================================================================

@login_required
def ajouter_document_afase(request, demande_id):
    """
    Permet à l'agent ou au cadre d'ajouter un document GED
    directement depuis l'interface AFASE.
    Le document est automatiquement lié à la demande.
    """
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.peut_agir_sur_objet(demande, "peut_modifier"):
        return HttpResponseForbidden()

    if request.method == "POST":
        form = DocumentGEDForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.content_object = demande.beneficiaire
            doc.uploaded_by = request.user
            doc.save()

            # Liaison automatique à la demande via PieceJustificative
            PieceJustificative.objects.get_or_create(
                demande=demande,
                document_ged=doc,
                defaults={'type_piece': 'AUTRE', 'statut': 'VALIDE'}
            )
            messages.success(request, "Document ajouté et lié à la demande.")
            return redirect("AidFi:afase_detail", demande_id=demande.id)
    else:
        form = DocumentGEDForm(user=request.user)

    return render(
        request, 
        "AidFi/afase_ajouter_document.html", 
        {
            "form": form,
            "demande": demande,
        }
    )


# =============================================================================
# TÉLÉCHARGEMENT DU PDF OFFICIEL
# =============================================================================

@login_required
def afase_pdf(request, demande_id):
    """
    Téléchargement du PDF officiel de la demande AFASE.
    Accessible en lecture seule.
    """
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.a_la_capacite("peut_voir"):
        return HttpResponseForbidden("Accès refusé")

    buffer = generer_pdf_afase(demande)
    return FileResponse(
        buffer, 
        as_attachment=True, 
        filename=f"afase_{demande.id}.pdf"
    )
