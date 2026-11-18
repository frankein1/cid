# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/tests_demo_donnees.py
"""Jeu de données fictives (init2, init_demo) : création, situations récentes, réinitialisation sans doublon."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from beneficiaire.models_journal import NotePersonnelle
from messagerie.models import Message


class JeuDeDonneesTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        call_command("init2", stdout=StringIO())

    def situations(self):
        return {
            "messages": Message.objects.filter(objet__startswith="[démo]").count(),
            "notes": NotePersonnelle.objects.filter(contenu__startswith="[démo]").count(),
            "transmissibles": NotePersonnelle.objects.filter(contenu__startswith="[démo]", a_transmettre=True).count(),
        }

    def test_reaffectation_et_notes_crees_puis_sans_doublon(self):
        call_command("init_demo", stdout=StringIO())
        self.assertEqual(self.situations(), {"messages": 1, "notes": 2, "transmissibles": 1})
        m = Message.objects.get(objet__startswith="[démo]")
        self.assertEqual(m.motifs_contact, ["REAFFECTATION"])
        self.assertIsNotNone(m.mds_demandeuse)
        self.assertEqual(m.decision_reaffectation, "")
        call_command("init_demo", "--reinitialiser", stdout=StringIO())
        self.assertEqual(self.situations(), {"messages": 1, "notes": 2, "transmissibles": 1})
