# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_expulsions_dsf.py
"""
Captures de la fiche « Expulsions : convocations, DSF, carence », sur la base de démonstration fraîchement
réinitialisée (dossiers DEMO-EXP-001 à 003). Les PDF (courrier, Cerfa) sont photographiés page 1. Voir _commun.py.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, OUT, page, shot  # noqa: E402


def dossier(pg, numero):
    pg.goto(B + f"/logement/expulsions/?statut=tous&q={numero}")
    pg.goto(B + pg.locator(f"a:has-text('{numero}')").first.get_attribute("href"))


def photo_pdf(pg, url, fiche, n, page_pdf=1, haut=0.0, bas=1.0):
    """Page d'un PDF de CID en image (avec la session de l'agent), recadrée en hauteur."""
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "doc.pdf"
        f.write_bytes(pg.request.get(B + url).body())
        subprocess.run(["pdftoppm", "-r", "110", "-f", str(page_pdf), "-l", str(page_pdf), "-png", str(f),
                        str(Path(tmp) / "p")], check=True, capture_output=True)
        img = Image.open(next(Path(tmp).glob("p*.png"))).convert("RGB")
        w, h = img.size
        (OUT / fiche).mkdir(parents=True, exist_ok=True)
        img.crop((0, int(h * haut), w, int(h * bas))).save(OUT / fiche / f"{n}.jpg", quality=82, optimize=True)
    print("ok", fiche, n)


with sync_playwright() as p:
    nav = p.chromium.launch()
    ts = page(nav, "as1_mds1")
    dossier(ts, "DEMO-EXP-001")
    shot(ts, "expulsions-dsf", "01", "#expulsion-convocations")
    photo_pdf(ts, ts.locator("#expulsion-convocations a:has-text('courrier')").first.get_attribute("href"),
              "expulsions-dsf", "02", bas=0.62)
    shot(ts, "expulsions-dsf", "03", "#expulsion-bailleur")
    diag = ts.locator("#expulsion-diagnostics a").first.get_attribute("href")
    ts.goto(B + diag.rstrip("/") + "/modifier/")
    shot(ts, "expulsions-dsf", "04", "#dsf-section-1", top=True)
    ts.locator("#dsf-section-6 summary").click()
    shot(ts, "expulsions-dsf", "05", "#dsf-bilan")
    photo_pdf(ts, diag.rstrip("/") + "/document.pdf", "expulsions-dsf", "06", page_pdf=1, bas=0.55)
    cadre = page(nav, "chef_mds1")
    cadre.goto(B + diag)
    shot(cadre, "expulsions-dsf", "07", "#dsf-visa", top=True)
    dossier(ts, "DEMO-EXP-003")
    ts.goto(B + ts.locator("#expulsion-diagnostics a").first.get_attribute("href"))
    ts.goto(B + ts.locator("#dsf-envoi a").first.get_attribute("href"))
    shot(ts, "expulsions-dsf", "08", "#envoi-form", top=True)
    dossier(ts, "DEMO-EXP-002")
    shot(ts, "expulsions-dsf", "09", "#expulsion-diagnostics")
    nav.close()
