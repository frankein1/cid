# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/services/stats_ip.py
"""
Statistiques IP : nombre reçu dans l'année (date de réception CRIP), nombre traité par agent,
dates de début / point intermédiaire / fin prévue / fin réelle, délai respecté (oui/non) et
dépassement en jours. Tout est calculé à partir de ce qui est saisi dans CID (actions, visas, envoi).
"""
from collections import defaultdict

from django.db.models import Q

from protection_enfance.models import InformationPreoccupante
from protection_enfance.models.m_ip import STATUTS_OUVERTS

MOIS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre",
        "Novembre", "Décembre"]


def _nom(u):
    return (u.get_full_name() or u.username) if u else "-"


def calculer(annee, mds=None, agent=None):
    qs = (InformationPreoccupante.objects.filter(date_reception_crip__year=annee)
          .exclude(statut='RECUE')
          .select_related('mds', 'binome_1', 'binome_2').prefetch_related('actions__participants', 'enfants'))
    if mds is not None:
        qs = qs.filter(Q(mds=mds) | Q(mds_partage=mds)).distinct()
    if agent is not None:
        qs = qs.filter(Q(binome_1=agent) | Q(binome_2=agent))

    mois = [{'nom': MOIS[i], 'recues': 0, 'terminees': 0, 'dans_delai': 0, 'hors_delai': 0} for i in range(12)]
    par_agent = defaultdict(lambda: {'ip': 0, 'terminees': 0, 'dans_delai': 0, 'hors_delai': 0,
                                     'depassement': 0, 'en_cours': 0, 'actions': 0})
    lignes = []
    total = {'recues': 0, 'en_cours': 0, 'terminees': 0, 'dans_delai': 0, 'hors_delai': 0,
             'en_retard': 0, 'depassement': 0, 'enfants': 0}
    for ip in qs:
        fin = ip.date_fin_reelle
        respecte = ip.delai_respecte
        nb_actions = len([a for a in ip.actions.all() if a.resultat != 'PREVU'])
        lignes.append({'ip': ip, 'debut': ip.date_reception_crip, 'intermediaire': ip.date_intermediaire,
                       'fin_prevue': ip.date_echeance, 'fin_reelle': fin, 'respecte': respecte,
                       'depassement': ip.depassement_jours, 'actions': nb_actions,
                       'binome': ", ".join(_nom(u) for u in ip.binome) or "-"})
        mois[ip.date_reception_crip.month - 1]['recues'] += 1
        total['recues'] += 1
        total['enfants'] += len(ip.enfants.all())
        if fin and fin.year == annee:
            m = mois[fin.month - 1]
            m['terminees'] += 1
            m['dans_delai' if respecte else 'hors_delai'] += 1
        if fin:
            total['terminees'] += 1
            total['dans_delai' if respecte else 'hors_delai'] += 1
            total['depassement'] += ip.depassement_jours
        elif ip.statut in STATUTS_OUVERTS:
            total['en_cours'] += 1
            if ip.alerte == 'retard':
                total['en_retard'] += 1
        for u in ip.binome:
            a = par_agent[u]
            a['ip'] += 1
            a['actions'] += sum(1 for x in ip.actions.all() if x.resultat != 'PREVU'
                                and (x.auteur_id == u.pk or u in x.participants.all()))
            if fin:
                a['terminees'] += 1
                a['dans_delai' if respecte else 'hors_delai'] += 1
                a['depassement'] += ip.depassement_jours
            else:
                a['en_cours'] += 1

    cumul = 0
    for m in mois:
        cumul += m['recues']
        m['cumul_recues'] = cumul
    total['taux_delai'] = round(100 * total['dans_delai'] / total['terminees']) if total['terminees'] else None
    total['depassement_moyen'] = (round(total['depassement'] / total['hors_delai'], 1)
                                  if total['hors_delai'] else 0)
    agents = sorted(({'agent': u, **v, 'depassement_moyen': round(v['depassement'] / v['hors_delai'], 1)
                      if v['hors_delai'] else 0} for u, v in par_agent.items()),
                    key=lambda x: (-x['ip'], x['agent'].last_name))
    return {'mois': mois, 'agents': agents, 'lignes': sorted(lignes, key=lambda l: l['debut']), 'total': total}


def lignes_csv(r):
    yield ["Référence", "MDS", "Binôme", "Reçue CRIP (début)", "Point intermédiaire", "Fin prévue", "Fin réelle",
           "Délai respecté", "Dépassement (jours)", "Démarches réalisées", "Statut", "Décision"]
    for l in r['lignes']:
        ip = l['ip']
        f = lambda d: d.strftime('%d/%m/%Y') if d else ""
        yield [ip.numero, str(ip.mds or ""), l['binome'], f(l['debut']), f(l['intermediaire']), f(l['fin_prevue']),
               f(l['fin_reelle']), {True: "oui", False: "non", None: "en cours"}[l['respecte']], l['depassement'],
               l['actions'], ip.get_statut_display(), ip.get_decision_finale_display() if ip.decision_finale else ""]
    yield []
    yield ["Agent", "IP (binôme)", "En cours", "Terminées", "Dans le délai", "Hors délai", "Dépassement moyen (j)",
           "Démarches"]
    for a in r['agents']:
        yield [_nom(a['agent']), a['ip'], a['en_cours'], a['terminees'], a['dans_delai'], a['hors_delai'],
               a['depassement_moyen'], a['actions']]
