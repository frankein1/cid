# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# ru/views.py
from io import BytesIO
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ged.models import DocumentGED, DocumentType
from mds.models import UserMDSProfile
from .forms import (
    DemandeRUForm, FicheRetourSASForm, PieceRUForm, TraitementRUForm, TransmissionMDSForm,
)
from .models import DemandeRelationUsager, FicheRetourSAS
from .services import (
    affecter_a_un_travailleur, journaliser, peut_gerer_mds, peut_gerer_sas,
    relancer as service_relancer, soumettre_evaluation, transmettre_reponse,
    transmettre_sas_vers_mds, valider_evaluation,
)

logger = logging.getLogger(__name__)


def _demandes_visibles(user):
    if peut_gerer_sas(user):
        return DemandeRelationUsager.objects.all()
    if not user.a_la_capacite("peut_voir"):
        return DemandeRelationUsager.objects.none()
    mds_ids = UserMDSProfile.objects.filter(user=user, actif=True).values_list("mds_id", flat=True)
    return DemandeRelationUsager.objects.filter(mds_id__in=mds_ids, date_notification_mds__isnull=False)


def _demande_pour_user(user, pk):
    demande = get_object_or_404(
        _demandes_visibles(user).select_related("mds", "agent_assigne", "validee_par", "reponse_transmise_par"),
        pk=pk,
    )
    if not demande.peut_etre_vu_par(user):
        raise PermissionDenied("Cette demande est hors de votre périmètre d'accès.")
    return demande


def _peut_modifier_traitement(user, demande):
    if not peut_gerer_mds(user, demande) or demande.est_cloturee:
        return False
    statut = DemandeRelationUsager.Statut
    if user.a_la_capacite("peut_valider"):
        # Le cadre peut affecter et corriger l'évaluation jusqu'au visa. Après visa, l'évaluation est figée :
        # toute modification exigerait un nouveau visa, ce que le circuit ne prévoit pas.
        return demande.statut in (statut.A_TRAITER_MDS, statut.EN_EVALUATION, statut.A_VALIDER_CADRE)
    return demande.agent_assigne_id == user.pk and demande.statut == statut.EN_EVALUATION


def _peut_modifier_saisine(user, demande):
    return bool(
        not demande.est_cloturee
        and ((peut_gerer_sas(user) and demande.statut == DemandeRelationUsager.Statut.A_TRAITER_SAS)
             or (peut_gerer_mds(user, demande) and demande.statut == DemandeRelationUsager.Statut.A_TRAITER_MDS))
    )


@login_required
def liste(request):
    user = request.user
    if not (peut_gerer_sas(user) or user.a_la_capacite("peut_voir")):
        raise PermissionDenied("L'accès au module Relation Usager n'est pas autorisé.")
    queryset = _demandes_visibles(user).select_related("mds", "agent_assigne")
    recherche = request.GET.get("q", "").strip()
    statut = request.GET.get("statut", "")
    priorite = request.GET.get("priorite", "")
    if recherche:
        queryset = queryset.filter(
            Q(nom_usager__icontains=recherche) | Q(prenom_usager__icontains=recherche)
            | Q(objet__icontains=recherche) | Q(reference_sap__icontains=recherche)
            | Q(emetteur__icontains=recherche)
        )
    if statut:
        queryset = queryset.filter(statut=statut)
    if priorite:
        queryset = queryset.filter(priorite=priorite)
    demandes = list(queryset)
    if request.GET.get("retard") == "1":
        demandes = [d for d in demandes if d.est_en_retard]
    return render(request, "ru/liste.html", {
        "demandes": demandes,
        "recherche": recherche,
        "statut_selectionne": statut,
        "priorite_selectionnee": priorite,
        "statuts": DemandeRelationUsager.Statut.choices,
        "priorites": DemandeRelationUsager.Priorite.choices,
        "peut_creer": peut_gerer_sas(user) or (user.a_la_capacite("peut_creer") and user.a_la_capacite("peut_voir")),
        "gestion_sas": peut_gerer_sas(user),
    })


@login_required
def creer(request):
    user = request.user
    if not (peut_gerer_sas(user) or (user.a_la_capacite("peut_creer") and user.a_la_capacite("peut_voir"))):
        raise PermissionDenied("La création d'une demande RU n'est pas autorisée.")
    if request.method == "POST":
        form = DemandeRUForm(request.POST, user=user)
        if form.is_valid():
            demande = form.save(commit=False)
            demande.cree_par = user
            if demande.circuit == DemandeRelationUsager.Circuit.MDS:
                if peut_gerer_sas(user):
                    # Le délai MDS ne démarre qu'au clic explicite d'envoi au travailleur social.
                    demande.date_notification_mds = None
                    demande.statut = DemandeRelationUsager.Statut.A_TRAITER_SAS
                else:
                    # Saisine reçue directement par la MDS : le délai part de la réception.
                    demande.date_notification_mds = demande.date_notification_mds or demande.date_reception
                    demande.statut = DemandeRelationUsager.Statut.A_TRAITER_MDS
            else:
                demande.mds = None
                demande.date_notification_mds = None
                demande.statut = DemandeRelationUsager.Statut.A_TRAITER_SAS
            demande.save()
            journaliser(demande, "CREATION", user, f"Demande reçue par {demande.get_canal_display()}")
            messages.success(request, f"Demande {demande.reference} enregistrée.")
            return redirect("ru:detail", pk=demande.pk)
    else:
        initial = {}
        if not peut_gerer_sas(user):
            initial["circuit"] = DemandeRelationUsager.Circuit.MDS
        form = DemandeRUForm(user=user, initial=initial)
    return render(request, "ru/formulaire.html", {"form": form, "titre": "Nouvelle demande Relation Usager"})


@login_required
def detail(request, pk):
    demande = _demande_pour_user(request.user, pk)
    peut_sas = peut_gerer_sas(request.user)
    peut_cadre = bool(demande.mds_id and peut_gerer_mds(request.user, demande) and request.user.a_la_capacite("peut_valider"))
    peut_traiter = _peut_modifier_traitement(request.user, demande)
    try:
        fiche = demande.fiche_retour_sas
    except FicheRetourSAS.DoesNotExist:
        fiche = None
    ct = ContentType.objects.get_for_model(DemandeRelationUsager)
    pieces = DocumentGED.objects.filter(content_type=ct, object_id=demande.pk).select_related("type_document", "uploaded_by")
    type_document = DocumentType.objects.filter(code="RU_PJ", actif=True).first()
    transmission_form = TransmissionMDSForm(demande=demande)
    fiche_form = FicheRetourSASForm(instance=fiche, demande=demande)
    piece_form = PieceRUForm(type_document=type_document)
    traitement_form = TraitementRUForm(user=request.user, instance=demande)
    return render(request, "ru/detail.html", {
        "demande": demande,
        "historique": demande.historique.select_related("acteur"),
        "relances": demande.relances.select_related("effectuee_par"),
        "pieces": pieces,
        "piece_form": piece_form,
        "traitement_form": traitement_form,
        "transmission_form": transmission_form,
        "fiche_form": fiche_form,
        "fiche": fiche,
        "type_document_disponible": bool(type_document),
        "peut_sas": peut_sas,
        "peut_cadre": peut_cadre,
        "peut_traiter": peut_traiter,
        "peut_modifier_saisine": _peut_modifier_saisine(request.user, demande),
        "peut_relancer": peut_sas and demande.est_en_retard and not demande.est_cloturee,
        "peut_saisir_fiche_sas": peut_sas and not demande.est_cloturee and demande.statut in (
            DemandeRelationUsager.Statut.A_TRAITER_SAS, DemandeRelationUsager.Statut.A_VALIDER_SAS,
        ),
    })


@login_required
def modifier(request, pk):
    demande = _demande_pour_user(request.user, pk)
    if not _peut_modifier_saisine(request.user, demande):
        raise PermissionDenied("Modification non autorisée ou demande déjà clôturée.")
    if request.method == "POST":
        form = DemandeRUForm(request.POST, user=request.user, instance=demande)
        if form.is_valid():
            form.save()
            journaliser(demande, "MISE_A_JOUR_SAISINE", request.user)
            messages.success(request, "Les informations de la demande ont été mises à jour.")
            return redirect("ru:detail", pk=demande.pk)
    else:
        form = DemandeRUForm(user=request.user, instance=demande)
    return render(request, "ru/formulaire.html", {"form": form, "titre": f"Modifier {demande.reference}", "demande": demande})


@login_required
@require_POST
def transmettre_mds(request, pk):
    demande = _demande_pour_user(request.user, pk)
    form = TransmissionMDSForm(request.POST, demande=demande)
    if not form.is_valid():
        messages.error(request, "Choisissez une MDS et un travailleur social rattaché à cette MDS.")
        return redirect("ru:detail", pk=demande.pk)
    try:
        transmettre_sas_vers_mds(demande, form.cleaned_data["mds"], form.cleaned_data["agent"], request.user)
        messages.success(request, f"Demande transmise à {form.cleaned_data['agent'].get_full_name()} ({form.cleaned_data['mds'].nom}).")
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, str(exc))
    return redirect("ru:detail", pk=demande.pk)


@login_required
@require_POST
def traitement(request, pk):
    demande = _demande_pour_user(request.user, pk)
    if demande.est_cloturee or not _peut_modifier_traitement(request.user, demande):
        raise PermissionDenied("Vous ne pouvez pas modifier le traitement de cette demande.")
    action = request.POST.get("action", "enregistrer")
    peut_cadre = request.user.is_superuser or request.user.a_la_capacite("peut_valider")
    if action == "affecter" and not peut_cadre:
        raise PermissionDenied("Seul le cadre MDS peut affecter le travailleur social.")
    form = TraitementRUForm(request.POST, user=request.user, instance=demande)
    if not form.is_valid():
        messages.error(request, "Le formulaire de traitement contient des erreurs.")
        return redirect("ru:detail", pk=demande.pk)
    with transaction.atomic():
        updated = form.save(commit=False)
        if not peut_cadre:
            updated.agent_assigne = demande.agent_assigne
        updated.save()
        if action == "affecter":
            try:
                affecter_a_un_travailleur(demande, updated.agent_assigne, request.user)
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, str(exc))
                return redirect("ru:detail", pk=demande.pk)
        elif action == "soumettre":
            try:
                soumettre_evaluation(demande, request.user)
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, str(exc))
                return redirect("ru:detail", pk=demande.pk)
        else:
            journaliser(demande, "MISE_A_JOUR_EVALUATION", request.user)
    messages.success(request, "Le traitement de la demande a été enregistré.")
    return redirect("ru:detail", pk=demande.pk)


@login_required
@require_POST
def fiche_retour(request, pk):
    demande = _demande_pour_user(request.user, pk)
    if not (peut_gerer_sas(request.user) and not demande.est_cloturee and demande.statut in (
        DemandeRelationUsager.Statut.A_TRAITER_SAS, DemandeRelationUsager.Statut.A_VALIDER_SAS,
    )):
        raise PermissionDenied("La fiche retour est réservée au SAS à l'étape de finalisation.")
    try:
        fiche = demande.fiche_retour_sas
    except FicheRetourSAS.DoesNotExist:
        fiche = FicheRetourSAS(demande=demande, cree_par=request.user)
    form = FicheRetourSASForm(request.POST, instance=fiche, demande=demande)
    if form.is_valid():
        fiche = form.save(commit=False)
        fiche.demande = demande
        fiche.modifie_par = request.user
        fiche.save()
        demande.usager_informe_transmission = form.cleaned_data["usager_informe_transmission"]
        demande.date_information_usager = form.cleaned_data["date_information_usager"]
        demande.save(update_fields=["usager_informe_transmission", "date_information_usager", "updated_at"])
        journaliser(demande, "FICHE_RETOUR_SAS", request.user, "Fiche de retour SAS enregistrée")
        messages.success(request, "La fiche retour SAS a été enregistrée.")
    else:
        messages.error(request, "Vérifiez les champs de la fiche retour SAS.")
    return redirect("ru:detail", pk=demande.pk)


@login_required
@require_POST
def action(request, pk):
    demande = _demande_pour_user(request.user, pk)
    code = request.POST.get("action", "")
    try:
        if code == "valider_mds":
            valider_evaluation(demande, request.user)
            messages.success(request, "Évaluation validée. Le SAS est informé dans la messagerie CID.")
        elif code == "transmettre_reponse":
            transmettre_reponse(demande, request.user)
            messages.success(request, "La transmission finale est enregistrée et le dossier est clôturé. L'envoi externe n'est pas automatisé.")
        elif code == "relancer":
            service_relancer(demande, request.user, request.POST.get("commentaire", ""))
            if demande.date_escalade_direction:
                messages.success(request, "Troisième relance enregistrée : transmission à la direction tracée.")
            else:
                messages.success(request, "Relance enregistrée.")
        else:
            raise ValidationError("Action inconnue.")
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, str(exc))
    return redirect("ru:detail", pk=demande.pk)


@login_required
@require_POST
def ajouter_piece(request, pk):
    demande = _demande_pour_user(request.user, pk)
    if demande.est_cloturee or not (peut_gerer_sas(request.user) or peut_gerer_mds(request.user, demande)):
        raise PermissionDenied("Téléversement non autorisé.")
    type_document = DocumentType.objects.filter(code="RU_PJ", actif=True).first()
    if not type_document:
        messages.error(request, "Le type GED des pièces RU n'est pas installé. Appliquez les migrations.")
        return redirect("ru:detail", pk=demande.pk)
    form = PieceRUForm(request.POST, request.FILES, type_document=type_document)
    if form.is_valid():
        try:
            fichier = form.cleaned_data["fichier"]
            DocumentGED.create_from_buffer(
                buffer=fichier, filename=fichier.name, content_object=demande,
                type_document=type_document, user=request.user, confidentialite="RESTREINT",
                raison=f"Pièce de la demande {demande.reference}: {form.cleaned_data['titre']}", request=request,
            )
            journaliser(demande, "PIECE_AJOUTEE", request.user, form.cleaned_data["titre"])
            messages.success(request, "La pièce a été versée à la GED sécurisée.")
        except Exception:
            logger.exception("Échec du dépôt GED d'une pièce RU %s", demande.pk)
            messages.error(request, "La GED n'a pas pu enregistrer cette pièce.")
    else:
        messages.error(request, "Vérifiez le titre et le fichier PDF (format / taille autorisés).")
    return redirect("ru:detail", pk=demande.pk)


@login_required
def formulaire_pdf(request, pk):
    demande = _demande_pour_user(request.user, pk)
    from .pdf import rendre_formulaire
    buffer = BytesIO()
    rendre_formulaire(demande, buffer)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{demande.reference}.pdf"'
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
def fiche_retour_pdf(request, pk):
    demande = _demande_pour_user(request.user, pk)
    if not peut_gerer_sas(request.user) or not hasattr(demande, "fiche_retour_sas"):
        raise PermissionDenied("La fiche retour SAS n'est pas disponible.")
    from .pdf import rendre_fiche_retour_sas
    buffer = BytesIO()
    rendre_fiche_retour_sas(demande.fiche_retour_sas, buffer)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Fiche-retour-SAS-{demande.reference}.pdf"'
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
def courrier_rdv_pdf(request, pk, rang):
    demande = _demande_pour_user(request.user, pk)
    if rang not in (1, 2) or demande.est_cloturee or not (
        peut_gerer_sas(request.user) or peut_gerer_mds(request.user, demande)
    ):
        raise PermissionDenied("Génération du courrier non autorisée.")
    date_rdv = demande.date_premier_rendez_vous if rang == 1 else demande.date_second_rendez_vous
    if not date_rdv:
        messages.error(request, "Renseignez la date du rendez-vous avant de générer son courrier PDF.")
        return redirect("ru:detail", pk=demande.pk)
    if rang == 2 and not demande.absence_premier_rendez_vous:
        messages.error(request, "Le second courrier est disponible après l'absence au premier rendez-vous.")
        return redirect("ru:detail", pk=demande.pk)
    from .pdf import rendre_courrier_rdv
    buffer = BytesIO()
    rendre_courrier_rdv(demande, rang, buffer)
    now = timezone.now()
    field_name = "courrier_premier_rdv_genere_le" if rang == 1 else "courrier_second_rdv_genere_le"
    setattr(demande, field_name, now)
    demande.save(update_fields=[field_name, "updated_at"])
    journaliser(demande, f"COURRIER_RDV{rang}_GENERE", request.user, f"Courrier PDF du rendez-vous du {date_rdv:%d/%m/%Y} généré")
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Convocation-RDV{rang}-{demande.reference}.pdf"'
    response["Cache-Control"] = "private, no-store"
    return response
