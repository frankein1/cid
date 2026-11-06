# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/stats_accompagnement.py
"""
Statistiques de l'accompagnement : entretiens (activité, file active, types, modes, orientations, suites), public
accompagné, budgets du foyer, ateliers collectifs.

Trois usages, un seul calcul :
- le cadre de MDS pilote son équipe (détail par agent, pour sa MDS seulement) ;
- le rapport d'activité annuel (période = l'année, page imprimable, export CSV) ;
- la direction compare les MDS (tableau par MDS, jamais de détail par agent).

Règles :
- seuls les champs structurés sont comptés : aucun texte libre, jamais la synthèse privée ;
- secret statistique : un effectif de personnes ou de foyers compris entre 1 et 4 est affiché « < 5 », sans
  pourcentage qui permettrait de le recalculer ;
- un entretien est compté dans la MDS actuelle de l'usager (pas d'historique des transferts dans le calcul).
"""
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from statistics import median

SEUIL = 5
TRANCHES_AGE = [(0, 17, "Moins de 18 ans"), (18, 24, "18-24 ans"), (25, 39, "25-39 ans"), (40, 59, "40-59 ans"),
                (60, 200, "60 ans et plus")]
TRANCHES_RAV = [(None, Decimal(0), "Négatif"), (Decimal(0), Decimal(5), "0 à 5 €"), (Decimal(5), Decimal(10), "5 à 10 €"),
                (Decimal(10), Decimal(15), "10 à 15 €"), (Decimal(15), None, "15 € et plus")]


def masque(n):
    """Secret statistique sur un effectif de personnes ou de foyers."""
    return "< 5" if 0 < n < SEUIL else str(n)


def pct(a, b):
    return f"{round(100 * a / b)} %" if b else "—"


def pct_masque(a, b):
    """Part d'un effectif soumis au secret : pas de pourcentage qui laisserait recalculer un « < 5 »."""
    return pct(a, b) if a == 0 or a >= SEUIL else "—"


def _age(naissance, jour):
    return jour.year - naissance.year - ((jour.month, jour.day) < (naissance.month, naissance.day))


@dataclass
class Perimetre:
    mds_ids: list | None          # None = tout le département
    par_agent: bool               # détail par agent (cadre de MDS uniquement)


def _entretiens(p, debut, fin):
    from .models_journal import EntretienSocial
    qs = EntretienSocial.objects.filter(date__gte=debut, date__lte=fin)
    if p.mds_ids is not None:
        qs = qs.filter(beneficiaire__mds_id__in=p.mds_ids)
    return qs


def activite(p, debut, fin):
    from .models_journal import EntretienSocial
    qs = _entretiens(p, debut, fin).select_related('auteur', 'orientation', 'beneficiaire').prefetch_related('types')
    ents = list(qs)
    personnes = {e.beneficiaire_id for e in ents}
    deja_vus = set(EntretienSocial.objects.filter(beneficiaire_id__in=personnes, date__lt=debut)
                   .values_list('beneficiaire_id', flat=True))
    minutes = sum(e.duree_minutes or 0 for e in ents)
    legaux = [e for e in ents if any(t.legal for t in e.types.all())]
    par_mode = Counter(e.get_mode_display() for e in ents)
    par_type, personnes_type = Counter(), defaultdict(set)
    for e in ents:
        for t in e.types.all():
            par_type[str(t)] += 1
            personnes_type[str(t)].add(e.beneficiaire_id)
    sans_type = sum(1 for e in ents if not e.types.all())
    orientations = Counter(e.orientation.organisme for e in ents if e.orientation_id)
    aujourd_hui = date.today()
    retard = [e for e in ents if e.suite_a_donner and not e.suite_faite and e.echeance and e.echeance < aujourd_hui]
    res = {
        "entretiens": len(ents), "heures": round(minutes / 60, 1), "sans_duree": sum(1 for e in ents if not e.duree_minutes),
        "file_active": len(personnes), "nouveaux": len(personnes - deja_vus),
        "legaux": len(legaux), "part_legaux": pct(len(legaux), len(ents)),
        "par_mode": par_mode.most_common(),
        "par_type": [(t, n, masque(len(personnes_type[t]))) for t, n in par_type.most_common()],
        "sans_type": sans_type,
        "orientations": [(o, n) for o, n in orientations.most_common(15)],
        "suites_ouvertes": sum(1 for e in ents if e.suite_a_donner and not e.suite_faite),
        "suites_retard": len(retard),
        "personnes_ids": personnes,
    }
    if p.par_agent:
        agents = defaultdict(lambda: {"entretiens": 0, "minutes": 0, "personnes": set(), "retard": 0})
        for e in ents:
            a = agents[e.auteur.get_full_name() or e.auteur.username if e.auteur else "—"]
            a["entretiens"] += 1
            a["minutes"] += e.duree_minutes or 0
            a["personnes"].add(e.beneficiaire_id)
        for e in retard:
            agents[e.auteur.get_full_name() or e.auteur.username if e.auteur else "—"]["retard"] += 1
        res["par_agent"] = sorted(((nom, v["entretiens"], round(v["minutes"] / 60, 1), masque(len(v["personnes"])), v["retard"])
                                   for nom, v in agents.items()), key=lambda x: -x[1])
    return res


def public(personnes_ids, fin):
    from .models import Beneficiaire
    gens = list(Beneficiaire.tous.filter(pk__in=personnes_ids).only('date_naissance', 'civilite', 'ville', 'marital_status'))
    ages = Counter()
    for b in gens:
        a = _age(b.date_naissance, fin) if b.date_naissance else None
        for lo, hi, lib in TRANCHES_AGE:
            if a is not None and lo <= a <= hi:
                ages[lib] += 1
    civ = Counter(b.get_civilite_display() for b in gens)
    villes = Counter((b.ville or "—").strip().title() for b in gens)
    return {"ages": [(lib, masque(ages[lib])) for _, _, lib in TRANCHES_AGE],
            "civilites": [(c, masque(n)) for c, n in civ.most_common()],
            "communes": [(v, masque(n)) for v, n in villes.most_common(10)]}


def budgets(p, debut, fin):
    """Dernier budget de chaque foyer établi sur la période."""
    from AidFi.services.budget_afase import CHARGES, _d
    from .models_budget import BudgetFoyer
    qs = BudgetFoyer.objects.filter(date_etabli__gte=debut, date_etabli__lte=fin)
    if p.mds_ids is not None:
        qs = qs.filter(beneficiaire__mds_id__in=p.mds_ids)
    derniers = {}
    for bf in qs.order_by('date_etabli', 'pk'):
        derniers[bf.beneficiaire_id] = bf
    bfs = list(derniers.values())
    n = len(bfs)
    tranches = Counter()
    for bf in bfs:
        for lo, hi, lib in TRANCHES_RAV:
            if (lo is None or bf.reste_a_vivre >= lo) and (hi is None or bf.reste_a_vivre < hi):
                tranches[lib] += 1
    libelles = {code: lib for _, lignes in CHARGES for code, lib in lignes}
    impayes, postes = 0, Counter()
    for bf in bfs:
        lignes = (bf.charges or {}).get('lignes', {}) if isinstance(bf.charges, dict) else {}
        en_retard = [code for code, v in lignes.items() if _d(v.get('non_payee'))]
        if en_retard:
            impayes += 1
            postes.update(libelles.get(c, c) for c in en_retard)
    dettes = [bf.total_dettes for bf in bfs if bf.total_dettes]
    return {"foyers": masque(n), "n": n,
            "tranches": [(lib, masque(tranches[lib]), pct_masque(tranches[lib], n)) for _, _, lib in TRANCHES_RAV],
            "rav_median": round(median([bf.reste_a_vivre for bf in bfs]), 2) if n >= SEUIL else None,
            "impayes": masque(impayes), "part_impayes": pct_masque(impayes, n),
            "postes": [(lib, masque(k)) for lib, k in postes.most_common(8)],
            "dettes": masque(len(dettes)), "part_dettes": pct_masque(len(dettes), n),
            "dette_mediane": round(median(dettes), 2) if len(dettes) >= SEUIL else None}


def ateliers(p, debut, fin):
    from planning.models import ParticipantAtelier as P, SeanceAtelier
    qs = SeanceAtelier.objects.filter(date__gte=debut, date__lte=fin).exclude(statut=SeanceAtelier.ANNULEE)
    if p.mds_ids is not None:
        qs = qs.filter(mds_id__in=p.mds_ids)
    seances = list(qs.select_related('atelier').prefetch_related('participants'))
    par_atelier = defaultdict(lambda: Counter())
    tot = Counter()
    for s in seances:
        parts = list(s.participants.all())
        ins = [x for x in parts if x.liste == P.PRINCIPALE]
        c = Counter(seances=1, places=s.places or 0, places_connues=len(ins) if s.places else 0,
                    inscrits=len(ins), attente=sum(1 for x in parts if x.liste == P.ATTENTE),
                    presents=sum(1 for x in ins if x.presence == P.VENU),
                    notes=sum(1 for x in ins if x.presence), externes=sum(1 for x in ins if x.beneficiaire_id is None))
        par_atelier[s.atelier.nom] += c
        tot += c

    def ligne(nom, c):
        return (nom, c["seances"], c["inscrits"], pct(c["places_connues"], c["places"]), pct(c["presents"], c["notes"]),
                c["attente"], pct(c["externes"], c["inscrits"]))
    return {"total": ligne("Ensemble", tot), "par_atelier": [ligne(n, c) for n, c in sorted(par_atelier.items())],
            "seances": tot["seances"]}


def comparaison_mds(debut, fin, mds_qs):
    """Tableau de la direction : une ligne par MDS, sans aucun détail par agent."""
    lignes = []
    for m in mds_qs:
        p = Perimetre([m.pk], False)
        a = activite(p, debut, fin)
        b = budgets(p, debut, fin)
        at = ateliers(p, debut, fin)
        lignes.append((m.nom, a["entretiens"], a["heures"], masque(a["file_active"]), a["part_legaux"],
                       b["rav_median"] if b["rav_median"] is not None else "—", b["part_impayes"], at["seances"],
                       at["total"][4]))
    return lignes


def calculer(p, debut, fin):
    a = activite(p, debut, fin)
    return {"activite": a, "public": public(a.pop("personnes_ids"), fin), "budgets": budgets(p, debut, fin),
            "ateliers": ateliers(p, debut, fin)}


def lignes_csv(r, comparaison=None):
    a, pu, b, at = r["activite"], r["public"], r["budgets"], r["ateliers"]
    yield ["Rubrique", "Libellé", "Valeur", "Complément"]
    for k, lib in [("entretiens", "Entretiens"), ("heures", "Heures d'entretien"), ("file_active", "File active (personnes vues)"),
                   ("nouveaux", "dont personnes vues pour la première fois"), ("legaux", "Entretiens d'accompagnement légal"),
                   ("suites_ouvertes", "Suites à donner ouvertes"), ("suites_retard", "dont en retard")]:
        v = a[k]
        yield ["Activité", lib, masque(v) if k in ("file_active", "nouveaux") else v, ""]
    for m, n in a["par_mode"]:
        yield ["Mode d'entretien", m, n, ""]
    for t, n, pers in a["par_type"]:
        yield ["Type d'accompagnement", t, n, f"personnes : {pers}"]
    for o, n in a["orientations"]:
        yield ["Orientation", o, n, ""]
    for x in a.get("par_agent", []):
        yield ["Agent", x[0], x[1], f"{x[2]} h, {x[3]} personnes, {x[4]} suites en retard"]
    for rub, cle in [("Âge", "ages"), ("Civilité", "civilites"), ("Commune", "communes")]:
        for lib, n in pu[cle]:
            yield ["Public – " + rub, lib, n, ""]
    yield ["Budget", "Foyers (dernier budget de la période)", b["foyers"], ""]
    for lib, n, part in b["tranches"]:
        yield ["Budget – reste à vivre / jour / pers.", lib, n, part]
    yield ["Budget", "Reste à vivre médian", b["rav_median"] if b["rav_median"] is not None else "—", ""]
    yield ["Budget", "Foyers avec impayés", b["impayes"], b["part_impayes"]]
    for lib, n in b["postes"]:
        yield ["Budget – poste impayé", lib, n, ""]
    yield ["Budget", "Foyers avec dettes", b["dettes"], b["part_dettes"]]
    yield ["Budget", "Dette médiane", b["dette_mediane"] if b["dette_mediane"] is not None else "—", ""]
    for x in [at["total"]] + at["par_atelier"]:
        yield ["Atelier", x[0], x[1], f"inscrits {x[2]}, remplissage {x[3]}, présence {x[4]}, attente {x[5]}, extérieurs {x[6]}"]
    for x in comparaison or []:
        yield ["MDS", x[0], x[1], f"{x[2]} h, file active {x[3]}, légal {x[4]}, RAV médian {x[5]}, impayés {x[6]}, "
                                  f"séances {x[7]}, présence {x[8]}"]
