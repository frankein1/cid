# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_copp.py
"""
Captures de la fiche « Demande de logement et commission des publics prioritaires », sur la base de démonstration
fraîchement réinitialisée (FAM2-SOP : demande de logement et saisine en préparation). Voir _commun.py.
"""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, page, shot  # noqa: E402

with sync_playwright() as p:
    nav = p.chromium.launch()
    ts = page(nav, "as1_mds1")
    ts.goto(B + "/beneficiaire/FAM2-SOP/")
    shot(ts, "copp", "01", "#copp-nouvelle button")
    ts.goto(B + "/logement/demande/FAM2-SOP/")
    shot(ts, "copp", "02", "input[name=nud]", top=True)
    ts.goto(B + "/beneficiaire/FAM2-SOP/")
    ts.click("#fsl-usager li a:has-text('COPP')")
    ts.wait_for_load_state()
    pk = re.search(r"/copp/(\d+)/", ts.url).group(1)
    ts.goto(f"{B}/logement/copp/{pk}/modifier/")
    shot(ts, "copp", "03", "#motifs")
    shot(ts, "copp", "04", "#pieces")
    ts.goto(f"{B}/logement/copp/{pk}/")
    shot(ts, "copp", "05", "#copp-actions")
    ts.goto(f"{B}/logement/envoi/copp/{pk}/")
    shot(ts, "copp", "06", "input[name=objet]", top=True)
    ca = page(nav, "chef_mds1")
    ca.goto(B + "/logement/papier-economise/")
    shot(ca, "copp", "07", "#papier", top=True)
    nav.close()
