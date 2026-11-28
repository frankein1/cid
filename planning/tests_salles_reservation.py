# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# planning/tests_salles_reservation.py
"""Réservation des salles : permanences prioritaires, marge de 30 minutes après un rendez-vous hors permanence. Données fictives."""
from datetime import date, time

from django.test import TestCase

from core.models import User
from mds.models import MDS, MDSReception
from planning.agenda import MARGE_HORS_PERMANENCE_MINUTES, salle_occupee
from planning.models import CreneauRdv

JOUR = date(2026, 12, 1)


class SalleOccupeeTests(TestCase):
    def setUp(self):
        self.mds = MDS.objects.create(code_mds="TS1", nom="MDS ESSAI SALLE", adresse="2 rue D", code_postal="13110",
                                      ville="Port-de-Bouc")
        self.salle = MDSReception.objects.create(mds=self.mds, nom="Salle D")
        self.agent = User.objects.create_user("agent_salle", password="x", matricule="AGSALLE")

    def rdv(self, nature, debut, fin, statut='RESERVE', salle=None):
        return CreneauRdv.objects.create(date=JOUR, heure_debut=debut, heure_fin=fin, mds=self.mds,
                                         salle=salle or self.salle, agent=self.agent, nature=nature,
                                         statut=statut)

    def test_marge_de_trente_minutes(self):
        self.assertEqual(MARGE_HORS_PERMANENCE_MINUTES, 30)

    def test_hors_permanence_bloque_dans_la_marge_apres(self):
        # 09:00-09:40 + 30 min de marge = jusqu'à 10:10
        self.rdv('HORS_PERMANENCE', time(9), time(9, 40))
        self.assertTrue(salle_occupee(self.salle, JOUR, time(10), time(10, 30), 'HORS_PERMANENCE'))
        self.assertFalse(salle_occupee(self.salle, JOUR, time(10, 10), time(10, 30), 'HORS_PERMANENCE'))

    def test_marge_de_la_nouvelle_saisie_compte_aussi(self):
        # Rendez-vous 10:00-10:30 : sa marge court jusqu'à 11:00, donc 10:45 est refusé
        self.rdv('HORS_PERMANENCE', time(10), time(10, 30))
        self.assertTrue(salle_occupee(self.salle, JOUR, time(9), time(9, 40), 'HORS_PERMANENCE'))
        self.assertFalse(salle_occupee(self.salle, JOUR, time(9), time(9, 30), 'HORS_PERMANENCE'))

    def test_permanence_bloque_un_hors_permanence(self):
        self.rdv('PERMANENCE', time(9), time(9, 30))
        self.assertTrue(salle_occupee(self.salle, JOUR, time(9, 10), time(9, 40), 'HORS_PERMANENCE'))

    def test_permanence_non_bloquee_par_un_hors_permanence(self):
        self.rdv('HORS_PERMANENCE', time(9), time(9, 30))
        self.assertEqual(salle_occupee(self.salle, JOUR, time(9), time(9, 30), 'PERMANENCE'), [])

    def test_permanence_bloque_une_autre_permanence(self):
        self.rdv('PERMANENCE', time(9), time(9, 30))
        self.assertTrue(salle_occupee(self.salle, JOUR, time(9, 15), time(9, 45), 'PERMANENCE'))

    def test_rendez_vous_annule_ne_bloque_pas(self):
        self.rdv('PERMANENCE', time(9), time(9, 30), statut='ANNULE_MDS')
        self.assertEqual(salle_occupee(self.salle, JOUR, time(9), time(9, 30), 'HORS_PERMANENCE'), [])

    def test_autre_salle_non_concernee(self):
        autre = MDSReception.objects.create(mds=self.mds, nom="Salle E")
        self.rdv('PERMANENCE', time(9), time(9, 30))
        self.assertEqual(salle_occupee(autre, JOUR, time(9), time(9, 30), 'HORS_PERMANENCE'), [])

    def test_sans_salle_aucun_conflit(self):
        self.assertEqual(salle_occupee(None, JOUR, time(9), time(9, 30), 'HORS_PERMANENCE'), [])
