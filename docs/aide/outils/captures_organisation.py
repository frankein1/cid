# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures_organisation.py
"""
Captures de la fiche « Organiser la MDS : fonctions, équipe IP, MDS de proximité », sur la base de démonstration
(MDS TEST 01 de territoire, MDS TEST 02 de proximité rattachée). Voir _commun.py.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _commun import B, page, shot  # noqa: E402

import os  # noqa: E402
import django  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cid.settings")
django.setup()
from core.models import User  # noqa: E402
from mds.models import MDS  # noqa: E402

M1 = MDS.objects.get(code_mds="MDSTEST1").pk
M2 = MDS.objects.get(code_mds="MDSTEST2").pk
CADRE1 = User.objects.get(username="cadre_mds1").pk
AS2 = User.objects.get(username="as2_mds1").pk

with sync_playwright() as p:
    nav = p.chromium.launch()
    c2 = page(nav, "chef_mds2")
    c2.goto(f"{B}/mds/{M2}/modifier/")
    shot(c2, "mds-organisation", "01", "select[name=mds_territoire]")
    c1 = page(nav, "chef_mds1")
    c1.goto(f"{B}/mds/{M1}/utilisateurs/{CADRE1}/modifier/")
    shot(c1, "mds-organisation", "02", "input[name=role_specifique]")
    c1.goto(f"{B}/mds/{M1}/utilisateurs/{AS2}/modifier/")
    shot(c1, "mds-organisation", "03", "input[name=equipe_ip]")
    c2.goto(f"{B}/mds/{M2}/utilisateurs/")
    shot(c2, "mds-organisation", "04", "tr:has-text('CODIR MDSTEST1')")
    nav.close()
