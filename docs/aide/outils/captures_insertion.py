# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_insertion.py
"""
Captures des fiches d'aide « RSA – Insertion » (référentiel des actions), sur la base de démonstration
fraîchement réinitialisée (python manage.py init_demo --reinitialiser). Voir _commun.py.
Comptes : as1_mds1 (consultation), chef_mds1 (action locale), admin_pi1 (import CSV). Fichier CSV fictif.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, RAW, page, prep, shot, soumettre  # noqa: E402

CSV_FICTIF = (
    "code;libelle;type;niveau;mds;poles;territoire;porteur;public_vise;duree;comite_suivi;rythme_comite;actif\n"
    "DEMO-EMPLOI;Atelier recherche d'emploi (fictif);emploi;DEPARTEMENTAL;;PI-DEMO;;Association Emploi (fictif);"
    "Bénéficiaires du RSA;3 mois;non;;oui\n"
    "DEMO-MOBIL;Plateforme mobilité (fictif) – mise à jour;mobilite;DEPARTEMENTAL;;PI-DEMO;;Association Mobilité "
    "Exemple (fictif);Bénéficiaires du RSA;6 mois;non;;oui\n"
    "DEMO-ERREUR;Ligne en erreur (fictif);type-inconnu;DEPARTEMENTAL;;;;;;;;;\n"
)

with sync_playwright() as p:
    nav = p.chromium.launch()

    # ===================== Consulter (agent social)
    ts = page(nav, "as1_mds1")
    ts.goto(B + "/insertion/")
    shot(ts, "insertion-actions", "01", "a[href$='/insertion/actions/']", top=True)
    ts.goto(B + "/insertion/actions/?type=mobilite")
    shot(ts, "insertion-actions", "02", "form[method=get]", top=True)
    ts.goto(B + "/insertion/actions/")
    ts.click("a:has-text('Plateforme mobilité')"); ts.wait_for_load_state()
    shot(ts, "insertion-actions", "03", None, top=True)

    # ===================== Créer une action locale (cadre de MDS)
    ca = page(nav, "chef_mds1")
    ca.goto(B + "/insertion/actions/")
    shot(ca, "insertion-action-locale", "01", "a[href$='/insertion/actions/nouvelle/']", top=True)
    ca.goto(B + "/insertion/actions/nouvelle/")
    ca.fill("input[name=code]", "LOC-GARDE")
    ca.fill("input[name=libelle]", "Garde d'enfants ponctuelle (fictif)")
    ca.select_option("select[name=type_action]", label="Garde d'enfants")
    ca.fill("input[name=porteur]", "Centre social du quartier (fictif)")
    ca.fill("input[name=duree]", "Selon les besoins")
    ca.fill("textarea[name=public_vise]", "Parents bénéficiaires du RSA en démarche d'insertion (fictif)")
    shot(ca, "insertion-action-locale", "02", "select[name=mds]", top=True)
    soumettre(ca, "form:has(input[name=libelle])")
    shot(ca, "insertion-action-locale", "03", None, top=True)

    # ===================== Import CSV (agent du pôle insertion)
    pi = page(nav, "admin_pi1")
    pi.goto(B + "/insertion/actions/importer/")
    shot(pi, "insertion-import", "01", "a[href$='/insertion/actions/modele.csv']", top=True)
    fichier = RAW / "actions_fictives.csv"
    fichier.write_text(CSV_FICTIF, encoding="utf-8")
    pi.set_input_files("input[name=fichier]", str(fichier))
    pi.click("button:has-text('Analyser')"); pi.wait_for_load_state()
    shot(pi, "insertion-import", "02", "form:has(input[name=etape]) button", top=True)
    soumettre(pi, "form:has(input[name=etape])")
    shot(pi, "insertion-import", "03", None, top=True)
    pi.goto(B + "/insertion/actions/")
    prep(pi)
    shot(pi, "insertion-import", "04", "a[href^='/insertion/actions/export.csv']", top=True)
    nav.close()
    print("ok")
