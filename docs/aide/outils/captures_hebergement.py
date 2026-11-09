# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_hebergement.py
"""
Captures de la fiche « Hébergement d'urgence », sur la base de démonstration fraîchement réinitialisée.
Voir _commun.py.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, page, shot  # noqa: E402

F = "hebergement-urgence"


def dossier(pg, nom, statut="ouverts"):
    pg.goto(B + f"/logement/hebergement/?statut={statut}")
    pg.goto(B + pg.locator(f"tr:has-text('{nom}') a").first.get_attribute("href"))


with sync_playwright() as p:
    nav = p.chromium.launch()
    ts = page(nav, "as1_mds1")
    ts.goto(B + "/beneficiaire/FAM4-NOL/")
    shot(ts, F, "01", "#hebergement-nouveau")
    ts.goto(B + "/logement/hebergement/")
    shot(ts, F, "02", "#hebergement-liste", top=True)
    dossier(ts, "VIDAL")
    shot(ts, F, "03", "#hebergement-demarches", top=True)
    shot(ts, F, "04", "#hebergement-fiches")
    dossier(ts, "CHERIF")
    ts.goto(B + ts.locator("#hebergement-fiches li a").first.get_attribute("href"))
    shot(ts, F, "05", "#fiche-personnes", top=True)
    cadre = page(nav, "chef_mds1")
    cadre.goto(ts.url)
    shot(cadre, F, "06", "#fiche-visa", top=True)
    dossier(ts, "AMRANI")
    shot(ts, F, "07", "#hebergement-echeance", top=True)
    shot(ts, F, "08", "#hebergement-prise-en-charge", top=True)
    cadre.goto(B + "/logement/hebergement/statistiques/")
    shot(cadre, F, "09", "#hebergement-stats", top=True)
    nav.close()
