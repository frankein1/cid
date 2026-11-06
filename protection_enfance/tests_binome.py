# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/tests_binome.py
"""Binôme d'évaluation d'une IP : un professionnel qui suit la famille n'est pas proposé (non recommandé) ; le cadre
peut passer outre en confirmant, la décision est tracée ; l'accès à l'IP ne change pas. Données fictives."""
from datetime import date, timedelta
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase
from django.utils import timezone

from beneficiaire.models import Beneficiaire
from core.models import Profil, User
from mds.models import MDS, UserMDSProfile
from protection_enfance.models import EnfantIP, HistoriqueAction, InformationPreoccupante
from protection_enfance.services import ip_circuit
from protection_enfance.services.ip_circuit import CircuitError
from protection_enfance.services.ip_referents import suivis


class BinomeTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.mds = MDS.objects.create(code_mds="TI1", nom="MDS ESSAI", adresse="1 rue A", code_postal="13110", ville="Port-de-Bouc")
        self.referente = self.agent("clara", "MDS_AGENTS_SOCIAUX")
        self.as2 = self.agent("sarah", "MDS_AGENTS_SOCIAUX")
        self.as3 = self.agent("ines", "MDS_AGENTS_SOCIAUX")
        self.cadre = self.agent("hugo", "MDS_RESPONSABLE")
        self.mere = self.usager("TI-1", "Lucie", date(1990, 1, 1), referent_mds=self.referente)
        self.fils = self.usager("TI-2", "Adam", date(2016, 1, 1))
        self.ip = InformationPreoccupante.objects.create(
            date_reception_crip=timezone.now() - timedelta(days=2), origine="MDS", niveau_urgence="COURANTE",
            famille=self.mere, mds=self.mds, description="Situation fictive.", statut="TRANSMISE_MDS")
        EnfantIP.objects.create(ip=self.ip, beneficiaire=self.fils, nom="ESSAI", prenom="Adam", date_naissance=date(2016, 1, 1))

    def agent(self, login, profil):
        u = User.objects.create_user(login, password="x", matricule=login.upper(), first_name=login.title())
        u.profils.add(Profil.objects.get(code=profil))
        UserMDSProfile.objects.create(user=u, mds=self.mds, actif=True, principale=True)
        return u

    def usager(self, code, prenom, naissance, **extra):
        return Beneficiaire.objects.create(code_interne=code, civilite="MME", nom="ESSAI", prenom=prenom,
                                           date_naissance=naissance, adresse="3 rue C", code_postal="13110",
                                           ville="Port-de-Bouc", mds=self.mds, **extra)

    def test_qui_suit_la_famille(self):
        from beneficiaire.models import EntretienSocial
        EntretienSocial.objects.create(beneficiaire=self.fils, auteur=self.as3, objet="Entretien fictif")
        self.assertEqual(suivis(self.ip), {self.referente.pk: ["référent(e) MDS de la famille"],
                                           self.as3.pk: ["mène les entretiens d'accompagnement"]})

    def test_proposition_sans_la_referente(self):
        p = ip_circuit.proposer_binome(self.ip)
        self.assertNotIn(self.referente, [u for u, _ in p["ts"]])
        self.assertNotIn(self.referente, p["proposition"])
        self.assertEqual([(u, q) for u, q, _ in p["exclus"]], [(self.referente, "TS")])

    def test_le_cadre_doit_confirmer(self):
        with self.assertRaises(CircuitError):
            ip_circuit.designer_binome(self.ip, self.referente, self.as2, self.cadre)
        ip_circuit.designer_binome(self.ip, self.referente, self.as2, self.cadre, forcer=True)
        self.ip.refresh_from_db()
        self.assertEqual(self.ip.binome_derogation, "Décision du cadre")
        self.assertTrue(HistoriqueAction.objects.filter(information=self.ip, action__icontains="malgré le suivi").exists())
        # binôme sans personne qui suit la famille : pas de mention
        ip_circuit.designer_binome(self.ip, self.as2, self.as3, self.cadre)
        self.ip.refresh_from_db()
        self.assertEqual(self.ip.binome_derogation, "")

    def test_ecran_du_cadre(self):
        c = Client(HTTP_HOST="localhost")
        c.force_login(self.cadre)
        url = f"/protection-enfance/ip/{self.ip.numero}/"
        self.assertContains(c.get(url), "suit déjà la famille")
        c.post(url + "binome/", {"referent_1": self.referente.pk, "referent_2": self.as2.pk})
        self.ip.refresh_from_db()
        self.assertIsNone(self.ip.binome_1)                                       # refusé sans confirmation
        c.post(url + "binome/", {"referent_1": self.referente.pk, "referent_2": self.as2.pk, "forcer": "on",
                                 "motif_derogation": "Sous-effectif (fictif)"})
        self.ip.refresh_from_db()
        self.assertEqual((self.ip.binome_1, self.ip.binome_derogation), (self.referente, "Sous-effectif (fictif)"))
        self.assertContains(c.get(url), "Confirmé par le cadre")
