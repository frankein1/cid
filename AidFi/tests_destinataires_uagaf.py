# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/tests_destinataires_uagaf.py
"""Destinataires de l'UAGAF : import CSV et prise en compte par le circuit d'envoi. Données fictives."""
from django.test import TestCase, override_settings

from AidFi.models import DestinataireUAGAF
from AidFi.services.destinataires_uagaf import adresses_actives, importer_destinataires


class ImportDestinatairesTests(TestCase):

    def test_import_cree_puis_met_a_jour(self):
        texte = "nom;email;actif\nUAGAF;uagaf@example.com;oui\nAgent;agent@example.com;non\n"
        self.assertEqual(importer_destinataires(texte), (2, 0))
        self.assertEqual(importer_destinataires("nom;email;actif\nUAGAF nouveau;uagaf@example.com;oui\n"), (0, 1))
        self.assertEqual(DestinataireUAGAF.objects.get(email='uagaf@example.com').nom, 'UAGAF nouveau')

    def test_seules_les_adresses_actives_sont_retenues(self):
        importer_destinataires("nom;email;actif\nUAGAF;uagaf@example.com;oui\nAgent;agent@example.com;non\n")
        self.assertEqual(adresses_actives(), ['uagaf@example.com'])

    def test_adresse_invalide_refusee_sans_rien_enregistrer(self):
        with self.assertRaisesMessage(ValueError, "Ligne 3 invalide"):
            importer_destinataires("nom;email;actif\nUAGAF;uagaf@example.com;oui\nX;pas-une-adresse;oui\n")
        self.assertEqual(DestinataireUAGAF.objects.count(), 0)

    def test_en_tete_incorrect_refuse(self):
        with self.assertRaisesMessage(ValueError, "En-tête attendu"):
            importer_destinataires("mail;actif\nuagaf@example.com;oui\n")

    def test_actif_invalide_refuse(self):
        with self.assertRaisesMessage(ValueError, "colonne actif"):
            importer_destinataires("nom;email;actif\nUAGAF;uagaf@example.com;peut-etre\n")


class CircuitAdressesUAGAFTests(TestCase):

    @override_settings(AFASE_UAGAF_EMAILS=['env@example.com'])
    def test_la_table_prime_sur_la_variable_d_environnement(self):
        from AidFi.services.afase_circuit import _adresses_uagaf
        DestinataireUAGAF.objects.create(nom='UAGAF', email='table@example.com', actif=True)
        self.assertEqual(_adresses_uagaf(), ['table@example.com'])

    @override_settings(AFASE_UAGAF_EMAILS=['env@example.com'])
    def test_sans_table_la_variable_d_environnement_sert_de_secours(self):
        from AidFi.services.afase_circuit import _adresses_uagaf
        self.assertEqual(_adresses_uagaf(), ['env@example.com'])
