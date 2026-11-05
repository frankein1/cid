# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/openfisca_moteur.py
"""
Moteur de simulation, exécuté DANS L'ENVIRONNEMENT PYTHON SÉPARÉ d'OpenFisca (.venv-openfisca),
jamais importé par Django : OpenFisca impose des versions de paquets incompatibles avec CID
(gunicorn < 23 notamment) et occupe ~200 Mo de mémoire, libérés dès la fin du calcul.

Entrée (stdin, JSON) : {"situation": <situation OpenFisca>, "mois": "AAAA-MM", "variables": [...]}
Sortie (stdout, JSON) : {"resultats": {variable: montant}, "version": "<version openfisca-france>"}
                        ou {"erreur": "<message>"}
Aucune donnée n'est écrite ni envoyée ailleurs.
"""
import json
import sys


def main():
    try:
        demande = json.load(sys.stdin)
        from importlib.metadata import version
        from openfisca_core.simulation_builder import SimulationBuilder
        from openfisca_france import FranceTaxBenefitSystem

        tbs = FranceTaxBenefitSystem()
        sim = SimulationBuilder().build_from_entities(tbs, demande["situation"])
        resultats = {}
        for v in demande["variables"]:
            valeurs = sim.calculate(v, demande["mois"])
            resultats[v] = round(float(sum(valeurs)), 2)
        json.dump({"resultats": resultats, "version": version("openfisca-france")}, sys.stdout)
    except Exception as e:  # message lisible renvoyé à CID, sans pile d'appels
        json.dump({"erreur": f"{type(e).__name__} : {e}"[:500]}, sys.stdout)


if __name__ == "__main__":
    main()
