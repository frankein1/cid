# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# ged/tests_chiffrement.py
"""Chiffrement des fichiers de la GED : format, clés, rotation, stockage, migration des anciens fichiers.
Contenus fictifs ; clés tirées au hasard pour les tests (jamais une vraie clé)."""
import base64
import os
import tempfile
from io import StringIO
from unittest import mock

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import Client, TestCase

from core.models import User
from ged import chiffrement as ch
from ged.models import DocumentGED, DocumentType, DocumentVersion
from ged.storage import SeaweedFSStorage

CLE = base64.b64encode(os.urandom(32)).decode()
CLE2 = base64.b64encode(os.urandom(32)).decode()
SANS = {"GED_CLE_MAITRESSE": "", "GED_CLES_ANCIENNES": "", "GED_KMS": "", "GED_CLE_ID": ""}
AVEC = {**SANS, "GED_CLE_MAITRESSE": CLE}
CONTENU = b"%PDF-1.4 attestation fictive de test " * 50


class FormatTests(TestCase):
    @mock.patch.dict(os.environ, AVEC)
    def test_aller_retour(self):
        c = ch.chiffrer(CONTENU)
        self.assertTrue(ch.est_chiffre(c))
        self.assertNotIn(b"attestation", c)
        self.assertEqual(ch.dechiffrer(c), CONTENU)
        self.assertNotEqual(ch.chiffrer(CONTENU), c)            # une clé et un nonce neufs à chaque fois
        self.assertEqual(ch.lire_entete(c)["kid"], "k1")

    @mock.patch.dict(os.environ, AVEC)
    def test_alteration_refusee(self):
        c = bytearray(ch.chiffrer(CONTENU))
        c[-5] ^= 1                                               # contenu modifié
        with self.assertRaises(ch.ErreurChiffrement):
            ch.dechiffrer(bytes(c))
        c = ch.chiffrer(CONTENU).replace(b'"kid":"k1"', b'"kid":"k2"')   # en-tête modifié
        with self.assertRaises(ch.ErreurChiffrement):
            ch.dechiffrer(c)

    def test_ancien_fichier_en_clair(self):
        self.assertEqual(ch.dechiffrer(CONTENU), CONTENU)

    def test_mauvaise_cle(self):
        with mock.patch.dict(os.environ, AVEC):
            c = ch.chiffrer(CONTENU)
        with mock.patch.dict(os.environ, {**SANS, "GED_CLE_MAITRESSE": CLE2}):
            with self.assertRaises(ch.ErreurChiffrement):
                ch.dechiffrer(c)
        with mock.patch.dict(os.environ, SANS):
            with self.assertRaises(ch.ErreurChiffrement):
                ch.dechiffrer(c)

    def test_rotation(self):
        with mock.patch.dict(os.environ, AVEC):
            ancien = ch.chiffrer(CONTENU)
        with mock.patch.dict(os.environ, {**SANS, "GED_CLE_MAITRESSE": CLE2, "GED_CLE_ID": "k2",
                                          "GED_CLES_ANCIENNES": f"k1:{CLE}"}):
            self.assertEqual(ch.dechiffrer(ancien), CONTENU)
            self.assertEqual(ch.lire_entete(ch.chiffrer(CONTENU))["kid"], "k2")

    def test_cle_invalide(self):
        with mock.patch.dict(os.environ, {**SANS, "GED_CLE_MAITRESSE": base64.b64encode(b"court").decode()}):
            self.assertFalse(ch.actif())

    def test_openbao(self):
        cle = os.urandom(32)
        env = {**SANS, "GED_KMS": "openbao", "OPENBAO_ADDR": "https://kms.exemple.test", "OPENBAO_TOKEN": "t"}

        def repondre(url, json, **kw):
            r = mock.Mock(status_code=200)
            if "/datakey/plaintext/cid-ged" in url:
                r.json.return_value = {"data": {"plaintext": base64.b64encode(cle).decode(), "ciphertext": "vault:v1:xx"}}
            else:
                self.assertEqual(json, {"ciphertext": "vault:v1:xx"})
                r.json.return_value = {"data": {"plaintext": base64.b64encode(cle).decode()}}
            return r
        with mock.patch.dict(os.environ, env), mock.patch("ged.chiffrement.requests.post", side_effect=repondre) as p:
            c = ch.chiffrer(CONTENU)
            self.assertEqual(ch.lire_entete(c)["kms"], "openbao")
            self.assertEqual(ch.dechiffrer(c), CONTENU)
            self.assertEqual(p.call_args.kwargs["headers"], {"X-Vault-Token": "t"})


class StockageTests(TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp()

    def stockage(self):
        s = SeaweedFSStorage()
        s.use_pcloud, s.use_temporary, s.temp_dir = False, True, self.dossier
        return s

    @mock.patch.dict(os.environ, AVEC)
    def test_depot_chiffre_lecture_en_clair(self):
        s = self.stockage()
        fid = s.save("piece.pdf", ContentFile(CONTENU))
        self.assertTrue(ch.est_chiffre(s.open_brut(fid)))      # sur le disque : illisible
        self.assertEqual(s.open(fid).read(), CONTENU)          # pour CID : en clair

    @mock.patch.dict(os.environ, SANS)
    def test_sans_cle_en_clair(self):
        s = self.stockage()
        fid = s.save("piece.pdf", ContentFile(CONTENU))
        self.assertEqual(s.open_brut(fid), CONTENU)

    def test_migration_des_anciens_fichiers(self):
        u = User.objects.create_user("ts", password="x", matricule="TS")
        t = DocumentType.objects.create(code="T", nom="Pièce", categorie=DocumentType._meta.get_field("categorie").choices[0][0])
        s = self.stockage()
        with mock.patch.dict(os.environ, SANS):
            fid = s.save("piece.pdf", ContentFile(CONTENU))       # déposé avant l'activation
        doc = DocumentGED.objects.create(content_type=ContentType.objects.get_for_model(User), object_id=u.pk,
                                         type_document=t, titre="Pièce", seaweedfs_id=fid, extension="pdf")
        DocumentVersion.objects.create(document=doc, numero=1, seaweedfs_id=fid, extension="pdf",
                                       taille_octets=len(CONTENU), hash_md5="x")
        with mock.patch.dict(os.environ, AVEC), mock.patch("ged.management.commands.chiffrer_ged.SeaweedFSStorage",
                                                          return_value=s):
            out = StringIO()
            call_command("chiffrer_ged", "--essai", stdout=out)
            self.assertIn("1 fichier(s) à chiffrer", out.getvalue())
            self.assertEqual(DocumentVersion.objects.get().seaweedfs_id, fid)
            call_command("chiffrer_ged", stdout=out)
            v = DocumentVersion.objects.get()
            self.assertNotEqual(v.seaweedfs_id, fid)
            self.assertEqual(DocumentGED.objects.get().seaweedfs_id, v.seaweedfs_id)
            self.assertTrue(ch.est_chiffre(s.open_brut(v.seaweedfs_id)))
            self.assertEqual(s.open(v.seaweedfs_id).read(), CONTENU)
            with self.assertRaises(FileNotFoundError):
                s.open_brut(fid)                                   # l'ancien fichier en clair a disparu
            out = StringIO()
            call_command("chiffrer_ged", stdout=out)                # relance : rien à refaire
            self.assertIn("0 fichier(s) chiffrés, 1 déjà chiffré(s)", out.getvalue())

    def test_page_etat(self):
        su = User.objects.create_superuser("su", password="x", matricule="SU")
        c = Client(HTTP_HOST="localhost")
        c.force_login(su)
        with mock.patch.dict(os.environ, SANS):
            self.assertContains(c.get("/ged/chiffrement/"), "Chiffrement inactif")
        with mock.patch.dict(os.environ, AVEC):
            self.assertContains(c.get("/ged/chiffrement/"), "Chiffrement actif")


class BoutonTests(TestCase):
    def test_bouton_chiffrer_les_anciens(self):
        su = User.objects.create_superuser("su", password="x", matricule="SU")
        c = Client(HTTP_HOST="localhost")
        c.force_login(su)
        with mock.patch.dict(os.environ, AVEC), mock.patch("django.core.management.call_command") as cmd:
            r = c.post("/ged/chiffrement/")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(cmd.call_args.kwargs["max"], 50)
