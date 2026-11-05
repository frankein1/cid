# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_journal.py
"""
Captures de la fiche d'aide « Journal d'activité », sur la base de démonstration fraîchement réinitialisée
(python manage.py init_demo --reinitialiser). Voir _commun.py.
as1_mds1 consulte et modifie la fiche de Sarah AMRANI (fictive), puis chef_mds1 (cadre) regarde le journal du dossier.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, page, shot, soumettre  # noqa: E402

with sync_playwright() as p:
    nav = p.chromium.launch()
    ts = page(nav, "as1_mds1")
    ts.goto(f"{B}/beneficiaire/FAM5-SAR/")
    ts.goto(f"{B}/beneficiaire/FAM5-SAR/modifier/")
    actuel = ts.input_value("input[name=telephone_mobile]")   # la démo garde la valeur d'une capture à l'autre
    ts.fill("input[name=telephone_mobile]", "0611223344" if actuel != "0611223344" else "0655667788")
    soumettre(ts, "form:has(input[name=telephone_mobile])")
    ca = page(nav, "chef_mds1")
    ca.goto(f"{B}/beneficiaire/FAM5-SAR/")
    shot(ca, "journal-activite", "01", "#lien-journal")
    ca.click("#lien-journal"); ca.wait_for_load_state()
    ca.locator("#tableau-journal details").first.evaluate("d => d.open = true")
    shot(ca, "journal-activite", "02", "#tableau-journal", top=True)
    shot(ca, "journal-activite", "03", "#filtres")
    nav.close()
    print("ok")
