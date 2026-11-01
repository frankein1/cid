# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/_commun.py
"""
Outils communs aux scripts de captures des fiches d'aide (Playwright, hors ligne).
Prérequis : base de démonstration (init_demo), runserver sur 127.0.0.1:8055, et dans TW une compilation
Tailwind locale (out.css) avec node_modules/@fortawesome/fontawesome-free.
"""
import os
from pathlib import Path

from PIL import Image

B = os.environ.get("CID_URL", "http://127.0.0.1:8055")
OUT = Path(__file__).resolve().parent.parent / "img"
RAW = Path(os.environ.get("RAW", "/tmp/captures_aide"))
TW = Path(os.environ.get("TW", "/tmp/tw"))
FA = TW / "node_modules/@fortawesome/fontawesome-free"
MDP = os.environ.get("MDP_DEMO", "testpass123")
STYLE = ".cid-hl{outline:4px solid #dc2626 !important;outline-offset:4px;border-radius:8px}"
HL = """(sel)=>{document.querySelectorAll('.cid-hl').forEach(e=>e.classList.remove('cid-hl'));
 if(!sel) return true; const e=document.querySelector(sel); if(!e) return false; e.classList.add('cid-hl');
 e.scrollIntoView({block:'center'}); return true;}"""
RAW.mkdir(parents=True, exist_ok=True)
_css = None


def _route(r):
    u = r.request.url
    if "webfonts" in u:
        return r.fulfill(path=str(FA / "webfonts" / u.split("/")[-1].split("?")[0]))
    if "127.0.0.1" in u or "localhost" in u:
        return r.continue_()
    return r.abort()


def page(navigateur, user=None, largeur=1280):
    """Nouvel onglet (français, heure de Paris), connecté avec 'user' si donné."""
    ctx = navigateur.new_context(viewport={"width": largeur, "height": 760}, locale="fr-FR", timezone_id="Europe/Paris")
    pg = ctx.new_page()
    pg.route("**/*", _route)
    if user:
        pg.goto(B + "/login/")
        pg.fill("input[name=username]", user)
        pg.fill("input[name=password]", MDP)
        pg.click("form:has(input[name=username]) button[type=submit]")
        pg.wait_for_load_state()
        assert "/login/" not in pg.url, f"connexion impossible pour {user}"
    return pg


def prep(pg):
    global _css
    if _css is None:
        _css = (TW / "out.css").read_text()
    pg.add_style_tag(content=_css)
    pg.add_style_tag(path=str(FA / "css/all.min.css"))
    pg.add_style_tag(content=STYLE)
    pg.wait_for_timeout(250)


def shot(pg, fiche, n, sel=None, top=False, element=None):
    """Capture JPEG dans img/<fiche>/<n>.jpg ; 'sel' est encadré en rouge ; 'element' : capture de cet élément seul."""
    prep(pg)
    pg.evaluate(HL, None)
    if sel:
        cible = pg.locator(sel).first
        try:
            cible.wait_for(state="attached", timeout=8000)
        except Exception:
            raise AssertionError((fiche, n, sel, pg.url))
        cible.evaluate("e => { e.classList.add('cid-hl'); e.scrollIntoView({block: 'center'}); }")
    if top:
        pg.evaluate("window.scrollTo(0,0)")
    pg.wait_for_timeout(150)
    (OUT / fiche).mkdir(parents=True, exist_ok=True)
    brut = RAW / f"{fiche}_{n}.png"
    if element:
        pg.locator(element).first.screenshot(path=str(brut))
    else:
        pg.screenshot(path=str(brut))
    Image.open(brut).convert("RGB").save(OUT / fiche / f"{n}.jpg", quality=82, optimize=True)
    print("ok", fiche, n)


def soumettre(pg, form_sel):
    pg.locator(f"{form_sel} button:not([type=button])").last.click()
    pg.wait_for_load_state()


def pdf_en_image(pdf_bytes, fiche, n, page_no=1):
    """Première page d'un PDF (courrier, formulaire) en vignette."""
    import subprocess
    src = RAW / f"{fiche}_{n}.pdf"
    src.write_bytes(pdf_bytes)
    subprocess.run(["pdftoppm", "-r", "70", "-png", "-f", str(page_no), "-l", str(page_no), str(src), str(RAW / f"{fiche}_{n}")], check=True)
    png = sorted(RAW.glob(f"{fiche}_{n}-*.png"))[-1]
    (OUT / fiche).mkdir(parents=True, exist_ok=True)
    Image.open(png).convert("RGB").save(OUT / fiche / f"{n}.jpg", quality=85, optimize=True)
    print("ok", fiche, n, "(pdf)")


def pdf_fictif(chemin, titre):
    """Petit PDF « document fictif » pour les dépôts de pièces pendant les captures."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(chemin), pagesize=A4)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(72, 760, "DOCUMENT FICTIF")
    c.setFont("Helvetica", 14)
    c.drawString(72, 730, titre)
    c.drawString(72, 705, "Pièce de démonstration – aucune donnée réelle.")
    c.save()
    return chemin
