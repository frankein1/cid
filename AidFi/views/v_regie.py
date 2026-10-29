# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/views/v_regie.py
"""
Régie d'urgence, sur le modèle des CAP :
  AS propose → cadre (ou adjoint, secrétaire générale) décide → régie centrale verse sous 24 h → clôture.
Le versement se fait en espèces ou à un tiers (facture et RIB joints, montant éventuellement partiel).
"""
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from beneficiaire.models import Beneficiaire
from AidFi.forms.f_regie import DecisionRegieForm, DemandeRegieForm
from AidFi.models.m_generique import PieceJustificative, TypeAide
from AidFi.models.m_regie import DELAI_VERSEMENT_HEURES, DemandeRegie

DECIDER = 'peut_valider_cheque_aidfi'      # cadre, adjoints, secrétaire générale (comme les CAP)
REGIE_CENTRALE = 'cap_regie_centrale'


def _regie_max():
    """Maximum de la régie s'il a été saisi dans les paramètres (sinon : rappel seulement)."""
    from AidFi.models.m_referentiel import ParametresAides
    return ParametresAides.actuels().regie_montant_max


def _peut_voir(user, d):
    return (user.peut_agir_sur_objet(d, 'peut_voir') or user.peut_agir_sur_objet(d, DECIDER)
            or (user.a_la_capacite(REGIE_CENTRALE) and d.statut in ('TRANSMISE_PAIERIE', 'CLOTUREE')))


def _joindre(demande, fichier, type_piece, titre, user, request):
    """Pièce jointe (facture, RIB du tiers) : rangée dans la GED de l'usager et liée à la demande."""
    from ged.models import DocumentGED, DocumentType
    type_doc, _ = DocumentType.objects.get_or_create(
        code="REGIE_PIECE", defaults={"nom": "Pièce de régie d'urgence", "categorie": "finances",
                                      "extensions_autorisees": ["pdf", "jpg", "jpeg", "png"],
                                      "taille_max_mb": 10, "est_sensible": True, "actif": True})
    doc = DocumentGED.objects.create(content_object=demande.beneficiaire, type_document=type_doc,
                                     titre=f"{titre} – régie d'urgence n° {demande.pk}",
                                     confidentialite="RESTREINT", uploaded_by=user)
    doc.add_new_version(buffer=fichier, filename=fichier.name, user=user,
                        raison=f"Régie d'urgence n° {demande.pk}", request=request)
    PieceJustificative.objects.create(demande=demande, document_ged=doc, type_piece=type_piece,
                                      statut='VALIDE', verifie_par=user, date_verification=timezone.now())


@login_required
def regie_urgence_create(request, beneficiaire_id):
    beneficiaire = get_object_or_404(Beneficiaire, pk=beneficiaire_id)
    if not request.user.peut_agir_sur_objet(beneficiaire, 'peut_instruire'):
        return HttpResponseForbidden("Seul(e) un(e) assistant(e) social(e) de la MDS de l'usager peut demander une régie.")
    form = DemandeRegieForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        type_regie, _ = TypeAide.objects.get_or_create(
            code='REGIE', defaults={'nom': "Régie d'urgence", 'description': "Versement d'urgence par la régie centrale",
                                    'actif': True, 'cree_par': request.user})
        try:
            with transaction.atomic():
                demande = DemandeRegie(
                    beneficiaire=beneficiaire, demandeur=beneficiaire, type_aide=type_regie,
                    montant_sollicite=cd['montant'], motivation=cd['motivation'],
                    mode_paiement=cd['mode_paiement'],
                    tiers_nom=cd['tiers_nom'] if cd['mode_paiement'] == 'TIERS' else "",
                    tiers_reference=cd['tiers_reference'] if cd['mode_paiement'] == 'TIERS' else "",
                    statut='DEPOSEE', cree_par=request.user)
                demande._acteur = request.user          # journal + message au responsable de la MDS
                demande.save()
                if cd['mode_paiement'] == 'TIERS':
                    _joindre(demande, cd['facture'], 'FACTURE_DEVIS', "Facture du tiers", request.user, request)
                    _joindre(demande, cd['rib_tiers'], 'RIB', "RIB du tiers", request.user, request)
        except Exception:
            messages.error(request, "Les pièces n'ont pas pu être enregistrées. Réessayez plus tard.")
            return render(request, "AidFi/regie_form.html", {"form": form, "beneficiaire": beneficiaire})
        messages.success(request, "Demande de régie d'urgence transmise au cadre.")
        return redirect("AidFi:regie_detail", demande_id=demande.pk)
    return render(request, "AidFi/regie_form.html", {"form": form, "beneficiaire": beneficiaire})


@login_required
def regie_detail(request, demande_id):
    d = get_object_or_404(DemandeRegie.objects.select_related('beneficiaire__mds'), pk=demande_id)
    if not _peut_voir(request.user, d):
        return HttpResponseForbidden("Accès refusé")
    return render(request, "AidFi/regie_detail.html", {
        "demande": d, "beneficiaire": d.beneficiaire, "suivis": d.suivis.order_by('id'),
        "pieces": d.pieces_justificatives.select_related('document_ged'),
        "can_decider": d.statut == 'DEPOSEE' and request.user.peut_agir_sur_objet(d, DECIDER),
        "can_verser": d.statut == 'TRANSMISE_PAIERIE' and request.user.a_la_capacite(REGIE_CENTRALE),
        "decision_form": DecisionRegieForm(initial={'decision': 'ACCORD', 'montant_accorde': d.montant_sollicite}),
        "delai": DELAI_VERSEMENT_HEURES,
        "regie_max": _regie_max(),
    })


@login_required
@require_POST
def regie_decision(request, demande_id):
    d = get_object_or_404(DemandeRegie, pk=demande_id)
    if d.statut != 'DEPOSEE' or not request.user.peut_agir_sur_objet(d, DECIDER):
        return HttpResponseForbidden("Accès refusé")
    form = DecisionRegieForm(request.POST)
    if not form.is_valid():
        for erreurs in form.errors.values():
            for e in erreurs:
                messages.error(request, e)
        return redirect("AidFi:regie_detail", demande_id=d.pk)
    d.decide_par, d.date_decision = request.user, timezone.now()
    if form.cleaned_data['decision'] == 'ACCORD':
        d.montant_accorde = form.cleaned_data['montant_accorde']
        d.statut = 'TRANSMISE_PAIERIE'          # part directement à la régie centrale
    else:
        d.motif_refus = form.cleaned_data['motif_refus']
        d.statut = 'REFUSEE'
    d._acteur = request.user                    # journal + message à l'AS (+ régie centrale)
    d.save()
    plafond = _regie_max()
    if plafond is not None and d.montant_accorde and d.montant_accorde > plafond:
        messages.warning(request, f"Montant supérieur au maximum renseigné pour la régie ({plafond} €) : "
                                  "vérifiez la note de service en vigueur.")
    messages.success(request, f"Décision enregistrée : {d.get_statut_display()}.")
    return redirect("AidFi:regie_detail", demande_id=d.pk)


@login_required
@require_POST
def regie_versement(request, demande_id):
    """Régie centrale : versement effectué (espèces ou tiers) → clôture, l'AS et le cadre sont prévenus."""
    from django.utils.dateparse import parse_datetime
    d = get_object_or_404(DemandeRegie, pk=demande_id)
    if d.statut != 'TRANSMISE_PAIERIE' or not request.user.a_la_capacite(REGIE_CENTRALE):
        return HttpResponseForbidden("Accès réservé à la régie centrale.")
    try:
        texte = (request.POST.get("montant") or "").replace(",", ".").strip()
        montant = Decimal(texte) if texte else d.montant_accorde
    except InvalidOperation:
        messages.error(request, "Montant invalide.")
        return redirect("AidFi:regie_detail", demande_id=d.pk)
    if montant <= 0 or montant > d.montant_accorde:
        messages.error(request, "Le montant versé doit être positif et ne pas dépasser le montant accordé.")
        return redirect("AidFi:regie_detail", demande_id=d.pk)
    quand = parse_datetime(request.POST.get("date") or "")
    d.date_versement = timezone.make_aware(quand) if quand and timezone.is_naive(quand) else (quand or timezone.now())
    d.montant_verse, d.verse_par = montant, request.user
    d.reference_comptable = (request.POST.get("reference_comptable") or "").strip()[:60]
    d.statut, d._acteur = 'CLOTUREE', request.user
    d.save()
    from AidFi.signals import prevenir_versement_regie
    prevenir_versement_regie(d, request.user)
    messages.success(request, "Versement enregistré : dossier clôturé, l'AS et le cadre sont prévenus.")
    return redirect("AidFi:regie_detail", demande_id=d.pk)
