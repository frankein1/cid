# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_file_active.py
"""
Captures des fiches d'aide « File active RSA » et « Statistiques RSA », sur la base de démonstration fraîchement
réinitialisée (python manage.py init_demo --reinitialiser). Voir _commun.py.
Comptes : as1_mds1 (référente : sa file active), cadre_pi1 (pôle insertion : les MDS du pôle).
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, page, shot  # noqa: E402

with sync_playwright() as p:
    nav = p.chromium.launch()
    ts = page(nav, "as1_mds1")
    ts.goto(B + "/insertion/")
    shot(ts, "file-active", "01", "#tuile-file-active", top=True)
    ts.goto(B + "/insertion/file-active/")
    shot(ts, "file-active", "02", "#tableau-file-active", top=True)
    ts.select_option("select[name=alerte]", "sans_contrat")
    shot(ts, "file-active", "03", "#filtres")
    ts.click("#filtres button"); ts.wait_for_load_state()
    shot(ts, "file-active", "04", "#export-csv", top=True)

    ca = page(nav, "cadre_pi1")
    ca.goto(B + "/insertion/statistiques/")
    shot(ca, "statistiques-rsa", "01", "#indicateurs", top=True)
    shot(ca, "statistiques-rsa", "02", "#par-mds")
    shot(ca, "statistiques-rsa", "03", "#par-action")
    shot(ca, "statistiques-rsa", "04", "#export-csv", top=True)
    nav.close()
    print("ok")
