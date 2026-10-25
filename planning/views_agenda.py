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
from django.db.models import Q
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
            rdv.partenaires.set(d['partenaires'])
            HistoriqueCreneau.objects.create(creneau=rdv, action='CREATION', utilisateur=request.user,
                                             commentaire=f"{rdv.get_nature_display()} – {rdv.get_domaine_display()}")
            messages.success(request, f"Rendez-vous noté le {rdv.date:%d/%m/%Y} à {rdv.heure_debut:%H:%M}.")
            if rdv.partenaires.filter(email__gt='').exists():
                # Tripartite : on propose tout de suite d'inviter le partenaire
                return redirect('planning:invitation_partenaire', creneau_id=rdv.pk)
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
    if rdv.nature == 'REUNION':
        if not rdv.peut_gerer_reunion(request.user):
            return HttpResponseForbidden("Une réunion se gère par celui qui l'a convoquée ou par un cadre.")
    elif not rdv.voit_le_detail(request.user):
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
    # Réunion annulée ou reportée : les participants sont prévenus, leur agenda est libéré
    if rdv.nature == 'REUNION' and statut in ('ANNULE_MDS', 'REPORT_MDS', 'ANNULE_USAGER', 'REPORT_USAGER'):
        qui = request.user.get_full_name() or request.user.username
        _prevenir(rdv.co_intervenants.all(), request.user, rdv,
                  f"Annulation : {rdv.intitule} – {rdv.date:%d/%m/%Y} à {rdv.heure_debut:%H:%M}",
                  f"La réunion « {rdv.intitule} » du {rdv.date:%d/%m/%Y} ({rdv.heure_debut:%H:%M}–"
                  f"{rdv.heure_fin:%H:%M}) est {rdv.get_statut_display().lower()} par {qui}.\n"
                  f"Le créneau est libéré dans votre agenda CID.")
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
        rdvs = rdvs.filter(Q(agent_id=request.GET['agent']) | Q(co_intervenants=request.GET['agent']))
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
        'peut_convoquer': request.user.a_la_capacite('planning_convoquer') and mds is not None,
    }


# =============================================================================
# RÉUNIONS (lot 2)
# =============================================================================

def _prevenir(participants, organisateur, reunion, objet, texte):
    """Message CID à chaque participant (l'organisateur ne s'écrit pas à lui-même)."""
    from messagerie.models import Message, StatutLecture
    for p in participants:
        if p.pk == organisateur.pk:
            continue
        msg = Message.objects.create(
            expediteur=organisateur, destinataire=p, objet=objet[:255], contenu=texte,
            beneficiaire=reunion.beneficiaire,   # rattaché au dossier si la réunion en concerne un
            motif='coordination_equipe', priorite='importante', reference=f"REUNION-{reunion.pk}")
        StatutLecture.objects.create(message=msg, utilisateur=p, type_reception='destinataire')


@login_required
def nouvelle_reunion(request):
    """
    Convoquer une réunion : grille des disponibilités de l'équipe (libre / occupé / indisponible),
    puis blocage automatique de l'agenda des participants. La convocation s'impose.
    """
    from .agenda import conflits_agent, grille_disponibilites, indisponibilites
    mds = _mds_de(request.user)
    if not (request.user.a_la_capacite('planning_convoquer') and mds):
        messages.error(request, "Vous n'avez pas le droit de convoquer une réunion.")
        return redirect('planning:calendrier_rdv')

    jour = parse_date(request.POST.get('date') or request.GET.get('date') or '') or timezone.localdate()
    avertissements = []
    from .forms import ReunionForm
    if request.method == 'POST':
        form = ReunionForm(request.POST, mds=mds)
        if form.is_valid():
            d = form.cleaned_data
            for p in d['participants']:
                for c in conflits_agent(p, d['date'], d['heure_debut'], d['heure_fin']):
                    avertissements.append(f"{p.get_full_name() or p.username} : déjà occupé(e) de "
                                          f"{c.heure_debut:%H:%M} à {c.heure_fin:%H:%M}")
                if indisponibilites(p, d['date'], d['heure_debut'], d['heure_fin']).exists():
                    avertissements.append(f"{p.get_full_name() or p.username} : indisponible ce jour-là")
            if not avertissements or request.POST.get('confirmer') == '1':
                texte = d['intitule'] + (f"\n{d['ordre_du_jour']}" if d['ordre_du_jour'] else "")
                reunion = CreneauRdv.objects.create(
                    salle=None, mds=mds, agent=None, date=d['date'],
                    heure_debut=d['heure_debut'], heure_fin=d['heure_fin'],
                    nature='REUNION', domaine=d['domaine'], type_rdv='AUTRE', modalite='MDS',
                    beneficiaire=d['beneficiaire'],
                    lieu_precis=d['lieu_precis'], description=texte, statut='RESERVE',
                    cree_par=request.user, reserve_par=request.user, date_reservation=timezone.now())
                reunion.co_intervenants.set(d['participants'])
                HistoriqueCreneau.objects.create(creneau=reunion, action='CREATION', utilisateur=request.user,
                                                 commentaire=f"Réunion : {len(d['participants'])} participant(s)")
                organisateur = request.user.get_full_name() or request.user.username
                _prevenir(d['participants'], request.user, reunion,
                          f"Convocation : {d['intitule']} – {d['date']:%d/%m/%Y} à {d['heure_debut']:%H:%M}",
                          f"Vous êtes convoqué(e) par {organisateur}.\n\n"
                          f"Réunion : {d['intitule']}\n"
                          + (f"Dossier : {d['beneficiaire'].prenom} {d['beneficiaire'].nom.upper()} "
                             f"({d['beneficiaire'].code_interne})\n" if d['beneficiaire'] else "")
                          + f"Date : {d['date']:%d/%m/%Y}, de {d['heure_debut']:%H:%M} "
                          f"à {d['heure_fin']:%H:%M}\nLieu : {d['lieu_precis'] or '-'}\n\n"
                          f"{d['ordre_du_jour']}\n\nLe créneau est bloqué dans votre agenda CID. "
                          f"En cas d'empêchement, prévenez {organisateur} ou votre cadre.")
                messages.success(request, f"Réunion convoquée : {len(d['participants'])} agenda(s) bloqué(s).")
                if reunion.beneficiaire:
                    return redirect('beneficiaire:detail_beneficiaire', code_interne=reunion.beneficiaire.code_interne)
                return redirect('planning:calendrier_rdv')
    else:
        initial = {'date': jour, 'domaine': 'INSTITUTIONNEL', 'heure_debut': request.GET.get('debut', '')}
        dossier = Beneficiaire.objects.filter(pk=request.GET.get('beneficiaire') or 0, mds=mds).first()
        if dossier:
            initial['beneficiaire_id'] = dossier.pk
        form = ReunionForm(mds=mds, initial=initial)

    agents = form.fields['participants'].queryset
    coches = set(int(x) for x in request.POST.getlist('participants') if x.isdigit())
    grille = grille_disponibilites(agents, jour)
    for ligne in grille['lignes']:
        ligne['coche'] = ligne['agent'].pk in coches
    id_dossier = form['beneficiaire_id'].value()
    dossier = Beneficiaire.objects.filter(pk=id_dossier, mds=mds).first() if str(id_dossier or '').isdigit() else None
    return render(request, 'planning/reunion_form.html', {
        'form': form, 'grille': grille, 'jour': jour, 'avertissements': avertissements, 'dossier': dossier,
        'jour_precedent': jour.fromordinal(jour.toordinal() - 1),
        'jour_suivant': jour.fromordinal(jour.toordinal() + 1),
    })


# =============================================================================
# INVITATION DES PARTENAIRES (lot 3)
# =============================================================================

def _corps_invitation(user, texte):
    return (f"Bonjour,\n\n{texte}\n\nVous trouverez l'invitation en pièce jointe : "
            f"un clic l'ajoute à votre agenda.\n\nCordialement,\n{user.get_full_name() or user.username}")


@login_required
def invitation_eml(request, creneau_id):
    """Un seul bouton : brouillon d'e-mail à tous les partenaires, invitation déjà jointe."""
    from django.http import HttpResponse
    from .invitation import brouillon_eml, texte_invitation
    rdv = get_object_or_404(CreneauRdv, pk=creneau_id)
    if not rdv.voit_le_detail(request.user):
        return HttpResponseForbidden("Réservé à l'agent du rendez-vous et au cadre.")
    avec_lieu = request.GET.get('lieu', '1') != '0'
    partenaires = [p for p in rdv.partenaires.all() if p.email]
    if not partenaires:
        messages.error(request, "Aucun partenaire de ce rendez-vous n'a d'e-mail dans l'annuaire.")
        return redirect('planning:invitation_partenaire', creneau_id=rdv.pk)
    contenu = brouillon_eml(rdv, partenaires, request.user,
                            _corps_invitation(request.user, texte_invitation(rdv, avec_lieu)), avec_lieu)
    HistoriqueCreneau.objects.create(creneau=rdv, action='MODIFICATION', utilisateur=request.user,
                                     commentaire=f"Invitation préparée pour {len(partenaires)} partenaire(s)")
    r = HttpResponse(contenu, content_type='message/rfc822')
    r['Content-Disposition'] = f'attachment; filename="invitation_{rdv.date:%Y%m%d}_{rdv.heure_debut:%H%M}.eml"'
    return r


@login_required
def invitation_partenaire(request, creneau_id):
    """Préparer l'e-mail et le fichier .ics pour chaque partenaire du rendez-vous."""
    from urllib.parse import quote
    from .invitation import objet_invitation, texte_invitation
    rdv = get_object_or_404(CreneauRdv, pk=creneau_id)
    if not rdv.voit_le_detail(request.user):
        return HttpResponseForbidden("Réservé à l'agent du rendez-vous et au cadre.")
    avec_lieu = request.GET.get('lieu', '1') != '0'
    objet, texte = objet_invitation(rdv), texte_invitation(rdv, avec_lieu)
    corps = _corps_invitation(request.user, texte)
    invites = [{'partenaire': p,
                'mailto': f"mailto:{p.email}?subject={quote(objet)}&body={quote(corps)}" if p.email else ""}
               for p in rdv.partenaires.all()]
    return render(request, 'planning/invitation_partenaire.html', {
        'rdv': rdv, 'invites': invites, 'texte': texte, 'objet': objet, 'avec_lieu': avec_lieu,
        'nb_avec_email': sum(1 for i in invites if i['partenaire'].email),
    })


@login_required
def invitation_ics(request, creneau_id, partenaire_id):
    from django.http import HttpResponse
    from .invitation import fichier_ics
    rdv = get_object_or_404(CreneauRdv, pk=creneau_id)
    if not rdv.voit_le_detail(request.user):
        return HttpResponseForbidden("Réservé à l'agent du rendez-vous et au cadre.")
    partenaire = get_object_or_404(rdv.partenaires, pk=partenaire_id)
    r = HttpResponse(fichier_ics(rdv, partenaire, request.GET.get('lieu', '1') != '0'),
                     content_type='text/calendar; charset=utf-8; method=REQUEST')
    r['Content-Disposition'] = f'attachment; filename="invitation_{rdv.date:%Y%m%d}_{rdv.heure_debut:%H%M}.ics"'
    return r
