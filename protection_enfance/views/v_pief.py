# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/views/v_pief.py
"""Inspecteur enfance famille : contreseing du rapport (ou autre suite, ou complément) et validation des saisines."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from protection_enfance.models import SaisineIP
from protection_enfance.models.m_ip import CAP_PIEF, DECISIONS_FINALES
from protection_enfance.services import ip_circuit as circuit
from protection_enfance.services.ip_circuit import CircuitError
from protection_enfance.views.v_ip import _refus, get_ip

# Préconisation du rapport → décision proposée par défaut à l'inspecteur
DECISION_PAR_PRECONISATION = {'AUCUNE_SUITE': 'CLASSEMENT', 'DROIT_COMMUN': 'DROIT_COMMUN', 'AED': 'AED',
                              'SAISINE_JUDICIAIRE': 'SAISINE_PROCUREUR', 'AUTRE': 'AUTRE'}


@login_required
@require_POST
def avis_rapport(request, ip_id):
    ip = get_ip(request, ip_id)
    if not request.user.a_la_capacite(CAP_PIEF):
        return _refus()
    avis = request.POST.get('avis')
    commentaire = (request.POST.get('commentaire') or '').strip()
    decision = request.POST.get('decision') or ''
    if avis == 'ACCORD':
        decision = DECISION_PAR_PRECONISATION.get(circuit.rapport_de(ip).preconisation, 'AUTRE')
    if avis not in ('ACCORD', 'AUTRE_SUITE', 'COMPLEMENT'):
        messages.error(request, "Choisissez un avis.")
    elif avis == 'AUTRE_SUITE' and decision not in dict(DECISIONS_FINALES):
        messages.error(request, "Précisez la suite décidée.")
    elif avis in ('AUTRE_SUITE', 'COMPLEMENT') and not commentaire:
        messages.error(request, "Un commentaire est nécessaire pour une autre suite ou un complément.")
    else:
        try:
            circuit.avis_inspecteur(ip, request.user, avis, decision if avis != 'COMPLEMENT' else '', commentaire)
            messages.success(request, "Avis enregistré : la MDS est prévenue.")
        except CircuitError as e:
            messages.error(request, str(e))
    return redirect('protection_enfance:rapport', ip_id=ip.numero)


@login_required
@require_POST
def saisine_pief(request, saisine_id):
    s = get_object_or_404(SaisineIP.objects.select_related('ip'), pk=saisine_id)
    if not request.user.a_la_capacite(CAP_PIEF):
        return _refus()
    try:
        circuit.decision_pief_saisine(s, request.user, request.POST.get('valide') == 'oui',
                                      (request.POST.get('commentaire') or '').strip())
        messages.success(request, f"Saisine : {s.get_statut_display()}.")
    except CircuitError as e:
        messages.error(request, str(e))
    from django.urls import reverse
    return redirect(reverse('protection_enfance:ip_detail', kwargs={'ip_id': s.ip.numero}) + "#saisines")
