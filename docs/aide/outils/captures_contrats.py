# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_contrats.py
"""
Captures des fiches d'aide du contrat RSA, sur la base de démonstration fraîchement réinitialisée
(python manage.py init_demo --reinitialiser). Voir _commun.py.
Comptes : as1_mds1 (référente), admin_pi1, cadre_pi1 et medecin_pi1 (pôle insertion de démonstration).
Usagers fictifs : Yasmine CHERIF (nouveau contrat), Céline GARNIER (contrat santé), Sarah AMRANI (à renouveler).
"""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, page, pdf_en_image, shot, soumettre  # noqa: E402


def contrat_de(pg, code):
    pg.goto(f"{B}/insertion/beneficiaire/{code}/contrats/")
    return re.search(r"/insertion/contrats/(\d+)/", pg.locator("a[href*='/insertion/contrats/']").first
                     .get_attribute("href")).group(1)


with sync_playwright() as p:
    nav = p.chromium.launch()
    ts = page(nav, "as1_mds1")

    # ===================== Rédiger et transmettre un contrat (référente)
    ts.goto(f"{B}/beneficiaire/FAM10-YAS/")
    shot(ts, "contrat-rediger", "01", "#lien-contrats-rsa")
    ts.click("#lien-contrats-rsa"); ts.wait_for_load_state()
    shot(ts, "contrat-rediger", "02", "#nouveau-contrat", top=True)
    ts.click("#nouveau-contrat"); ts.wait_for_load_state()
    ts.select_option("select[name=nature]", "EMPLOI")
    shot(ts, "contrat-rediger", "03", "select[name=type_contrat]", top=True)
    ts.select_option("select[name=niveau_etudes]", "N3")
    ts.fill("input[name=emploi_recherche]", "Agente de restauration collective (fictif)")
    ts.check("input[name=permis_b]")
    ts.fill("textarea[name=parole_situation]", "Je suis seule avec mon fils ; il entre à l'école en septembre (fictif).")
    ts.fill("textarea[name=parole_souhaits]", "Trouver un emploi à temps partiel près de chez moi (fictif).")
    ts.fill("textarea[name=objectifs]", "Accéder à un emploi dans la restauration collective (fictif).")
    ts.fill("textarea[name=etapes]", "1. Atelier mobilité.\n2. Accompagnement vers l'emploi.")
    shot(ts, "contrat-rediger", "04", "textarea[name=objectifs]")
    ts.select_option("select[name='lignes-0-action']", label="Plateforme mobilité (fictif) (DEMO-MOBIL)")
    ts.fill("input[name='lignes-0-date_entree']", "2026-11-10")
    shot(ts, "contrat-rediger", "05", "#rubrique-actions")
    ts.fill("input[name=date_signature]", "2026-11-04")
    ts.check("input[name=engagement_renouvellement]")
    ts.check("input[name=accord_allocataire]")
    shot(ts, "contrat-rediger", "06", "#enregistrer-transmettre")
    ts.click("#enregistrer-transmettre"); ts.wait_for_load_state()
    shot(ts, "contrat-rediger", "07", None, top=True)
    yasmine = re.search(r"/insertion/contrats/(\d+)/", ts.url).group(1)

    # ===================== Le pôle : réception, commission
    ad = page(nav, "admin_pi1")
    ad.goto(B + "/insertion/")
    shot(ad, "contrat-pole", "01", "#tuile-contrats", top=True)
    ad.click("#tuile-contrats"); ad.wait_for_load_state()
    shot(ad, "contrat-pole", "02", f"a[href='/insertion/contrats/{yasmine}/']", top=True)
    ad.goto(f"{B}/insertion/contrats/{yasmine}/")
    shot(ad, "contrat-pole", "03", "#panneau-admin")
    soumettre(ad, "#panneau-admin")
    ca = page(nav, "cadre_pi1")
    ca.goto(f"{B}/insertion/contrats/{yasmine}/")
    ca.check("input[name=decision][value=VALIDE]")
    ca.fill("input[name=date_debut]", "2026-11-10")
    ca.fill("input[name=duree_mois]", "6")
    ca.fill("textarea[name=commentaire]", "Projet cohérent (fictif).")
    shot(ca, "contrat-pole", "04", "#panneau-cadre")
    soumettre(ca, "#panneau-cadre")
    shot(ca, "contrat-pole", "05", "#bloc-decision", top=True)
    # Validé sauf action, sur le contrat de Nadia (reçu au pôle)
    nadia = contrat_de(ts, "FAM7-NAD")
    ca.goto(f"{B}/insertion/contrats/{nadia}/")
    ca.check("input[name=decision][value=VALIDE_SAUF_ACTION]")
    ca.locator("#panneau-cadre input[name^=non_retenue_]").first.check()
    ca.locator("#panneau-cadre input[name^=motif_non_retenue_]").first.fill("Plus de place cette session (fictif)")
    shot(ca, "contrat-pole", "06", "#panneau-cadre .decision-sauf")
    soumettre(ca, "#panneau-cadre")
    pdf_en_image(ca.request.get(f"{B}/insertion/contrats/{nadia}/notification.pdf").body(), "contrat-pole", "07")

    # ===================== Contrat santé : certificat, avis du médecin
    celine = contrat_de(ts, "FAM9-CEL")
    ts.goto(f"{B}/insertion/contrats/{celine}/")
    shot(ts, "contrat-sante", "01", f"a[href$='/insertion/contrats/{celine}/certificat-medical.pdf']", top=True)
    pdf_en_image(ts.request.get(f"{B}/insertion/contrats/{celine}/certificat-medical.pdf").body(), "contrat-sante", "02")
    me = page(nav, "medecin_pi1")
    me.goto(B + "/insertion/contrats/")
    shot(me, "contrat-sante", "03", f"a[href='/insertion/contrats/{celine}/']", top=True)
    me.goto(f"{B}/insertion/contrats/{celine}/")
    me.check("input[name=avis][value=FAVORABLE]")
    me.fill("textarea[name=motivation]", "Parcours de soins adapté à la durée du contrat.")
    shot(me, "contrat-sante", "04", "#panneau-medecin")
    soumettre(me, "#panneau-medecin")
    shot(me, "contrat-sante", "05", "#bloc-sante", top=True)

    # ===================== File active et renouvellement (référente)
    ts.goto(B + "/insertion/contrats/?vue=a_renouveler")
    shot(ts, "contrat-renouveler", "01", "#onglets", top=True)
    sarah = contrat_de(ts, "FAM5-SAR")
    ts.goto(f"{B}/insertion/contrats/{sarah}/")
    shot(ts, "contrat-renouveler", "02", "#panneau-renouveler")
    soumettre(ts, "#panneau-renouveler")
    shot(ts, "contrat-renouveler", "03", "select[name=type_contrat]", top=True)
    aurelie = contrat_de(ts, "FAM12-AUR")
    ts.goto(f"{B}/insertion/contrats/{aurelie}/modifier/")
    shot(ts, "contrat-renouveler", "04", "h1", top=True)
    nav.close()
    print("ok")
