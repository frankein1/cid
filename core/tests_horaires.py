# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/tests_horaires.py
"""Saisie 24 h : lecture des heures et dates, pas de 10 minutes. Données fictives."""
from datetime import date, time

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.utils import timezone

from core.horaires import lire_date_heure, lire_heure, lire_jour, verifier_pas_de_dix


class LectureHorairesTests(SimpleTestCase):
    def test_heure_24h(self):
        self.assertEqual(lire_heure("09:30"), time(9, 30))
        self.assertEqual(lire_heure("23:50"), time(23, 50))

    def test_heure_invalide(self):
        self.assertIsNone(lire_heure("2h01"))
        self.assertIsNone(lire_heure("25:00"))
        self.assertIsNone(lire_heure("10:60"))
        self.assertIsNone(lire_heure(""))

    def test_date_heure_jj_mm_aaaa(self):
        moment = lire_date_heure("01/12/2026 14:10")
        self.assertEqual(timezone.localtime(moment).date(), date(2026, 12, 1))
        self.assertEqual(timezone.localtime(moment).time(), time(14, 10))

    def test_date_heure_iso_accepte(self):
        self.assertIsNotNone(lire_date_heure("2026-12-01T14:10"))

    def test_date_heure_invalide(self):
        self.assertIsNone(lire_date_heure("31/02/2026 10:00"))
        self.assertIsNone(lire_date_heure(""))

    def test_jour_iso(self):
        self.assertEqual(lire_jour("2026-12-01"), date(2026, 12, 1))
        self.assertIsNone(lire_jour(""))

    def test_pas_de_dix_minutes(self):
        self.assertEqual(verifier_pas_de_dix(time(10, 40)), time(10, 40))
        with self.assertRaises(ValidationError):
            verifier_pas_de_dix(time(10, 5))
