# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/tests_annuaire_creation.py
"""Annuaire obligatoire avant création d'un usager, et prise de message depuis l'annuaire. Données fictives."""
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase

from beneficiaire.models import Beneficiaire
from beneficiaire.views import ajouter_beneficiaire  # noqa: F401  (vérifie l'import sans cycle)
from core.models import Profil, User
from mds.models import MDS, UserMDSProfile
from messagerie.models import Message
from messagerie.views import jours_ouvres_apres

ANNUAIRE = "/beneficiaire/annuaire/"
CREATION = "/beneficiaire/ajouter/"


class AnnuaireCreationTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.mds = MDS.objects.create(code_mds="TA1", nom="MDS ESSAI", adresse="1 rue A", code_postal="13110",
                                      ville="Port-de-Bouc")
        self.accueil = self.agent("accueil", self.mds)
        self.ts = self.agent("ts", self.mds)
        self.b = Beneficiaire.objects.create(code_interne="AN-1", civilite="MME", nom="DUPONT", prenom="Jade",
                                             date_naissance=date(1988, 3, 1), adresse="3 rue C", code_postal="13110",
                                             ville="Port-de-Bouc", mds=self.mds)

    def agent(self, login, mds):
        u = User.objects.create_user(login, password="x", matricule=login.upper(), first_name=login.title())
        u.profils.add(Profil.objects.get(code="MDS_AGENTS_SOCIAUX"))
        UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True)
        return u

    def client_de(self, u):
        c = Client(HTTP_HOST="localhost")
        c.force_login(u)
        return c

    def chercher(self, client, **criteres):
        return client.get(ANNUAIRE, criteres)

    # --- création réservée à l'annuaire ---

    def test_creation_refusee_sans_recherche(self):
        r = self.client_de(self.accueil).get(CREATION)
        self.assertRedirects(r, ANNUAIRE, fetch_redirect_response=False)

    def test_recherche_sans_resultat_ouvre_la_creation_prefillee(self):
        c = self.client_de(self.accueil)
        r = self.chercher(c, nom="Martin", prenom="Luc", date_naissance="1990-05-05")
        self.assertContains(r, "Cet usager n'est pas connu de CID")
        self.assertContains(r, "nom=Martin")
        r = c.get(CREATION, {"nom": "Martin", "prenom": "Luc", "date_naissance": "05/05/1990"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'value="Martin"')

    def test_creation_exige_la_confirmation(self):
        c = self.client_de(self.accueil)
        self.chercher(c, nom="Martin", prenom="Luc", date_naissance="1990-05-05")
        r = c.post(CREATION, {"nom": "Martin", "prenom": "Luc", "date_naissance": "05/05/1990",
                              "civilite": "MME", "mds": self.mds.pk, "adresse": "1 rue D", "code_postal": "13110", "ville": "Port-de-Bouc"})
        self.assertEqual(r.status_code, 200)  # pas de création sans case cochée
        self.assertFalse(Beneficiaire.objects.filter(nom="Martin").exists())

    def test_creation_apres_recherche_puis_recherche_effacee(self):
        c = self.client_de(self.accueil)
        self.chercher(c, nom="Martin", prenom="Luc", date_naissance="1990-05-05")
        r = c.post(CREATION, {"nom": "Martin", "prenom": "Luc", "date_naissance": "05/05/1990", "civilite": "MME", "mds": self.mds.pk,
                              "adresse": "1 rue D", "code_postal": "13110", "ville": "Port-de-Bouc",
                              "confirme_creation": "oui"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Beneficiaire.objects.filter(nom="Martin", mds=self.mds).exists())
        # une seule création par recherche
        self.assertEqual(c.get(CREATION).status_code, 302)

    def test_creation_suivie_d_un_message(self):
        c = self.client_de(self.accueil)
        self.chercher(c, nom="Martin", prenom="Luc", date_naissance="1990-05-05")
        r = c.post(CREATION, {"nom": "Martin", "prenom": "Luc", "date_naissance": "05/05/1990", "civilite": "MME", "mds": self.mds.pk,
                              "adresse": "1 rue D", "code_postal": "13110", "ville": "Port-de-Bouc",
                              "confirme_creation": "oui", "suite": "message"})
        benef = Beneficiaire.objects.get(nom="Martin")
        self.assertRedirects(r, f"/messagerie/nouveau/{benef.pk}/?prise=1", fetch_redirect_response=False)

    def test_annuaire_accessible_a_tout_agent_connecte(self):
        self.assertEqual(self.chercher(self.client_de(self.accueil), nom="Dupont", prenom="Jade",
                                       date_naissance="1988-03-01").status_code, 200)

    # --- prise de message depuis l'annuaire ---

    def test_prise_de_message_depuis_annuaire(self):
        c = self.client_de(self.accueil)
        r = self.chercher(c, nom="Dupont", prenom="Jade", date_naissance="1988-03-01")
        self.assertContains(r, f"/messagerie/nouveau/{self.b.pk}/?prise=1")
        r = c.get(f"/messagerie/nouveau/{self.b.pk}/", {"prise": "1"})
        self.assertContains(r, "Prise de message pour")

    def test_message_enregistre_avec_date_de_rappel(self):
        c = self.client_de(self.accueil)
        r = c.post(f"/messagerie/nouveau/{self.b.pk}/", {
            "destinataire": self.ts.pk, "objet": "Rappeler Mme Dupont", "contenu": "Message fictif",
            "priorite": "normale", "motif": "demande_rdv", "date_rappel": "2026-11-20"})
        self.assertEqual(r.status_code, 302)
        msg = Message.objects.get(objet="Rappeler Mme Dupont")
        self.assertEqual(msg.date_rappel, date(2026, 11, 20))
        self.assertEqual(msg.beneficiaire, self.b)

    def test_jours_ouvres(self):
        vendredi = date(2026, 11, 13)
        self.assertEqual(jours_ouvres_apres(vendredi, 3), date(2026, 11, 18))  # vendredi + 3 jours ouvrés = mercredi
        lundi = date(2026, 11, 9)
        self.assertEqual(jours_ouvres_apres(lundi, 3), date(2026, 11, 12))


class RechercheToleranteTests(TestCase):
    """Fautes de frappe sur le nom et le prénom, date à un chiffre près (ou jour et mois inversés), villes écrites
    avec ou sans tirets, espaces ou accents."""

    @classmethod
    def setUpTestData(cls):
        from datetime import date
        from mds.models import MDS
        mds = MDS.objects.create(code_mds="TST01", nom="MDS TEST 01", adresse="1 rue A", code_postal="13110", ville="Port-de-Bouc")
        cls.monop = Beneficiaire.objects.create(
            nom="MONOP", prenom="Jean", date_naissance=date(1977, 3, 2), mds=mds,
            ville="Port-de-Bouc", adresse="12 rue de la Mer", code_postal="13110")
        Beneficiaire.objects.create(
            nom="DUPONT", prenom="Jeanne", date_naissance=date(1990, 1, 1), mds=mds,
            ville="Marseille", adresse="3 avenue du Prado", code_postal="13008")

    def test_faute_de_frappe_sur_le_nom(self):
        from beneficiaire.views_annuaire import rechercher
        resultats, _ = rechercher(nom="moop", prenom="jean")
        self.assertIn(self.monop, resultats)
        self.assertTrue(resultats[0].proche)

    def test_date_a_un_chiffre_pres(self):
        from datetime import date
        from beneficiaire.views_annuaire import rechercher
        resultats, _ = rechercher(nom="monop", date_naissance=date(1971, 3, 2))
        self.assertIn(self.monop, resultats)

    def test_jour_et_mois_inverses(self):
        from datetime import date
        from beneficiaire.views_annuaire import rechercher
        resultats, _ = rechercher(nom="monop", date_naissance=date(1977, 2, 3))
        self.assertIn(self.monop, resultats)

    def test_ville_sans_tirets_ni_espaces(self):
        from beneficiaire.views_annuaire import rechercher
        for ville in ("port de bouc", "portdebouc", "Port-de-Bouc", "Port-De-Bouc"):
            resultats, _ = rechercher(nom="monop", adresse=ville)
            self.assertIn(self.monop, resultats, ville)

    def test_faute_ne_fait_pas_tout_remonter(self):
        from beneficiaire.views_annuaire import rechercher
        resultats, _ = rechercher(nom="zzzz", prenom="Yann")
        self.assertEqual(resultats, [])
