# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_expulsions.py
"""
Captures de la fiche « Prévention des expulsions », sur la base de démonstration fraîchement réinitialisée
(dossiers DEMO-EXP-001 à 006). Voir _commun.py.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, page, shot  # noqa: E402


def pk(pg, numero):
    pg.goto(B + f"/logement/expulsions/?statut=tous&q={numero}")
    return pg.locator(f"a:has-text('{numero}')").first.get_attribute("href")


with sync_playwright() as p:
    nav = p.chromium.launch()
    sl = page(nav, "agent_sl1")
    sl.goto(B + "/logement/expulsions/")
    shot(sl, "expulsions", "01", "#expulsion-nouveau", top=True)
    sl.goto(B + "/beneficiaire/annuaire/?nom=garnier&prenom=c%C3%A9line")
    shot(sl, "expulsions", "02", "#annuaire", top=True)
    sl.goto(B + "/logement/expulsions/nouveau/")
    sl.fill("input[name=code_usager]", "FAM9-CEL")
    shot(sl, "expulsions", "03", "#bloc-locataire")
    shot(sl, "expulsions", "04", "#bloc-decision")
    sl.goto(B + pk(sl, "DEMO-EXP-005"))
    shot(sl, "expulsions", "05", "#expulsion-usager")
    cadre = page(nav, "chef_mds1")
    cadre.goto(B + pk(cadre, "DEMO-EXP-002"))
    shot(cadre, "expulsions", "06", "#expulsion-suivi", top=True)
    ts = page(nav, "as1_mds1")
    ts.goto(B + pk(ts, "DEMO-EXP-001"))
    shot(ts, "expulsions", "07", "#expulsion-etapes")
    shot(ts, "expulsions", "08", "#etape-ajout")
    ts.goto(B + pk(ts, "DEMO-EXP-003"))
    shot(ts, "expulsions", "09", "#expulsion-decision", top=True)
    ts.goto(B + "/beneficiaire/FAM8-LAU/")
    shot(ts, "expulsions", "10", "#expulsion-usager-encart")
    secr = page(nav, "secr_sl1")
    secr.goto(B + "/logement/expulsions/statistiques/")
    shot(secr, "expulsions", "11", "#expulsion-stats", top=True)
    nav.close()
