# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/views/v_expulsion_mds.py
"""Prévention des expulsions, côté MDS : convocations au diagnostic, questionnaire au bailleur, diagnostic social et
financier (Cerfa) ou bordereau de carence, visa du cadre en un clic. L'envoi passe par « Envoi par mail » /
« Imprimer pour envoi » (v_envoi.py), qui alimente le compteur de papier économisé."""
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time
from django.views.decorators.http import require_POST

from ..models import ConvocationExpulsion as C, DiagnosticExpulsion as G, DossierExpulsion as D
from ..services import expulsion as X, expulsion_mds as M
from ..services.dsf import CHAMPS, LIMITES, SECTIONS, calculs

REFUS = "Réservé aux agents de la MDS chargée du dossier et au Service Logement."


def _pdf(contenu, nom):
    r = HttpResponse(contenu, content_type='application/pdf')
    r['Content-Disposition'] = f'inline; filename="{nom}"'
    return r


def _ecriture(request, dossier):
    return X.peut_voir(request.user, dossier) and X.peut_ecrire(request.user, dossier) and dossier.mds_id


# ------------------------------------------------------------------------------------------------- convocations
@login_required
@require_POST
def expulsion_convoquer(request, pk):
    d = get_object_or_404(D, pk=pk)
    if not _ecriture(request, d):
        return HttpResponseForbidden(REFUS)
    jour, heure = parse_date(request.POST.get('date') or ''), parse_time(request.POST.get('heure') or '')
    if not jour or not heure:
        messages.error(request, "Indiquez la date et l'heure du rendez-vous.")
        return redirect('logement:expulsion_detail', pk=d.pk)
    agent = X.referents_possibles(d).filter(pk=request.POST.get('agent')).first()
    quand = timezone.make_aware(datetime.combine(jour, heure))
    conv = M.convoquer(d, request.user, quand, agent=agent, lieu=(request.POST.get('lieu') or '').strip())
    qui = conv.agent.get_full_name() if conv.agent else "l'agent"
    messages.success(request, f"{conv.get_type_convocation_display()} enregistrée et posée dans l'agenda de {qui}. "
                              "Le courrier s'ouvre pour l'impression.")
    return redirect(reverse('logement:expulsion_detail', args=[d.pk]) + f"?courrier={conv.pk}")


@login_required
def convocation_pdf(request, pk):
    conv = get_object_or_404(C.objects.select_related('dossier__mds', 'agent'), pk=pk)
    if not X.peut_voir(request.user, conv.dossier):
        return HttpResponseForbidden(REFUS)
    from ..services.expulsion_documents import convocation_pdf as fabriquer
    return _pdf(fabriquer(conv), f"convocation_{conv.dossier.numero}_{conv.pk}.pdf")


@login_required
@require_POST
def convocation_noter(request, pk):
    conv = get_object_or_404(C.objects.select_related('dossier'), pk=pk)
    if not _ecriture(request, conv.dossier):
        return HttpResponseForbidden(REFUS)
    statut = request.POST.get('statut')
    if statut in dict(C.STATUTS):
        M.noter(conv, statut, request.user)
        if statut == C.ABSENT and M.carence_possible(conv.dossier):
            messages.warning(request, "Deux convocations sans réponse : vous pouvez établir le bordereau de carence.")
    return redirect('logement:expulsion_detail', pk=conv.dossier_id)


# ------------------------------------------------------------------------------------------------- bailleur
@login_required
@require_POST
def questionnaire_preparer(request, pk):
    d = get_object_or_404(D, pk=pk)
    if not _ecriture(request, d):
        return HttpResponseForbidden(REFUS)
    retour = parse_date(request.POST.get('retour') or '')
    if not retour:
        messages.error(request, "Indiquez la date de retour souhaitée.")
        return redirect('logement:expulsion_detail', pk=d.pk)
    d.questionnaire_retour_avant = retour
    email = (request.POST.get('email') or '').strip()
    if email:
        d.proprietaire_email = email
    d.save()
    return redirect('logement:envoi_dossier', nature='bailleur', pk=d.pk)


@login_required
def questionnaire_pdf(request, pk):
    d = get_object_or_404(D, pk=pk)
    if not X.peut_voir(request.user, d):
        return HttpResponseForbidden(REFUS)
    from ..services.expulsion_documents import questionnaire_pdf as fabriquer
    retour = d.questionnaire_retour_avant or (timezone.localdate() + timedelta(days=15))
    return _pdf(fabriquer(d, retour), f"questionnaire_bailleur_{d.numero}.pdf")


@login_required
@require_POST
def questionnaire_recu(request, pk):
    d = get_object_or_404(D, pk=pk)
    if not _ecriture(request, d):
        return HttpResponseForbidden(REFUS)
    d.questionnaire_bailleur_retour = timezone.localdate()
    d.tracer(request.user, "Questionnaire du bailleur reçu")
    d.save()
    messages.success(request, "Retour du bailleur noté : pensez à le joindre au diagnostic (GED).")
    return redirect('logement:expulsion_detail', pk=d.pk)


# ------------------------------------------------------------------------------------------------- DSF, carence
@login_required
@require_POST
def diagnostic_nouveau(request, pk):
    d = get_object_or_404(D, pk=pk)
    if not _ecriture(request, d):
        return HttpResponseForbidden(REFUS)
    type_document = request.POST.get('type_document', G.DSF)
    if type_document not in dict(G.TYPES):
        type_document = G.DSF
    g = d.diagnostics.filter(type_document=type_document).exclude(statut=G.ENVOYE).first() \
        or M.nouveau_diagnostic(d, request.user, type_document)
    return redirect('logement:diagnostic_modifier' if type_document == G.DSF else 'logement:diagnostic_detail', pk=g.pk)


def _diag(request, pk):
    g = get_object_or_404(G.objects.select_related('dossier__mds', 'dossier__beneficiaire', 'cadre', 'redacteur'), pk=pk)
    return g, X.peut_voir(request.user, g.dossier)


@login_required
def diagnostic_modifier(request, pk):
    g, voir = _diag(request, pk)
    if not voir or not _ecriture(request, g.dossier):
        return HttpResponseForbidden(REFUS)
    if g.statut == G.ENVOYE:
        messages.info(request, "Ce document est déjà transmis : ouvrez-en un nouveau si la situation a changé.")
        return redirect('logement:diagnostic_detail', pk=g.pk)
    if request.method == 'POST':
        v = {}
        for cle, c in CHAMPS.items():
            if c['type'] == 'case':
                if request.POST.get(cle):
                    v[cle] = True
            else:
                x = (request.POST.get(cle) or '').strip()
                if x:
                    v[cle] = x[:LIMITES[cle]] if cle in LIMITES else x[:300]
        g.donnees = v
        if g.statut in (G.VISE, G.A_VISER):        # une modification après le visa le fait redemander
            g.statut, g.cadre, g.date_validation_cadre = G.BROUILLON, None, None
            messages.warning(request, "Le diagnostic a changé après le visa : redemandez le visa du cadre.")
        g.tracer(request.user, "Modifié")
        g.save()
        messages.success(request, "Diagnostic enregistré.")
        return redirect('logement:diagnostic_detail' if request.POST.get('suite') else 'logement:diagnostic_modifier',
                        pk=g.pk)
    sections = [(titre, [dict(c, valeur=(g.donnees or {}).get(c['cle'], '')) for c in champs]) for titre, champs in SECTIONS]
    return render(request, 'logement/diagnostic_form.html', {'g': g, 'd': g.dossier, 'sections': sections,
                                                             'bilan': calculs(g.donnees or {}), 'limites': LIMITES})


@login_required
def diagnostic_detail(request, pk):
    g, voir = _diag(request, pk)
    if not voir:
        return HttpResponseForbidden(REFUS)
    ecrire = bool(_ecriture(request, g.dossier))
    v = g.donnees or {}
    resume = {'locataire': f"{v.get('Noms', g.dossier.nom.upper())} {v.get('Prénoms', g.dossier.prenom)}",
              'audience': v.get('Date 10', ''), 'dette': v.get('Montant dette', ''),
              'renseignes': len([k for k in v if k in CHAMPS]), 'total': len(CHAMPS),
              'evaluation': bool(v.get('Evaluation sociale')), 'convocations': v.get('convocations', '')}
    return render(request, 'logement/diagnostic_detail.html', {
        'g': g, 'd': g.dossier, 'peut_ecrire': ecrire, 'peut_viser': M.peut_viser(request.user, g), 'resume': resume,
        'convocations': g.dossier.convocations.all(), 'bilan': calculs(g.donnees or {}) if g.type_document == G.DSF else {}})


@login_required
def diagnostic_pdf(request, pk):
    g, voir = _diag(request, pk)
    if not voir:
        return HttpResponseForbidden(REFUS)
    from ..services.expulsion_documents import document
    nom = "DSF" if g.type_document == G.DSF else "bordereau_carence"
    return _pdf(document(g), f"{nom}_{g.dossier.numero}.pdf")


@login_required
@require_POST
def diagnostic_action(request, pk):
    g, voir = _diag(request, pk)
    if not voir:
        return HttpResponseForbidden(REFUS)
    action = request.POST.get('action')
    if action == 'viser':
        if not M.peut_viser(request.user, g) or g.statut not in (G.A_VISER, G.BROUILLON):
            return HttpResponseForbidden("Visa réservé au cadre de la MDS.")
        M.viser(g, request.user)
        messages.success(request, "Visé : votre visa daté figure sur le document. Le rédacteur est prévenu.")
    elif action == 'demander_visa':
        if not _ecriture(request, g.dossier):
            return HttpResponseForbidden(REFUS)
        if g.type_document == G.CARENCE and request.POST.get('convocations') is not None:
            g.donnees = dict(g.donnees or {}, convocations=request.POST.get('convocations', '').strip()[:200])
        cadre = M.demander_visa(g, request.user)
        messages.success(request, f"Visa demandé{' à ' + cadre.get_full_name() if cadre else ''} : il est prévenu "
                                  "dans CID.")
    elif action == 'enregistrer' and g.type_document == G.CARENCE:
        if not _ecriture(request, g.dossier):
            return HttpResponseForbidden(REFUS)
        g.donnees = dict(g.donnees or {}, convocations=request.POST.get('convocations', '').strip()[:200])
        g.save()
    return redirect('logement:diagnostic_detail', pk=g.pk)


__all__ = ['expulsion_convoquer', 'convocation_pdf', 'convocation_noter', 'questionnaire_preparer',
           'questionnaire_pdf', 'questionnaire_recu', 'diagnostic_nouveau', 'diagnostic_modifier',
           'diagnostic_detail', 'diagnostic_pdf', 'diagnostic_action']
