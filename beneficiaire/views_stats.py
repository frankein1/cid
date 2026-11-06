# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/views_stats.py
"""Page « Statistiques de l'accompagnement » : cadres de MDS (leur MDS, détail par agent) et direction
(tout le département, comparaison des MDS, sans détail par agent). Export CSV ; période libre ou année civile."""
import csv
from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone

from mds.models import MDS, UserMDSProfile

from . import stats_accompagnement as st


def _direction(u):
    return u.is_superuser or u.a_la_capacite('peut_administrer') or u.a_la_capacite('stats_departement')


def _date(v, defaut):
    try:
        return date.fromisoformat(v)
    except (TypeError, ValueError):
        return defaut


@login_required
def statistiques_accompagnement(request):
    u = request.user
    direction = _direction(u)
    mes_mds = list(MDS.objects.filter(profils_utilisateurs__user=u, profils_utilisateurs__actif=True).distinct())
    if not direction and not (u.a_la_capacite('peut_valider') and mes_mds):
        return HttpResponseForbidden("Statistiques réservées aux cadres de MDS et à la direction.")
    j = timezone.localdate()
    annee = request.GET.get('annee', '')
    if annee.isdigit():
        debut, fin = date(int(annee), 1, 1), min(date(int(annee), 12, 31), j)
    else:
        debut, fin = _date(request.GET.get('debut'), date(j.year, 1, 1)), _date(request.GET.get('fin'), j)
    if debut > fin:
        debut, fin = fin, debut
    choix = MDS.objects.all().order_by('nom') if direction else MDS.objects.filter(pk__in=[m.pk for m in mes_mds])
    mds_id = request.GET.get('mds', '')
    mds = choix.filter(pk=mds_id).first() if mds_id.isdigit() else None
    if mds:
        p = st.Perimetre([mds.pk], par_agent=not direction or mds in mes_mds)
    elif direction:
        p = st.Perimetre(None, par_agent=False)
    else:
        p = st.Perimetre([m.pk for m in mes_mds], par_agent=True)
    r = st.calculer(p, debut, fin)
    comparaison = st.comparaison_mds(debut, fin, choix) if direction and not mds else None
    if request.GET.get('format') == 'csv':
        rep = HttpResponse(content_type='text/csv; charset=utf-8')
        rep['Content-Disposition'] = (f'attachment; filename="accompagnement_{debut:%Y%m%d}_{fin:%Y%m%d}'
                                      f'{"_" + mds.code_mds if mds else ""}.csv"')
        rep.write('﻿')
        w = csv.writer(rep, delimiter=';')
        w.writerow([f"Statistiques de l'accompagnement du {debut:%d/%m/%Y} au {fin:%d/%m/%Y}",
                    mds.nom if mds else ("Département" if direction else ", ".join(m.nom for m in mes_mds))])
        for ligne in st.lignes_csv(r, comparaison):
            w.writerow(ligne)
        return rep
    return render(request, 'beneficiaire/statistiques_accompagnement.html', {
        'r': r, 'a': r['activite'], 'debut': debut, 'fin': fin, 'choix': choix, 'mds': mds, 'direction': direction,
        'comparaison': comparaison, 'par_agent': p.par_agent, 'annees': range(j.year, j.year - 4, -1),
        'file_active': st.masque(r['activite']['file_active']), 'nouveaux': st.masque(r['activite']['nouveaux']),
        'perimetre': mds.nom if mds else ("Tout le département" if direction else ", ".join(m.nom for m in mes_mds)),
        'requete': request.GET.urlencode(),
    })
