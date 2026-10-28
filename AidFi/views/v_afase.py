# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/views/v_afase.py

from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils import timezone
import base64

from AidFi.forms.afase_workflow_form import AFASEWorkflowForm
from AidFi.forms.f_afase import EvaluationSocialeAFASEForm, DecisionAFASEForm
from AidFi.models.m_afase import DemandeAFASE
from AidFi.models.m_generique import PieceJustificative
from AidFi.services.afase_pdf import generer_pdf_afase
from AidFi.services import afase_circuit as circuit
from ged.services import stocker_pdf_afase
from ged.forms import DocumentGEDForm
from beneficiaire.models import Beneficiaire


# =============================================================================
# CRÉATION / MODIFICATION D'UNE DEMANDE AFASE
# =============================================================================

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
        if not demande.est_modifiable:
            messages.error(request, "Cette demande a fait l'objet d'une décision : elle n'est plus modifiable.")
            return redirect("AidFi:afase_detail", demande_id=demande.id)

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

    from AidFi.forms.afase_workflow_form import enfants_proposes
    from AidFi.services import budget_afase
    if request.method == "POST":
        # Formulaire réaffiché après une erreur : on garde ce qui a été saisi
        ressources, charges, dettes = budget_afase.depuis_post(request.POST)
        enfants_lignes = form._enfants_post() if hasattr(form, "_enfants_post") else []
    else:
        ressources = budget.ressources if budget else {}
        charges = budget.charges if budget else {}
        dettes = list(budget.dettes or []) if budget else []
        enfants_lignes = enfants_proposes(beneficiaire, demande)
    enfants_lignes = list(enfants_lignes) + [
        {"nom": "", "prenom": "", "date_naissance": None, "sexe": "", "situation": "", "a_naitre": False,
         "concerne": False, "beneficiaire_id": None} for _ in range(2)]
    dettes = dettes + [{"creancier": "", "montant": ""} for _ in range(max(3 - len(dettes), 1))]
    ancien_budget = bool(budget) and not (budget_afase.est_nouveau(budget.ressources)
                                          or budget_afase.est_nouveau(budget.charges)) and bool(budget.ressources or budget.charges)

    return render(
        request,
        "AidFi/f_afase.html",
        {
            "form": form,
            "beneficiaire": beneficiaire,
            "demande": demande,
            "action": action,
            "enfants_lignes": enfants_lignes,
            "grille": budget_afase.grille(ressources, charges),
            "dettes": dettes,
            "rubriques_ressources": budget_afase.RESSOURCES,
            "rubriques_charges": budget_afase.CHARGES,
            "colonnes_ressources": budget_afase.COLONNES_RESSOURCES,
            "colonnes_charges": budget_afase.COLONNES_CHARGES,
            "a_preciser": budget_afase.A_PRECISER,
            "ancien_budget": budget.affichage if ancien_budget else None,
        },
    )


# =============================================================================
# DÉTAIL D'UNE DEMANDE AFASE
# =============================================================================

@login_required
def afase_detail(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    vue_controle = circuit.controle_peut_voir(request.user, demande)
    if not (request.user.peut_agir_sur_objet(demande, "peut_voir") or vue_controle):
        return HttpResponseForbidden("Accès refusé")

    decision = getattr(demande, "decision", None)
    from AidFi.services.afase_alertes import alertes

    return render(
        request,
        "AidFi/afase_detail.html",
        {
            "demande": demande,
            "decision": decision,
            "alertes": alertes(demande) if not decision else [],
            "beneficiaire": demande.beneficiaire,
            "can_modifier": demande.est_modifiable and request.user.peut_agir_sur_objet(demande, "peut_modifier"),
            "can_decider": request.user.peut_agir_sur_objet(demande, "peut_decider"),
            "can_instruire": request.user.peut_agir_sur_objet(demande, "peut_instruire"),
            "can_paiement": _peut_suivre_paiement(request.user, demande, decision),
            # Circuit du paiement (contrôle → comptabilité → paierie)
            "pieces_requises": circuit.etat_pieces(demande),
            "pieces_manquantes": circuit.pieces_manquantes(demande),
            "can_transmettre": circuit.peut_transmettre(request.user, demande),
            "vue_controle": vue_controle,
            "can_ajouter_piece": _peut_ajouter_piece(request.user, demande),
        },
    )


def _peut_ajouter_piece(user, demande):
    """Avant décision : l'agent ; après un accord et avant transmission : aussi le cadre (compléter le dossier)."""
    if demande.est_modifiable and user.peut_agir_sur_objet(demande, "peut_modifier"):
        return True
    return demande.statut == "ACCORDEE" and (
        user.peut_agir_sur_objet(demande, "peut_modifier") or circuit.peut_transmettre(user, demande))


@login_required
def afase_transmettre(request, demande_id):
    """Le cadre (ou le secrétariat) transmet le dossier complet au service de contrôle."""
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)
    if request.method != "POST":
        return HttpResponseForbidden()
    try:
        circuit.transmettre(demande, request.user, request.POST.get("paiement_a"),
                            request.POST.get("organisme_paiement", ""), request.POST.get("identites") == "on")
        messages.success(request, "Dossier transmis à l'UAGAF.")
    except circuit.CircuitErreur as e:
        messages.error(request, str(e))
    return redirect("AidFi:afase_detail", demande_id=demande.id)


@login_required
def afase_controle_action(request, demande_id, action):
    """Service de contrôle : paiement demandé (logiciel comptable), paiement effectué, renvoi à la MDS."""
    from django.utils.dateparse import parse_date
    from decimal import InvalidOperation
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)
    if request.method != "POST" or not circuit.controle_peut_voir(request.user, demande):
        return HttpResponseForbidden("Accès réservé à l'UAGAF.")
    try:
        if action == "paiement-demande":
            circuit.demander_paiement(demande, request.user, parse_date(request.POST.get("date") or ""),
                                      request.POST.get("reference"))
            messages.success(request, "Demande de paiement enregistrée.")
        elif action == "paiement-effectue":
            circuit.enregistrer_paiement(demande, request.user, parse_date(request.POST.get("date") or ""),
                                         circuit.lire_montant(request.POST.get("montant")))
            messages.success(request, "Paiement enregistré : dossier clôturé, la MDS est prévenue.")
        elif action == "renvoi":
            circuit.renvoyer(demande, request.user, request.POST.get("motif"))
            messages.success(request, "Dossier renvoyé à la MDS.")
            return redirect("AidFi:afase_controle")
        else:
            return HttpResponseForbidden()
    except (circuit.CircuitErreur, InvalidOperation) as e:
        messages.error(request, str(e) if isinstance(e, circuit.CircuitErreur) else "Montant invalide.")
    return redirect("AidFi:afase_detail", demande_id=demande.id)


@login_required
def afase_controle(request):
    """File du service de contrôle : dossiers AFASE transmis par toutes les MDS."""
    if not circuit.est_controle(request.user):
        return HttpResponseForbidden("Accès réservé à l'UAGAF.")
    demandes = (DemandeAFASE.objects.filter(statut__in=('TRANSMISE_CONTROLE', 'PAIEMENT_DEMANDE'))
                .select_related('beneficiaire__mds', 'decision').order_by('decision__date_transmission_controle'))
    return render(request, "AidFi/afase_controle.html", {"demandes": demandes, "maintenant": timezone.now()})


def _peut_suivre_paiement(user, demande, decision):
    """Suivi du paiement d'une AFASE accordée : cadre, secrétariat ou gestion financière de la MDS."""
    if not decision or decision.type_decision != "ACCORD":
        return False
    return any(user.peut_agir_sur_objet(demande, cap)
               for cap in ("peut_decider", "peut_valider_cheque_aidfi", "peut_gerer_finance"))


@login_required
def afase_paiement(request, demande_id):
    """Enregistrer l'envoi à la régie, la délivrance et le montant délivré."""
    from decimal import Decimal, InvalidOperation
    from django.utils.dateparse import parse_date
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)
    decision = getattr(demande, "decision", None)
    if request.method != "POST" or not _peut_suivre_paiement(request.user, demande, decision):
        return HttpResponseForbidden("Accès refusé")
    decision.date_envoi_regie = parse_date(request.POST.get("date_envoi_regie") or "")
    decision.date_delivrance = parse_date(request.POST.get("date_delivrance") or "")
    try:
        montant = (request.POST.get("montant_delivre") or "").replace(",", ".").strip()
        decision.montant_delivre = Decimal(montant) if montant else None
    except InvalidOperation:
        messages.error(request, "Montant délivré invalide.")
        return redirect("AidFi:afase_detail", demande_id=demande.id)
    if decision.date_delivrance and decision.montant_delivre is None:
        decision.montant_delivre = decision.montant_accorde   # par défaut : le montant accordé
    decision.save(update_fields=["date_envoi_regie", "date_delivrance", "montant_delivre"])
    messages.success(request, "Suivi du paiement enregistré.")
    return redirect("AidFi:afase_detail", demande_id=demande.id)


# =============================================================================
# ÉVALUATION SOCIALE (TRAVAILLEUR SOCIAL)
# =============================================================================

@login_required
def afase_evaluation(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.peut_agir_sur_objet(demande, "peut_instruire"):
        return HttpResponseForbidden("Accès refusé")

    if not demande.est_modifiable:
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
            demande._acteur = request.user   # journal des statuts
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
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.peut_agir_sur_objet(demande, "peut_decider"):
        return HttpResponseForbidden("Accès refusé")

    if demande.statut != "DEPOSEE":
        messages.error(request, "Cette demande n'est pas en attente de décision.")
        return redirect("AidFi:afase_detail", demande_id=demande.id)

    decision = getattr(demande, "decision", None)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "RETOUR_INSTRUCTION":
            demande.statut = "EN_INSTRUCTION"
            demande._acteur = request.user   # journal des statuts
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

                demande.statut = {
                    "ACCORD": "ACCORDEE",
                    "REFUS": "REFUSEE",
                    "AJO": "AJO",   # retour au travailleur social
                }[decision.type_decision]
                demande._acteur = request.user   # journal des statuts
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


# =============================================================================
# PRÉVISUALISATION AVANT VALIDATION FINALE
# =============================================================================

@login_required
def afase_previsualisation(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not request.user.peut_agir_sur_objet(demande, "peut_voir"):
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
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not _peut_ajouter_piece(request.user, demande):
        messages.error(request, "Vous ne pouvez plus ajouter de pièce à cette demande.")
        return redirect("AidFi:afase_detail", demande_id=demande.id)

    if request.method == "POST":
        form = DocumentGEDForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            fichier = request.FILES["file"]
            doc = form.save(commit=False)
            doc.content_object = demande.beneficiaire
            doc.uploaded_by = request.user
            doc.save()
            # Stockage physique du fichier (version 1)
            try:
                doc.add_new_version(
                    buffer=fichier, filename=fichier.name,
                    user=request.user, raison=f"Pièce AFASE dossier {demande.id}",
                    request=request,
                )
            except Exception:
                doc.delete()
                messages.error(request, "Le fichier n'a pas pu être stocké. Réessayez plus tard.")
                return redirect("AidFi:afase_detail", demande_id=demande.id)

            from AidFi.models.m_generique import TYPE_PIECE_CHOICES
            type_piece = request.POST.get("type_piece")
            if type_piece not in dict(TYPE_PIECE_CHOICES):
                type_piece = 'AUTRE'
            PieceJustificative.objects.get_or_create(
                demande=demande,
                document_ged=doc,
                defaults={'type_piece': type_piece, 'statut': 'VALIDE'}
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
            "types_piece": __import__('AidFi.models.m_generique', fromlist=['x']).TYPE_PIECE_CHOICES,
            "type_initial": request.GET.get("type", ""),
        }
    )


# =============================================================================
# TÉLÉCHARGEMENT DU PDF OFFICIEL
# =============================================================================

@login_required
def afase_pdf(request, demande_id):
    demande = get_object_or_404(DemandeAFASE, pk=demande_id)

    if not (request.user.peut_agir_sur_objet(demande, "peut_voir") or circuit.controle_peut_voir(request.user, demande)):
        return HttpResponseForbidden("Accès refusé")

    buffer = generer_pdf_afase(demande)
    return FileResponse(
        buffer, 
        as_attachment=True, 
        filename=f"afase_{demande.id}.pdf"
    )


# Alias pour compatibilité
afase_creer = afase_creer_ou_modifier
