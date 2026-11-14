# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/tests_notes_personnelles.py
"""Notes personnelles du journal : privées à leur auteur, transmission décidée note par note, suppression libre. Données fictives."""
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase

from beneficiaire.models import Beneficiaire
from beneficiaire.models_journal import NotePersonnelle
from beneficiaire.transfert import transferer
from core.models import Profil, User
from mds.models import MDS, UserMDSProfile


class NotesPersonnellesTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.origine = MDS.objects.create(code_mds="NP1", nom="MDS ORIGINE", adresse="1 rue A", code_postal="13110", ville="Port-de-Bouc")
        self.accueil = MDS.objects.create(code_mds="NP2", nom="MDS ACCUEIL", adresse="1 rue B", code_postal="13500", ville="Martigues")
        self.ts = self.agent("ts", self.origine)
        self.collegue = self.agent("collegue", self.origine)
        self.cadre = self.agent("cadre", self.origine, cadre=True)
        self.nouveau = self.agent("nouveau", self.accueil)
        self.b = Beneficiaire.objects.create(code_interne="NP-1", civilite="MME", nom="ESSAI", prenom="Nora",
                                             date_naissance=date(1985, 4, 2), adresse="5 rue E", code_postal="13110",
                                             ville="Port-de-Bouc", mds=self.origine)

    def agent(self, login, mds, cadre=False):
        u = User.objects.create_user(login, password="x", matricule=login.upper(), first_name=login.title())
        u.profils.add(Profil.objects.get(code="MDS_AGENTS_SOCIAUX"))
        UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True, peut_gerer_utilisateurs=cadre)
        return u

    def client_de(self, u):
        c = Client(HTTP_HOST="localhost")
        c.force_login(u)
        return c

    def noter(self, user, contenu="Note fictive", transmettre=False):
        data = {"contenu": contenu}
        if transmettre:
            data["a_transmettre"] = "oui"
        return self.client_de(user).post(f"/beneficiaire/{self.b.code_interne}/journal/note/", data)

    def test_note_datee_et_saisie_par_la_mds(self):
        self.noter(self.ts, "Demande de logement en 08/26")
        n = NotePersonnelle.objects.get()
        self.assertEqual(n.auteur, self.ts)
        self.assertIsNotNone(n.date_note)
        self.assertFalse(n.a_transmettre)

    def test_saisie_refusee_hors_mds(self):
        self.noter(self.nouveau, "Intrusion")
        self.assertFalse(NotePersonnelle.objects.exists())

    def test_note_privee_a_son_auteur(self):
        self.noter(self.ts, "Secret du TS")
        url = f"/beneficiaire/{self.b.code_interne}/journal/"
        self.assertContains(self.client_de(self.ts).get(url), "Secret du TS")
        self.assertNotContains(self.client_de(self.collegue).get(url), "Secret du TS")

    def test_transfert_applique_le_choix_de_chaque_note(self):
        self.noter(self.ts, "Transmise", transmettre=True)
        self.noter(self.ts, "Gardée")
        transferer(self.b, [self.b], self.accueil, self.cadre)
        transmise = NotePersonnelle.objects.get(contenu="Transmise")
        gardee = NotePersonnelle.objects.get(contenu="Gardée")
        self.assertEqual(transmise.transmise_a_mds, self.accueil)
        self.assertIsNotNone(transmise.transmise_le)
        self.assertIsNone(gardee.transmise_a_mds)
        self.assertTrue(transmise.peut_lire(self.nouveau))
        self.assertFalse(gardee.peut_lire(self.nouveau))
        self.assertFalse(gardee.peut_lire(self.collegue))

    def test_suppression_independante_du_transfert(self):
        self.noter(self.ts, "À supprimer", transmettre=True)
        transferer(self.b, [self.b], self.accueil, self.cadre)
        n = NotePersonnelle.objects.get()
        self.client_de(self.ts).post(f"/beneficiaire/journal/note/{n.pk}/supprimer/")
        self.assertFalse(NotePersonnelle.objects.exists())

    def test_seul_l_auteur_modifie_ou_supprime(self):
        self.noter(self.ts, "Pas touche")
        n = NotePersonnelle.objects.get()
        self.client_de(self.collegue).post(f"/beneficiaire/journal/note/{n.pk}/supprimer/")
        self.client_de(self.collegue).post(f"/beneficiaire/journal/note/{n.pk}/transmission/", {"a_transmettre": "oui"})
        n.refresh_from_db()
        self.assertFalse(n.a_transmettre)
        self.assertTrue(NotePersonnelle.objects.exists())

    def test_auteur_garde_ses_notes_apres_transfert(self):
        self.noter(self.ts, "Après transfert")
        transferer(self.b, [self.b], self.accueil, self.cadre)
        r = self.client_de(self.ts).get("/beneficiaire/journal/mes-notes/")
        self.assertContains(r, "Après transfert")
