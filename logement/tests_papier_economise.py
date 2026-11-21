# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/tests_papier_economise.py
"""Pages d'un envoi papier : minimums par type de pièce (livret 4, identité 2, justificatifs 3 à eux deux)."""
from django.test import SimpleTestCase

from logement.services.envoi import pages_pieces


class PagesPiecesTests(SimpleTestCase):
    def test_aucune_piece_donne_les_minimums(self):
        # Livret 4 + identité 2 + RIB 1 + justificatifs 3 = 10 pages : le minimum d'une AFASE
        self.assertEqual(pages_pieces({'IDENTITE': 0, 'LIVRET_FAMILLE': 0, 'RIB': 0,
                                       'DOMICILE': 0, 'FACTURE_DEVIS': 0}), 10)

    def test_pages_reelles_au_dessus_du_minimum(self):
        self.assertEqual(pages_pieces({'IDENTITE': 3, 'LIVRET_FAMILLE': 6, 'RIB': 1,
                                       'DOMICILE': 2, 'FACTURE_DEVIS': 2}), 3 + 6 + 1 + 4)

    def test_justificatifs_comptent_au_moins_trois_pages(self):
        self.assertEqual(pages_pieces({'DOMICILE': 1, 'FACTURE_DEVIS': 0}), 3)

    def test_piece_sans_minimum_compte_une_page(self):
        self.assertEqual(pages_pieces({'AUTRE': 0}), 1)
