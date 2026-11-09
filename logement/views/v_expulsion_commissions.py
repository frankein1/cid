# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/views/v_expulsion_commissions.py
"""Commissions de la prévention des expulsions : séances (CAPEX locale, commission préfectorale, CCAPEX), ordre du
jour, actualisation par la MDS (visa du cadre, envoi), avis. Passerelles vers le FSL, la COPP et la demande de
logement depuis le dossier."""
from datetime import datetime

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time
from django.views.decorators.http import require_POST

from mds.models import MDS

from ..models import CommissionExpulsion as K, DossierExpulsion as D, PassageCommission as P
from ..services import commissions as S, expulsion as X, expulsion_mds as M

REFUS = "Réservé au Service Logement et aux agents des MDS concernées."
CHAMP = "w-full border border-gray-300 rounded-md px-3 py-2 text-sm"


class CommissionForm(forms.ModelForm):
    class Meta:
        model = K
        fields = ['type_commission', 'nom', 'date', 'heure', 'lieu', 'date_limite', 'email', 'mds']
        widgets = {'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                   'date_limite': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                   'mds': forms.CheckboxSelectMultiple}

    def __init__(self, *args, mds_possibles=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mds'].label = "MDS concernées"
        if mds_possibles is not None:
            self.fields['mds'].queryset = mds_possibles
        for nom, f in self.fields.items():
            if nom != 'mds':
                f.widget.attrs.setdefault('class', CHAMP)


def _mds_possibles(user):
    if X.est_sl(user) or X.est_admin(user):
        return MDS.objects.filter(active=True).order_by('nom')
    return X.mds_de(user).order_by('nom')


def _pdf(contenu, nom):
    r = HttpResponse(contenu, content_type='application/pdf')
    r['Content-Disposition'] = f'inline; filename="{nom}"'
    return r


# ------------------------------------------------------------------------------------------------- séances
@login_required
def commissions_liste(request):
    if not (X.peut_voir_module(request.user) or request.user.a_la_capacite('expulsion_sl_stats')):
        return HttpResponseForbidden(REFUS)
    qs = S.commissions_visibles(request.user)
    j = timezone.localdate()
    return render(request, 'logement/commissions_liste.html', {
        'a_venir': qs.filter(date__gte=j).order_by('date'), 'passees': qs.filter(date__lt=j).order_by('-date')[:20],
        'peut_creer': S.peut_gerer(request.user)})


@login_required
def commission_form(request, pk=None):
    k = get_object_or_404(K, pk=pk) if pk else None
    if not S.peut_gerer(request.user, k):
        return HttpResponseForbidden(REFUS)
    form = CommissionForm(request.POST or None, instance=k, mds_possibles=_mds_possibles(request.user))
    if request.method == 'POST' and form.is_valid():
        k = form.save(commit=False)
        if not k.pk:
            k.cree_par = request.user
        k.save()
        form.save_m2m()
        messages.success(request, "Séance enregistrée.")
        return redirect('logement:commission_detail', pk=k.pk)
    return render(request, 'logement/commission_form.html', {'form': form, 'k': k})


@login_required
def commission_detail(request, pk):
    k = get_object_or_404(K.objects.prefetch_related('mds'), pk=pk)
    if not S.commissions_visibles(request.user).filter(pk=k.pk).exists():
        return HttpResponseForbidden(REFUS)
    visibles = X.dossiers_visibles(request.user)
    passages = k.passages.filter(dossier__in=visibles).select_related('dossier__mds', 'dossier__referent')
    candidats = visibles.filter(statut=D.EN_COURS).exclude(passages__commission=k)
    if k.mds.exists():
        candidats = candidats.filter(mds__in=k.mds.all())
    return render(request, 'logement/commission_detail.html', {
        'k': k, 'passages': passages, 'candidats': candidats.order_by('nom')[:200], 'avis': P.AVIS,
        'peut_gerer': S.peut_gerer(request.user, k), 'peut_inscrire': X.peut_voir_module(request.user)})


@login_required
def commission_odj(request, pk):
    k = get_object_or_404(K, pk=pk)
    if not S.commissions_visibles(request.user).filter(pk=k.pk).exists():
        return HttpResponseForbidden(REFUS)
    return _pdf(S.odj_pdf(k, request.user), f"ordre_du_jour_{k.date:%Y%m%d}.pdf")


@login_required
@require_POST
def commission_inscrire(request, pk):
    k = get_object_or_404(K, pk=pk)
    d = get_object_or_404(D, pk=request.POST.get('dossier'))
    if not (S.commissions_visibles(request.user).filter(pk=k.pk).exists() and X.peut_ecrire(request.user, d)):
        return HttpResponseForbidden(REFUS)
    p, cree = S.inscrire(k, d, request.user)
    messages.success(request, f"{d.nom_complet} inscrit(e) à l'ordre du jour." if cree else "Déjà inscrit.")
    if request.POST.get('retour') == 'dossier':
        return redirect('logement:expulsion_detail', pk=d.pk)
    return redirect('logement:commission_detail', pk=k.pk)


@login_required
@require_POST
def commission_tenue(request, pk):
    k = get_object_or_404(K, pk=pk)
    if not S.peut_gerer(request.user, k):
        return HttpResponseForbidden(REFUS)
    k.tenue = True
    k.compte_rendu = (request.POST.get('compte_rendu') or k.compte_rendu).strip()
    k.save()
    messages.success(request, "Séance marquée comme tenue.")
    return redirect('logement:commission_detail', pk=k.pk)


# ------------------------------------------------------------------------------------------------- passages
def _passage(request, pk):
    p = get_object_or_404(P.objects.select_related('dossier__mds', 'dossier__beneficiaire', 'commission', 'cadre'), pk=pk)
    return p, X.peut_voir(request.user, p.dossier)


@login_required
def passage_detail(request, pk):
    p, voir = _passage(request, pk)
    if not voir:
        return HttpResponseForbidden(REFUS)
    ecrire = X.peut_ecrire(request.user, p.dossier) and bool(p.dossier.mds_id)
    if request.method == 'POST' and ecrire and p.statut != P.TRANSMISE:
        v = {cle: (request.POST.get(cle) or '').strip()[:4000] for cle in S.CHAMPS if (request.POST.get(cle) or '').strip()}
        p.actualisation = v
        if p.statut in (P.A_VISER, P.VISEE):
            p.statut, p.cadre, p.date_validation_cadre = P.A_FAIRE, None, None
            messages.warning(request, "L'actualisation a changé après le visa : redemandez le visa du cadre.")
        p.tracer(request.user, "Actualisation modifiée")
        p.save()
        messages.success(request, "Actualisation enregistrée.")
        return redirect('logement:passage_detail', pk=p.pk)
    sections = [(t, [dict(c, valeur=(p.actualisation or {}).get(c['cle'], '')) for c in cs]) for t, cs in S.SECTIONS]
    return render(request, 'logement/passage_detail.html', {
        'p': p, 'd': p.dossier, 'k': p.commission, 'sections': sections, 'peut_ecrire': ecrire,
        'peut_viser': S.peut_viser(request.user, p), 'peut_avis': S.peut_gerer(request.user, p.commission),
        'avis': P.AVIS, 'referents': X.referents_possibles(p.dossier),
        'convocations': p.convocations.select_related('agent')})


@login_required
def passage_pdf(request, pk):
    p, voir = _passage(request, pk)
    if not voir:
        return HttpResponseForbidden(REFUS)
    return _pdf(S.actualisation_pdf(p), f"actualisation_{p.dossier.numero}.pdf")


@login_required
@require_POST
def passage_action(request, pk):
    p, voir = _passage(request, pk)
    if not voir:
        return HttpResponseForbidden(REFUS)
    action, user = request.POST.get('action'), request.user
    ecrire = X.peut_ecrire(user, p.dossier) and bool(p.dossier.mds_id)
    if action == 'demander_visa' and ecrire:
        cadre = S.demander_visa(p, user)
        messages.success(request, f"Visa demandé{' à ' + cadre.get_full_name() if cadre else ''}.")
    elif action == 'viser' and S.peut_viser(user, p) and p.statut in (P.A_FAIRE, P.A_VISER):
        S.viser(p, user)
        messages.success(request, "Visée : vos initiales et la date figurent sur l'actualisation.")
    elif action == 'avis' and S.peut_gerer(user, p.commission):
        avis = request.POST.get('avis')
        if avis not in dict(P.AVIS):
            messages.error(request, "Choisissez l'avis de la commission.")
        else:
            S.saisir_avis(p, user, avis, (request.POST.get('avis_detail') or '').strip()[:2000])
            messages.success(request, "Avis enregistré : le référent est prévenu et l'étape s'ajoute au dossier.")
        if request.POST.get('retour') == 'commission':
            return redirect('logement:commission_detail', pk=p.commission_id)
    elif action == 'convoquer' and ecrire:
        jour, heure = parse_date(request.POST.get('date') or ''), parse_time(request.POST.get('heure') or '')
        if not jour or not heure:
            messages.error(request, "Indiquez la date et l'heure du rendez-vous.")
        else:
            agent = X.referents_possibles(p.dossier).filter(pk=request.POST.get('agent')).first()
            conv = M.convoquer(p.dossier, user, timezone.make_aware(datetime.combine(jour, heure)), agent=agent,
                               lieu=(request.POST.get('lieu') or '').strip(), passage=p)
            messages.success(request, f"{conv.get_type_convocation_display()} : rendez-vous posé dans l'agenda.")
            return redirect(reverse('logement:passage_detail', args=[p.pk]) + f"?courrier={conv.pk}")
    elif action == 'retirer' and (ecrire or S.peut_gerer(user, p.commission)) and not p.avis:
        k = p.commission_id
        p.dossier.tracer(user, "Retiré de l'ordre du jour", str(p.commission))
        p.dossier.save()
        p.delete()
        messages.success(request, "Dossier retiré de l'ordre du jour.")
        return redirect('logement:commission_detail', pk=k)
    else:
        return HttpResponseForbidden(REFUS)
    return redirect('logement:passage_detail', pk=p.pk)


__all__ = ['commissions_liste', 'commission_form', 'commission_detail', 'commission_odj', 'commission_inscrire',
           'commission_tenue', 'passage_detail', 'passage_pdf', 'passage_action']
