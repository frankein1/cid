# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/simulation_droits.py
"""
Simulation des droits sociaux avec OpenFisca (moteur de calcul libre de l'État, openfisca.org).

La composition du foyer vient de la fiche usager (usager, conjoint et enfants vivant au foyer) ;
l'agent ne saisit que les ressources et le logement. Le calcul se fait SUR LE SERVEUR CID,
dans un processus séparé (connecteurs/openfisca_moteur.py) : aucune donnée ne sort.

Résultat INDICATIF : il ne vaut pas décision de la CAF ou de la MSA.

Installation (une fois, à la construction sur Render) :
  python -m venv .venv-openfisca && .venv-openfisca/bin/pip install -r requirements-openfisca.txt
Variable facultative : OPENFISCA_PYTHON (chemin de l'interpréteur ; défaut : .venv-openfisca/bin/python)
"""
import json
import os
import subprocess
from datetime import date
from pathlib import Path

from django.conf import settings

MOTEUR = Path(__file__).with_name("openfisca_moteur.py")
DELAI = 90  # secondes (le premier calcul charge la législation : quelques secondes)

PRESTATIONS = [  # (variable OpenFisca, libellé affiché)
    ("rsa", "RSA"),
    ("ppa", "Prime d'activité"),
    ("aide_logement", "Aide au logement (APL / ALF / ALS)"),
    ("af", "Allocations familiales"),
    ("cf", "Complément familial"),
    ("asf", "Allocation de soutien familial"),
]

LOGEMENTS = [
    ("locataire_vide", "Locataire (logement vide, parc privé)"),
    ("locataire_hlm", "Locataire HLM"),
    ("locataire_meuble", "Locataire meublé"),
    ("locataire_foyer", "En foyer"),
    ("proprietaire", "Propriétaire"),
    ("loge_gratuitement", "Hébergé gratuitement"),
    ("sans_domicile", "Sans domicile"),
]
ZONES = [("zone_1", "Zone 1 (Paris et proche couronne)"), ("zone_2", "Zone 2 (grandes agglomérations, dont Marseille)"),
         ("zone_3", "Zone 3 (reste du territoire)")]
RESSOURCES = [  # (variable OpenFisca, libellé) : montants mensuels moyens des 12 derniers mois
    ("salaire_net", "Salaire net"),
    ("chomage_net", "Allocation chômage"),
    ("retraite_nette", "Retraite"),
    ("pensions_alimentaires_percues", "Pension alimentaire reçue"),
]


def interpreteur():
    return os.environ.get("OPENFISCA_PYTHON") or str(Path(settings.BASE_DIR) / ".venv-openfisca" / "bin" / "python")


def disponible():
    return os.path.exists(interpreteur())


def foyer(beneficiaire):
    """Usager, conjoint et enfants vivant au foyer, d'après les liens familiaux de la fiche."""
    conjoint, enfants = None, []
    for m in beneficiaire.reseau_familial():
        if not m["vit_au_foyer"]:
            continue
        if m["type_lien"] == "CONJOINT" and conjoint is None:
            conjoint = m["personne"]
        elif m["type_lien"] == "ENFANT":
            enfants.append(m["personne"])
    return conjoint, sorted(enfants, key=lambda e: e.date_naissance or date.max)


def _mois_precedents(mois, n):
    a, m = map(int, mois.split("-"))
    res = []
    for _ in range(n):
        m -= 1
        if m == 0:
            a, m = a - 1, 12
        res.append(f"{a:04d}-{m:02d}")
    return res


def situation(beneficiaire, saisie, mois):
    """
    Situation OpenFisca. `saisie` : {"ressources": {"demandeur"|"conjoint": {variable: montant}},
    "logement": statut, "loyer": montant, "zone": zone}.
    Les ressources sont reportées sur le mois simulé et les 12 précédents (périodes de référence
    du RSA, de la prime d'activité et des aides au logement).
    """
    conjoint, enfants = foyer(beneficiaire)
    periodes = [mois] + _mois_precedents(mois, 24)
    individus, parents = {}, []
    for cle, personne in (("demandeur", beneficiaire), ("conjoint", conjoint)):
        if personne is None:
            continue
        ind = {"date_naissance": {"ETERNITY": personne.date_naissance.isoformat()}}
        for var, montant in (saisie.get("ressources", {}).get(cle) or {}).items():
            ind[var] = {p: float(montant or 0) for p in periodes}
        individus[cle] = ind
        parents.append(cle)
    ids_enfants = []
    for i, e in enumerate(enfants, 1):
        individus[f"enfant{i}"] = {"date_naissance": {"ETERNITY": e.date_naissance.isoformat()}}
        ids_enfants.append(f"enfant{i}")
    loyer = float(saisie.get("loyer") or 0)
    return {
        "individus": individus,
        "familles": {"famille": {"parents": parents, "enfants": ids_enfants}},
        "foyers_fiscaux": {"foyer_fiscal": {"declarants": parents, "personnes_a_charge": ids_enfants}},
        "menages": {"menage": {
            "personne_de_reference": ["demandeur"], **({"conjoint": ["conjoint"]} if conjoint else {}),
            "enfants": ids_enfants,
            "statut_occupation_logement": {mois: saisie.get("logement") or "locataire_vide"},
            "loyer": {mois: loyer}, "zone_apl": {mois: saisie.get("zone") or "zone_2"},
        }},
    }


class SimulationErreur(Exception):
    pass


def simuler(beneficiaire, saisie, mois=None):
    """Lance le calcul dans le processus OpenFisca ; renvoie (lignes [(libellé, montant)], version)."""
    if not disponible():
        raise SimulationErreur("Le moteur OpenFisca n'est pas installé sur ce serveur.")
    mois = mois or date.today().strftime("%Y-%m")
    demande = {"situation": situation(beneficiaire, saisie, mois), "mois": mois,
               "variables": [v for v, _ in PRESTATIONS]}
    try:
        p = subprocess.run([interpreteur(), "-I", str(MOTEUR)], input=json.dumps(demande), capture_output=True,
                           text=True, timeout=DELAI)
        rep = json.loads(p.stdout or "{}")
    except subprocess.TimeoutExpired as e:
        raise SimulationErreur("Le calcul a pris trop de temps : réessayez.") from e
    except (OSError, ValueError) as e:
        raise SimulationErreur("Le moteur OpenFisca n'a pas répondu correctement.") from e
    if "erreur" in rep or "resultats" not in rep:
        raise SimulationErreur(f"Calcul impossible ({rep.get('erreur', 'réponse vide')}).")
    return [(lib, rep["resultats"].get(v, 0.0)) for v, lib in PRESTATIONS], rep.get("version", "?")
