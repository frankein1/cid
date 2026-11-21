# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/tests_papier_economise.py
"""Pages comptées par envoi : minimum du CSV (dossier et pièces jointes séparés) ou pages réelles si elles sont plus
nombreuses. Le minimum AFASE (4 pages de dossier, 5 de pièces) vient de la migration 0018 ; l'import CSV est testé
avec un fichier temporaire."""
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

from logement.models import ReglePagesEnvoi
from logement.services import envoi


class ComptagePagesTests(TestCase):
    def test_afase_minimum_du_csv(self):
        # 4 pages de dossier et 5 de pièces jointes : minimums du fichier CSV
        self.assertEqual(envoi.compter('AFASE', 0, 0), (4, 5))

    def test_pieces_reelles_au_dessus_du_minimum(self):
        self.assertEqual(envoi.compter('AFASE', 0, 9), (4, 9))

    def test_dossier_reel_au_dessus_du_minimum(self):
        self.assertEqual(envoi.compter('AFASE', 6, 2), (6, 5))

    def test_type_sans_regle_compte_le_reel(self):
        self.assertEqual(envoi.compter('INCONNU', 3, 2), (3, 2))

    def test_type_present_avec_minimum_zero(self):
        ReglePagesEnvoi.objects.update_or_create(code='FSL', defaults={
            'libelle': 'Demande FSL', 'pages_dossier': 0, 'pages_pieces_jointes': 0})
        self.assertEqual(envoi.compter('FSL', 3, 2), (3, 2))

    def test_enregistrer_applique_le_minimum_et_le_libelle(self):
        from core.models import User
        obj = User.objects.create(username='pages_test')
        e = envoi.enregistrer(obj, 'AFASE', None, 'MAIL', 0, 0)
        self.assertEqual((e.pages_dossier, e.pages_pieces, e.pages), (4, 5, 9))
        self.assertEqual(e.nature, 'Aide financière (AFASE)')


class ImportCSVTests(TestCase):
    def _csv(self, contenu):
        dossier = tempfile.mkdtemp(prefix='pages_csv_')
        chemin = Path(dossier) / 'pages.csv'
        chemin.write_text(contenu, encoding='utf-8')
        return str(chemin)

    def test_import_cree_puis_met_a_jour(self):
        chemin = self._csv("code;libelle;pages_dossier;pages_pieces_jointes\nCOPP;Saisine COPP;2;3\n")
        call_command('importer_pages_envois', chemin)
        self.assertEqual(envoi.compter('COPP', 0, 0), (2, 3))
        call_command('importer_pages_envois', self._csv(
            "code;libelle;pages_dossier;pages_pieces_jointes\ncopp;Saisine COPP;4;1\n"))
        self.assertEqual(ReglePagesEnvoi.objects.filter(code='COPP').count(), 1)
        self.assertEqual(envoi.compter('COPP', 0, 0), (4, 1))

    def test_valeur_invalide_refusee(self):
        chemin = self._csv("code;libelle;pages_dossier;pages_pieces_jointes\nFSL;Demande FSL;quatre;0\n")
        with self.assertRaisesMessage(CommandError, "Ligne 2 invalide"):
            call_command('importer_pages_envois', chemin)

    def test_entete_incorrecte_refusee(self):
        with self.assertRaisesMessage(CommandError, "En-tête attendu"):
            call_command('importer_pages_envois', self._csv("code;libelle\nFSL;Demande FSL\n"))


class PagesDocumentsTests(SimpleTestCase):
    def test_document_non_pdf_compte_une_page(self):
        from unittest import mock
        with mock.patch('logement.services.envoi.contenu_document', return_value=('photo.jpg', b'x')):
            self.assertEqual(envoi.pages_document(object()), 1)
