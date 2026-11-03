# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_messagerie_ged_rdv.py
"""
Captures des fiches d'aide « Messagerie », « Documents (GED) » et « Rendez-vous », sur la base de démonstration
fraîchement réinitialisée (python manage.py init_demo --reinitialiser). Voir _commun.py.
Usagère suivie : Sarah AMRANI (FAM5-SAR), référente Agent Social 1 (as1_mds1).
Les documents déposés sont de petits PDF « DOCUMENT FICTIF » ; en local, la GED écrit sur le disque (pas de pCloud).
"""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, RAW, page, pdf_fictif, shot, soumettre  # noqa: E402


def option_contenant(pg, select, texte):
    return pg.evaluate("([s, t]) => [...document.querySelector(s).options].find(o => o.text.includes(t)).value",
                       [select, texte])


with sync_playwright() as p:
    nav = p.chromium.launch()
    ts = page(nav, "as1_mds1")
    ts.goto(f"{B}/beneficiaire/FAM5-SAR/")
    id_sarah = re.search(r"/messagerie/nouveau/(\d+)/",
                         ts.locator("a[href*='/messagerie/nouveau/']").first.get_attribute("href")).group(1)

    # ===================== GED : déposer, consulter
    shot(ts, "ged-deposer", "01", "a[href$='/ged/beneficiaires/FAM5-SAR/upload/']")
    ts.click("a[href$='/ged/beneficiaires/FAM5-SAR/upload/']"); ts.wait_for_load_state()
    ts.set_input_files("input[name=file]", str(pdf_fictif(RAW / "justificatif.pdf", "Justificatif de domicile (fictif)")))
    ts.fill("input[name=titre]", "Justificatif de domicile – octobre")
    ts.select_option("select[name=type_document]", label="Administratif - Justificatif de domicile")
    ts.select_option("select[name=confidentialite]", "RESTREINT")
    shot(ts, "ged-deposer", "02", "select[name=confidentialite]")
    soumettre(ts, "form:has(input[name=titre])")
    shot(ts, "ged-deposer", "03", None, top=True)
    ts.goto(f"{B}/beneficiaire/FAM5-SAR/")
    shot(ts, "ged-deposer", "04", "a[href$='/ged/beneficiaires/FAM5-SAR/documents/']")
    ts.goto(f"{B}/ged/beneficiaires/FAM5-SAR/documents/")
    shot(ts, "ged-deposer", "05", "a[href$='/download/']", top=True)
    ts.locator("a[href^='/ged/documents/']:not([href$='/download/'])").first.click(); ts.wait_for_load_state()
    shot(ts, "ged-deposer", "06", "a[href$='/download/']", top=True)

    # ===================== MESSAGERIE : écrire (depuis la fiche usager), lire, répondre
    ts.goto(f"{B}/beneficiaire/FAM5-SAR/")
    shot(ts, "messagerie", "01", f"a[href$='/messagerie/nouveau/{id_sarah}/']")
    ts.goto(f"{B}/messagerie/nouveau/{id_sarah}/")
    ts.select_option("select[name=destinataire]", option_contenant(ts, "select[name=destinataire]", "(chef_mds1)"))
    ts.fill("input[name=objet]", "Justificatif de domicile reçu")
    ts.select_option("select[name=motif]", "validation_document")
    ts.fill("textarea[name=contenu]", "Bonjour, Mme AMRANI a apporté son justificatif de domicile, joint à ce message (fictif).")
    shot(ts, "messagerie", "02", "select[name=destinataire]", top=True)
    ts.locator("input[name=documents_ged]").first.check()
    shot(ts, "messagerie", "03", "input[name=documents_ged]")
    soumettre(ts, "form:has(textarea[name=contenu])")
    ca = page(nav, "chef_mds1")
    ca.goto(B + "/messagerie/")
    shot(ca, "messagerie", "04", "a[href*='/messagerie/message/']", top=True)
    ca.locator("a[href*='/messagerie/message/']").first.click(); ca.wait_for_load_state()
    shot(ca, "messagerie", "05", "a[href*='/messagerie/repondre/']")
    ca.click("a[href*='/messagerie/repondre/']"); ca.wait_for_load_state()
    ca.fill("textarea[name=contenu]", "Merci, c'est noté (fictif).")
    shot(ca, "messagerie", "06", "textarea[name=contenu]")
    soumettre(ca, "form:has(textarea[name=contenu])")
    ts.goto(B + "/messagerie/")
    shot(ts, "messagerie", "07", "a[href*='?filtre=non_lus']", top=True)

    # ===================== RENDEZ-VOUS : permanence, autre rendez-vous, issue
    ts.goto(f"{B}/beneficiaire/FAM5-SAR/")
    shot(ts, "rdv-prendre", "01", f"a[href$='/planning/creer-rdv/{id_sarah}/']")
    ts.goto(f"{B}/planning/creer-rdv/{id_sarah}/"); ts.wait_for_load_state()
    shot(ts, "rdv-prendre", "02", "a[href*='/planning/reserver/']", top=True)
    ts.locator("a[href*='/planning/reserver/']").first.click(); ts.wait_for_load_state()
    ts.fill("textarea[name=description]", "Point sur le budget (fictif).")
    shot(ts, "rdv-prendre", "03", "select[name=domaine]")
    soumettre(ts, "form:has(textarea[name=description])")
    shot(ts, "rdv-prendre", "04", None, top=True)
    ts.goto(f"{B}/planning/rdv/nouveau/?beneficiaire={id_sarah}")
    ts.select_option("select[name=motif]", "VAD|SOCIAL")
    ts.fill("input[name=lieu_precis]", "Domicile (fictif)")
    shot(ts, "rdv-prendre", "05", "select[name=motif]", top=True)
    ts.goto(B + "/planning/")
    ts.wait_for_selector(".fc-next-button")
    if not ts.locator(".fc-timegrid-event").count():   # le week-end, les rendez-vous de démo sont la semaine suivante
        ts.click(".fc-next-button")
    ts.wait_for_selector(".fc-timegrid-event", timeout=10000)
    shot(ts, "rdv-issue", "01", ".fc-timegrid-event", top=True)
    ts.locator(".fc-timegrid-event:has-text('AMRANI'), .fc-timegrid-event").first.click()
    ts.wait_for_selector(".swal2-popup")
    ts.select_option(".swal2-popup select[name=statut]", "VENU_RECU")
    shot(ts, "rdv-issue", "02", ".swal2-popup select[name=statut]")
    soumettre(ts, ".swal2-popup form[action$='/issue/']")
    ts.wait_for_selector(".fc-timegrid-event")
    shot(ts, "rdv-issue", "03", None, top=True)
    nav.close()
    print("ok")
