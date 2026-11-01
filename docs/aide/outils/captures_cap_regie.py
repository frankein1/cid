# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_cap_regie.py
"""
Captures des fiches d'aide « Chèques service (CAP) » et « Régie d'urgence », sur la base de démonstration
fraîchement réinitialisée (python manage.py init_demo --reinitialiser). Voir _commun.py.
"""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, RAW, page, pdf_en_image, pdf_fictif, prep, shot, soumettre  # noqa: E402


def aides_de(pg, code):
    pg.goto(f"{B}/beneficiaire/{code}/")
    pg.click("a[href*='/AidFi/beneficiaire/'][href$='/dashboard/']")
    pg.wait_for_load_state()


with sync_playwright() as p:
    nav = p.chromium.launch()

    # ===================== CAP : demande (TS, Sarah AMRANI)
    ts = page(nav, "asmith")
    aides_de(ts, "FAM5-SAR")
    shot(ts, "cap-demander", "01", "a[href$='/cap/nouvelle/']")
    ts.click("a[href$='/cap/nouvelle/']"); ts.wait_for_load_state()
    ts.fill("input[name=montant]", "40")
    ts.fill("textarea[name=motivation]", "Plus de denrées en fin de mois, deux enfants en bas âge (fictif).")
    shot(ts, "cap-demander", "02", "input[name=montant]")
    soumettre(ts, "form:has(textarea[name=motivation])")
    cap = re.search(r"/cap/(\d+)/", ts.url).group(1)
    shot(ts, "cap-demander", "03", None, top=True)

    # ===================== CAP : décision, remise, clôture (cadre)
    ca = page(nav, "kchef")
    ca.goto(B + "/AidFi/cadre/dashboard/")
    shot(ca, "cap-decider", "01", f"a[href$='/cap/{cap}/']", top=True)
    ca.goto(f"{B}/AidFi/cap/{cap}/")
    ca.check("input[name=decision][value=ACCORD]") if ca.locator("input[name=decision][value=ACCORD]").count() else None
    ca.fill("input[name=montant_accorde]", "40")
    shot(ca, "cap-decider", "02", "input[name=montant_accorde]")
    soumettre(ca, "form:has(input[name=montant_accorde])")
    ca.click("button:has-text('Utiliser cette proposition')")
    ca.select_option("select[name=remis_a]", label="Agent Social 1")
    shot(ca, "cap-decider", "03", "textarea[name=numeros]")
    soumettre(ca, "form:has(select[name=remis_a])")
    shot(ca, "cap-decider", "04", f"a[href$='/cap/{cap}/feuille.pdf']")
    pdf_en_image(ca.request.get(f"{B}/AidFi/cap/{cap}/feuille.pdf").body(), "cap-decider", "05")
    ca.set_input_files(f"form[action$='/cap/{cap}/cloturer/'] input[type=file]",
                       str(pdf_fictif(RAW / "feuille_signee.pdf", "Feuille de remise signée (fictif)")))
    shot(ca, "cap-decider", "06", f"form[action$='/cap/{cap}/cloturer/'] button")
    soumettre(ca, f"form[action$='/cap/{cap}/cloturer/']")
    shot(ca, "cap-decider", "07", None, top=True)

    # ===================== CAP : coffre (régisseur de la MDS : Agent Admin 1)
    rg = page(nav, "MarioB")
    prep(rg)
    rg.goto(B + "/AidFi/cap/coffres/"); rg.wait_for_load_state()
    shot(rg, "cap-coffre", "01", "a[href$='/reception/']", top=True)
    rg.click("a[href$='/reception/']"); rg.wait_for_load_state()
    rg.fill("input[name=date_validite]", rg.evaluate("new Date(Date.now()+365*864e5).toISOString().slice(0,10)"))
    rg.fill("input[name=reference]", "BORD-FICTIF-2")
    shot(rg, "cap-coffre", "02", "input[name=date_validite]")
    soumettre(rg, "form:has(input[name=date_validite])")
    rg.check("input[name=valeur][value='20']")
    for n in ("FICTIF-20-0001", "FICTIF-20-0002"):
        rg.fill("input[name=numero]", n); rg.press("input[name=numero]", "Enter"); rg.wait_for_load_state()
    shot(rg, "cap-coffre", "03", "input[name=numero]")
    rg.on("dialog", lambda d: d.accept())
    soumettre(rg, "form:has(input[name=action][value=terminer])")
    rg.goto(B + "/AidFi/cap/coffres/"); rg.wait_for_load_state()
    shot(rg, "cap-coffre", "04", "summary:has-text('Signaler')")
    soumettre(rg, "form[action$='/inventaire/']")
    shot(rg, "cap-coffre", "05", None, top=True)

    # ===================== RÉGIE : demande (TS, Yasmine CHERIF, paiement à un tiers)
    aides_de(ts, "FAM10-YAS")
    shot(ts, "regie-demander", "01", "a[href$='/regie/nouvelle/']")
    ts.click("a[href$='/regie/nouvelle/']"); ts.wait_for_load_state()
    ts.fill("input[name=montant]", "60")
    ts.fill("textarea[name=motivation]", "Nuit d'hôtel en urgence après un dégât des eaux (fictif).")
    ts.check("input[name=mode_paiement][value=TIERS]")
    ts.fill("input[name=tiers_nom]", "Hôtel du Port (fictif)")
    ts.fill("input[name=tiers_reference]", "Facture H-DEMO-7")
    ts.set_input_files("input[name=facture]", str(pdf_fictif(RAW / "facture.pdf", "Facture de l'hôtel (fictif)")))
    ts.set_input_files("input[name=rib_tiers]", str(pdf_fictif(RAW / "rib_tiers.pdf", "RIB de l'hôtel (fictif)")))
    shot(ts, "regie-demander", "02", "input[name=mode_paiement][value=TIERS]")
    soumettre(ts, "form:has(textarea[name=motivation])")
    regie = re.search(r"/regie/(\d+)/", ts.url).group(1)
    shot(ts, "regie-demander", "03", None, top=True)

    # ===================== RÉGIE : décision (cadre) puis versement (régie centrale)
    ca.goto(f"{B}/AidFi/regie/{regie}/")
    ca.check("input[name=decision][value=ACCORD]") if ca.locator("input[name=decision][value=ACCORD]").count() else None
    ca.fill("input[name=montant_accorde]", "60")
    shot(ca, "regie-decider", "01", "input[name=montant_accorde]")
    soumettre(ca, "form:has(input[name=montant_accorde])")
    shot(ca, "regie-decider", "02", None, top=True)
    rc = page(nav, "regie1")
    rc.goto(B + "/AidFi/cap/paierie/")
    shot(rc, "regie-decider", "03", f"a[href$='/regie/{regie}/']", top=True)
    rc.goto(f"{B}/AidFi/regie/{regie}/")
    rc.fill("input[name=reference_comptable]", "EJ-DEMO-0200")
    shot(rc, "regie-decider", "04", "input[name=montant]")
    soumettre(rc, "form:has(input[name=reference_comptable])")
    shot(rc, "regie-decider", "05", None, top=True)
    nav.close()
    print("CAP", cap, "régie", regie)
