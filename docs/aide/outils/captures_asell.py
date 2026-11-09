# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_asell.py
"""
Captures de la fiche « Orienter vers une mesure ASELL », sur la base de démonstration fraîchement réinitialisée.
Voir _commun.py.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, page, shot  # noqa: E402

with sync_playwright() as p:
    nav = p.chromium.launch()
    ts = page(nav, "as1_mds1")
    ts.goto(B + "/beneficiaire/FAM8-LAU/")
    shot(ts, "asell", "01", "#asell-nouvelle")
    lien_renforce = ts.locator("#fsl-usager a:has-text('ASELL renforcé')").first.get_attribute("href")
    ts.goto(B + "/beneficiaire/FAM5-SAR/")
    ts.goto(B + ts.locator("#fsl-usager a:has-text('ASELL généraliste')").first.get_attribute("href"))
    shot(ts, "asell", "02", "#asell-operateur", top=True)
    shot(ts, "asell", "04", "#asell-reponse", top=True)
    ts.goto(B + lien_renforce)
    shot(ts, "asell", "03", "section:has-text('Logement et procédure')")
    nav.close()
