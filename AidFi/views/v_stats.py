# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/views/v_stats.py
"""Statistiques des aides financières, mois par mois sur une année (cadres de la MDS)."""
import csv

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from AidFi.services.stats_aides import calculer, lignes_csv
from mds.models import UserMDSProfile


@login_required
def statistiques_aides(request):
    user = request.user
    mds = getattr(user, 'mds_principale', None) or getattr(
        UserMDSProfile.objects.filter(user=user, actif=True).select_related('mds').first(), 'mds', None)
    if not (mds and (user.is_superuser or user.a_la_capacite('peut_valider'))):
        messages.error(request, "Statistiques réservées aux cadres de la MDS.")
        return redirect('core:dashboard')

    annee_courante = timezone.localdate().year
    try:
        annee = int(request.GET.get('annee', annee_courante))
    except ValueError:
        annee = annee_courante
    agents = get_user_model().objects.filter(profils_mds__mds=mds, profils_mds__actif=True)\
        .distinct().order_by('last_name', 'first_name')
    agent = agents.filter(pk=request.GET.get('agent')).first() if request.GET.get('agent', '').isdigit() else None
    resultat = calculer(mds, annee, agent)

    if request.GET.get('format') == 'csv':
        r = HttpResponse(content_type='text/csv; charset=utf-8')
        r['Content-Disposition'] = (f'attachment; filename="aides_{mds.code_mds}_{annee}'
                                    f'{"_" + agent.username if agent else ""}.csv"')
        r.write('﻿')
        w = csv.writer(r, delimiter=';')
        w.writerow([f"Aides financières {mds.nom}", f"année {annee}", agent.get_full_name() if agent else "Toute la MDS"])
        for ligne in lignes_csv(resultat):
            w.writerow(ligne)
        return r

    return render(request, 'AidFi/statistiques_aides.html', {
        'r': resultat, 'annee': annee, 'annees': list(range(annee_courante, annee_courante - 6, -1)),
        'agents': agents, 'agent': agent, 'mds': mds, 'query': request.GET.urlencode(),
    })
