# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# ru/tests_rdv_courrier.py
"""Relation usager : le rendez-vous est posé dans l'agenda (salle, mémo, heures). Données fictives."""
from datetime import date, time
from types import SimpleNamespace
from unittest import mock

from django.test import TestCase

from core.models import User
from mds.models import MDS, MDSReception
from planning.models import CreneauRdv
from ru.rendez_vous import poser_rdv_ru

JOUR = date(2026, 12, 3)


class RendezVousRUTests(TestCase):
    def setUp(self):
        self.mds = MDS.objects.create(code_mds="TR1", nom="MDS ESSAI RU", adresse="6 rue H", code_postal="13110",
                                      ville="Port-de-Bouc")
        self.salle = MDSReception.objects.create(mds=self.mds, nom="Salle H")
        self.agent = User.objects.create_user("agent_ru", password="x", matricule="AGRU")

    def demande(self, heure=time(10), date_rdv=JOUR):
        d = SimpleNamespace(pk=1, reference="RU-ESSAI-1", mds=self.mds, agent_assigne=self.agent,
                            date_premier_rendez_vous=date_rdv, heure_premier_rendez_vous=heure,
                            date_second_rendez_vous=None, heure_second_rendez_vous=None,
                            creneau_premier_rdv=None, creneau_second_rdv=None)
        d.save = mock.Mock()
        return d

    def test_pose_le_rendez_vous_avec_le_memo_mds(self):
        d = self.demande()
        rdv = poser_rdv_ru(d, 1, self.agent, salle=self.salle)
        self.assertEqual(CreneauRdv.objects.count(), 1)
        self.assertEqual(d.creneau_premier_rdv, rdv)
        self.assertEqual(rdv.salle, self.salle)
        self.assertEqual(rdv.lieu_precis, "MDS : 6 rue H, 13110 Port-de-Bouc")
        self.assertEqual(rdv.salle, self.salle)
        self.assertEqual((rdv.heure_debut, rdv.heure_fin), (time(10), time(10, 40)))

    def test_horaire_hors_pas_de_dix_minutes_refuse(self):
        with self.assertRaises(ValueError):
            poser_rdv_ru(self.demande(heure=time(10, 5)), 1, self.agent)
        self.assertFalse(CreneauRdv.objects.exists())

    def test_hors_heures_a_la_mds_refuse(self):
        with self.assertRaises(ValueError):
            poser_rdv_ru(self.demande(heure=time(18)), 1, self.agent)
        self.assertFalse(CreneauRdv.objects.exists())

    def test_salle_occupee_refuse(self):
        CreneauRdv.objects.create(date=JOUR, heure_debut=time(9, 50), heure_fin=time(10, 30), mds=self.mds,
                                  salle=self.salle, agent=self.agent, nature='HORS_PERMANENCE', statut='RESERVE')
        with self.assertRaises(ValueError):
            poser_rdv_ru(self.demande(), 1, self.agent, salle=self.salle)
