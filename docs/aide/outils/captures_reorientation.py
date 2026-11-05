# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_reorientation.py
"""
Captures des fiches d'aide de la réorientation, sur la base de démonstration fraîchement réinitialisée
(python manage.py init_demo --reinitialiser). Voir _commun.py.
Comptes : as1_mds1 (référente), admin_pi1 et cadre_pi1 (pôle insertion de démonstration).
Usagers fictifs : Aurélie AUBERT (demande à inscrire) ; à la prochaine commission : Sarah AMRANI,
Nadia BENSALEM, Thomas LEGRAND (ajourné une fois).
"""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, page, pdf_en_image, shot, soumettre  # noqa: E402

with sync_playwright() as p:
    nav = p.chromium.launch()
    ts = page(nav, "as1_mds1")

    # ===================== Demander une réorientation (référente)
    ts.goto(f"{B}/insertion/beneficiaire/FAM12-AUR/contrats/")
    shot(ts, "reorientation-demander", "01", "#reorientations-beneficiaire")
    ts.locator("#reorientations-beneficiaire a[href*='/insertion/reorientations/']").first.click(); ts.wait_for_load_state()
    ts.click("a[href$='/modifier/']"); ts.wait_for_load_state()
    ts.fill("textarea[name=motif]", "Accompagnement logement et emploi proposé par l'association (fictif).")
    ts.check("input[name=avis_personne][value=ACCORD]")
    shot(ts, "reorientation-demander", "02", "#rubrique-orientation", top=True)
    ts.click("#enregistrer-inscrire"); ts.wait_for_load_state()
    shot(ts, "reorientation-demander", "03", None, top=True)

    # ===================== La commission (pôle)
    ad = page(nav, "admin_pi1")
    ad.goto(B + "/insertion/")
    shot(ad, "commission-reorientation", "01", "#tuile-reorientation", top=True)
    ad.goto(B + "/insertion/commissions/")
    shot(ad, "commission-reorientation", "02", "#nouvelle-commission", top=True)
    ad.locator("a[href*='/insertion/commissions/']:has-text('dossier')").first.click(); ad.wait_for_load_state()
    commission = re.search(r"/insertion/commissions/(\d+)/", ad.url).group(1)
    shot(ad, "commission-reorientation", "03", "#ordre-du-jour", top=True)
    for nom in ("Agent Pôle insertion", "Cadre Pôle insertion", "Agent Social 1", "Agent Social 1 MDS 2"):
        case = ad.locator(f"#participants label:has-text('{nom}') input")
        if case.count():
            case.first.check()
    shot(ad, "commission-reorientation", "04", "#participants")
    soumettre(ad, "#participants")
    ca = page(nav, "cadre_pi1")
    ca.goto(f"{B}/insertion/commissions/{commission}/")
    sarah = ca.locator("#ordre-du-jour > div:has-text('AMRANI')").first
    sarah.locator("input[value=ACCEPTEE]").check()
    shot(ca, "commission-reorientation", "05", "#ordre-du-jour > div:has-text('AMRANI')")
    sarah.locator("form.decision-dossier button").click(); ca.wait_for_load_state()
    for nom, decision, motif in (("BENSALEM", "ACCEPTEE", ""), ("LEGRAND", "REFUSEE", "Emploi trouvé, suivi par la MDS (fictif)."),
                                 ("AUBERT", "AJOURNEE", "Rencontrer l'association avant de décider (fictif).")):
        bloc = ca.locator(f"#ordre-du-jour > div:has-text('{nom}')").first
        bloc.locator(f"input[value={decision}]").check()
        if motif:
            bloc.locator("textarea").fill(motif)
        if nom == "LEGRAND":
            shot(ca, "commission-reorientation", "06", f"#ordre-du-jour > div:has-text('{nom}')")
        bloc.locator("form.decision-dossier button").click(); ca.wait_for_load_state()
    ca.once("dialog", lambda dlg: dlg.accept())
    shot(ca, "commission-reorientation", "07", "#cloturer")
    ca.click("#cloturer button"); ca.wait_for_load_state()
    pdf_en_image(ca.request.get(f"{B}/insertion/commissions/{commission}/releve.pdf").body(),
                 "commission-reorientation", "08")
    ts.goto(f"{B}/insertion/beneficiaire/FAM5-SAR/contrats/")
    ts.locator("#reorientations-beneficiaire a[href*='/insertion/reorientations/']").first.click(); ts.wait_for_load_state()
    demande = re.search(r"/insertion/reorientations/(\d+)/", ts.url).group(1)
    shot(ts, "commission-reorientation", "09", "#bloc-decision", top=True)
    pdf_en_image(ts.request.get(f"{B}/insertion/reorientations/{demande}/notification.pdf").body(),
                 "commission-reorientation", "10")

    # ===================== Les organismes
    ad.goto(B + "/insertion/organismes/")
    shot(ad, "organismes-reorientation", "01", "#form-organismes", top=True)
    nav.close()
    print("ok")
