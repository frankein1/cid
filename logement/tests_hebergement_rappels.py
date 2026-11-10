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

    def test_champs_dedies_font_disparaitre_le_rappel(self):
        f = self.fiche(F.SAS)
        f.donnees = {'oqtf': 'non', 'droits': 'droits ouverts', 'mecs': 'oui'}
        f.save()
        self.assertEqual(self.codes(f), ['PIECES'])
        g = self.fiche(F.ETAT)
        g.donnees = {'oqtf': 'non', 'identite_numero': '1234567890', 'via_sas': 'oui', 'mecs': 'non'}
        g.save()
        self.assertEqual(self.codes(g), ['PIECES'])

    def test_piece_identite_dans_la_ged_retire_le_rappel_pieces(self):
        from django.contrib.contenttypes.models import ContentType
        from ged.models import DocumentGED, DocumentType
        from beneficiaire.models import Beneficiaire
        f = self.fiche(F.SAS)
        self.assertIn('PIECES', self.codes(f))
        self.assertIn("pièce d'identité ou titre de séjour", H.pieces_manquantes(f))
        t = DocumentType.objects.get_or_create(code='CI', defaults={'nom': "Carte d'identité", 'categorie': 'IDENTITE'})[0]
        DocumentGED.objects.create(content_type=ContentType.objects.get_for_model(Beneficiaire), object_id=self.b.pk,
                                   type_document=t, titre="CI (fictive).pdf", seaweedfs_id="fictif", extension="pdf")
        self.assertNotIn('PIECES', self.codes(f))

    def test_adresse_sas_et_texte_personnalisable_depuis_l_administration(self):
        from .models import RappelHebergement as RH
        self.assertEqual(H.sas_email(), "l'adresse du SAS (à paramétrer dans l'administration)")
        DestinataireHebergement.objects.create(nom="SAS (fictif)", email="sas@example.org", est_sas=True)
        g = self.fiche(F.ETAT)
        self.assertIn("sas@example.org", [r['texte'] for r in H.rappels(g) if r['code'] == 'SAS_SEUL'][0])
        RH.objects.create(code='OQTF', texte="Texte local : vérifiez l'OQTF.", reference="Note locale 2026")
        textes = {r['code']: r for r in H.rappels(g)}
        self.assertEqual(textes['OQTF']['texte'], "Texte local : vérifiez l'OQTF.")
        self.assertEqual(textes['OQTF']['reference'], "Note locale 2026")
        RH.objects.filter(code='OQTF').update(actif=False)
        self.assertNotIn('OQTF', self.codes(g))

