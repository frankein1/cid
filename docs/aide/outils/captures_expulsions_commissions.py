# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_expulsions_commissions.py
"""
Captures de la fiche « Expulsions : commissions » (CAPEX locale, commission préfectorale), sur la base de
démonstration fraîchement réinitialisée. Voir _commun.py.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, page, shot  # noqa: E402


def dossier(pg, numero):
    pg.goto(B + f"/logement/expulsions/?statut=tous&q={numero}")
    pg.goto(B + pg.locator(f"a:has-text('{numero}')").first.get_attribute("href"))


with sync_playwright() as p:
    nav = p.chromium.launch()
    sl = page(nav, "agent_sl1")
    sl.goto(B + "/logement/expulsions/commissions/")
    shot(sl, "expulsions-commissions", "01", "#commissions-liste", top=True)
    sl.goto(B + "/logement/expulsions/commissions/nouvelle/")
    shot(sl, "expulsions-commissions", "02", "#commission-form", top=True)
    sl.goto(B + "/logement/expulsions/commissions/")
    sl.goto(B + sl.locator("#commissions-liste a:has-text('Commission préfectorale')").first.get_attribute("href"))
    shot(sl, "expulsions-commissions", "03", "#commission-odj", top=True)
    ts = page(nav, "as1_mds1")
    dossier(ts, "DEMO-EXP-001")
    shot(ts, "expulsions-commissions", "04", "#expulsion-commissions")
    ts.goto(B + ts.locator("#expulsion-commissions a").first.get_attribute("href"))
    shot(ts, "expulsions-commissions", "05", "#actualisation-form", top=True)
    cadre = page(nav, "chef_mds1")
    cadre.goto(ts.url)
    shot(cadre, "expulsions-commissions", "06", "#passage-visa")
    cadre.goto(B + "/logement/expulsions/commissions/")
    cadre.goto(B + cadre.locator("#commissions-liste a:has-text('CAPEX')").first.get_attribute("href"))
    shot(cadre, "expulsions-commissions", "07", "#commission-odj", top=True)
    dossier(ts, "DEMO-EXP-001")
    shot(ts, "expulsions-commissions", "08", "#expulsion-passerelles")
    nav.close()
