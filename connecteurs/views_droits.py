# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/views_droits.py
"""Droits CAF / France Travail sur la fiche : écarts à régler, montants relevés sur l'accès partenaire CAF."""
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from beneficiaire.models import Beneficiaire

from .ecarts import regler
from .models import EcartSituation, PrestationRelevee


def _fiche(request, code_interne):
    b = get_object_or_404(Beneficiaire, code_interne=code_interne)
    if b.niveau_acces(request.user) != 'complet':
        return b, HttpResponseForbidden("Réservé aux agents de la MDS de l'usager.")
    return b, None


def _retour(b):
    return redirect(reverse('beneficiaire:detail_beneficiaire', kwargs={'code_interne': b.code_interne}) + '#situation-externe')


@login_required
@require_POST
def regler_ecart(request, code_interne, pk):
    b, refus = _fiche(request, code_interne)
    if refus:
        return refus
    e = get_object_or_404(EcartSituation, pk=pk, beneficiaire=b, regle_le__isnull=True)
    regler(e, request.user, request.POST.get('commentaire', '').strip())
    messages.success(request, "Écart marqué comme réglé.")
    return _retour(b)


@login_required
@require_POST
def relever_prestations(request, code_interne):
    """« Actualiser les aides » : montants vus sur l'accès partenaire CAF, cochés un par un (rien d'obligatoire)."""
    b, refus = _fiche(request, code_interne)
    if refus:
        return refus
    try:
        jour = date.fromisoformat(request.POST.get('date_releve', ''))
    except ValueError:
        jour = date.today()
    n = 0
    for code, _, _ in PrestationRelevee.PRESTATIONS:
        if request.POST.get(f'p_{code}') != '1':
            continue
        try:
            montant = Decimal(request.POST.get(f'm_{code}', '').replace(',', '.').replace(' ', ''))
        except InvalidOperation:
            messages.error(request, f"Montant illisible pour « {dict((c, l) for c, l, _ in PrestationRelevee.PRESTATIONS)[code]} ».")
            continue
        if montant < 0 or montant > 100000:
            continue
        PrestationRelevee.objects.create(beneficiaire=b, prestation=code, montant=montant, date_releve=jour,
                                         saisi_par=request.user)
        n += 1
    if n:
        messages.success(request, f"{n} montant{'s' if n > 1 else ''} enregistré{'s' if n > 1 else ''}. "
                                  "Ils peuvent être repris dans le budget du foyer.")
    else:
        messages.info(request, "Aucune aide cochée : rien n'a été enregistré.")
    return _retour(b)


def derniers_releves(beneficiaire):
    """Le dernier montant relevé pour chaque prestation."""
    vus = {}
    for p in beneficiaire.prestations_relevees.select_related('saisi_par'):
        vus.setdefault(p.prestation, p)
    return [vus[c] for c, _, _ in PrestationRelevee.PRESTATIONS if c in vus]
