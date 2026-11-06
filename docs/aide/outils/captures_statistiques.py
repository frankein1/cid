# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_statistiques.py
"""
Captures de la fiche « Statistiques de l'accompagnement », sur la base de démonstration fraîchement réinitialisée
(python manage.py init_demo --reinitialiser, jeu « présentation » compris). Voir _commun.py.
chef_mds1 (cadre de la MDS TEST 01) ; un super-administrateur pour la vue de la direction (CAPTURE_ADMIN).
"""
import os
import sys
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, page, shot  # noqa: E402

AN = date.today().year
with sync_playwright() as p:
    nav = p.chromium.launch()
    ca = page(nav, "chef_mds1")
    ca.goto(f"{B}/beneficiaire/statistiques/accompagnement/?annee={AN}")
    shot(ca, "statistiques-accompagnement", "01", "#stats-activite", top=True)
    shot(ca, "statistiques-accompagnement", "02", "#stats-types")
    shot(ca, "statistiques-accompagnement", "03", "#stats-agents")
    shot(ca, "statistiques-accompagnement", "04", "#stats-budgets")
    ad = page(nav, os.environ.get("CAPTURE_ADMIN", "superadmin"))
    ad.goto(f"{B}/beneficiaire/statistiques/accompagnement/?annee={AN}")
    shot(ad, "statistiques-accompagnement", "05", "#stats-comparaison")
    nav.close()
    print("ok")
