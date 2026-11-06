# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/tests/test_anonymisation.py
"""Anonymiseur de base : verrous, usagers, agents, textes libres, documents détachés sans suppression."""
import os
from datetime import date, time
from io import StringIO
from unittest import mock

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from beneficiaire.models import Beneficiaire, LienFamilial
from core.models import User
from ged.models import DocumentGED, DocumentType
from mds.models import MDS
from planning.models import CreneauRdv


class AnonymisationTests(TestCase):
    def setUp(self):
        self.mds = MDS.objects.create(code_mds="T1", nom="MDS Essai", adresse="1 rue A", code_postal="13000", ville="Exemple")
        self.agent = User.objects.create_user("jessai", password="x", first_name="Inès", last_name="ESSAI",
                                              email="ines.essai@cid.test", matricule="M123")
        self.su = User.objects.create_superuser("admin", password="x", matricule="SU", email="admin@cid.test")
        commun = dict(adresse="12 avenue Réelle", code_postal="13110", ville="Port-de-Bouc", mds=self.mds)
        self.mere = Beneficiaire.objects.create(code_interne="T-M", civilite="MME", nom="DURANDEAU", prenom="Lucie",
                                                date_naissance=date(1990, 6, 15), nir="290061312345678",
                                                email="lucie@exemple.test", telephone_mobile="0611223344", **commun)
        self.fils = Beneficiaire.objects.create(code_interne="T-F", civilite="M.", nom="DURANDEAU", prenom="Noé",
                                                date_naissance=date(2015, 3, 1), **commun)
        LienFamilial.objects.create(personne_a=self.mere, personne_b=self.fils, type_lien="ENFANT",
                                    commentaire="Le père, M. Réel, ne doit pas être contacté")
        self.rdv = CreneauRdv.objects.create(date=date.today(), heure_debut=time(9), heure_fin=time(9, 30),
                                             agent=self.agent, beneficiaire=self.mere, statut="RESERVE",
                                             description="Entretien avec Mme DURANDEAU au sujet de ses dettes")
        t = DocumentType.objects.create(code="T", nom="Pièce", categorie=DocumentType._meta.get_field("categorie").choices[0][0])
        self.doc = DocumentGED.objects.create(content_type=ContentType.objects.get_for_model(Beneficiaire),
                                              object_id=self.mere.pk, type_document=t,
                                              titre="Avis d'imposition DURANDEAU", seaweedfs_id="pcl_vrai_fichier")

    def lancer(self, **env):
        with mock.patch.dict(os.environ, env):
            call_command("anonymiser_base", "--base", settings.DATABASES["default"]["NAME"], "--confirmer",
                         stdout=StringIO())

    def test_verrous(self):
        nom = settings.DATABASES["default"]["NAME"]
        with mock.patch.dict(os.environ, {"CID_ANONYMISATION_AUTORISEE": ""}):
            with self.assertRaisesMessage(CommandError, "CID_ANONYMISATION_AUTORISEE"):
                call_command("anonymiser_base", "--base", nom, "--confirmer")
        with mock.patch.dict(os.environ, {"CID_ANONYMISATION_AUTORISEE": "1"}):
            with self.assertRaisesMessage(CommandError, "pas à « production »"):
                call_command("anonymiser_base", "--base", "production", "--confirmer")
            with self.assertRaisesMessage(CommandError, "--confirmer"):
                call_command("anonymiser_base", "--base", nom)
        self.assertEqual(Beneficiaire.objects.get(pk=self.mere.pk).nom, "DURANDEAU")   # rien n'a bougé

    def test_anonymisation(self):
        with mock.patch("ged.storage.SeaweedFSStorage.delete") as suppression:
            self.lancer(CID_ANONYMISATION_AUTORISEE="1")
        suppression.assert_not_called()                                  # aucun fichier touché dans le stockage
        m, f = Beneficiaire.objects.get(pk=self.mere.pk), Beneficiaire.objects.get(pk=self.fils.pk)
        self.assertNotEqual(m.nom, "DURANDEAU")
        self.assertEqual(m.nom, f.nom)                                   # la famille garde un même nom
        self.assertNotEqual(m.prenom, "Lucie")
        self.assertEqual((m.nir, m.email, m.telephone_mobile), ("", "", ""))
        self.assertNotIn("Réelle", m.adresse)
        self.assertEqual(m.ville, "Port-de-Bouc")                        # la commune reste (statistiques)
        self.assertLessEqual(abs((m.date_naissance - date(1990, 6, 15)).days), 45)
        self.assertNotIn("DURANDEAU", CreneauRdv.objects.get(pk=self.rdv.pk).description)
        self.assertNotIn("Réel", LienFamilial.objects.get().commentaire)
        d = DocumentGED.objects.get(pk=self.doc.pk)
        self.assertNotIn("DURANDEAU", d.titre)
        self.assertTrue(d.seaweedfs_id.startswith("anonymise-"))        # détaché du vrai fichier
        a = User.objects.get(pk=self.agent.pk)
        self.assertEqual((a.username, a.email, a.has_usable_password()), (f"agent{a.pk}", f"agent{a.pk}@cid.invalid", False))
        self.assertTrue(User.objects.get(pk=self.su.pk).check_password("x"))   # super-administrateur conservé
        self.assertEqual(MDS.objects.get().adresse, "1 rue A")           # paramétrage intact
