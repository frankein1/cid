# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# messagerie/tests_reaffectation.py
"""Demande de réaffectation : décision du cadre de la MDS d'origine, transfert ou refus motivé. Données fictives."""
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from beneficiaire.models import Beneficiaire, TransfertMDS
from core.models import Profil, User
from mds.models import MDS, UserMDSProfile
from messagerie.models import Message


class ReaffectationTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.origine = MDS.objects.create(code_mds="RA1", nom="MDS ORIGINE", adresse="1 rue A", code_postal="13110", ville="Port-de-Bouc")
        self.demandeuse = MDS.objects.create(code_mds="RA2", nom="MDS DEMANDEUSE", adresse="1 rue B", code_postal="13500", ville="Martigues")
        self.ts = self.agent("ts", self.origine)                                  # travailleur social de l'origine
        self.cadre = self.agent("cadre", self.origine, cadre=True)               # cadre de l'origine
        self.demandeur = self.agent("demandeur", self.demandeuse)               # agent de la MDS demandeuse
        self.b = Beneficiaire.objects.create(code_interne="RA-1", civilite="MME", nom="MARTIN", prenom="Lise",
                                             date_naissance=date(1979, 6, 2), adresse="8 rue D", code_postal="13110",
                                             ville="Port-de-Bouc", mds=self.origine)

    def agent(self, login, mds, cadre=False):
        u = User.objects.create_user(login, password="x", matricule=login.upper(), first_name=login.title())
        u.profils.add(Profil.objects.get(code="MDS_AGENTS_SOCIAUX"))
        UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True, peut_gerer_utilisateurs=cadre)
        return u

    def client_de(self, u):
        c = Client(HTTP_HOST="localhost")
        c.force_login(u)
        return c

    def demander(self):
        """La MDS demandeuse prend un message réaffectation sur l'usager, adressé au TS d'origine."""
        self.client_de(self.demandeur).post(
            reverse("messagerie:nouveau_message_beneficiaire", args=[self.b.pk]),
            {"destinataire": self.ts.pk, "objet": "Demande de réaffectation", "contenu": "Lise a déménagé à Martigues.",
             "priorite": "normale", "motif": "autre", "date_rappel": "2026-11-20",
             "mode_contact": "TELEPHONE", "motifs_contact": ["REAFFECTATION"]})
        return Message.objects.get(objet="Demande de réaffectation")

    def decider(self, user, **data):
        m = Message.objects.get(objet="Demande de réaffectation")
        return self.client_de(user).post(reverse("messagerie:decider_reaffectation", args=[m.id]), data)

    def test_mds_demandeuse_memorisee(self):
        m = self.demander()
        self.assertEqual(m.mds_demandeuse, self.demandeuse)
        self.assertEqual(m.decision_reaffectation, "")

    def test_seul_le_cadre_decide(self):
        self.demander()
        self.decider(self.ts, decision="accepter")
        m = Message.objects.get(objet="Demande de réaffectation")
        self.assertEqual(m.decision_reaffectation, "")
        self.b.refresh_from_db()
        self.assertEqual(self.b.mds, self.origine)

    def test_refus_exige_un_motif(self):
        self.demander()
        self.decider(self.cadre, decision="refuser", motif_refus="   ")
        m = Message.objects.get(objet="Demande de réaffectation")
        self.assertEqual(m.decision_reaffectation, "")
        self.assertFalse(Message.objects.filter(reponse_a=m).exists())

    def test_refus_motive_transmis_et_demande_close(self):
        self.demander()
        self.decider(self.cadre, decision="refuser", motif_refus="Suivi en cours sur le logement")
        m = Message.objects.get(objet="Demande de réaffectation")
        self.assertEqual(m.decision_reaffectation, "REFUSEE")
        self.assertEqual(m.motif_refus, "Suivi en cours sur le logement")
        self.assertIsNotNone(m.reponse_le)
        self.assertEqual(m.decision_reaffectation_par, self.cadre)
        reponse = Message.objects.get(reponse_a=m)
        self.assertEqual(reponse.destinataire, self.demandeur)
        self.assertIn("Suivi en cours sur le logement", reponse.contenu)
        self.b.refresh_from_db()
        self.assertEqual(self.b.mds, self.origine)

    def test_acceptation_transfere_et_clot(self):
        self.demander()
        self.decider(self.cadre, decision="accepter")
        m = Message.objects.get(objet="Demande de réaffectation")
        self.assertEqual(m.decision_reaffectation, "ACCEPTEE")
        self.b.refresh_from_db()
        self.assertEqual(self.b.mds, self.demandeuse)
        self.assertTrue(TransfertMDS.objects.filter(beneficiaire=self.b, mds_destination=self.demandeuse).exists())
        reponse = Message.objects.get(reponse_a=m)
        self.assertEqual(reponse.destinataire, self.demandeur)
        self.assertIn("acceptée", reponse.contenu)

    def test_decision_non_rejouable(self):
        self.demander()
        self.decider(self.cadre, decision="refuser", motif_refus="Non")
        self.decider(self.cadre, decision="accepter")
        m = Message.objects.get(objet="Demande de réaffectation")
        self.assertEqual(m.decision_reaffectation, "REFUSEE")
        self.b.refresh_from_db()
        self.assertEqual(self.b.mds, self.origine)

    def test_affichage_selon_le_role(self):
        m = self.demander()
        url = reverse("messagerie:voir_message", args=[m.id])
        self.assertContains(self.client_de(self.cadre).get(url), 'id="form-decision-reaffectation"')
        r = self.client_de(self.ts).get(url)
        self.assertNotContains(r, 'id="form-decision-reaffectation"')
        self.assertContains(r, "En attente de la décision du cadre")
        self.decider(self.cadre, decision="refuser", motif_refus="Non")
        r = self.client_de(self.cadre).get(url)
        self.assertNotContains(r, 'id="form-decision-reaffectation"')
        self.assertContains(r, "Demande refusée")
