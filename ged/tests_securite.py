# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# ged/tests_securite.py
"""Analyse de sécurité du 6/11/2026 : pièces jointes de messages, contrôles de dépôt dans la messagerie,
validation d'un document. Fichiers et personnes fictifs ; stockage temporaire."""
import tempfile
from datetime import date
from io import StringIO
from unittest import mock

from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase

from beneficiaire.models import Beneficiaire
from core.models import Profil, User
from ged.models import DocumentGED, DocumentType
from ged.storage import SeaweedFSStorage
from mds.models import MDS, UserMDSProfile
from messagerie.models import Message

PDF = b"%PDF-1.4 piece jointe fictive"


def _stockage_temporaire():
    s = SeaweedFSStorage()
    s.use_pcloud, s.use_temporary, s.temp_dir = False, True, tempfile.mkdtemp()
    return s


class SecuriteTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.p = mock.patch("ged.models.SeaweedFSStorage", side_effect=_stockage_temporaire)
        self.p.start()
        self.addCleanup(self.p.stop)
        self.m1 = MDS.objects.create(code_mds="TG1", nom="MDS UN", adresse="1 rue A", code_postal="13110", ville="Port-de-Bouc")
        self.m2 = MDS.objects.create(code_mds="TG2", nom="MDS DEUX", adresse="1 rue B", code_postal="13500", ville="Martigues")
        self.a = self.agent("alice", self.m1)
        self.b = self.agent("bastien", self.m1)
        self.intrus = self.agent("hugo", self.m1)          # même MDS, mais pas dans la conversation
        self.cadre1 = self.agent("chef1", self.m1, "MDS_RESPONSABLE")
        self.cadre2 = self.agent("chef2", self.m2, "MDS_RESPONSABLE")

    def agent(self, login, mds, profil="MDS_AGENTS_SOCIAUX"):
        u = User.objects.create_user(login, password="x", matricule=login.upper())
        u.profils.add(Profil.objects.get(code=profil))
        UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True)
        return u

    def client_de(self, u):
        c = Client(HTTP_HOST="localhost")
        c.force_login(u)
        return c

    def test_piece_jointe_d_un_message_reservee_aux_participants(self):
        c = self.client_de(self.a)
        c.post("/messagerie/nouveau/", {"destinataire": self.b.pk, "objet": "Coordination", "contenu": "Texte fictif",
                                       "nouveaux_fichiers": SimpleUploadedFile("note.pdf", PDF)})
        doc = DocumentGED.objects.get()
        self.assertIsInstance(doc.content_object, Message)
        self.assertTrue(doc.peut_etre_vu_par(self.a))
        self.assertTrue(doc.peut_etre_vu_par(self.b))
        self.assertFalse(doc.peut_etre_vu_par(self.intrus))          # avant : vu par tout agent (pas de MDS)
        self.assertEqual(self.client_de(self.intrus).get(f"/ged/documents/{doc.pk}/download/").status_code, 403)
        # l'intrus ne peut pas non plus la joindre à son propre message
        self.client_de(self.intrus).post("/messagerie/nouveau/", {"destinataire": self.a.pk, "objet": "x",
                                                                 "contenu": "y", "documents_ged": [doc.pk]})
        self.assertFalse(Message.objects.get(expediteur=self.intrus).pieces_jointes.exists())

    def test_messagerie_applique_les_regles_de_la_ged(self):
        c = self.client_de(self.a)
        r = c.post("/messagerie/nouveau/", {"destinataire": self.b.pk, "objet": "Script", "contenu": "x",
                                           "nouveaux_fichiers": SimpleUploadedFile("outil.exe", b"MZ fictif")}, follow=True)
        self.assertContains(r, "non autorisée")
        self.assertFalse(Message.objects.exists())                  # rien d'envoyé, rien de déposé
        self.assertFalse(DocumentGED.objects.exists())
        gros = SimpleUploadedFile("gros.pdf", b"%PDF" + b"0" * (11 * 1024 * 1024))
        r = c.post("/messagerie/nouveau/", {"destinataire": self.b.pk, "objet": "Gros", "contenu": "x",
                                           "nouveaux_fichiers": gros}, follow=True)
        self.assertContains(r, "trop volumineux")
        self.assertFalse(Message.objects.exists())
        # réponse : mêmes règles
        m = Message.objects.create(expediteur=self.b, destinataire=self.a, objet="Q", contenu="?", cree_par=self.b)
        c.post(f"/messagerie/repondre/{m.pk}/", {"contenu": "R", "nouveaux_fichiers": SimpleUploadedFile("page.html", b"<p>")})
        self.assertEqual(Message.objects.count(), 1)
        c.post(f"/messagerie/repondre/{m.pk}/", {"contenu": "R", "nouveaux_fichiers": SimpleUploadedFile("ok.pdf", PDF)})
        self.assertEqual(Message.objects.get(reponse_a=m).pieces_jointes.count(), 1)

    def test_validation_controle_la_mds(self):
        usager = Beneficiaire.objects.create(code_interne="TG-1", civilite="MME", nom="ESSAI", prenom="Lina",
                                             date_naissance=date(1990, 1, 1), adresse="1 rue", code_postal="13110",
                                             ville="Port-de-Bouc", mds=self.m1)
        t = DocumentType.objects.create(code="T", nom="Pièce", categorie="divers")
        doc = DocumentGED.objects.create(content_type=ContentType.objects.get_for_model(Beneficiaire), object_id=usager.pk,
                                         type_document=t, titre="Pièce fictive", seaweedfs_id="x", extension="pdf")
        url = f"/ged/documents/{doc.pk}/validate/"
        self.assertEqual(Client(HTTP_HOST="localhost").post(url).status_code, 302)      # pas connecté → connexion
        self.assertEqual(self.client_de(self.cadre1).get(url).status_code, 405)         # POST seulement
        self.assertEqual(self.client_de(self.cadre2).post(url).status_code, 403)        # autre MDS
        self.assertEqual(self.client_de(self.a).post(url).status_code, 403)             # pas cadre
        self.client_de(self.cadre1).post(url)
        doc.refresh_from_db()
        self.assertEqual(doc.statut, "VALIDE")

    def test_extensions_ecrites_avec_un_point(self):
        from ged.validation import erreurs_fichier
        t = DocumentType(extensions_autorisees=[".PDF", "docx"], taille_max_mb=1)
        self.assertEqual(erreurs_fichier(SimpleUploadedFile("a.pdf", PDF), t), [])
        self.assertTrue(erreurs_fichier(SimpleUploadedFile("a.svg", b"<svg/>"), DocumentType(extensions_autorisees=[])))
