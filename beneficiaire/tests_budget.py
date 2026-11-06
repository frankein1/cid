# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/tests_budget.py
"""Budget du foyer : calcul, historique, budget partagé par le foyer, accès, reprise dans l'AFASE. Données fictives."""
from datetime import date
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase

from beneficiaire.budget import budget_en_cours
from beneficiaire.models import Beneficiaire, BudgetFoyer, LienFamilial
from core.models import Profil, User
from mds.models import MDS, UserMDSProfile

POST = {"date_etabli": "2026-11-02", "nb_personnes_foyer": "2", "commentaire": "Essai",
        "r__rsa__demandeur": "800", "r__logement__demandeur": "200", "c__loyer__payee": "500",
        "c__electricite__payee": "40", "c__electricite__non_payee": "120",
        "d__0__creancier": "Fournisseur fictif", "d__0__montant": "120"}


class BudgetTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.mds = MDS.objects.create(code_mds="TB1", nom="MDS ESSAI", adresse="1 rue A", code_postal="13110",
                                      ville="Port-de-Bouc")
        self.autre = MDS.objects.create(code_mds="TB2", nom="MDS AUTRE", adresse="1 rue B", code_postal="13500",
                                        ville="Martigues")
        self.as_ = self.agent("amina", self.mds)
        self.b = self.usager("BU-1", "Clara")
        self.conjoint = self.usager("BU-2", "Yanis")
        LienFamilial.objects.create(personne_a=self.b, personne_b=self.conjoint, type_lien="CONJOINT", vit_au_foyer=True,
                                    date_debut=date(2020, 1, 1))

    def agent(self, login, mds):
        u = User.objects.create_user(login, password="x", matricule=login.upper())
        u.profils.add(Profil.objects.get(code="MDS_AGENTS_SOCIAUX"))
        UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True)
        return u

    def usager(self, code, prenom):
        return Beneficiaire.objects.create(code_interne=code, civilite="MME", nom="ESSAI", prenom=prenom,
                                           date_naissance=date(1990, 1, 1), adresse="3 rue C", code_postal="13110",
                                           ville="Port-de-Bouc", mds=self.mds)

    def client_de(self, u):
        c = Client(HTTP_HOST="localhost")
        c.force_login(u)
        return c

    def test_saisie_calcul_et_historique(self):
        c = self.client_de(self.as_)
        r = c.post("/beneficiaire/BU-1/budget/nouveau/", POST)
        self.assertEqual(r.status_code, 302)
        bf = BudgetFoyer.objects.get()
        # (1000 − 540 payées) / 2 / 30 ; les 120 € non payés ne comptent pas
        self.assertEqual(bf.reste_a_vivre, Decimal("7.67"))
        self.assertEqual(bf.total_dettes, Decimal("120"))
        self.assertContains(c.get("/beneficiaire/BU-1/budget/"), "7,67")
        # un nouveau budget part du précédent, et l'ancien reste dans l'historique
        self.assertContains(c.get("/beneficiaire/BU-1/budget/nouveau/"), 'value="800')
        c.post("/beneficiaire/BU-1/budget/nouveau/", {**POST, "date_etabli": "2026-11-05", "r__rsa__demandeur": "900"})
        self.assertEqual(BudgetFoyer.objects.count(), 2)
        self.assertEqual(budget_en_cours(self.b).date_etabli, date(2026, 11, 5))
        self.assertContains(c.get("/beneficiaire/BU-1/"), "Budget du foyer")

    def test_budget_commun_au_foyer(self):
        BudgetFoyer.objects.create(beneficiaire=self.b, nb_personnes_foyer=2)
        self.assertEqual(budget_en_cours(self.conjoint).beneficiaire, self.b)
        r = self.client_de(self.as_).get("/beneficiaire/BU-2/budget/")
        self.assertContains(r, "même foyer")

    def test_acces(self):
        etranger = self.agent("hugo", self.autre)
        c = self.client_de(etranger)
        self.assertEqual(c.get("/beneficiaire/BU-1/budget/").status_code, 403)
        self.assertEqual(c.post("/beneficiaire/BU-1/budget/nouveau/", POST).status_code, 403)
        self.assertFalse(BudgetFoyer.objects.exists())

    def test_reprise_dans_nouvelle_afase(self):
        self.client_de(self.as_).post("/beneficiaire/BU-1/budget/nouveau/", POST)
        su = User.objects.create_superuser("su", password="x", matricule="SU")
        UserMDSProfile.objects.create(user=su, mds=self.mds, actif=True, principale=True)
        r = self.client_de(su).get(f"/AidFi/beneficiaire/{self.b.pk}/afase/nouvelle/")
        self.assertContains(r, "Repris du budget du foyer du 02/11/2026")
        self.assertContains(r, 'value="800')
