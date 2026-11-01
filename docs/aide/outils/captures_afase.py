# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_afase.py
"""
Captures des fiches d'aide AFASE, sur la base de démonstration fraîchement réinitialisée
(python manage.py init_demo --reinitialiser). Voir _commun.py pour les prérequis.
"""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, RAW, page, pdf_en_image, pdf_fictif, prep, shot, soumettre  # noqa: E402


def id_afase(pg):
    return re.search(r"/afase/(\d+)/", pg.url).group(1)


def ouvrir_afase(pg, code_famille):
    """Depuis la fiche de l'usager → tableau de ses aides → dernière AFASE."""
    pg.goto(f"{B}/beneficiaire/{code_famille}/")
    pg.click("a[href*='/AidFi/beneficiaire/'][href$='/dashboard/']")
    pg.wait_for_load_state()
    lien = pg.evaluate("""Array.from(document.querySelectorAll('table a')).map(a => a.getAttribute('href'))
                          .find(h => /\\/AidFi\\/afase\\/\\d+\\/$/.test(h))""")
    assert lien, code_famille
    pg.goto(B + lien)


def choisir_code(pg, groupe, code):
    """Les codes d'accord et de refus partagent les mêmes valeurs : on choisit dans le bon groupe."""
    pg.evaluate("""([g, c]) => { const o = document.querySelector(`select[name=code_decision] optgroup[label="${g}"] option[value="${c}"]`);
                                 o.selected = true; o.parentElement.parentElement.dispatchEvent(new Event('change')); }""", [groupe, code])


def deposer_piece(pg, afase, type_piece, libelle_type_doc, titre):
    pg.goto(f"{B}/AidFi/afase/{afase}/ajouter-document/?type={type_piece}")
    pg.select_option("select[name=type_piece]", type_piece)
    valeur = pg.evaluate("""(t) => Array.from(document.querySelectorAll('select[name=type_document] option'))
                              .find(o => o.textContent.includes(t))?.value""", libelle_type_doc)
    assert valeur, libelle_type_doc
    pg.select_option("select[name=type_document]", valeur)
    pg.fill("input[name=titre]", titre)
    pg.set_input_files("input[name=file]", str(pdf_fictif(RAW / f"{type_piece}.pdf", titre)))


with sync_playwright() as p:
    nav = p.chromium.launch()

    # ===================== TRAVAILLEUR SOCIAL : demander une AFASE (famille AUBERT)
    pg = page(nav, "asmith")
    pg.goto(B + "/beneficiaire/FAM12-AUR/")
    shot(pg, "afase-demander", "01", "a[href*='/AidFi/beneficiaire/'][href$='/dashboard/']")
    pg.click("a[href*='/AidFi/beneficiaire/'][href$='/dashboard/']"); pg.wait_for_load_state()
    shot(pg, "afase-demander", "02", "a[href$='/afase/nouvelle/']")
    pg.click("a[href$='/afase/nouvelle/']"); pg.wait_for_load_state()
    pg.select_option("select[name=demandeur]", pg.evaluate(
        "Array.from(document.querySelectorAll('select[name=demandeur] option')).find(o => o.textContent.includes('Aurélie')).value"))
    pg.select_option("select[name=lien_demandeur]", "MERE")
    pg.fill("input[name=date_signature_demandeur]", pg.evaluate("new Date().toISOString().slice(0,10)"))
    pg.select_option("select[name=qualite_ts]", "AS")
    pg.select_option("select[name=avis_ts]", "FAVORABLE")
    pg.fill("input[name=situation_pro_demandeur]", "Agent d'entretien à temps partiel (fictif)")
    pg.fill("input[name=situation_pro_conjoint]", "37 ans, en recherche d'emploi (fictif)")
    shot(pg, "afase-demander", "03", "select[name=demandeur]", top=True)
    shot(pg, "afase-demander", "04", "input[name=e__0__concerne]")
    pg.click("button[data-next='2']")
    pg.fill("input[name=montant_sollicite]", "150"); pg.fill("input[name=duree_demande]", "1")
    pg.select_option("select[name=motif_envisage]", "1")
    pg.wait_for_timeout(300)
    shot(pg, "afase-demander", "05", "select[name=motif_envisage]")
    pg.click("button[data-next='3']")
    pg.select_option("select[name=code_instruction]", "4")
    pg.fill("textarea[name=situation_sociale]", "Couple avec deux enfants ; baisse de revenus après une fin de contrat (fictif).")
    pg.fill("textarea[name=justification_demande]", "Aide ponctuelle pour l'alimentation des enfants en attendant l'ouverture des droits (fictif).")
    pg.fill("textarea[name=plan_action]", "Rendez-vous budget dans un mois ; dossier CAF à mettre à jour (fictif).")
    pg.select_option("select[name=adhesion_famille]", "FORTE")
    shot(pg, "afase-demander", "06", "select[name=code_instruction]")
    pg.click("button[data-next='4']")
    for champ, v in [("r__salaire__demandeur", "820"), ("r__chomage__conjoint", "540"), ("r__familiales__demandeur", "290"),
                     ("c__loyer__payee", "720"), ("c__electricite__payee", "110"), ("c__telephone__payee", "40"),
                     ("c__assurances__payee", "35"), ("c__electricite__non_payee", "180")]:
        pg.fill(f"input[name={champ}]", v)
    pg.wait_for_timeout(300)
    shot(pg, "afase-demander", "07", "input[name=nb_personnes_foyer]")
    pg.click("button[type=submit].btn-success"); pg.wait_for_load_state()
    if "/afase/" not in pg.url or "nouvelle" in pg.url:
        print("ÉCHEC", pg.url, pg.evaluate("Array.from(document.querySelectorAll('.errorlist, .text-red-600, .bg-red-50, [role=alert]')).map(e=>e.innerText).join(' | ')"))
    afase = id_afase(pg)
    shot(pg, "afase-demander", "08", f"a[href$='/afase/{afase}/ajouter-document/']", top=True)
    deposer_piece(pg, afase, "RIB", "identité bancaire", "RIB de Mme AUBERT (fictif)")
    shot(pg, "afase-demander", "09", "select[name=type_piece]")
    soumettre(pg, "form:has(input[name=file])")
    for t, lib, titre in [("IDENTITE", "Carte d'identité", "Pièces d'identité (fictif)"), ("LIVRET_FAMILLE", "Autre document", "Livret de famille (fictif)"),
                          ("DOMICILE", "Justificatif de domicile", "Justificatif de domicile (fictif)")]:
        deposer_piece(pg, afase, t, lib, titre); soumettre(pg, "form:has(input[name=file])")
    shot(pg, "afase-demander", "10", f"a[href$='/afase/{afase}/evaluation/']")
    pg.goto(f"{B}/AidFi/afase/{afase}/evaluation/")
    shot(pg, "afase-demander", "11", "form:has(textarea[name=justification_demande]) button")
    soumettre(pg, "form:has(textarea[name=justification_demande])")
    shot(pg, "afase-demander", "12", None, top=True)

    # ===================== TRAVAILLEUR SOCIAL : répondre à un ajournement (famille ROUX)
    ouvrir_afase(pg, "FAM6-KEV")
    ajo = id_afase(pg)
    shot(pg, "afase-ajournement", "01", "div.bg-amber-50:has-text('Demande ajournée')", top=False)
    shot(pg, "afase-ajournement", "02", f"a[href$='/afase/{ajo}/evaluation/']")
    deposer_piece(pg, ajo, "RESSOURCES", "Avis d'imposition", "Avis d'imposition (fictif)")
    soumettre(pg, "form:has(input[name=file])")
    pg.goto(f"{B}/AidFi/afase/{ajo}/evaluation/")
    soumettre(pg, "form:has(textarea[name=justification_demande])")
    shot(pg, "afase-ajournement", "03", None, top=True)

    # ===================== CADRE : décider (CLASSIC Claire, puis l'AFASE AUBERT déposée ci-dessus)
    pc = page(nav, "kchef")
    prep(pc); pc.click("#cadre-button"); pc.wait_for_timeout(200)
    shot(pc, "afase-decider", "01", "#cadre-menu a[href$='/cadre/dashboard/']")
    pc.goto(B + "/AidFi/cadre/dashboard/")
    shot(pc, "afase-decider", "02", f"a[href$='/afase/{afase}/decision/']")
    pc.goto(f"{B}/AidFi/afase/{afase}/decision/")
    shot(pc, "afase-decider", "03", "h2:has-text('Aide à la décision')")
    shot(pc, "afase-decider", "04", "input[name=type_decision][value=ACCORD]")
    pc.check("input[name=type_decision][value=REFUS]"); pc.wait_for_timeout(200)
    choisir_code(pc, "Refus", "3")
    pc.fill("input[name=precision_notification]", "le Fonds de solidarité logement")
    shot(pc, "afase-decider", "05", "input[name=precision_notification]")
    pc.check("input[name=type_decision][value=AJO]"); pc.wait_for_timeout(200)
    shot(pc, "afase-decider", "06", "#bouton-decision")
    pc.check("input[name=type_decision][value=ACCORD]"); pc.wait_for_timeout(200)
    choisir_code(pc, "Accord", "1")
    pc.fill("input[name=precision_notification]", "")
    pc.fill("textarea[name=motivation]", "Difficulté ponctuelle avérée ; plan d'action engagé (fictif).")
    shot(pc, "afase-decider", "07", "#bouton-decision")
    pc.click("#bouton-decision"); pc.wait_for_load_state()
    shot(pc, "afase-decider", "08", None, top=True)

    # ===================== CADRE : notifier et transmettre à l'UAGAF (même dossier)
    shot(pc, "afase-transmettre", "01", f"a[href$='/afase/{afase}/notification/']")
    r = pc.request.get(f"{B}/AidFi/afase/{afase}/notification/")
    pdf_en_image(r.body(), "afase-transmettre", "02")
    deposer_piece(pc, afase, "FACTURE_DEVIS", "Autre document", "Devis du magasin d'alimentation (fictif)")
    soumettre(pc, "form:has(input[name=file])")
    pc.check("input[name=identites]")
    shot(pc, "afase-transmettre", "03", "input[name=identites]")
    pc.click(f"form[action$='/afase/{afase}/transmettre/'] button[type=submit]"); pc.wait_for_load_state()
    shot(pc, "afase-transmettre", "04", None, top=True)

    # ===================== UAGAF : contrôler et enregistrer le paiement
    pu = page(nav, "uagaf1")
    pu.goto(B + "/AidFi/afase/controle/")
    shot(pu, "afase-uagaf", "01", f"tr:has-text('n° {afase}')")
    pu.goto(f"{B}/AidFi/afase/{afase}/")
    shot(pu, "afase-uagaf", "02", f"form[action$='/controle/paiement-demande/'] input[name=date]")
    shot(pu, "afase-uagaf", "03", f"form[action$='/controle/renvoi/'] textarea[name=motif], form[action$='/controle/renvoi/'] input[name=motif]")
    pu.fill(f"form[action$='/controle/paiement-demande/'] input[name=reference]", "EJ-DEMO-0100")
    pu.click(f"form[action$='/controle/paiement-demande/'] button[type=submit]"); pu.wait_for_load_state()
    pu.goto(f"{B}/AidFi/afase/{afase}/")
    shot(pu, "afase-uagaf", "04", f"form[action$='/controle/paiement-effectue/'] button[type=submit]")
    pu.click(f"form[action$='/controle/paiement-effectue/'] button[type=submit]"); pu.wait_for_load_state()
    pu.goto(f"{B}/AidFi/afase/{afase}/")
    shot(pu, "afase-uagaf", "05", "h3:has-text('Circuit du paiement')")

    # ===================== CADRE : recours (LALANNE refusé → enregistrer ; GARNIER en cours → issue)
    ouvrir_afase(pc, "API-FRA")
    shot(pc, "afase-recours", "01", "form:has(input[name=date_recours]) button")
    ouvrir_afase(pc, "FAM9-CEL")
    pc.select_option("select[name=issue]", "ACCORD")
    pc.fill("input[name=date_issue]", pc.evaluate("new Date().toISOString().slice(0,10)"))
    shot(pc, "afase-recours", "02", "select[name=issue]")
    soumettre(pc, "form:has(select[name=issue])")
    shot(pc, "afase-recours", "03", None, top=True)
    pc.goto(B + "/AidFi/statistiques/")
    shot(pc, "afase-recours", "04", "h2:has-text('Recours contre les refus')")

    # ===================== INSPECTEUR : AFASE des familles avec une mesure ASE
    pi = page(nav, "pief1")
    pi.goto(B + "/AidFi/afase/inspecteur/")
    shot(pi, "afase-inspecteur", "01", "a:has-text('Laura PEREZ')")
    pi.click("a:has-text('Laura PEREZ')"); pi.wait_for_load_state()
    shot(pi, "afase-inspecteur", "02", "a:has-text('Décider')", top=False)
    nav.close()
    print("AFASE créée pour les captures :", afase)
