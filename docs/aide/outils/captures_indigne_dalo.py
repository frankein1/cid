# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_indigne_dalo.py
"""
Captures des fiches « Logement indigne » et « Recours DALO », sur la base de démonstration
fraîchement réinitialisée (signalements 9 à 12, recours DALO de FAM2-SOP). Voir _commun.py.
Lecture seule : aucune donnée n'est modifiée.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, page, shot, pdf_en_image  # noqa: E402

FI = "logement-indigne"
FD = "dalo-recours"


def ouvrir_signalement(pg, texte):
    """Ouvre le signalement dont le titre contient « texte » ; renvoie son adresse (…/indigne/<pk>/)."""
    pg.goto(B + "/logement/indigne/")
    href = pg.locator(f"a[href*='/logement/indigne/']:has-text('{texte}')").first.get_attribute("href")
    pg.goto(B + href)
    return href

with sync_playwright() as p:
    nav = p.chromium.launch()
    ts = page(nav, "as1_mds1")
    cadre = page(nav, "chef_mds1")

    # Logement indigne
    ts.goto(B + "/logement/indigne/")
    shot(ts, FI, "01", "button:has-text('Nouveau signalement')", top=True)
    ts.goto(B + "/logement/indigne/nouveau/")
    shot(ts, FI, "02", top=True)
    adresse = ouvrir_signalement(ts, "RECOMP")
    shot(ts, FI, "03", top=True)
    shot(ts, FI, "04", "text=Signatures")
    pdf_en_image(ts.context.request.get(B + adresse + "note-vad.pdf").body(), FI, "05")
    cadre.goto(B + adresse)
    shot(cadre, FI, "06", "text=Suivi")
    shot(cadre, FI, "07", "button:has-text('Clore le signalement')")
    cadre.goto(B + "/logement/indigne/statistiques/")
    shot(cadre, FI, "08", top=True)

    # Recours DALO
    ts.goto(B + "/beneficiaire/FAM2-SOP/")
    shot(ts, FD, "01", "a:has-text('Recours DALO')", element="div.bg-white:has(a:has-text('Recours DALO'))")
    ts.goto(B + "/logement/dalo/FAM2-SOP/")
    shot(ts, FD, "02", top=True)
    shot(ts, FD, "03", "text=Ressources")
    shot(ts, FD, "04", "text=Lieux de travail")
    shot(ts, FD, "05", "text=Motifs")
    pdf_en_image(ts.context.request.get(B + "/logement/dalo/FAM2-SOP/cerfa.pdf").body(), FD, "06")
    nav.close()
