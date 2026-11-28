# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# planning/tests_saisie_horaire.py
"""Saisie des horaires (24 h, pas de 10 minutes) et lieu d'un rendez-vous (VAD, hors permanence). Données fictives."""
from datetime import time
from types import SimpleNamespace

from django import forms
from django.test import SimpleTestCase

from planning.forms import SaisieHoraire, lieu_du_rendez_vous


class _Formulaire(SaisieHoraire, forms.Form):
    heure_debut = forms.TimeField()
    heure_fin = forms.TimeField()


class SaisieHoraireTests(SimpleTestCase):
    def test_pas_de_dix_minutes_accepte(self):
        f = _Formulaire(data={'heure_debut': '14:10', 'heure_fin': '14:30'})
        self.assertTrue(f.is_valid(), f.errors)
        self.assertEqual(f.cleaned_data['heure_debut'], time(14, 10))

    def test_minute_impaire_refusee(self):
        f = _Formulaire(data={'heure_debut': '14:01', 'heure_fin': '14:30'})
        self.assertFalse(f.is_valid())
        self.assertIn('heure_debut', f.errors)

    def test_format_24_heures_et_widget_texte(self):
        f = _Formulaire()
        self.assertEqual(f.fields['heure_debut'].widget.input_type, 'text')
        self.assertIn('pattern', f.fields['heure_debut'].widget.attrs)
        self.assertEqual(f.fields['heure_debut'].input_formats, ['%H:%M'])

    def test_initial_affiche_en_24_heures(self):
        f = _Formulaire(initial={'heure_debut': time(14, 0)})
        self.assertIn('value="14:00"', str(f['heure_debut']))


class LieuDuRendezVousTests(SimpleTestCase):
    usager = SimpleNamespace(adresse='3 rue C', code_postal='13110', ville='Port-de-Bouc')
    sans_adresse = SimpleNamespace(adresse='', code_postal='', ville='')

    def test_vad_au_domicile_de_la_fiche(self):
        lieu, erreur = lieu_du_rendez_vous('VAD', self.usager, 'n\'importe quoi')
        self.assertIsNone(erreur)
        self.assertEqual(lieu, 'Domicile : 3 rue C, 13110 Port-de-Bouc')

    def test_vad_sans_adresse_refusee(self):
        lieu, erreur = lieu_du_rendez_vous('VAD', self.sans_adresse, '')
        self.assertIsNotNone(erreur)

    def test_hors_permanence_exige_un_lieu(self):
        lieu, erreur = lieu_du_rendez_vous('HORS_PERMANENCE', self.usager, '   ')
        self.assertIsNotNone(erreur)

    def test_hors_permanence_avec_lieu(self):
        lieu, erreur = lieu_du_rendez_vous('HORS_PERMANENCE', self.usager, 'MDS Port-de-Bouc, salle A')
        self.assertIsNone(erreur)
        self.assertEqual(lieu, 'MDS Port-de-Bouc, salle A')
