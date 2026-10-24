# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# planning/views_agenda.py
"""
Agenda unifié : rendez-vous de l'agent (VAD, hors permanence, partenaire…) à côté des permanences.
Les permanences restent créées par le cadre (génération des créneaux) ; tout le reste se note ici.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from beneficiaire.models import Beneficiaire
from mds.models import UserMDSProfile

from .agenda import (est_premiere_fois, evenement, evenement_indisponibilite, legende,
                     rdv_de_la_mds)
from .forms import ISSUES_RDV, RdvAgentForm
from .models import CreneauRdv, HistoriqueCreneau, JourBloque
from .utils import est_jour_ferie

# Nature → ancien type_rdv (pour les écrans qui l'affichent encore)
ANCIEN_TYPE = {'VAD': 'VISITE_DOMICILE', 'HORS_PERMANENCE': 'HORS_PERMANENCE',
               'TELEPHONIQUE': 'TELEPHONIQUE', 'PARTENAIRE': 'AUTRE', 'AUTRE': 'AUTRE'}


def _retour(request):
    """Page de retour après une action (seulement une adresse interne à CID)."""
    url = request.POST.get('retour', '')
    if url and url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}):
        return url
    return 'planning:calendrier_rdv'


def _mds_de(user):
    return getattr(user, 'mds_principale', None) or getattr(
        UserMDSProfile.objects.filter(user=user, actif=True).select_related('mds').first(), 'mds', None)


@login_required
def nouveau_rdv(request):
    """Noter un rendez-vous hors permanence (agent social ou d'accueil)."""
    mds = _mds_de(request.user)
    if not (request.user.a_la_capacite('peut_creer') and mds):
        messages.error(request, "Vous n'avez pas le droit de créer un rendez-vous.")
        return redirect('planning:calendrier_rdv')

    beneficiaire = None
    if request.GET.get('beneficiaire'):
        beneficiaire = Beneficiaire.objects.filter(pk=request.GET['beneficiaire'], mds=mds).first()

    if request.method == 'POST':
        form = RdvAgentForm(request.POST, mds=mds)
        if form.is_valid():
            d = form.cleaned_data
            rdv = CreneauRdv.objects.create(
                salle=None, mds=mds, agent=d['agent'], beneficiaire=d['beneficiaire'],
                date=d['date'], heure_debut=d['heure_debut'], heure_fin=d['heure_fin'],
                nature=d['nature'], domaine=d['domaine'], type_rdv=ANCIEN_TYPE.get(d['nature'], 'AUTRE'),
                modalite='VAD' if d['nature'] == 'VAD' else 'AUTRE',
                lieu_precis=d['lieu_precis'], description=d['description'],
                premiere_fois=d['premiere_fois'], statut='RESERVE',
                cree_par=request.user, reserve_par=request.user, date_reservation=timezone.now(),
            )
            rdv.co_intervenants.set(d['co_intervenants'])
            HistoriqueCreneau.objects.create(creneau=rdv, action='CREATION', utilisateur=request.user,
                                             commentaire=f"{rdv.get_nature_display()} – {rdv.get_domaine_display()}")
            messages.success(request, f"Rendez-vous noté le {rdv.date:%d/%m/%Y} à {rdv.heure_debut:%H:%M}.")
            if rdv.beneficiaire:
                return redirect('beneficiaire:detail_beneficiaire', code_interne=rdv.beneficiaire.code_interne)
            return redirect('planning:calendrier_rdv')
    else:
        initial = {'agent': request.user.pk, 'date': request.GET.get('date') or timezone.localdate()}
        if request.GET.get('debut'):
            initial['heure_debut'] = request.GET['debut']
        if beneficiaire:
            initial['beneficiaire_id'] = beneficiaire.pk
            initial['premiere_fois'] = est_premiere_fois(beneficiaire, mds)
        form = RdvAgentForm(initial=initial, mds=mds)

    return render(request, 'planning/rdv_agent_form.html', {'form': form, 'beneficiaire': beneficiaire})


@login_required
def api_premiere_fois(request):
    """Pré-cocher « 1er rendez-vous » quand l'agent choisit l'usager dans le formulaire."""
    mds = _mds_de(request.user)
    b = Beneficiaire.objects.filter(pk=request.GET.get('beneficiaire_id'), mds=mds).first()
    return JsonResponse({'premiere_fois': est_premiere_fois(b, mds)})


@login_required
@require_POST
def issue_rdv(request, creneau_id):
    """Après le rendez-vous : réalisé, VAD usager absent, absent, annulé, reporté…"""
    rdv = get_object_or_404(CreneauRdv, pk=creneau_id)
    if not rdv.voit_le_detail(request.user):
        return HttpResponseForbidden("Réservé à l'agent du rendez-vous et au cadre.")
    statut = request.POST.get('statut')
    if statut not in dict(ISSUES_RDV) or (statut == 'VAD_ABSENT' and rdv.nature != 'VAD'):
        messages.error(request, "Issue du rendez-vous non valable.")
        return redirect(_retour(request))

    ancien = rdv.get_statut_display()
    rdv.statut = statut
    rdv.premiere_fois = request.POST.get('premiere_fois') == 'on'
    rdv.save(update_fields=['statut', 'premiere_fois', 'date_modification'])
    HistoriqueCreneau.objects.create(creneau=rdv, action='MODIFICATION', utilisateur=request.user,
                                     commentaire=f"{ancien} → {rdv.get_statut_display()}")
    # 1er rendez-vous réalisé avec un agent social : il devient référent s'il n'y en a pas
    b = rdv.beneficiaire
    if (b and statut == 'VENU_RECU' and rdv.premiere_fois and b.referent_mds_id is None
            and rdv.agent and rdv.agent.a_la_capacite('peut_instruire')):
        b.referent_mds = rdv.agent
        b.save(update_fields=['referent_mds'])
    messages.success(request, f"Rendez-vous du {rdv.date:%d/%m/%Y} : {rdv.get_statut_display().lower()}.")
    return redirect(_retour(request))


@login_required
def api_agenda(request):
    """Événements du calendrier unifié (permanences, rendez-vous, indisponibilités, fermetures)."""
    debut = parse_date(request.GET.get('start', '')[:10]) or (parse_datetime(request.GET.get('start', '')) or timezone.now()).date()
    fin = parse_date(request.GET.get('end', '')[:10]) or debut
    mds = _mds_de(request.user)
    events = []

    jour = debut
    while jour <= fin:
        if est_jour_ferie(jour):
            events.append({'title': 'FÉRIÉ', 'start': jour.isoformat(), 'allDay': True,
                           'display': 'background', 'backgroundColor': '#FEE2E2'})
        jour = jour.fromordinal(jour.toordinal() + 1)

    for b in JourBloque.objects.filter(date__range=(debut, fin)).select_related('agent', 'salle'):
        if b.agent_id and not b.salle_id:
            if mds and not UserMDSProfile.objects.filter(user=b.agent, mds=mds, actif=True).exists():
                continue
            events.append(evenement_indisponibilite(b))
        elif b.salle_id and mds and b.salle.mds_id != mds.id:
            continue
        else:
            events.append({'id': f'bloque-{b.id}', 'title': f"FERMÉ : {b.get_raison_display()}",
                           'start': f"{b.date.isoformat()}T{b.heure_debut:%H:%M:%S}",
                           'end': f"{b.date.isoformat()}T{b.heure_fin:%H:%M:%S}",
                           'backgroundColor': '#991B1B', 'borderColor': '#7F1D1D', 'textColor': '#FFFFFF',
                           'extendedProps': {'type': 'blocage', 'detail': False}})

    rdvs = CreneauRdv.objects.filter(date__range=(debut, fin))
    if mds and not request.user.a_la_capacite('peut_administrer'):
        rdvs = rdv_de_la_mds(mds).filter(date__range=(debut, fin))
    if request.GET.get('agent'):
        rdvs = rdvs.filter(agent_id=request.GET['agent'])
    rdvs = rdvs.select_related('agent', 'salle', 'beneficiaire').distinct()
    for c in rdvs:
        if c.peut_etre_vu_par(request.user):
            e = evenement(c, request.user)
            if e:
                events.append(e)
    return JsonResponse(events, safe=False)


def contexte_calendrier(request):
    """Ajouts au contexte de la page calendrier : légende, filtre agent, droits."""
    mds = _mds_de(request.user)
    from django.contrib.auth import get_user_model
    agents = get_user_model().objects.filter(profils_mds__mds=mds, profils_mds__actif=True, is_active=True)\
        .distinct().order_by('last_name') if mds else []
    return {
        'legende': legende(),
        'agents_mds': agents,
        'agent_filtre': request.GET.get('agent', ''),
        'issues_rdv': ISSUES_RDV,
        'peut_noter_rdv': request.user.a_la_capacite('peut_creer') and mds is not None,
    }
