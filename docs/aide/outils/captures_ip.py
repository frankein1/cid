# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_ip.py
"""
Captures des fiches d'aide « Informations préoccupantes », sur la base de démonstration fraîchement
réinitialisée (python manage.py init_demo --reinitialiser). Voir _commun.py.
Parcours suivi : la CRIP enregistre une IP (famille CHERIF), la transmet ; le cadre désigne le binôme ;
le binôme convoque, note les présences et rédige le rapport ; visas ; avis de l'inspecteur.
Saisine du procureur : sur l'IP PEREZ (en évaluation).
"""
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, page, pdf_en_image, shot, soumettre  # noqa: E402

AUJOURDHUI = datetime.now().strftime("%Y-%m-%d")
DANS_7_JOURS = (datetime.now() + timedelta(days=7)).replace(hour=10, minute=0).strftime("%Y-%m-%dT%H:%M")


def numero_ip(pg):
    return re.search(r"/ip/(D13-\d+)/", pg.url).group(1)


def ouvrir_ip(pg, famille):
    pg.goto(B + "/protection-enfance/ip/")
    pg.click(f"tr:has-text('{famille}') a[href*='/ip/D13-']")
    pg.wait_for_load_state()


with sync_playwright() as p:
    nav = p.chromium.launch()

    # ===================== CRIP : enregistrer et transmettre (famille CHERIF)
    cr = page(nav, "crip_c1")
    cr.goto(B + "/protection-enfance/ip/")
    shot(cr, "ip-saisir", "01", "a[href$='/ip/nouvelle/']", top=True)
    cr.goto(B + "/protection-enfance/ip/nouvelle/")
    cr.fill("input[name=date_reception_crip]", AUJOURDHUI)
    cr.select_option("select[name=origine]", "EDUCATION")
    cr.select_option("select[name=niveau_urgence]", "COURANTE")
    cr.fill("textarea[name=description]", "L'école signale qu'Adam arrive souvent sans repas et très fatigué (fictif).")
    cr.check("input[name=dangers_signales] >> nth=0")
    shot(cr, "ip-saisir", "02", "select[name=origine]")
    cr.fill("input[name=signalant_nom]", "Mme Exemple")
    cr.fill("input[name=signalant_qualite]", "Directrice d'école (fictif)")
    cr.fill("input[name=code_famille]", "FAM10-YAS")
    cr.select_option("select[name=mds]", label="MDSTEST1 - MDS TEST 01 (Port-de-Bouc)")
    shot(cr, "ip-saisir", "03", "input[name=code_famille]")
    soumettre(cr, "form:has(textarea[name=description])")
    ip = numero_ip(cr)
    # Après l'enregistrement, CID ouvre la composition familiale (adultes repris du dossier)
    shot(cr, "ip-saisir", "04", "select[name=adultes-0-qualite]", top=True)
    cr.goto(f"{B}/protection-enfance/ip/{ip}/")
    shot(cr, "ip-saisir", "05", f"form[action$='/ip/{ip}/transmettre/'] button")
    soumettre(cr, f"form[action$='/ip/{ip}/transmettre/']")
    shot(cr, "ip-saisir", "06", None, top=True)

    # ===================== CADRE : réunion IP et binôme
    ca = page(nav, "chef_mds1")
    ca.goto(f"{B}/protection-enfance/ip/{ip}/")
    ca.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
    ca.click("button[data-type=REUNION_IP]")
    ca.fill("form[action$='/demarche/'] input[name=date]", datetime.now().strftime("%Y-%m-%dT09:30"))
    ca.select_option("form[action$='/demarche/'] select[name=resultat]", "REALISE")
    ca.fill("form[action$='/demarche/'] textarea[name=compte_rendu]", "Présentation de l'IP en réunion ; binôme proposé (fictif).")
    shot(ca, "ip-binome", "01", "button[data-type=REUNION_IP]")
    soumettre(ca, "form[action$='/demarche/']")
    b = f"form[action$='/ip/{ip}/binome/']"
    ca.select_option(f"{b} select >> nth=0", label="Agent Social 3")
    ca.select_option(f"{b} select >> nth=1", label="Agent PMI 1")
    shot(ca, "ip-binome", "02", f"{b} button")
    soumettre(ca, f"form[action$='/ip/{ip}/binome/']")
    shot(ca, "ip-binome", "03", "section:has(h2:has-text('Binôme'))")

    # ===================== BINÔME : convoquer, présences, démarches, rapport
    ts = page(nav, "as3_mds1")
    ts.goto(f"{B}/protection-enfance/ip/{ip}/")
    f = f"form[action$='/ip/{ip}/audition/']"
    ts.evaluate("document.getElementById('nouvelle-audition').open = true")
    ts.select_option(f"{f} select[name=aud-type_action]", "AUDITION_PARENTS")
    ts.fill(f"{f} input[name=aud-date]", DANS_7_JOURS)
    for case in ts.locator(f"{f} input[name=aud-adultes]").all():
        case.check()
    shot(ts, "ip-evaluer", "01", f"{f} button")
    soumettre(ts, f)
    shot(ts, "ip-evaluer", "02", "a[href$='/courrier.pdf']")
    lien = ts.locator("a[href$='/courrier.pdf']").first.get_attribute("href")
    pdf_en_image(ts.request.get(B + lien).body(), "ip-evaluer", "03")
    ts.goto(f"{B}/protection-enfance/ip/{ip}/")
    presences = "form[action*='/presences/']"
    ts.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
    ts.locator(f"{presences} select[name^=presence_]").first.select_option("PRESENT")
    shot(ts, "ip-evaluer", "04", f"{presences} select[name^=presence_]")
    soumettre(ts, presences)
    ts.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
    ts.click("button[data-type=VAD]") if ts.locator("button[data-type=VAD]").count() else ts.click("button[data-type=APPEL]")
    shot(ts, "ip-evaluer", "05", "form[action$='/demarche/'] select[name=type_action]")
    ts.goto(f"{B}/protection-enfance/ip/{ip}/rapport/")
    ts.fill("textarea[name=composition_familiale]", "Mère seule avec Adam, 3 ans (fictif).")
    ts.fill("textarea[name=parole_parents]", "Mme CHERIF reconnaît des difficultés passagères (fictif).")
    ts.fill("textarea[name=analyse]", "Difficultés matérielles ponctuelles ; mère adhérente aux propositions (fictif).")
    shot(ts, "ip-evaluer", "06", "textarea[name=analyse]", top=True)
    ts.locator("input[name$='-conclusion'][value=RISQUE]").first.check()
    ts.locator("input[name$='-dangers_constates']").first.check()
    ts.select_option("select[name=preconisation]", "DROIT_COMMUN")
    ts.fill("textarea[name=preconisation_detail]", "Accompagnement social et suivi PMI (fictif).")
    shot(ts, "ip-evaluer", "07", "select[name=preconisation]")
    ts.click("button[name=soumettre]"); ts.wait_for_load_state()
    shot(ts, "ip-evaluer", "08", None, top=True)

    # ===================== SYNTHÈSE : visas du cadre et du binôme
    ca.goto(f"{B}/protection-enfance/ip/{ip}/rapport/")
    ca.fill("input[name=date_synthese]", AUJOURDHUI)
    shot(ca, "ip-synthese", "01", "button[name=role][value=cadre]")
    ca.click("button[name=role][value=cadre]"); ca.wait_for_load_state()
    ts.goto(f"{B}/protection-enfance/ip/{ip}/rapport/")
    shot(ts, "ip-synthese", "02", "button[name=role][value=as]")
    ts.click("button[name=role][value=as]"); ts.wait_for_load_state()
    ts.goto(f"{B}/protection-enfance/ip/{ip}/")
    shot(ts, "ip-synthese", "03", None, top=True)

    # ===================== INSPECTEUR : avis
    pi = page(nav, "ief_p1")
    pi.goto(B + "/protection-enfance/ip/")
    shot(pi, "ip-inspecteur", "01", f"a[href$='/ip/{ip}/']", top=True)
    pi.goto(f"{B}/protection-enfance/ip/{ip}/rapport/")
    shot(pi, "ip-inspecteur", "02", "input[name=avis][value=ACCORD]")
    soumettre(pi, "form[action$='/avis/']")
    pi.goto(f"{B}/protection-enfance/ip/{ip}/")
    shot(pi, "ip-inspecteur", "03", None, top=True)

    # ===================== SAISINE DU PROCUREUR (IP PEREZ, en évaluation ; binôme : Agent Social 1 et PMI)
    ts = page(nav, "as1_mds1")
    ouvrir_ip(ts, "PEREZ")
    perez = numero_ip(ts)
    ts.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
    ts.fill("form[action$='/saisine/'] textarea[name=motif]", "Soins urgents refusés pour Mila malgré plusieurs rappels (fictif).")
    shot(ts, "ip-saisine", "01", "form[action$='/saisine/'] button")
    soumettre(ts, "form[action$='/saisine/']")
    ca.goto(f"{B}/protection-enfance/ip/{perez}/")
    shot(ca, "ip-saisine", "02", "button[name=choix][value=DEMANDER_PIEF]")
    ca.click("button[name=choix][value=DEMANDER_PIEF]"); ca.wait_for_load_state()
    pi.goto(f"{B}/protection-enfance/ip/{perez}/")
    shot(pi, "ip-saisine", "03", "button[name=valide][value=oui]")
    pi.click("button[name=valide][value=oui]"); pi.wait_for_load_state()
    ca.goto(f"{B}/protection-enfance/ip/{perez}/")
    ca.fill("form[action$='/effectuee/'] input[name=reference]", "Envoi par courriel au parquet (fictif)")
    shot(ca, "ip-saisine", "04", "form[action$='/effectuee/'] button")
    nav.close()
    print("IP", ip, "saisine sur", perez)
