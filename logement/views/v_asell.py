# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/views/v_asell.py
"""Orientation ASELL (généraliste ou renforcée, accès ou maintien) : fiche préremplie depuis l'usager ou depuis son
dossier de prévention des expulsions, PDF, envoi à l'opérateur, réponse."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from beneficiaire.models import Beneficiaire
from beneficiaire.views import user_peut_agir_sur_beneficiaire

from ..models import DossierExpulsion, OperateurASELL, OrientationASELL as A
from ..services import asell as S

REFUS = "Réservé aux agents de la MDS de l'usager."


def _orientation(request, pk):
    a = get_object_or_404(A.objects.select_related('beneficiaire', 'mds', 'operateur', 'dossier_expulsion', 'cree_par'), pk=pk)
    return a, S.peut_voir(request.user, a)


@login_required
@require_POST
def asell_nouvelle(request, code_interne):
    b = get_object_or_404(Beneficiaire.tous.select_related('mds'), code_interne=code_interne)
    if b.niveau_acces(request.user) != 'complet' or not user_peut_agir_sur_beneficiaire(request.user, b) or not b.mds_id:
        return HttpResponseForbidden(REFUS)
    type_mesure = request.POST.get('type_mesure')
    volet = request.POST.get('volet') or A.MAINTIEN
    if type_mesure not in dict(A.TYPES) or volet not in dict(A.VOLETS):
        return HttpResponseForbidden(REFUS)
    dossier = DossierExpulsion.objects.filter(pk=request.POST.get('dossier_expulsion') or 0, beneficiaire=b).first() \
        or DossierExpulsion.objects.filter(beneficiaire=b, statut=DossierExpulsion.EN_COURS).order_by('-pk').first()
    a = A.objects.filter(beneficiaire=b, type_mesure=type_mesure, statut=A.BROUILLON).first()
    if a is None:
        a = S.creer(b, request.user, type_mesure, volet, dossier)
        messages.success(request, "Fiche préremplie : vérifiez chaque rubrique, choisissez l'opérateur et rédigez l'évaluation.")
    return redirect('logement:asell_detail', pk=a.pk)


@login_required
def asell_detail(request, pk):
    a, voir = _orientation(request, pk)
    if not voir:
        return HttpResponseForbidden(REFUS)
    ecrire = S.peut_ecrire(request.user, a)
    if request.method == 'POST':
        if not (ecrire and a.modifiable):
            return HttpResponseForbidden(REFUS)
        a.donnees = S.lire_formulaire(request.POST, a.type_mesure)
        a.volet = request.POST.get('volet') if request.POST.get('volet') in dict(A.VOLETS) else a.volet
        a.operateur = OperateurASELL.objects.filter(pk=request.POST.get('operateur') or 0, actif=True).first()
        a.operateur_libre = "" if a.operateur else (request.POST.get('operateur_libre') or '').strip()[:150]
        a.tracer(request.user, "Fiche modifiée")
        a.save()
        messages.success(request, "Fiche enregistrée.")
        return redirect('logement:asell_detail', pk=a.pk)
    from ..services import asell_operateurs as AO
    secteur, autres = AO.pour_usager(a.type_mesure, a.beneficiaire)
    if a.operateur and a.operateur not in secteur + autres:       # opérateur retiré depuis : on le garde visible
        autres = [a.operateur] + autres
    return render(request, 'logement/asell_detail.html', {
        'a': a, 'b': a.beneficiaire, 'sections': S.pour_gabarit(a), 'peut_ecrire': ecrire and a.modifiable,
        'peut_repondre': ecrire, 'manques': S.manques(a) if a.modifiable else [], 'volets': A.VOLETS,
        'operateurs_secteur': secteur, 'operateurs_autres': autres, 'reponses': A.REPONSES})


@login_required
def asell_pdf(request, pk):
    a, voir = _orientation(request, pk)
    if not voir:
        return HttpResponseForbidden(REFUS)
    r = HttpResponse(S.fiche_pdf(a), content_type='application/pdf')
    r['Content-Disposition'] = f'inline; filename="orientation_asell_{a.pk}.pdf"'
    return r


@login_required
@require_POST
def asell_action(request, pk):
    a, voir = _orientation(request, pk)
    if not voir or not S.peut_ecrire(request.user, a):
        return HttpResponseForbidden(REFUS)
    p, action = request.POST, request.POST.get('action')
    retour_usager = redirect('beneficiaire:detail_beneficiaire', code_interne=a.beneficiaire.code_interne)
    if action == 'reponse' and a.statut == A.ENVOYEE:
        if p.get('reponse') not in dict(A.REPONSES):
            messages.error(request, "Choisissez la réponse reçue.")
        else:
            S.enregistrer_reponse(a, request.user, p.get('reponse'), parse_date(p.get('date_reponse') or ''),
                                  (p.get('detail') or '').strip())
            messages.success(request, "Réponse enregistrée.")
    elif action == 'supprimer' and a.statut == A.BROUILLON:
        a.delete()
        messages.success(request, "Brouillon supprimé.")
        return retour_usager
    elif action == 'abandonner' and a.statut == A.ENVOYEE and not a.reponse:
        a.statut = A.ABANDONNEE
        a.tracer(request.user, "Abandonnée", (p.get('detail') or '').strip()[:200])
        a.save()
        messages.success(request, "Orientation abandonnée.")
    else:
        return HttpResponseForbidden(REFUS)
    return redirect('logement:asell_detail', pk=a.pk)


__all__ = ['asell_nouvelle', 'asell_detail', 'asell_pdf', 'asell_action']
