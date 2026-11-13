# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# adultevul/views.py
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from mds.models import UserMDSProfile
from .forms import CelluleForm, MotifForm, QualificationForm, RenvoiForm, SituationForm
from .pdf import ANNEXES, annexe_disponible, rendre_annexe
from .models import PROPOSITIONS, STATUTS, SituationAdulteVulnerable
from .services import (
    cloturer, constituer_cellule, controler_rapport, creer_situation, decider, enregistrer_cellule,
    peut_decider, peut_evaluer, peut_piloter, qualifier, renvoyer_rapport, soumettre_rapport, valider_rapport,
)


def _acces_module(user):
    return bool(user.is_superuser or user.a_la_capacite('peut_administrer') or user.a_la_capacite('peut_voir'))


def _situations_visibles(user):
    if user.is_superuser or user.a_la_capacite('peut_administrer'):
        return SituationAdulteVulnerable.objects.all()
    mds_ids = UserMDSProfile.objects.filter(user=user, actif=True).values_list('mds_id', flat=True)
    return SituationAdulteVulnerable.objects.filter(mds_id__in=mds_ids)


def _situation_pour_user(user, pk):
    if not _acces_module(user):
        raise PermissionDenied("L'accès au module adultes vulnérables n'est pas autorisé.")
    situation = get_object_or_404(_situations_visibles(user).select_related('mds', 'cellule'), pk=pk)
    return situation


@login_required
def liste(request):
    if not _acces_module(request.user):
        raise PermissionDenied("L'accès au module adultes vulnérables n'est pas autorisé.")
    situations = _situations_visibles(request.user).select_related('mds').order_by('-date_reception', '-id')
    statut = request.GET.get('statut', '')
    if statut:
        situations = situations.filter(statut=statut)
    if request.GET.get('ouvertes') == '1':
        situations = situations.exclude(statut__in=['CLOTUREE', 'NON_QUALIFIEE'])
    return render(request, 'adultevul/liste.html', {
        'situations': situations[:300],
        'statut_selectionne': statut,
        'statuts': STATUTS,
    })


@login_required
def creer(request):
    user = request.user
    if not _acces_module(user):
        raise PermissionDenied("L'accès au module adultes vulnérables n'est pas autorisé.")
    if request.method == 'POST':
        form = SituationForm(request.POST, user=user)
        if form.is_valid():
            situation = form.save(commit=False)
            try:
                creer_situation(situation, user)
            except PermissionDenied as exc:
                messages.error(request, str(exc))
                return redirect('adultevul:liste')
            messages.success(request, f"Recueil {situation.numero} enregistré. Il reste à le qualifier.")
            return redirect(situation.get_absolute_url())
    else:
        form = SituationForm(user=user)
    return render(request, 'adultevul/formulaire.html', {
        'form': form, 'titre': "Recueillir une information préoccupante (annexe 1)",
        'sous_titre': "Adulte susceptible d'être vulnérable ou en danger. Les faits sont retranscrits mot pour mot.",
        'bouton': "Enregistrer le recueil", 'retour': reverse('adultevul:liste'),
    })


@login_required
def detail(request, pk):
    user = request.user
    situation = _situation_pour_user(user, pk)
    cellule = getattr(situation, 'cellule', None)
    soumettre_possible = situation.statut == 'EVALUATION' and peut_evaluer(user, situation)
    return render(request, 'adultevul/detail.html', {
        'situation': situation,
        'cellule': cellule,
        'cellule_propositions': PROPOSITIONS,
        'annexes': [(n, libelle) for n, libelle in ANNEXES.items() if annexe_disponible(situation, n)],
        'historique': situation.historique.select_related('auteur').all(),
        'manques': controler_rapport(situation) if soumettre_possible and cellule else [],
        'peut_qualifier': situation.statut == 'RECUE' and peut_piloter(user, situation),
        'peut_constituer': situation.statut == 'QUALIFIEE' and peut_piloter(user, situation),
        'peut_editer_cellule': situation.statut == 'EVALUATION' and peut_evaluer(user, situation),
        'peut_soumettre': soumettre_possible,
        'peut_viser': situation.statut == 'RAPPORT' and peut_piloter(user, situation),
        'peut_renvoyer': situation.statut == 'RAPPORT' and peut_piloter(user, situation),
        'peut_decider': situation.statut == 'VALIDEE' and peut_decider(user, situation),
        'peut_cloturer': situation.statut in ('DECIDEE', 'NON_QUALIFIEE') and peut_piloter(user, situation),
    })


@login_required
@require_POST
def qualifier_view(request, pk):
    situation = _situation_pour_user(request.user, pk)
    form = QualificationForm(request.POST)
    if form.is_valid():
        try:
            qualifier(situation, request.user, form.cleaned_data['qualifiee'], form.cleaned_data['motif'])
            messages.success(request, "Décision de qualification enregistrée.")
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, " ".join(getattr(exc, 'messages', [str(exc)])))
    else:
        messages.error(request, "Indiquez la décision et le motif.")
    return redirect(situation.get_absolute_url())


@login_required
def cellule(request, pk):
    """Constitue la cellule d'évaluation (annexe 2) ou la modifie tant que le rapport n'est pas soumis."""
    user = request.user
    situation = _situation_pour_user(user, pk)
    existante = getattr(situation, 'cellule', None)
    if existante is None and not peut_piloter(user, situation):
        raise PermissionDenied("Seul le cadre de la MDS peut constituer la cellule.")
    if existante is not None and not peut_evaluer(user, situation):
        raise PermissionDenied("Vous ne pouvez pas modifier cette évaluation.")
    if existante is not None and existante.verrouillee:
        messages.error(request, "Le rapport est soumis au visa : l'évaluation est figée.")
        return redirect(situation.get_absolute_url())

    if request.method == 'POST':
        form = CelluleForm(request.POST, instance=existante, mds=situation.mds)
        if form.is_valid():
            donnees = {k: v for k, v in form.cleaned_data.items() if k != 'referents'}
            referents = form.cleaned_data.get('referents') or []
            try:
                if existante is None:
                    constituer_cellule(situation, user, donnees, referents)
                    messages.success(request, "Cellule d'évaluation constituée.")
                else:
                    enregistrer_cellule(situation, user, donnees, referents)
                    messages.success(request, "Évaluation enregistrée.")
                return redirect(situation.get_absolute_url())
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, " ".join(getattr(exc, 'messages', [str(exc)])))
    else:
        form = CelluleForm(instance=existante, mds=situation.mds)
    return render(request, 'adultevul/formulaire.html', {
        'form': form, 'situation': situation,
        'titre': "Cellule d'évaluation (annexe 2)" if existante is None else "Évaluation et plan d'action",
        'sous_titre': situation.numero + " – " + situation.libelle_personne,
        'bouton': "Enregistrer", 'retour': situation.get_absolute_url(),
    })


@login_required
@require_POST
def soumettre(request, pk):
    situation = _situation_pour_user(request.user, pk)
    try:
        soumettre_rapport(situation, request.user)
        messages.success(request, "Rapport soumis au visa de l'adjoint Cohésion sociale.")
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, " ".join(getattr(exc, 'messages', [str(exc)])))
    return redirect(situation.get_absolute_url())


@login_required
@require_POST
def viser(request, pk):
    situation = _situation_pour_user(request.user, pk)
    try:
        valider_rapport(situation, request.user)
        messages.success(request, "Rapport visé. Le directeur peut prendre sa décision.")
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, " ".join(getattr(exc, 'messages', [str(exc)])))
    return redirect(situation.get_absolute_url())


@login_required
def renvoyer(request, pk):
    situation = _situation_pour_user(request.user, pk)
    if request.method == 'POST':
        form = RenvoiForm(request.POST)
        if form.is_valid():
            try:
                renvoyer_rapport(situation, request.user, form.cleaned_data['motif'])
                messages.success(request, "Rapport renvoyé pour compléments.")
                return redirect(situation.get_absolute_url())
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, " ".join(getattr(exc, 'messages', [str(exc)])))
    else:
        form = RenvoiForm()
    return render(request, 'adultevul/formulaire.html', {
        'form': form, 'titre': "Renvoyer le rapport pour compléments",
        'sous_titre': situation.numero, 'bouton': "Renvoyer", 'retour': situation.get_absolute_url(),
    })


@login_required
def decider_view(request, pk):
    situation = _situation_pour_user(request.user, pk)
    if request.method == 'POST':
        form = MotifForm(request.POST)
        if form.is_valid():
            try:
                decider(situation, request.user, form.cleaned_data['commentaire'])
                messages.success(request, "Décision administrative enregistrée.")
                return redirect(situation.get_absolute_url())
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, " ".join(getattr(exc, 'messages', [str(exc)])))
    else:
        form = MotifForm()
    return render(request, 'adultevul/formulaire.html', {
        'form': form, 'titre': "Décision administrative du directeur de MDS",
        'sous_titre': situation.numero, 'bouton': "Enregistrer la décision",
        'retour': situation.get_absolute_url(),
    })


@login_required
@require_POST
def cloturer_view(request, pk):
    situation = _situation_pour_user(request.user, pk)
    try:
        cloturer(situation, request.user)
        messages.success(request, "Situation clôturée.")
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, " ".join(getattr(exc, 'messages', [str(exc)])))
    return redirect(situation.get_absolute_url())


@login_required
def annexe_pdf(request, pk, numero):
    situation = _situation_pour_user(request.user, pk)
    if numero not in ANNEXES or not annexe_disponible(situation, numero):
        raise Http404("Cette annexe n'est pas disponible pour cette situation.")
    buffer = BytesIO()
    rendre_annexe(situation, numero, buffer)
    buffer.seek(0)
    reponse = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    reponse["Content-Disposition"] = f'attachment; filename="{situation.numero}-annexe-{numero}.pdf"'
    reponse["Cache-Control"] = "private, no-store"
    return reponse
