# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/views/v_evaluation.py
"""Évaluation : démarches (courriers, LRAR, rendez-vous…), rapport, synthèse et visas, saisine du procureur."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.http import require_POST

from protection_enfance.forms.f_evaluation import (ActionForm, AuditionForm, ConclusionEnfantForm, RapportForm,
                                                  SaisineForm, SuiviActionForm)
from protection_enfance.models import ActionIP, ConvoqueIP, SaisineIP
from protection_enfance.services import ip_circuit as circuit
from protection_enfance.services import ip_convocations as convocations
from protection_enfance.services import ip_pdf
from protection_enfance.services.ip_circuit import CircuitError
from protection_enfance.views.v_ip import _professionnels, _refus, get_ip


def _retour(ip, ancre=""):
    from django.urls import reverse
    return redirect(reverse('protection_enfance:ip_detail', kwargs={'ip_id': ip.numero}) + ancre)


def _erreurs(request, form):
    for champ, erreurs in form.errors.items():
        libelle = form.fields[champ].label if champ in form.fields else ""
        for e in erreurs:
            messages.error(request, f"{libelle} : {e}" if libelle else e)


# =============================================================================
# DÉMARCHES
# =============================================================================

@login_required
@require_POST
def action_ajouter(request, ip_id):
    ip = get_ip(request, ip_id)
    user = request.user
    reunion = request.POST.get('type_action') in ('REUNION_IP', 'POINT_ETAPE', 'REUNION_SYNTHESE')
    # Les réunions sont aussi programmées par le cadre avant la désignation du binôme
    if not (ip.peut_evaluer(user) or (reunion and ip.peut_piloter(user)
                                      and ip.statut in ('TRANSMISE_MDS', 'EN_EVALUATION', 'SYNTHESE'))):
        return _refus()
    form = ActionForm(request.POST, ip=ip, professionnels=_professionnels(ip))
    if not form.is_valid():
        _erreurs(request, form)
        return _retour(ip, "#demarches")
    cd = dict(form.cleaned_data)
    participants = cd.pop('participants')
    agenda = cd.pop('ajouter_agenda')
    action = circuit.enregistrer_action(ip, user, cd, participants, agenda=agenda)
    messages.success(request, f"{action.get_type_action_display()} enregistré(e)."
                     + (" Inscrit(e) dans l'agenda." if action.creneau_id else ""))
    if action.est_courrier:
        messages.info(request, "Le courrier est prêt : bouton « PDF » sur la ligne de la démarche.")
    return _retour(ip, "#demarches")


# =============================================================================
# AUDITIONS : une case par personne, convocations produites aussitôt
# =============================================================================

@login_required
@require_POST
def audition_programmer(request, ip_id):
    ip = get_ip(request, ip_id)
    if not ip.peut_evaluer(request.user):
        return _refus()
    form = AuditionForm(request.POST, ip=ip, professionnels=_professionnels(ip), prefix='aud')
    if not form.is_valid():
        _erreurs(request, form)
        return _retour(ip, "#demarches")
    cd = form.cleaned_data
    try:
        action, courriers = convocations.programmer_audition(
            ip, request.user, cd['type_action'], cd['date'], cd['duree_minutes'],
            cd['adultes'] if cd['type_action'] == 'AUDITION_PARENTS' else [],
            cd['enfants'] if cd['type_action'] == 'AUDITION_ENFANT' else [],
            cd['participants'], agenda=cd['ajouter_agenda'])
        messages.success(request, f"{action.get_type_action_display()} programmée : {len(courriers)} courrier(s) "
                                  f"de convocation prêt(s) à imprimer (bouton « PDF » de chaque courrier).")
    except CircuitError as e:
        messages.error(request, str(e))
    return _retour(ip, "#demarches")


@login_required
@require_POST
def audition_presences(request, action_id):
    action = get_object_or_404(ActionIP.objects.select_related('ip'), pk=action_id)
    ip = action.ip
    if not (ip.est_binome(request.user) or ip.peut_piloter(request.user)) or ip.statut in ('TRANSMISE_PIEF', 'CLOTUREE'):
        return _refus()
    presences = {cv: (request.POST.get(f'presence_{cv.pk}', cv.presence),
                      (request.POST.get(f'motif_{cv.pk}') or '').strip())
                 for cv in action.convoques.all()}
    convocations.noter_presences(action, request.user, presences)
    messages.success(request, "Présences enregistrées.")
    return _retour(ip, "#demarches")


@login_required
@require_POST
def audition_relance(request, action_id):
    """Report à l'amiable (date convenue) ou LRAR, pour les personnes cochées d'un même foyer."""
    action = get_object_or_404(ActionIP.objects.select_related('ip'), pk=action_id)
    ip = action.ip
    if not ip.peut_evaluer(request.user):
        return _refus()
    ids = [int(i) for i in request.POST.getlist('convoques') if i.isdigit()]
    convoques = list(ConvoqueIP.objects.filter(action=action, pk__in=ids, suite__isnull=True))
    quand = parse_datetime(request.POST.get('date') or '')
    if quand and timezone.is_naive(quand):
        quand = timezone.make_aware(quand)
    if not quand:
        messages.error(request, "Indiquez la nouvelle date et l'heure.")
        return _retour(ip, "#demarches")
    try:
        if request.POST.get('mode') == 'lrar':
            convocations.relancer_lrar(convoques, request.user, quand, request.POST.get('numero_lrar'))
            messages.success(request, "LRAR enregistrée et nouvelle audition programmée : le courrier est prêt.")
        else:
            convocations.reporter(convoques, request.user, quand, request.POST.get('motif'))
            messages.success(request, "Report convenu enregistré : le nouveau courrier de convocation est prêt.")
    except CircuitError as e:
        messages.error(request, str(e))
    return _retour(ip, "#demarches")


@login_required
@require_POST
def action_suivi(request, action_id):
    action = get_object_or_404(ActionIP.objects.select_related('ip'), pk=action_id)
    ip = action.ip
    if not (ip.est_binome(request.user) or ip.peut_piloter(request.user)) or ip.statut in ('TRANSMISE_PIEF', 'CLOTUREE'):
        return _refus()
    form = SuiviActionForm(request.POST)
    if form.is_valid():
        circuit.mettre_a_jour_action(action, request.user, form.cleaned_data['resultat'],
                                     form.cleaned_data['compte_rendu'], form.cleaned_data['date_accuse_reception'])
        messages.success(request, "Démarche mise à jour.")
    else:
        _erreurs(request, form)
    return _retour(ip, "#demarches")


@login_required
def courrier_pdf(request, action_id):
    action = get_object_or_404(ActionIP.objects.select_related('ip__mds', 'ip__famille'), pk=action_id)
    if not action.ip.peut_voir(request.user) or not action.est_courrier:
        return _refus()
    nom = f"{'LRAR' if action.type_action == 'LRAR' else 'Convocation'}_{action.ip.numero}_{action.pk}.pdf"
    return FileResponse(ip_pdf.courrier_pdf(action), as_attachment=False, filename=nom,
                        content_type='application/pdf')


# =============================================================================
# RAPPORT, SYNTHÈSE, VISAS
# =============================================================================

@login_required
def rapport(request, ip_id):
    ip = get_ip(request, ip_id)
    user = request.user
    if not ip.peut_voir(user):
        return _refus()
    r = circuit.rapport_de(ip)
    modifiable = ip.peut_evaluer(user) and not r.verrouille
    form = RapportForm(request.POST or None, instance=r)
    enfants = list(ip.enfants.prefetch_related('dangers_constates'))
    conclusions = [(e, ConclusionEnfantForm(request.POST or None, instance=e, prefix=f'enfant{e.pk}'))
                   for e in enfants]
    if request.method == 'POST':
        if not modifiable:
            return _refus()
        if form.is_valid() and all(f.is_valid() for _, f in conclusions):
            r = form.save(commit=False)
            r.redige_par = user
            r.save()
            for _, f in conclusions:
                f.save()
            circuit.journal(ip, user, "Rapport enregistré (brouillon)")
            if request.POST.get('soumettre'):
                try:
                    circuit.soumettre_rapport(ip, user)
                    messages.success(request, "Rapport soumis : le cadre est prévenu pour organiser la synthèse.")
                    return _retour(ip, "#rapport")
                except CircuitError as e:
                    messages.error(request, str(e))
            else:
                messages.success(request, "Brouillon enregistré.")
            return redirect('protection_enfance:rapport', ip_id=ip.numero)
    return render(request, 'protection_enfance/ip_rapport.html', {
        'ip': ip, 'rapport': r, 'form': form, 'modifiable': modifiable, 'conclusions': conclusions,
        'enfants': enfants, 'non_cooperants': convocations.non_cooperants(ip),
        'actions': ip.actions.select_related('enfant').order_by('date'),
        'peut_piloter': ip.peut_piloter(user), 'est_binome': ip.est_binome(user),
        'est_pief': user.a_la_capacite('ip_pief'),
        'decisions': ip._meta.get_field('decision_finale').choices,
    })


@login_required
@require_POST
def rapport_viser(request, ip_id):
    ip = get_ip(request, ip_id)
    try:
        circuit.viser(ip, request.user, request.POST.get('role'), parse_date(request.POST.get('date_synthese') or ''))
        ip.refresh_from_db()
        messages.success(request, "Rapport transmis à l'inspecteur enfance famille." if ip.statut == 'TRANSMISE_PIEF'
                         else "Visa enregistré.")
    except CircuitError as e:
        messages.error(request, str(e))
    return redirect('protection_enfance:rapport', ip_id=ip.numero)


@login_required
@require_POST
def rapport_renvoyer(request, ip_id):
    ip = get_ip(request, ip_id)
    if not ip.peut_piloter(request.user):
        return _refus()
    try:
        circuit.renvoyer_en_redaction(ip, request.user, (request.POST.get('motif') or '').strip() or "Rapport à compléter")
        messages.success(request, "Rapport renvoyé au binôme.")
    except CircuitError as e:
        messages.error(request, str(e))
    return redirect('protection_enfance:rapport', ip_id=ip.numero)


@login_required
def rapport_pdf(request, ip_id):
    ip = get_ip(request, ip_id)
    if not ip.peut_voir(request.user):
        return _refus()
    circuit.journal(ip, request.user, "Rapport imprimé (PDF)")
    return FileResponse(ip_pdf.rapport_pdf(ip), as_attachment=False, filename=f"Rapport_{ip.numero}.pdf",
                        content_type='application/pdf')


# =============================================================================
# SAISINE DU PROCUREUR
# =============================================================================

@login_required
@require_POST
def saisine_proposer(request, ip_id):
    ip = get_ip(request, ip_id)
    if not (ip.est_binome(request.user) or ip.peut_piloter(request.user)):
        return _refus()
    form = SaisineForm(request.POST)
    if not form.is_valid():
        _erreurs(request, form)
    else:
        try:
            circuit.proposer_saisine(ip, request.user, form.cleaned_data['motif'], form.cleaned_data['danger_imminent'])
            messages.success(request, "Proposition transmise au cadre.")
        except CircuitError as e:
            messages.error(request, str(e))
    return _retour(ip, "#saisines")


@login_required
@require_POST
def saisine_cadre(request, saisine_id):
    s = get_object_or_404(SaisineIP.objects.select_related('ip'), pk=saisine_id)
    if not s.ip.peut_piloter(request.user):
        return _refus()
    try:
        circuit.decision_cadre_saisine(s, request.user, request.POST.get('choix'),
                                       (request.POST.get('commentaire') or '').strip())
        messages.success(request, f"Saisine : {s.get_statut_display()}.")
    except CircuitError as e:
        messages.error(request, str(e))
    return _retour(s.ip, "#saisines")


@login_required
@require_POST
def saisine_effectuee(request, saisine_id):
    s = get_object_or_404(SaisineIP.objects.select_related('ip'), pk=saisine_id)
    if not (s.ip.peut_piloter(request.user) or request.user.a_la_capacite('ip_pief')):
        return _refus()
    quand = parse_datetime(request.POST.get('date') or '')
    if quand and timezone.is_naive(quand):
        quand = timezone.make_aware(quand)
    try:
        circuit.saisine_effectuee(s, request.user, quand, (request.POST.get('reference') or '').strip()[:100])
        messages.success(request, "Saisine du procureur enregistrée.")
    except CircuitError as e:
        messages.error(request, str(e))
    return _retour(s.ip, "#saisines")


@login_required
def saisine_pdf(request, saisine_id):
    s = get_object_or_404(SaisineIP.objects.select_related('ip__mds', 'ip__famille'), pk=saisine_id)
    if not s.ip.peut_voir(request.user) or s.statut not in ('VALIDEE_PIEF', 'EFFECTUEE'):
        return _refus()
    circuit.journal(s.ip, request.user, "Courrier de saisine du procureur imprimé (PDF)")
    return FileResponse(ip_pdf.saisine_pdf(s), as_attachment=False, filename=f"Saisine_{s.ip.numero}.pdf",
                        content_type='application/pdf')
