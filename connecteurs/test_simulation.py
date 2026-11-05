# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/test_simulation.py
"""Simulation des droits (OpenFisca). Le calcul réel n'est testé que si le moteur est installé (.venv-openfisca).
Données entièrement fictives."""
import os
import unittest
from datetime import date
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from beneficiaire.models import Beneficiaire, LienFamilial
from connecteurs import simulation_droits as sd
from core.models import Profil, User
from mds.models import MDS, UserMDSProfile


class _Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        cls.mds = MDS.objects.create(code_mds="T1", nom="MDS Essai", adresse="1 rue A", code_postal="13000", ville="Exemple")
        cls.ts = User.objects.create_user("ts", password="x", first_name="Inès", matricule="TS")
        cls.ts.profils.add(Profil.objects.get(code="MDS_AGENTS_SOCIAUX"))
        UserMDSProfile.objects.create(user=cls.ts, mds=cls.mds, actif=True, principale=True)
        cls.benef = Beneficiaire.objects.create(code_interne="T-RDV", civilite="MME", nom="ESSAI", prenom="Lucie",
                                                date_naissance=date(1990, 1, 1), adresse="3 rue C",
                                                code_postal="13000", ville="Exemple", mds=cls.mds)

    def setUp(self):
        self.c = Client(HTTP_HOST="localhost")
        self.c.force_login(self.ts)




class _Foyer(_Base):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        commun = dict(adresse="3 rue C", code_postal="13000", ville="Exemple", mds=cls.mds)
        cls.e1 = Beneficiaire.objects.create(code_interne="T-E1", civilite="M.", nom="ESSAI", prenom="Noé",
                                             date_naissance=date(2018, 5, 1), **commun)
        cls.e2 = Beneficiaire.objects.create(code_interne="T-E2", civilite="MME", nom="ESSAI", prenom="Jade",
                                             date_naissance=date(2021, 3, 1), **commun)
        cls.dehors = Beneficiaire.objects.create(code_interne="T-E3", civilite="M.", nom="ESSAI", prenom="Tom",
                                                 date_naissance=date(2004, 3, 1), **commun)
        for e in (cls.e1, cls.e2):
            LienFamilial.objects.create(personne_a=cls.benef, personne_b=e, type_lien="ENFANT")
        LienFamilial.objects.create(personne_a=cls.benef, personne_b=cls.dehors, type_lien="ENFANT", vit_au_foyer=False)

    SAISIE = {"ressources": {"demandeur": {"salaire_net": 0}}, "logement": "locataire_vide", "loyer": 600,
              "zone": "zone_2"}


class SimulationSituationTests(_Foyer):
    def test_foyer_depuis_la_fiche(self):
        conjoint, enfants = sd.foyer(self.benef)
        self.assertIsNone(conjoint)
        self.assertEqual([e.prenom for e in enfants], ["Noé", "Jade"])  # l'enfant hors foyer est écarté

    def test_situation(self):
        s = sd.situation(self.benef, {**self.SAISIE, "ressources": {"demandeur": {"salaire_net": 900}}}, "2026-10")
        self.assertEqual(s["familles"]["famille"], {"parents": ["demandeur"], "enfants": ["enfant1", "enfant2"]})
        self.assertEqual(s["individus"]["demandeur"]["salaire_net"]["2026-10"], 900)
        self.assertEqual(s["individus"]["demandeur"]["salaire_net"]["2025-10"], 900)  # 12 mois et plus
        self.assertEqual(s["menages"]["menage"]["loyer"], {"2026-10": 600})

    def test_moteur_absent(self):
        with mock.patch.dict(os.environ, {"OPENFISCA_PYTHON": "/nexiste/pas"}):
            self.assertFalse(sd.disponible())
            with self.assertRaises(sd.SimulationErreur):
                sd.simuler(self.benef, self.SAISIE)
            r = self.c.get(reverse("beneficiaire:detail_beneficiaire", args=["T-RDV"]))
            self.assertNotContains(r, 'id="lien-simulation-droits"')

    def test_erreur_moteur_lisible(self):
        with mock.patch("connecteurs.simulation_droits.disponible", return_value=True), \
                mock.patch("connecteurs.simulation_droits.subprocess.run",
                           return_value=mock.Mock(stdout='{"erreur": "ValueError : essai"}')):
            with self.assertRaisesMessage(sd.SimulationErreur, "essai"):
                sd.simuler(self.benef, self.SAISIE)

    def test_acces_reserve_mds(self):
        autre = User.objects.create_user("autre", password="x", matricule="AU")
        self.c.force_login(autre)
        self.assertEqual(self.c.get(reverse("connecteurs:simuler_droits", args=["T-RDV"])).status_code, 403)


@unittest.skipUnless(sd.disponible(), "moteur OpenFisca non installé (.venv-openfisca)")
class SimulationReelleTests(_Foyer):
    """Calcul réel par OpenFisca, sur une famille fictive : parent seul, deux enfants, loyer 600 €."""
    def test_sans_ressources_puis_salarie(self):
        sans, _ = sd.simuler(self.benef, self.SAISIE, "2026-10")
        sans = dict(sans)
        self.assertGreater(sans["RSA"], 0)
        self.assertGreater(sans["Aide au logement (APL / ALF / ALS)"], 0)
        self.assertGreater(sans["Allocations familiales"], 0)
        avec, _ = sd.simuler(self.benef, {**self.SAISIE, "ressources": {"demandeur": {"salaire_net": 900}}}, "2026-10")
        avec = dict(avec)
        self.assertLess(avec["RSA"], sans["RSA"])
        self.assertGreater(avec["Prime d'activité"], 0)

    def test_page(self):
        r = self.c.get(reverse("beneficiaire:detail_beneficiaire", args=["T-RDV"]))
        self.assertContains(r, 'id="lien-simulation-droits"')
        r = self.c.post(reverse("connecteurs:simuler_droits", args=["T-RDV"]),
                        {"demandeur_salaire_net": "900", "logement": "locataire_vide", "loyer": "600", "zone": "zone_2"})
        self.assertContains(r, 'id="resultats-simulation"')
        self.assertContains(r, "Prime d&#x27;activité")
        self.assertContains(r, "Noé")
