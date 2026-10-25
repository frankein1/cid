# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# planning/statistiques.py
"""
Statistiques d'activité (lot 4) : nombre et heures de rendez-vous par NATURE × DOMAINE,
prévus et réalisés, premières fois, par période, pour la MDS ou pour un agent.

Règles de comptage :
  - prévu     : tout rendez-vous pris ou noté (un créneau de permanence resté libre ne compte pas) ;
  - réalisé   : « venu et reçu » + « VAD – usager absent » (l'agent s'est déplacé), ce dernier distingué ;
  - non réalisé : absent, venu non reçu, annulé ou reporté (usager ou MDS) ;
  - 1re fois  : rendez-vous réalisé coché « 1er rendez-vous » ;
  - un rendez-vous compte pour son agent ET ses co-intervenants (réunions comprises) dans la vue
    par agent, mais une seule fois dans les totaux de la MDS.
"""
from collections import defaultdict
from datetime import date, timedelta

from django.db.models import Q

from .agenda import rdv_de_la_mds
from .models import DOMAINES_RDV, NATURES_RDV, STATUTS_ANNULES, STATUTS_REALISES


def periodes_rapides(aujourd_hui=None):
    """Raccourcis : ce mois, mois précédent, ce trimestre, trimestre précédent, cette année, année précédente."""
    j = aujourd_hui or date.today()
    debut_mois = j.replace(day=1)
    fin_mois_prec = debut_mois - timedelta(days=1)
    t = (j.month - 1) // 3
    debut_trim = date(j.year, 3 * t + 1, 1)
    fin_trim_prec = debut_trim - timedelta(days=1)
    debut_trim_prec = date(fin_trim_prec.year, 3 * ((fin_trim_prec.month - 1) // 3) + 1, 1)

    def fin_de_mois(d):
        return (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

    return [
        ("Ce mois", debut_mois, fin_de_mois(j)),
        ("Mois précédent", fin_mois_prec.replace(day=1), fin_mois_prec),
        ("Ce trimestre", debut_trim, fin_de_mois(date(j.year, 3 * t + 3, 1))),
        ("Trimestre précédent", debut_trim_prec, fin_trim_prec),
        ("Cette année", date(j.year, 1, 1), date(j.year, 12, 31)),
        ("Année précédente", date(j.year - 1, 1, 1), date(j.year - 1, 12, 31)),
    ]


def _vide():
    return {'prevus': 0, 'realises': 0, 'vad_absent': 0, 'non_realises': 0,
            'min_prevues': 0, 'min_realisees': 0, 'premieres_fois': 0}


def _ajouter(case, r):
    case['prevus'] += 1
    case['min_prevues'] += r.duree_minutes
    if r.statut in STATUTS_REALISES:
        case['realises'] += 1
        case['min_realisees'] += r.duree_minutes
        if r.statut == 'VAD_ABSENT':
            case['vad_absent'] += 1
        if r.premiere_fois:
            case['premieres_fois'] += 1
    elif r.statut in STATUTS_ANNULES:
        case['non_realises'] += 1


def heures(minutes):
    """1 h 30 → '1h30' ; 0 → '–'."""
    if not minutes:
        return "–"
    h, m = divmod(int(minutes), 60)
    return f"{h}h{m:02d}" if h else f"{m} min"


def calculer(mds, debut, fin, agent=None):
    rdvs = (rdv_de_la_mds(mds).filter(date__range=(debut, fin)).exclude(statut='DISPONIBLE')
            .prefetch_related('co_intervenants').select_related('agent').distinct())
    if agent is not None:
        rdvs = rdvs.filter(Q(agent=agent) | Q(co_intervenants=agent)).distinct()
    rdvs = list(rdvs)

    croise = defaultdict(_vide)            # (nature, domaine)
    par_nature, par_domaine, total = defaultdict(_vide), defaultdict(_vide), _vide()
    par_agent = defaultdict(lambda: {'total': _vide(), 'domaines': defaultdict(_vide)})
    for r in rdvs:
        for case in (croise[(r.nature, r.domaine)], par_nature[r.nature], par_domaine[r.domaine], total):
            _ajouter(case, r)
        personnes = {u for u in r.co_intervenants.all()}
        if r.agent:
            personnes.add(r.agent)
        for p in personnes:
            _ajouter(par_agent[p]['total'], r)
            _ajouter(par_agent[p]['domaines'][r.domaine], r)

    natures, domaines = dict(NATURES_RDV), dict(DOMAINES_RDV)
    tableau = [{'nature': natures[n], 'code': n,
                'cases': [croise.get((n, d), _vide()) for d in domaines],
                'total': par_nature.get(n, _vide())}
               for n in natures if n in par_nature]
    agents = sorted(par_agent.items(), key=lambda kv: (kv[0].last_name, kv[0].first_name))
    return {
        'total': total,
        'tableau': tableau,
        'domaines': [{'code': d, 'libelle': lib, 'valeurs': par_domaine.get(d, _vide())} for d, lib in DOMAINES_RDV],
        'agents': [{'agent': a, 'total': v['total'],
                    'domaines': [v['domaines'].get(d, _vide()) for d in domaines]} for a, v in agents],
        'vad': par_nature.get('VAD', _vide()),
    }


def _h(minutes):
    """Heures décimales à la française (virgule) pour qu'Excel les lise comme des nombres."""
    return f"{minutes / 60:.2f}".replace('.', ',')


def lignes_csv(resultat):
    """Export tableur : une ligne par nature × domaine, puis par agent."""
    yield ["Nature", "Domaine", "Prévus", "Réalisés", "dont VAD usager absent", "Non réalisés",
           "Heures prévues", "Heures réalisées", "1res fois"]
    domaines = [d['libelle'] for d in resultat['domaines']]
    for ligne in resultat['tableau']:
        for dom, c in zip(domaines, ligne['cases']):
            if c['prevus']:
                yield [ligne['nature'], dom, c['prevus'], c['realises'], c['vad_absent'], c['non_realises'],
                       _h(c['min_prevues']), _h(c['min_realisees']), c['premieres_fois']]
    t = resultat['total']
    yield ["TOTAL", "", t['prevus'], t['realises'], t['vad_absent'], t['non_realises'],
           _h(t['min_prevues']), _h(t['min_realisees']), t['premieres_fois']]
    yield []
    yield ["Agent"] + [f"Heures réalisées {d}" for d in domaines] + ["Heures réalisées (total)", "Rendez-vous réalisés", "1res fois"]
    for a in resultat['agents']:
        yield ([a['agent'].get_full_name() or a['agent'].username]
               + [_h(c['min_realisees']) for c in a['domaines']]
               + [_h(a['total']['min_realisees']), a['total']['realises'], a['total']['premieres_fois']])
