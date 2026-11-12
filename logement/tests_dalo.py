# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/tests_dalo.py
"""Recours DALO : alerte « hors délais » au 6e mois après le dépôt (configurable), affichée sur la fiche usager.
Données fictives."""
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import Client, SimpleTestCase, TestCase, override_settings

from beneficiaire.models import Beneficiaire
from core.models import Profil, User
from mds.models import MDS, UserMDSProfile

from .models import DemandeLogementSocial


class AlerteDaloTests(SimpleTestCase):
    def dl(self, **kw):
        base = dict(dalo_depose=True, dalo_date=date(2026, 3, 15), dalo_etat='EN_COURS')
        base.update(kw)
        return DemandeLogementSocial(**base)

    def test_six_mois_puis_notification_le_mois_suivant(self):
        dl = self.dl()
        self.assertIsNone(dl.dalo_hors_delais(date(2026, 9, 30)), "6e mois atteint, pas encore notifiable")
        self.assertEqual(dl.dalo_hors_delais(date(2026, 10, 1)), date(2026, 9, 15))

    @override_settings(LOGEMENT_DALO_DELAI_MOIS=3)
    def test_delai_configurable_a_trois_mois(self):
        dl = self.dl()
        self.assertIsNone(dl.dalo_hors_delais(date(2026, 6, 30)))
        self.assertEqual(dl.dalo_hors_delais(date(2026, 7, 1)), date(2026, 6, 15))

    def test_pas_d_alerte_si_pas_depose_ou_decide(self):
        self.assertIsNone(self.dl(dalo_depose=False).dalo_hors_delais(date(2026, 12, 1)))
        self.assertIsNone(self.dl(dalo_date=None).dalo_hors_delais(date(2026, 12, 1)))
        self.assertIsNone(self.dl(dalo_etat='ACCEPTE').dalo_hors_delais(date(2026, 12, 1)))
        self.assertIsNone(self.dl(dalo_etat='REFUSE').dalo_hors_delais(date(2026, 12, 1)))


class AlerteDaloAffichageTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.mds = MDS.objects.create(code_mds="TD1", nom="MDS DALO", adresse="1 rue A", code_postal="13110",
                                      ville="Port-de-Bouc", email="mds@exemple.fr")
        u = User.objects.create_user("amina", password="x", matricule="AMINA", first_name="Amina", last_name="ESSAI")
        u.profils.add(Profil.objects.get(code="MDS_AGENTS_SOCIAUX"))
        UserMDSProfile.objects.create(user=u, mds=self.mds, actif=True, principale=True)
        self.ts = u
        self.b = Beneficiaire.objects.create(code_interne="DA-1", civilite="MME", nom="USAGER", prenom="Clara",
                                             date_naissance="1990-01-01", adresse="3 rue C", code_postal="13110",
                                             ville="Port-de-Bouc", mds=self.mds)
        DemandeLogementSocial.objects.create(beneficiaire=self.b, nud="NUD123", dalo_depose=True,
                                             dalo_date=date(2025, 1, 10), dalo_etat='EN_COURS')

    def test_bandeau_sur_la_fiche_usager(self):
        c = Client(HTTP_HOST="localhost")
        c.force_login(self.ts)
        self.assertContains(c.get(f"/beneficiaire/{self.b.code_interne}/"), "hors délais depuis")
