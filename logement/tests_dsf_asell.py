# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/tests_dsf_asell.py
"""DSF : mesure ASELL reportée dans « Autres mesures d'apurement ». Données fictives."""
from datetime import date

from logement.models import DossierExpulsion as D, OrientationASELL as A
from logement.services import dsf
from logement.tests_expulsion import _Base


class AsellDansDsfTests(_Base):
    def setUp(self):
        super().setUp()
        self.nouveau(mds=self.mds.pk, code_usager="EX-1", loyer="600", charges="40", dette="1800",
                     tribunal="Tribunal judiciaire (fictif)")
        self.b = D.objects.get().beneficiaire

    def _orientation(self, **champs):
        return A.objects.create(beneficiaire=self.b, mds=self.mds, **champs)

    def _texte(self):
        v = {}
        dsf._mesures_asell(self.b, v)
        return v.get("Autres mesures d'apurement")

    def test_sans_asell_rien_n_est_ecrit(self):
        self.assertIsNone(self._texte())

    def test_asell_engagee_avec_date_et_operateur(self):
        self._orientation(type_mesure=A.RENFORCE, volet=A.MAINTIEN, statut=A.ENVOYEE, reponse=A.ACCORD,
                          date_reponse=date(2026, 9, 1), operateur_libre="Opérateur (fictif)")
        self.assertEqual(self._texte(),
                         "ASELL renforcée engagée depuis le 01/09/2026 (opérateur : Opérateur (fictif)).")

    def test_demande_en_attente(self):
        self._orientation(statut=A.ENVOYEE, reponse=A.ATTENTE, date_envoi=date(2026, 10, 5))
        self.assertEqual(self._texte(), "ASELL demandée le 05/10/2026, en attente de réponse.")

    def test_abandonnee_ignoree(self):
        self._orientation(statut=A.ABANDONNEE, reponse=A.ACCORD, date_reponse=date(2026, 9, 1))
        self.assertIsNone(self._texte())
