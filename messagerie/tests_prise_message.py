# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# messagerie/tests_prise_message.py
"""Prise de message usager : tout agent connecté, visibilité de la MDS de l'usager, réponse du destinataire. Données fictives."""
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import NoReverseMatch, reverse

from beneficiaire.models import Beneficiaire
from core.models import Profil, User
from mds.models import MDS, UserMDSProfile
from messagerie.models import Message


class PriseMessageTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.mds = MDS.objects.create(code_mds="TM1", nom="MDS ESSAI", adresse="1 rue A", code_postal="13110",
                                      ville="Port-de-Bouc")
        self.autre = MDS.objects.create(code_mds="TM2", nom="MDS AUTRE", adresse="1 rue B", code_postal="13500",
                                        ville="Martigues")
        self.accueil = self.agent("accueil", self.mds)          # agent d'accueil de la MDS de l'usager
        self.ts = self.agent("ts", self.mds)                    # travailleur social de la MDS de l'usager
        self.ailleurs = self.agent("ailleurs", self.autre)      # agent d'une autre MDS
        self.centrale = self.agent("centrale", None)            # secrétariat de la direction centrale
        self.b = Beneficiaire.objects.create(code_interne="PM-1", civilite="MME", nom="DUPONT", prenom="Jade",
                                             date_naissance=date(1988, 3, 1), adresse="3 rue C", code_postal="13110",
                                             ville="Port-de-Bouc", mds=self.mds)

    def agent(self, login, mds):
        u = User.objects.create_user(login, password="x", matricule=login.upper(), first_name=login.title())
        u.profils.add(Profil.objects.get(code="MDS_AGENTS_SOCIAUX"))
        if mds is not None:
            UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True)
        return u

    def client_de(self, u):
        c = Client(HTTP_HOST="localhost")
        c.force_login(u)
        return c

    def prendre(self, client, **extra):
        data = {"destinataire": self.ts.pk, "objet": "Rappeler Mme Dupont", "contenu": "Message fictif",
                "priorite": "normale", "motif": "autre", "date_rappel": "2026-11-20",
                "mode_contact": "TELEPHONE", "motifs_contact": ["LOGEMENT", "INSERTION"], **extra}
        return client.post(reverse("messagerie:nouveau_message_beneficiaire", args=[self.b.pk]), data)

    # --- prise de message ---

    def test_tout_agent_connecte_peut_prendre_un_message(self):
        for u in (self.centrale, self.ailleurs):
            r = self.prendre(self.client_de(u), objet=f"Message de {u.username}")
            self.assertEqual(r.status_code, 302)
            self.assertTrue(Message.objects.filter(objet=f"Message de {u.username}", beneficiaire=self.b).exists())

    def test_mode_et_motifs_enregistres(self):
        self.prendre(self.client_de(self.accueil), objet="Avec motifs")
        m = Message.objects.get(objet="Avec motifs")
        self.assertEqual(m.mode_contact, "TELEPHONE")
        self.assertEqual(m.motifs_contact, ["LOGEMENT", "INSERTION"])
        self.assertEqual(m.date_rappel, date(2026, 11, 20))

    def test_valeurs_inconnues_ignorees(self):
        self.prendre(self.client_de(self.accueil), objet="Valeurs bidon", mode_contact="PIGEON",
                     motifs_contact=["LOGEMENT", "INVENTE"])
        m = Message.objects.get(objet="Valeurs bidon")
        self.assertEqual(m.mode_contact, "")
        self.assertEqual(m.motifs_contact, ["LOGEMENT"])

    def test_pas_d_usager_sans_annuaire(self):
        """Le sélecteur d'usager et son API ont disparu de la rédaction."""
        with self.assertRaises(NoReverseMatch):
            reverse("messagerie:rechercher_beneficiaire")

    # --- visibilité ---

    def test_message_visible_de_la_mds_de_l_usager(self):
        self.prendre(self.client_de(self.accueil), objet="Visible MDS")
        m = Message.objects.get(objet="Visible MDS")
        url = reverse("messagerie:voir_message", args=[m.id])
        self.assertEqual(self.client_de(self.ts).get(url).status_code, 200)        # destinataire de la MDS
        self.assertEqual(self.client_de(self.accueil).get(url).status_code, 200)   # expéditeur
        r = self.client_de(self.ailleurs).get(url)
        self.assertRedirects(r, reverse("messagerie:boite_reception"), fetch_redirect_response=False)

    def test_message_sans_usager_reste_prive(self):
        m = Message.objects.create(expediteur=self.accueil, destinataire=self.ts, objet="Interne", contenu="x")
        r = self.client_de(self.ailleurs).get(reverse("messagerie:voir_message", args=[m.id]))
        self.assertEqual(r.status_code, 302)

    # --- réponse du destinataire ---

    def test_destinataire_renseigne_la_reponse(self):
        self.prendre(self.client_de(self.accueil), objet="À répondre")
        m = Message.objects.get(objet="À répondre")
        r = self.client_de(self.ts).post(reverse("messagerie:reponse_usager", args=[m.id]), {
            "issue": "ENTRETIEN_TELEPHONIQUE", "reponse_texte": "Rappel effectué, rendez-vous fixé", "reponse_effectuee": "oui"})
        self.assertEqual(r.status_code, 302)
        m.refresh_from_db()
        self.assertEqual(m.issue, "ENTRETIEN_TELEPHONIQUE")
        self.assertIsNotNone(m.reponse_le)
        self.assertEqual(m.reponse_texte, "Rappel effectué, rendez-vous fixé")

    def test_date_de_reponse_figee_au_premier_enregistrement(self):
        self.prendre(self.client_de(self.accueil), objet="Figée")
        m = Message.objects.get(objet="Figée")
        url = reverse("messagerie:reponse_usager", args=[m.id])
        self.client_de(self.ts).post(url, {"reponse_effectuee": "oui"})
        m.refresh_from_db()
        premiere = m.reponse_le
        self.client_de(self.ts).post(url, {"reponse_effectuee": "oui", "reponse_texte": "Complément"})
        m.refresh_from_db()
        self.assertEqual(m.reponse_le, premiere)

    def test_seul_le_destinataire_repond(self):
        self.prendre(self.client_de(self.accueil), objet="Protégé")
        m = Message.objects.get(objet="Protégé")
        self.client_de(self.accueil).post(reverse("messagerie:reponse_usager", args=[m.id]),
                                          {"reponse_effectuee": "oui", "reponse_texte": "Intrus"})
        m.refresh_from_db()
        self.assertIsNone(m.reponse_le)
        self.assertEqual(m.reponse_texte, "")

    def test_reponse_refusee_en_consultation(self):
        self.prendre(self.client_de(self.accueil), objet="Consultation")
        m = Message.objects.get(objet="Consultation")
        r = self.client_de(self.ts).get(reverse("messagerie:voir_message", args=[m.id]))
        self.assertContains(r, "Prise de message")
        self.assertContains(r, 'id="form-reponse-usager"')
        r = self.client_de(self.accueil).get(reverse("messagerie:voir_message", args=[m.id]))
        self.assertNotContains(r, 'id="form-reponse-usager"')
