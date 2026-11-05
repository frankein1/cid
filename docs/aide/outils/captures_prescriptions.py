# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_prescriptions.py
"""
Captures des fiches d'aide des prescriptions, sur la base de démonstration fraîchement réinitialisée
(python manage.py init_demo --reinitialiser). Voir _commun.py.
Comptes : as1_mds1 (prescriptrice), admin_pi1 (pôle insertion de démonstration).
Usagers fictifs : Yasmine CHERIF (nouvelle prescription), Céline GARNIER (à valider par le pôle),
Nadia BENSALEM (en attente du porteur), Thomas LEGRAND (en cours).
"""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, page, shot, soumettre  # noqa: E402


def prescription_de(pg, code):
    pg.goto(f"{B}/insertion/beneficiaire/{code}/contrats/")
    return re.search(r"/insertion/prescriptions/(\d+)/", pg.locator("#prescriptions-beneficiaire a[href*='/insertion/prescriptions/']")
                     .first.get_attribute("href")).group(1)


with sync_playwright() as p:
    nav = p.chromium.launch()
    ts = page(nav, "as1_mds1")

    # ===================== Rédiger et adresser une prescription
    ts.goto(f"{B}/insertion/beneficiaire/FAM10-YAS/contrats/")
    shot(ts, "prescription-rediger", "01", "#nouvelle-prescription")
    ts.click("#nouvelle-prescription"); ts.wait_for_load_state()
    shot(ts, "prescription-rediger", "02", "#choix-actions form:has-text('Plateforme mobilité')", top=True)
    ts.locator("#choix-actions form:has-text('Plateforme mobilité') button").click(); ts.wait_for_load_state()
    ts.select_option("select[name=situation_rsa]", "MAJORE")
    ts.check("input[name=qpv]")
    shot(ts, "prescription-rediger", "03", "select[name=situation_rsa]", top=True)
    ts.check("#rubrique-freins input[value=MOBILITE]")
    ts.check("#rubrique-freins input[value=GARDE]")
    ts.fill("textarea[name=diagnostic]", "Pas de permis ; emploi visé à 15 km (fictif).")
    ts.fill("textarea[name=objectifs]", "Obtenir le code puis le permis B (fictif).")
    shot(ts, "prescription-rediger", "04", "#rubrique-freins")
    ts.locator("#rubrique-questions select").first.select_option("Code en cours")
    ts.locator("#rubrique-questions input[type=checkbox][value='Aide au permis']").check()
    shot(ts, "prescription-rediger", "05", "#rubrique-questions")
    ts.check("input[name=consentement]")
    ts.check("#rubrique-signature input[name=pieces_fournies]")
    shot(ts, "prescription-rediger", "06", "#enregistrer-adresser")
    ts.click("#enregistrer-adresser"); ts.wait_for_load_state()
    shot(ts, "prescription-rediger", "07", None, top=True)

    # ===================== Le pôle : validation, retour du porteur
    ad = page(nav, "admin_pi1")
    ad.goto(B + "/insertion/")
    shot(ad, "prescription-pole", "01", "#tuile-prescriptions", top=True)
    celine = prescription_de(ts, "FAM9-CEL")
    ad.goto(B + "/insertion/prescriptions/")
    shot(ad, "prescription-pole", "02", f"a[href='/insertion/prescriptions/{celine}/']", top=True)
    ad.goto(f"{B}/insertion/prescriptions/{celine}/")
    ad.check("input[name=decision][value=valider]")
    shot(ad, "prescription-pole", "03", "#panneau-pole")
    soumettre(ad, "#panneau-pole")
    nadia = prescription_de(ts, "FAM7-NAD")
    ad.goto(f"{B}/insertion/prescriptions/{nadia}/")
    ad.fill("input[name=premier_rdv_le]", "2026-11-03")
    ad.select_option("select[name=premier_rdv_issue]", "PRESENT")
    ad.check("input[name=issue][value=INTEGREE]")
    ad.fill("input[name=date_entree]", "2026-11-04")
    shot(ad, "prescription-pole", "04", "#panneau-retour")
    soumettre(ad, "#panneau-retour")
    shot(ad, "prescription-pole", "05", "#bloc-retour", top=True)

    # ===================== Suivre : en cours, sortie, contrat
    ts.goto(B + "/insertion/prescriptions/?vue=en_cours")
    shot(ts, "prescription-suivi", "01", "#onglets", top=True)
    thomas = prescription_de(ts, "FAM11-THO")
    ts.goto(f"{B}/insertion/prescriptions/{thomas}/")
    ts.check("input[name=issue][value=TERMINEE]")
    ts.fill("input[name=date_sortie]", "2026-11-04")
    ts.fill("input[name=motif_sortie]", "Atelier mené à son terme (fictif)")
    shot(ts, "prescription-suivi", "02", "#panneau-retour")
    soumettre(ts, "#panneau-retour")
    ts.click("a[href*='/insertion/contrats/']:has-text('contrat')"); ts.wait_for_load_state()
    shot(ts, "prescription-suivi", "03", "#actions-contrat")

    # ===================== Les questions propres à une action (référentiel)
    ad.goto(B + "/insertion/actions/?q=DEMO-MOBIL")
    ad.locator("a:has-text('Plateforme mobilité')").first.click(); ad.wait_for_load_state()
    shot(ad, "action-questions", "01", "#questions-action")
    ad.click("a[href$='/questions/']"); ad.wait_for_load_state()
    shot(ad, "action-questions", "02", "#form-questions", top=True)
    nav.close()
    print("ok")
