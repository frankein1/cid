# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# planning/tests_mon_planning.py
"""« Mon planning » : seuls mes rendez-vous à venir, classés par date et heure ; traités masqués. Données fictives."""
from datetime import date, time, timedelta
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase

from beneficiaire.models import Beneficiaire
from core.models import Profil, User
from mds.models import MDS, MDSReception, UserMDSProfile
from planning.models import CreneauRdv


class MonPlanningTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.mds = MDS.objects.create(code_mds="TM1", nom="MDS ESSAI M", adresse="1 rue M", code_postal="13110",
                                      ville="Port-de-Bouc")
        self.salle = MDSReception.objects.create(mds=self.mds, nom="Salle M")
        self.ts = self.utilisateur("tsm")
        self.autre = self.utilisateur("autre")
        self.usager = Beneficiaire.objects.create(code_interne="MP-1", civilite="M", nom="DURAND", prenom="Luc",
                                                  date_naissance=date(1980, 1, 1), adresse="1 rue D",
                                                  code_postal="13110", ville="Port-de-Bouc")
        demain = date.today() + timedelta(days=1)
        self.rdv_tard = self.rdv(demain, time(14), "RESERVE", self.ts)
        self.rdv_tot = self.rdv(demain, time(9), "RESERVE", self.ts)
        self.rdv_traite = self.rdv(demain, time(10), "VENU_RECU", self.ts)
        self.rdv_passe = self.rdv(date.today() - timedelta(days=3), time(9), "RESERVE", self.ts)
        self.rdv_lointain = self.rdv(date.today() + timedelta(days=60), time(9), "RESERVE", self.ts)
        self.rdv_autre = self.rdv(demain, time(11), "RESERVE", self.autre)
        self.client = Client()
        self.client.force_login(self.ts)

    def utilisateur(self, login):
        u = User.objects.create_user(login, password="x", matricule=login.upper())
        u.profils.add(Profil.objects.get(code="MDS_AGENTS_SOCIAUX"))
        UserMDSProfile.objects.create(user=u, mds=self.mds, actif=True, principale=True)
        return u

    def rdv(self, jour, heure, statut, agent):
        return CreneauRdv.objects.create(date=jour, heure_debut=heure, heure_fin=time(heure.hour, 30),
                                         salle=self.salle, mds=self.mds, beneficiaire=self.usager,
                                         agent=agent, statut=statut)

    def test_seuls_mes_rdv_a_venir_non_traites(self):
        r = self.client.get("/planning/mon-planning/")
        self.assertEqual(r.status_code, 200)
        ids = [x['heure'] for _, rdvs in r.context['jours'] for x in rdvs]
        self.assertEqual(ids, ["09:00", "14:00"])

    def test_co_intervention_listee(self):
        co = self.rdv(date.today() + timedelta(days=1), time(16), "RESERVE", self.autre)
        co.co_intervenants.add(self.ts)
        r = self.client.get("/planning/mon-planning/")
        heures = [x['heure'] for _, rdvs in r.context['jours'] for x in rdvs]
        self.assertIn("16:00", heures)
        self.assertEqual(heures.count("16:00"), 1)

    def test_classement_par_date_puis_heure(self):
        r = self.client.get("/planning/mon-planning/")
        self.assertEqual(len(r.context['jours']), 1)
        self.assertEqual(r.context['nb_rdv'], 2)

    def test_afficher_les_traites(self):
        r = self.client.get("/planning/mon-planning/?traites=1")
        heures = [x['heure'] for _, rdvs in r.context['jours'] for x in rdvs]
        self.assertIn("10:00", heures)

    def test_connexion_requise(self):
        r = Client().get("/planning/mon-planning/")
        self.assertEqual(r.status_code, 302)
