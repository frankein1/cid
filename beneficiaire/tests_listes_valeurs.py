# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/tests_listes_valeurs.py
"""Listes de valeurs de la fiche usager (hébergement, mobilité, CSP…). Données fictives."""
from datetime import date

from django.test import TestCase

from beneficiaire.forms import BeneficiaireForm
from beneficiaire.models import Beneficiaire, ValeurListe as V
from mds.models import MDS


class ListesValeursTests(TestCase):
    def setUp(self):
        self.mds = MDS.objects.create(code_mds="T1", nom="MDS Essai", adresse="1 rue A", code_postal="13000", ville="Exemple")
        self.b = Beneficiaire.objects.create(code_interne="T-LV", civilite="MME", nom="ESSAI", prenom="Lucie",
                                             date_naissance=date(1990, 1, 1), adresse="3 rue C", code_postal="13000",
                                             ville="Exemple", mds=self.mds)

    def test_valeurs_de_depart(self):
        self.assertTrue(V.objects.filter(liste=V.HEBERGEMENT, libelle="Locataire parc social").exists())
        self.assertEqual(V.objects.filter(liste=V.PROTECTION).count(), 8)
        self.assertEqual(set(V.objects.values_list("liste", flat=True)), {c for c, _ in V.LISTES})

    def donnees(self, **extra):
        f = BeneficiaireForm(instance=self.b)
        d = {k: v for k, v in f.initial.items() if v is not None and k not in ("mobilites",)}
        d.update({"telephone_mobile": "", "telephone_fixe": "", "date_naissance": "01/01/1990", "date_entree": ""})
        d.update(extra)
        return d

    def test_saisie_et_valeur_desactivee_conservee(self):
        heb = V.objects.get(liste=V.HEBERGEMENT, libelle="Hébergé chez un tiers")
        mob = list(V.objects.filter(liste=V.MOBILITE)[:2])
        f = BeneficiaireForm(self.donnees(mode_hebergement=heb.pk, mobilites=[m.pk for m in mob], aidant="on"),
                             instance=self.b)
        self.assertTrue(f.is_valid(), f.errors)
        f.save()
        f.save_m2m() if hasattr(f, "save_m2m") else None
        self.b.refresh_from_db()
        self.assertEqual((self.b.mode_hebergement, self.b.aidant, self.b.mobilites.count()), (heb, True, 2))
        # valeur désactivée : plus proposée aux autres, mais toujours valable pour ce dossier
        heb.actif = False
        heb.save()
        self.assertIn(heb, BeneficiaireForm(instance=self.b).fields["mode_hebergement"].queryset)
        autre = Beneficiaire.objects.create(code_interne="T-LV2", civilite="M.", nom="AUTRE", prenom="Noé",
                                            date_naissance=date(1980, 1, 1), adresse="x", code_postal="13000",
                                            ville="Exemple", mds=self.mds)
        self.assertNotIn(heb, BeneficiaireForm(instance=autre).fields["mode_hebergement"].queryset)
        # une valeur d'une autre liste est refusée
        mauvaise = V.objects.filter(liste=V.CSP).first()
        f = BeneficiaireForm(self.donnees(mode_hebergement=mauvaise.pk), instance=self.b)
        self.assertFalse(f.is_valid())
