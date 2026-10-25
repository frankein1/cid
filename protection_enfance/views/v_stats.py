# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/views/v_stats.py
import csv

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from mds.models import MDS, UserMDSProfile
from protection_enfance.models.m_ip import CAP_CRIP, CAP_PIEF
from protection_enfance.services.stats_ip import calculer, lignes_csv


@login_required
def statistiques_ip(request):
    user = request.user
    departemental = user.is_superuser or user.a_la_capacite(CAP_CRIP) or user.a_la_capacite(CAP_PIEF)
    mds_user = getattr(user, 'mds_principale', None) or getattr(
        UserMDSProfile.objects.filter(user=user, actif=True).select_related('mds').first(), 'mds', None)
    if not departemental and not (mds_user and user.a_la_capacite('peut_valider')):
        messages.error(request, "Statistiques IP réservées aux cadres, à la CRIP et aux inspecteurs.")
        return redirect('core:dashboard')

    annee_courante = timezone.localdate().year
    try:
        annee = int(request.GET.get('annee', annee_courante))
    except ValueError:
        annee = annee_courante
    if departemental:
        toutes = MDS.objects.filter(active=True).order_by('nom')
        mds = toutes.filter(pk=request.GET.get('mds')).first() if request.GET.get('mds', '').isdigit() else None
    else:
        toutes, mds = None, mds_user
    agents = get_user_model().objects.none()
    agent = None
    if mds:
        agents = get_user_model().objects.filter(profils_mds__mds=mds, profils_mds__actif=True)\
            .distinct().order_by('last_name', 'first_name')
        agent = agents.filter(pk=request.GET.get('agent')).first() if request.GET.get('agent', '').isdigit() else None
    r = calculer(annee, mds, agent)

    if request.GET.get('format') == 'csv':
        resp = HttpResponse(content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="ip_{mds.code_mds if mds else "departement"}_{annee}.csv"'
        resp.write('﻿')
        w = csv.writer(resp, delimiter=';')
        w.writerow([f"Informations préoccupantes – {mds.nom if mds else 'tout le département'}", f"année {annee}"])
        for ligne in lignes_csv(r):
            w.writerow(ligne)
        return resp

    return render(request, 'protection_enfance/statistiques_ip.html', {
        'r': r, 'annee': annee, 'annees': list(range(annee_courante, annee_courante - 6, -1)),
        'mds': mds, 'toutes_mds': toutes, 'agents': agents, 'agent': agent, 'query': request.GET.urlencode(),
    })
