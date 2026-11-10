# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/tests_hebergement_rappels.py
"""Hébergement d'urgence : rappels de la fiche méthodologique (OQTF, pièces, AGDREF, SAS, MECS) à lire en popup
avant la fiche. Données fictives."""
from datetime import timedelta

from django.utils import timezone

from beneficiaire.models import Beneficiaire
from .models import DemarcheHebergement as M, DestinataireHebergement, DossierHebergement as D, FicheHebergement as F
from .services import hebergement as H
from .tests_expulsion import _Base


class RappelsHebergementTests(_Base):
    def setUp(self):
        super().setUp()
        self.b.date_naissance = timezone.localdate() - timedelta(days=9000)
        self.b.save()
        DestinataireHebergement.objects.create(nom="Service d'appui (fictif)", email="appui@example.com")
        self.ts_c = self.client_de(self.ts)
        self.ts_c.post(f"/logement/hebergement/nouveau/{self.b.code_interne}/")
        self.d = D.objects.get()

    def fiche(self, type_fiche):
        self.ts_c.post(f"/logement/hebergement/{self.d.pk}/action/", {"action": "fiche", "type_fiche": type_fiche})
        return self.d.fiches.filter(type_fiche=type_fiche).latest('pk')

    def codes(self, f):
        return [r['code'] for r in H.rappels_non_lus(f)]

    def test_sas_rappels_oqtf_pieces_droits_mecs(self):
        f = self.fiche(F.SAS)
        self.assertEqual(self.codes(f), ['OQTF', 'PIECES', 'DROITS', 'MECS'])

    def test_ddets_rappels_agdref_et_passage_par_le_sas(self):
        f = self.fiche(F.ETAT)
        self.assertEqual(self.codes(f), ['OQTF', 'PIECES', 'AGDREF', 'SAS_SEUL', 'MECS'])
        f.donnees = {'identite_numero': '1234567890'}
        f.save()
        self.assertNotIn('AGDREF', self.codes(f))

    def test_mecs_disparait_si_la_demarche_est_tracee(self):
        f = self.fiche(F.SAS)
        M.objects.create(dossier=self.d, type_demarche='MECS')
        self.assertNotIn('MECS', self.codes(f))

    def test_popup_affiche_puis_accuse_lecture(self):
        f = self.fiche(F.SAS)
        page = self.ts_c.get(f"/logement/hebergement/fiche/{f.pk}/")
        self.assertContains(page, 'id="rappels"')
        self.assertContains(page, "Conformément à la fiche méthodologique")
        self.ts_c.post(f"/logement/hebergement/fiche/{f.pk}/action/",
                       {"action": "rappels_lus", "codes": ["OQTF", "PIECES", "DROITS", "MECS", "INVENTE"]})
        f.refresh_from_db()
        self.assertEqual(self.codes(f), [])
        self.assertTrue(any(h['action'] == 'Rappel lu' and h['detail'] == 'OQTF' for h in f.historique))
        self.assertFalse(any(h['detail'] == 'INVENTE' for h in f.historique))
        self.assertNotContains(self.ts_c.get(f"/logement/hebergement/fiche/{f.pk}/"), 'id="rappels"')

    def test_pas_de_popup_pour_une_fiche_envoyee(self):
        f = self.fiche(F.SAS)
        F.objects.filter(pk=f.pk).update(statut=F.ENVOYEE)
        self.assertNotContains(self.ts_c.get(f"/logement/hebergement/fiche/{f.pk}/"), 'id="rappels"')
