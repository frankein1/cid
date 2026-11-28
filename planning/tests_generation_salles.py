# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# planning/tests_generation_salles.py
"""Génération des permanences : salle libre sur la plage, alerte aux cadres si aucune. Données fictives."""
from datetime import date, time

from django.core import mail
from django.test import TestCase

from io import StringIO

from django.core.management import call_command

from core.models import Profil, User
from mds.models import DemiJourneeReception, MDS, MDSReception, UserMDSProfile
from planning.models import CreneauRdv
from planning.utils import generer_creneaux_permanences

LUNDI = date(2026, 12, 7)


class GenerationSallesTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.mds = MDS.objects.create(code_mds="TG1", nom="MDS ESSAI GEN", adresse="3 rue E", code_postal="13110",
                                      ville="Port-de-Bouc")
        self.salle = MDSReception.objects.create(mds=self.mds, nom="Salle G")
        self.agent = self.utilisateur("agent_gen", "AGGEN")
        self.agent2 = self.utilisateur("agent_gen2", "AGGEN2")
        self.cadre = self.utilisateur("cadre_gen", "CAGEN", capacite_cadre=True)
        DemiJourneeReception.objects.create(agent=self.agent, mds=self.mds, jour_semaine=0,
                                            heure_debut=time(9), heure_fin=time(12), type_lieu='MDS', actif=True)
        DemiJourneeReception.objects.create(agent=self.agent2, mds=self.mds, jour_semaine=0,
                                            heure_debut=time(9), heure_fin=time(12), type_lieu='MDS', actif=True)

    def utilisateur(self, login, matricule, capacite_cadre=False):
        u = User.objects.create_user(login, password="x", matricule=matricule, email=f"{login}@example.com")
        u.profils.add(Profil.objects.get(code="MDS_CADRES" if capacite_cadre else "MDS_AGENTS_SOCIAUX"))
        UserMDSProfile.objects.create(user=u, mds=self.mds, actif=True, principale=True)
        return u

    def test_salle_libre_utilisee(self):
        creneaux = generer_creneaux_permanences(LUNDI, 1, self.mds)
        self.assertTrue(creneaux)
        self.assertTrue(all(c.salle_id == self.salle.pk for c in creneaux))

    def test_salle_occupee_par_un_hors_permanence_sautee_et_cadre_alerte(self):
        # Un rendez-vous hors permanence prend la seule salle sur la matinée
        CreneauRdv.objects.create(date=LUNDI, heure_debut=time(10), heure_fin=time(10, 40), mds=self.mds,
                                  salle=self.salle, agent=self.agent, nature='HORS_PERMANENCE', statut='RESERVE')
        mail.outbox = []
        creneaux = generer_creneaux_permanences(LUNDI, 1, self.mds)
        matin = [c for c in creneaux if c.heure_debut < time(12)]
        self.assertEqual(matin, [])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("cadre_gen@example.com", mail.outbox[0].to)
        self.assertIn("07/12/2026", mail.outbox[0].body)
