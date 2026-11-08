# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_fsl.py
"""
Captures de la fiche « FSL : aide à l'accès au logement », sur la base de démonstration fraîchement réinitialisée
(python manage.py init_demo --reinitialiser), sans formulaire officiel déposé (trame CID). Voir _commun.py.
Parcours : nouvelle demande pour FAM2-SOP (préremplie avec son budget), demande FAM5-SAR en attente du cadre, note du cadre.
"""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, page, pdf_en_image, shot  # noqa: E402

with sync_playwright() as p:
    nav = p.chromium.launch()
    ts = page(nav, "as1_mds1")
    ts.goto(B + "/beneficiaire/FAM2-SOP/")
    shot(ts, "fsl-acces", "01", "#fsl-usager form")
    ts.locator("#fsl-usager button[value=ACCES]").click()
    ts.wait_for_load_state()
    shot(ts, "fsl-acces", "02", "#ressources")
    shot(ts, "fsl-acces", "03", "#pieces")
    # demande de FAM5 : pièces manquantes, avis du cadre demandé
    ts.goto(B + "/beneficiaire/FAM5-SAR/")
    ts.click("#fsl-usager li a:has-text('Accès')")
    ts.wait_for_load_state()
    fsl = re.search(r"/fsl/(\d+)/", ts.url).group(1)
    shot(ts, "fsl-acces", "04", "#fsl-pdf", top=True)
    pdf_en_image(ts.request.get(f"{B}/logement/fsl/{fsl}/dossier.pdf").body(), "fsl-acces", "05")
    ca = page(nav, "chef_mds1")
    ca.goto(f"{B}/logement/fsl/{fsl}/")
    ca.fill("textarea[name=note_cadre]", "Le bail est signé lundi ; il sera transmis dès réception (fictif).")
    shot(ca, "fsl-acces", "06", "button[value=cadre_accepte]")
    # énergie : demande instruite par un agent administratif (FAM5-SAR)
    ad = page(nav, "aa1_mds1")
    ad.goto(B + "/beneficiaire/FAM5-SAR/")
    ad.click("#fsl-usager li a:has-text('électricité')")
    ad.wait_for_load_state()
    shot(ad, "fsl-acces", "07", None, top=True)
    # maintien / concordat (FAM3-CLA)
    ts.goto(B + "/beneficiaire/FAM3-CLA/")
    ts.click("#fsl-usager li a:has-text('Maintien')")
    ts.wait_for_load_state()
    ts.goto(ts.url.rstrip("/") + "/modifier/")
    shot(ts, "fsl-acces", "08", "#maintien")
    nav.close()
