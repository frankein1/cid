# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_rgpd.py
"""
Captures de la fiche d'aide « Archivage RGPD », sur la base de démonstration fraîchement réinitialisée
(python manage.py init_demo --reinitialiser). Voir _commun.py.
chef_mds1 archive FERRAND Hugo (fictif), le consulte puis le désarchive (la démo revient à son état initial) ;
un super-administrateur ouvre l'effacement définitif (sans rien effacer). Compte super-administrateur : CAPTURE_ADMIN.
"""
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, page, shot, soumettre  # noqa: E402

with sync_playwright() as p:
    nav = p.chromium.launch()
    ca = page(nav, "chef_mds1")
    ca.goto(f"{B}/beneficiaire/rgpd/archivage/")
    shot(ca, "archivage-rgpd", "01", "#form-archiver")
    ca.locator("input[name=ids][value]").first.wait_for()
    ligne = ca.locator("#form-archiver tr:has-text('FERRAND') input[name=ids]")
    if ligne.count():
        ligne.check()
        soumettre(ca, "#form-archiver")
    shot(ca, "archivage-rgpd", "02", "#dossiers-archives")
    ca.goto(f"{B}/beneficiaire/rgpd/dossier/RGPD1-HUG/")
    shot(ca, "archivage-rgpd", "03", "#form-desarchiver", top=True)
    ca.select_option("#form-desarchiver select[name=motif]", "RETOUR")
    soumettre(ca, "#form-desarchiver")          # retour à l'état initial de la démo
    ad = page(nav, os.environ.get("CAPTURE_ADMIN", "superadmin"))
    ad.goto(f"{B}/beneficiaire/rgpd/effacement/")
    shot(ad, "archivage-rgpd", "04", "#form-effacement")
    nav.close()
    print("ok")
