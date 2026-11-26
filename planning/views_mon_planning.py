# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# planning/views_mon_planning.py
"""« Mon planning » : les prochains rendez-vous de l'agent connecté, classés par date puis par heure.
Les rendez-vous traités sont masqués (case « afficher les traités »). Sont listés les rendez-vous dont l'agent est titulaire ou co-intervenant."""
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from planning.models import CreneauRdv
from planning.views_permanences_jour import STATUTS_TRAITES

HORIZON_JOURS = 14


@login_required
def mon_planning(request):
    aujourd_hui = date.today()
    fin = aujourd_hui + timedelta(days=HORIZON_JOURS)
    traites = request.GET.get('traites') == '1'
    qs = (CreneauRdv.objects.filter(Q(agent=request.user) | Q(co_intervenants=request.user),
                                    beneficiaire__isnull=False, date__range=(aujourd_hui, fin))
          .select_related('beneficiaire', 'salle').distinct().order_by('date', 'heure_debut', 'pk'))
    qs = qs.filter(statut__in=STATUTS_TRAITES) if traites else qs.exclude(statut__in=STATUTS_TRAITES)
    jours = {}
    for c in qs:
        jours.setdefault(c.date, []).append({
            'heure': c.heure_debut.strftime('%H:%M'),
            'code': c.beneficiaire.code_interne or '',
            'nom': f"{c.beneficiaire.nom.upper()} {c.beneficiaire.prenom}",
            'motif': f"{c.get_nature_display()} – {c.get_domaine_display()}",
            'lieu': c.lieu_affichage,
            'statut': c.get_statut_display(),
            'traite': c.statut in STATUTS_TRAITES,
        })
    context = {
        'jours': sorted(jours.items()),
        'horizon': HORIZON_JOURS,
        'traites': traites,
        'nb_rdv': sum(len(v) for v in jours.values()),
    }
    return render(request, 'planning/mon_planning.html', context)
