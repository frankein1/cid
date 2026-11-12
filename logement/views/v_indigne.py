# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/views/v_indigne.py
"""Lutte contre le logement indigne : signalement, rapport de VAD (signé TS), fiche PDLHI (signée cadre), suivi."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from mds.models import UserMDSProfile

from ..models import SignalementHabitatIndigne
from ..services import indigne
from .v_copp import _date, _usager


def _membre(user, mds):
    return user.is_superuser or UserMDSProfile.objects.filter(user=user, mds=mds, actif=True).exists()


def _acces(request, pk):
    s = get_object_or_404(SignalementHabitatIndigne.objects.select_related('beneficiaire', 'mds', 'mds__responsable'),
                          pk=pk)
    voir = _membre(request.user, s.mds)
    ecrire = voir and request.user.a_la_capacite('peut_creer')
    return s, voir, ecrire


def _cadre(user, s):
    return user.is_superuser or (s.mds.responsable_id is not None and s.mds.responsable_id == user.pk)


def _champ(s, key, label, kind, choix):
    valeur = s.donnees.get(key, '')
    return {'key': key, 'label': label, 'kind': kind, 'choix': choix or [], 'valeur': valeur,
            'affiche': dict(choix or []).get(valeur, valeur) if choix else valeur}


def _champs_formulaire(s):
    """Sections avec, pour chaque rubrique, sa valeur courante (pour le gabarit)."""
    out = []
    for cle, titre, champs in indigne.SECTIONS:
        out.append({'titre': titre, 'champs': [
            _champ(s, key, label, kind, choix) for key, label, kind, choix in champs]})
    return out


@login_required
def indigne_liste(request):
    u = request.user
    qs = SignalementHabitatIndigne.objects.select_related('beneficiaire', 'mds')
    if not u.is_superuser:
        qs = qs.filter(mds__in=UserMDSProfile.objects.filter(user=u, actif=True).values('mds'))
    statut = request.GET.get('statut')
    if statut in dict(SignalementHabitatIndigne.STATUTS):
        qs = qs.filter(statut=statut)
    return render(request, 'logement/indigne_liste.html', {
        'signalements': qs, 'statuts': SignalementHabitatIndigne.STATUTS, 'statut': statut,
        'origines': SignalementHabitatIndigne.ORIGINES})


@login_required
@require_POST
def indigne_nouveau(request):
    p = request.POST
    origine = p.get('origine') if p.get('origine') in dict(SignalementHabitatIndigne.ORIGINES) else 'VAD'
    code = (p.get('code_interne') or '').strip()
    if code:
        from beneficiaire.models import Beneficiaire
        b = get_object_or_404(Beneficiaire.tous.select_related('mds'), code_interne=code)
        _, refus = _usager(request, code)
        if refus:
            return refus
        mds = b.mds
    else:
        b = None
        prof = UserMDSProfile.objects.filter(user=request.user, actif=True).order_by('-principale').first()
        if not prof and not request.user.is_superuser:
            return HttpResponseForbidden("Aucune MDS rattachée à votre compte.")
        mds = prof.mds if prof else None
        if mds is None:
            return HttpResponseForbidden("Précisez l'usager ou la MDS.")
    s = SignalementHabitatIndigne.objects.create(beneficiaire=b, mds=mds, origine=origine, cree_par=request.user)
    s.tracer(request.user, "Signalement créé", s.get_origine_display())
    s.save()
    messages.success(request, "Signalement créé. Renseignez la fiche, puis le rapport de VAD.")
    return redirect('logement:indigne_modifier', pk=s.pk)


@login_required
def indigne_detail(request, pk):
    s, voir, ecrire = _acces(request, pk)
    if not voir:
        return HttpResponseForbidden("Réservé aux agents de la MDS du signalement.")
    return render(request, 'logement/indigne_detail.html', {
        's': s, 'sections': _champs_formulaire(s), 'ecrire': ecrire,
        'peut_signer_fiche': ecrire and _cadre(request.user, s),
        'peut_suivre': ecrire and s.statut == s.ENVOYE})


@login_required
def indigne_modifier(request, pk):
    s, voir, ecrire = _acces(request, pk)
    if not ecrire:
        return HttpResponseForbidden("Réservé aux agents de la MDS du signalement.")
    if not s.modifiable:
        messages.error(request, "Ce signalement a été envoyé : il n'est plus modifiable.")
        return redirect('logement:indigne_detail', pk=s.pk)
    if request.method == 'POST':
        p = request.POST
        champs = indigne.champs_valides()
        nouvelles = {key: indigne.valeur_propre(key, p.get(key), champs) for key in champs}
        modifie_fiche = nouvelles != {k: s.donnees.get(k, '') for k in champs}
        s.donnees = nouvelles
        s.origine = p.get('origine') if p.get('origine') in dict(SignalementHabitatIndigne.ORIGINES) else s.origine
        s.permis_ville, s.permis_logement = bool(p.get('permis_ville')), bool(p.get('permis_logement'))
        rapport = (p.get('rapport_vad') or '').strip()
        modifie_vad = rapport != s.rapport_vad
        s.rapport_vad = rapport
        if modifie_vad and s.vad_signee:
            s.vad_signee_par, s.vad_date_signature = None, None
            s.tracer(request.user, "Signature du rapport de VAD retirée", "rapport modifié")
        if modifie_fiche and s.fiche_signee:
            s.fiche_signee_par, s.fiche_date_signature = None, None
            s.tracer(request.user, "Signature de la fiche retirée", "fiche modifiée")
        s.tracer(request.user, "Signalement modifié")
        s.save()
        messages.success(request, "Signalement enregistré.")
        return redirect('logement:indigne_detail', pk=s.pk)
    return render(request, 'logement/indigne_form.html', {
        's': s, 'sections': _champs_formulaire(s), 'origines': SignalementHabitatIndigne.ORIGINES})


@login_required
@require_POST
def indigne_action(request, pk):
    s, voir, ecrire = _acces(request, pk)
    if not voir:
        return HttpResponseForbidden("Réservé aux agents de la MDS du signalement.")
    if not ecrire and not _cadre(request.user, s):
        return HttpResponseForbidden("Action réservée aux agents de la MDS.")
    action = request.POST.get('action')
    maintenant = timezone.now()
    if action == 'signer_vad' and ecrire and s.statut != s.CLOS:
        if not s.rapport_vad:
            messages.error(request, "Rédigez le rapport de VAD avant de le signer.")
        else:
            s.vad_signee_par, s.vad_date_signature = request.user, maintenant
            s.tracer(request.user, "Rapport de VAD signé")
            messages.success(request, "Rapport de VAD signé.")
    elif action == 'signer_fiche' and s.modifiable and _cadre(request.user, s):
        s.fiche_signee_par, s.fiche_date_signature = request.user, maintenant
        s.tracer(request.user, "Fiche PDLHI signée (cadre)")
        messages.success(request, "Fiche PDLHI signée.")
    elif action == 'envoyer' and ecrire and s.modifiable:
        if not s.fiche_signee:
            messages.error(request, "La fiche doit être signée par le cadre avant l'envoi.")
        else:
            s.statut = s.ENVOYE
            s.date_envoi = _date(request.POST.get('date_envoi')) or timezone.localdate()
            s.tracer(request.user, "Fiche envoyée au PDLHI", s.date_envoi.strftime('%d/%m/%Y'))
            messages.success(request, "Signalement marqué comme envoyé au PDLHI.")
    elif action == 'suivi' and ecrire and s.statut == s.ENVOYE:
        p = request.POST
        s.reponse_pdlhi = (p.get('reponse_pdlhi') or '').strip()
        s.suite = (p.get('suite') or '').strip()
        s.enquete_salubrite = bool(p.get('enquete_salubrite'))
        s.bascule_dalo = bool(p.get('bascule_dalo'))
        s.tracer(request.user, "Suivi mis à jour")
        messages.success(request, "Suivi enregistré.")
    elif action == 'clore' and ecrire and s.statut == s.ENVOYE:
        s.statut = s.CLOS
        s.tracer(request.user, "Signalement clos")
    else:
        messages.error(request, "Action impossible dans l'état actuel du signalement.")
        return redirect('logement:indigne_detail', pk=s.pk)
    s.save()
    return redirect('logement:indigne_detail', pk=s.pk)
