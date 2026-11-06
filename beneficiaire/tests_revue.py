# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/tests_revue.py
"""Relecture des PR #73 à #78 : chaque correction a son test. Données fictives."""
from datetime import date, time
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase

from beneficiaire.archivage import derniere_activite
from beneficiaire.budget import budget_en_cours
from beneficiaire.models import Beneficiaire, BudgetFoyer, EntretienSocial, LienFamilial
from core.models import Profil, User
from mds.models import MDS, UserMDSProfile
from planning.models import Atelier, ParticipantAtelier as P, SeanceAtelier


class RevueTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.m1 = MDS.objects.create(code_mds="TR1", nom="MDS UN", adresse="1 rue A", code_postal="13110", ville="Port-de-Bouc")
        self.m2 = MDS.objects.create(code_mds="TR2", nom="MDS DEUX", adresse="1 rue B", code_postal="13500", ville="Martigues")
        self.auteur = self.agent("lucie", self.m1)
        self.b = self.usager("RV-1", self.m1)

    def agent(self, login, mds):
        u = User.objects.create_user(login, password="x", matricule=login.upper())
        u.profils.add(Profil.objects.get(code="MDS_AGENTS_SOCIAUX"))
        UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True)
        return u

    def usager(self, code, mds):
        return Beneficiaire.objects.create(code_interne=code, civilite="MME", nom="ESSAI", prenom="Rose",
                                           date_naissance=date(1985, 1, 1), adresse="3 rue C", code_postal="13110",
                                           ville="Port-de-Bouc", mds=mds)

    def client_de(self, u):
        c = Client(HTTP_HOST="localhost")
        c.force_login(u)
        return c

    def test_pas_de_redirection_externe(self):
        e = EntretienSocial.objects.create(beneficiaire=self.b, auteur=self.auteur, objet="x", suite_a_donner="y")
        r = self.client_de(self.auteur).post(f"/beneficiaire/journal/entretien/{e.pk}/suite-faite/",
                                             {"retour": "https://site-malveillant.example/"})
        self.assertEqual(r["Location"], "/beneficiaire/journal/mes-suites/")

    def test_administrateur_ne_lit_pas_la_synthese_privee(self):
        e = EntretienSocial.objects.create(beneficiaire=self.b, auteur=self.auteur, objet="Objet", synthese_privee="NOTE-AUTEUR")
        su = User.objects.create_superuser("su", password="x", matricule="SU")
        c = self.client_de(su)
        url = f"/beneficiaire/RV-1/journal/entretien/{e.pk}/"
        self.assertNotContains(c.get(url), "NOTE-AUTEUR")
        c.post(url, {"date": "2026-11-02", "mode": "RDV", "objet": "Objet corrigé"})
        e.refresh_from_db()
        self.assertEqual((e.objet, e.synthese_privee), ("Objet corrigé", "NOTE-AUTEUR"))   # la note est conservée

    def test_budget_partage_seulement_dans_la_meme_mds(self):
        autre = self.usager("RV-2", self.m2)
        LienFamilial.objects.create(personne_a=self.b, personne_b=autre, type_lien="CONJOINT", vit_au_foyer=True, date_debut=date(2020, 1, 1))
        BudgetFoyer.objects.create(beneficiaire=self.b, nb_personnes_foyer=2)
        self.assertIsNone(budget_en_cours(autre))
        meme = self.usager("RV-3", self.m1)
        LienFamilial.objects.create(personne_a=meme, personne_b=self.b, type_lien="ENFANT", vit_au_foyer=True, date_debut=date(2020, 1, 1))
        self.assertEqual(budget_en_cours(meme).beneficiaire, self.b)

    def test_csv_sans_formule_et_atelier_compte_comme_activite(self):
        s = SeanceAtelier.objects.create(atelier=Atelier.objects.create(nom="Cuisine", mds=self.m1), mds=self.m1,
                                         date=date(2026, 11, 20), heure_debut=time(14), heure_fin=time(16))
        P.objects.create(seance=s, nom="=HYPERLINK(\"x\")")
        P.objects.create(seance=s, beneficiaire=self.b)
        r = self.client_de(self.auteur).get(f"/planning/ateliers/seance/{s.pk}/emargement.csv")
        self.assertIn(b"'=HYPERLINK", r.content)
        Beneficiaire.objects.filter(pk=self.b.pk).update(date_creation="2020-01-01T00:00Z", date_modification="2020-01-01T00:00Z")
        self.assertEqual(derniere_activite([self.b.pk])[self.b.pk], date.today())
