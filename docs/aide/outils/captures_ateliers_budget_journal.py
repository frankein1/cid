# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_ateliers_budget_journal.py
"""
Captures des fiches « Ateliers collectifs », « Budget du foyer » et « Journal de l'accompagnement », sur la base de
démonstration fraîchement réinitialisée (python manage.py init_demo --reinitialiser). Voir _commun.py.
Agente : as1_mds1 ; usagère fictive AMRANI Sarah (FAM5-SAR). Aucune modification de la démo.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, page, pdf_en_image, shot  # noqa: E402

with sync_playwright() as p:
    nav = p.chromium.launch()
    pg = page(nav, "as1_mds1")
    # --- Ateliers collectifs
    pg.goto(f"{B}/planning/ateliers/")
    shot(pg, "ateliers-collectifs", "01", "#seances-a-venir", top=True)
    lien = pg.locator("#seances-a-venir tr:has-text('Cuisine') a").first.get_attribute("href")
    pg.goto(B + lien)
    shot(pg, "ateliers-collectifs", "02", "#inscrits")
    pg.goto(B + lien + "?q=ga")
    shot(pg, "ateliers-collectifs", "03", "#inscrire")
    pg.goto(f"{B}/planning/ateliers/")
    lien_passee = pg.locator("tr:has-text('Gérer son budget') a").first.get_attribute("href")
    pdf_en_image(pg.request.get(B + lien_passee + "emargement.pdf").body(), "ateliers-collectifs", "04")
    # --- Budget du foyer
    pg.goto(f"{B}/beneficiaire/FAM5-SAR/")
    shot(pg, "budget-foyer", "01", "#budget-usager")
    pg.goto(f"{B}/beneficiaire/FAM5-SAR/budget/")
    shot(pg, "budget-foyer", "02", "#budget-lecture", top=True)
    shot(pg, "budget-foyer", "03", "#budget-historique")
    pg.goto(f"{B}/beneficiaire/FAM5-SAR/budget/nouveau/")
    shot(pg, "budget-foyer", "04", "#budgetAfase")
    # --- Journal de l'accompagnement
    pg.goto(f"{B}/beneficiaire/FAM5-SAR/")
    shot(pg, "journal-accompagnement", "01", "#journal-usager")
    pg.goto(f"{B}/beneficiaire/FAM5-SAR/journal/?genre=entretien")
    shot(pg, "journal-accompagnement", "02", "#journal-liste", top=True)
    pg.goto(f"{B}/beneficiaire/FAM5-SAR/journal/entretien/")
    shot(pg, "journal-accompagnement", "03", "#form-entretien", top=True)
    pg.goto(f"{B}/beneficiaire/journal/mes-suites/")
    shot(pg, "journal-accompagnement", "04", "#mes-suites", top=True)
    nav.close()
    print("ok")
