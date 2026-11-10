# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/tests_fsl_pieces.py
"""FSL : pièces à cocher par type de demande, justification des absentes à l'envoi. Données fictives."""
from django.test import SimpleTestCase

from logement.models import DemandeFSL
from logement.services import pieces
from logement.tests_expulsion import _Base


class ListesFslTests(SimpleTestCase):
    def test_chaque_type_a_sa_liste_et_les_fluides_partagent_la_leur(self):
        self.assertEqual(pieces.liste_fsl('EAU'), pieces.liste_fsl('ENERGIE'))
        codes_acces = {c for c, _ in pieces.liste_fsl('ACCES')}
        codes_maintien = {c for c, _ in pieces.liste_fsl('MAINTIEN')}
        self.assertIn('BAIL', codes_acces)
        self.assertIn('CCAPEX', codes_maintien)
        self.assertNotIn('BAIL', codes_maintien)
        self.assertEqual(pieces.liste_fsl('INCONNU'), [])

    def test_manquantes_liste_les_pieces_non_cochees(self):
        libelles = pieces.manquantes('ENERGIE', ['ETAT_CIVIL', 'RIB', 'FACTURE'])
        self.assertEqual(len(libelles), len(pieces.liste_fsl('ENERGIE')) - 3)
        self.assertFalse(any("Justificatifs d'état civil" in l for l in libelles))


class EnvoiFslTests(_Base):
    def setUp(self):
        super().setUp()
        self.nouveau(mds=self.mds.pk, code_usager="EX-1", loyer="600", charges="40", dette="1800",
                     tribunal="Tribunal judiciaire (fictif)")
        self.demande = DemandeFSL.objects.create(beneficiaire=self.b, mds=self.mds, type_aide=DemandeFSL.ENERGIE,
                                                 statut=DemandeFSL.VALIDEE, avis='FAVORABLE')
        self.ts_c = self.client_de(self.ts)
        self.url = f"/logement/envoi/fsl/{self.demande.pk}/"

    def test_envoi_bloque_si_pieces_non_cochees_sans_justification(self):
        r = self.ts_c.post(self.url, {"action": "mail", "destinataire": "fsl@example.org"})
        self.assertRedirects(r, self.url, fetch_redirect_response=False)
        self.demande.refresh_from_db()
        self.assertFalse(any(h.get('action') == 'Envoi sans pièce(s)' for h in self.demande.historique or []))

    def test_justification_trop_longue_refusee(self):
        r = self.ts_c.post(self.url, {"action": "mail", "destinataire": "fsl@example.org",
                                      "justification_pieces": "x" * 201})
        self.assertRedirects(r, self.url, fetch_redirect_response=False)

    def test_envoi_avec_justification_est_trace(self):
        toutes = [c for c, _ in pieces.liste_fsl('ENERGIE')][:-1]   # une pièce absente
        r = self.ts_c.post(self.url, {"action": "mail", "destinataire": "fsl@example.org", "cochees": toutes,
                                      "justification_pieces": "Quittance en attente de la bailleresse (fictif)."})
        self.assertNotEqual(r['Location'], self.url)
        self.demande.refresh_from_db()
        self.assertTrue(any(h.get('action') == 'Envoi sans pièce(s)' for h in self.demande.historique or []))
