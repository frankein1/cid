# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_ru.py
"""
Captures des fiches « Relation usager » (SAS, travailleur social, cadre), sur la base de démonstration
(init_demo --reinitialiser : demandes « [démo] » à chaque étape du circuit). Voir _commun.py.
Lecture seule : aucune donnée n'est modifiée.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, page, shot, pdf_en_image  # noqa: E402


def ouvrir(pg, nom):
    """Ouvre la demande de l'usager « nom » depuis la liste ; renvoie son adresse (…/ru/<pk>/)."""
    pg.goto(B + "/ru/")
    href = pg.locator(f"tr:has-text('{nom}') a[href*='/ru/']").first.get_attribute("href")
    pg.goto(B + href)
    return href


with sync_playwright() as p:
    nav = p.chromium.launch()
    sas = page(nav, "ru_sas")
    ts = page(nav, "as1_mds1")
    cadre = page(nav, "chef_mds1")

    # Saisir et transmettre
    sas.goto(B + "/ru/")
    shot(sas, "ru-saisir", "01", "a:has-text('Enregistrer une demande')", top=True)
    sas.goto(B + "/ru/creer/")
    shot(sas, "ru-saisir", "02", top=True)
    ouvrir(sas, "BOYER")
    shot(sas, "ru-saisir", "03", "text=1. Envoyer du SAS")

    # Évaluer
    adresse = ouvrir(ts, "DURAND")
    shot(ts, "ru-evaluer", "01", top=True)
    shot(ts, "ru-evaluer", "02", "text=2. Évaluation MDS")
    shot(ts, "ru-evaluer", "03", "text=Courriers PDF de rendez-vous")
    pdf_en_image(ts.context.request.get(B + adresse + "courrier-rdv/1.pdf").body(), "ru-evaluer", "04")

    # Valider
    ouvrir(cadre, "ROUX")
    shot(cadre, "ru-valider", "01", "text=3. Validation et signature")
    ouvrir(cadre, "LEFEBVRE")
    shot(cadre, "ru-valider", "02", "text=Visa électronique")
    shot(cadre, "ru-valider", "03", "text=Historique du dossier")

    # Finaliser (SAS)
    ouvrir(sas, "LEFEBVRE")
    shot(sas, "ru-finaliser", "01", "text=4. Fiche retour SAS")
    adresse = ouvrir(sas, "GIRAUD")
    pdf_en_image(sas.context.request.get(B + adresse + "fiche-retour.pdf").body(), "ru-finaliser", "02")
    shot(sas, "ru-finaliser", "03", "text=Transmission enregistrée")

    # Délais et relances
    sas.goto(B + "/ru/?retard=1")
    shot(sas, "ru-relances", "01", "tr:has-text('DURAND')", top=True)
    ouvrir(sas, "DURAND")
    shot(sas, "ru-relances", "02", "text=Demande hors délai")
    shot(sas, "ru-relances", "03", "text=Relances")
    nav.close()
