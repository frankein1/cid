# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/tests_afase_envoi.py
"""Envoi d'une AFASE au service de contrôle : par mail à l'UAGAF (pages évitées) ou imprimé. Données fictives."""
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase, override_settings

from AidFi.services import afase_circuit as circuit


def _dossier():
    mds = SimpleNamespace(nom="MDS TEST 01", ville="Port-de-Bouc", email="mds@exemple.fr", type_mds="TERRITOIRE")
    usager = SimpleNamespace(nom="MONOP", prenom="Jean")
    decision = SimpleNamespace(montant_accorde="120,00", organisme_paiement="",
                               get_paiement_a_display=lambda: "la famille")
    pieces = mock.MagicMock()
    pieces.filter.return_value = []
    demande = SimpleNamespace(pk=7, mds=mds, beneficiaire=usager, decision=decision,
                              pieces_justificatives=mock.MagicMock())
    demande.pieces_justificatives.filter.return_value.select_related.return_value = pieces
    return demande


USER = SimpleNamespace(get_full_name=lambda: "Agent Test", username="as1_mds1")


class EnvoiAFASETests(SimpleTestCase):
    @override_settings(EMAIL_BACKEND='dummy')
    def test_mail_refuse_si_messagerie_non_reglee(self):
        with self.assertRaisesMessage(circuit.CircuitErreur, "messagerie de CID n'est pas réglée"):
            circuit._envoyer_dossier(_dossier(), USER, 'MAIL')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                       AFASE_UAGAF_EMAILS=['uagaf@exemple.fr'])
    def test_envoi_par_mail_enregistre_les_pages_evitees(self):
        with mock.patch('logement.services.envoi.envoyer_mail') as envoyer, \
                mock.patch('logement.services.envoi.enregistrer') as enregistrer:
            circuit._envoyer_dossier(_dossier(), USER, 'MAIL')
        destinataires, objet, message, pdf, nom_pdf, documents = envoyer.call_args.args
        self.assertEqual(destinataires, ['uagaf@exemple.fr'])
        self.assertIn("AFASE n° 7", objet)
        self.assertIsNone(pdf)
        self.assertEqual(documents, [])
        # Aucune pièce réelle : le minimum du CSV (AFASE : dossier 4 + pièces 5) est compté à l'enregistrement
        self.assertEqual((enregistrer.call_args.args[1], enregistrer.call_args.args[3:]), ('AFASE', ('MAIL', 0, 0)))

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', AFASE_UAGAF_EMAILS=[])
    def test_sans_adresse_uagaf_refus_explicite(self):
        with mock.patch('AidFi.services.afase_circuit._adresses_uagaf', return_value=[]):
            with self.assertRaisesMessage(circuit.CircuitErreur, "Aucune adresse de l'UAGAF"):
                circuit._envoyer_dossier(_dossier(), USER, 'MAIL')

    @override_settings(EMAIL_BACKEND='dummy')
    def test_envoi_imprime_ne_demande_pas_de_messagerie(self):
        with mock.patch('logement.services.envoi.enregistrer') as enregistrer:
            circuit._envoyer_dossier(_dossier(), USER, 'IMPRIME')
        self.assertEqual((enregistrer.call_args.args[1], enregistrer.call_args.args[3:]), ('AFASE', ('IMPRIME', 0, 0)))
