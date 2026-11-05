# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/tests/test_journal.py
"""Journal d'activité : consultations (dédoublonnées), modifications avec avant / après (champs sensibles masqués),
exports, accès au journal, purge. Données fictives."""
from datetime import date, timedelta
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase
from django.utils import timezone

from beneficiaire.models import Beneficiaire
from core import journal
from core.models import AuditLog, Profil, User
from core.utilisateur_courant import _utilisateur
from mds.models import MDS, UserMDSProfile


class JournalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        cls.mds = MDS.objects.create(code_mds="J1", nom="MDS Journal", adresse="1 rue A", code_postal="13000", ville="Exemple")
        cls.autre = MDS.objects.create(code_mds="J2", nom="MDS Autre", adresse="2 rue B", code_postal="13000", ville="Exemple")

        def compte(nom, profil, mds):
            u = User.objects.create_user(nom, password="x", first_name=nom, matricule=nom.upper())
            u.profils.add(Profil.objects.get(code=profil))
            UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True)
            return u
        cls.ts = compte("ts_j", "MDS_AGENTS_SOCIAUX", cls.mds)
        cls.cadre = compte("cadre_j", "MDS_RESPONSABLE", cls.mds)
        cls.cadre_autre = compte("cadre_k", "MDS_RESPONSABLE", cls.autre)
        cls.b = Beneficiaire.objects.create(code_interne="J-AAA", civilite="MME", nom="ESSAI", prenom="Lucie",
                                            date_naissance=date(1990, 1, 1), adresse="3 rue C", code_postal="13000",
                                            ville="Exemple", mds=cls.mds, nir="290017500000000")

    def test_consultation_dedoublonnee(self):
        cl = Client(HTTP_HOST="localhost")
        cl.force_login(self.ts)
        cl.get(f"/beneficiaire/{self.b.code_interne}/")
        cl.get(f"/beneficiaire/{self.b.code_interne}/")
        self.assertEqual(AuditLog.objects.filter(action="READ", beneficiaire=self.b).count(), 1)

    def test_modification_avant_apres_et_nir_masque(self):
        jeton = _utilisateur.set(self.ts)
        try:
            self.b.ville, self.b.nir = "Autre ville", "190017500000000"
            self.b.save()
        finally:
            _utilisateur.reset(jeton)
        log = AuditLog.objects.get(action="UPDATE", beneficiaire=self.b)
        ch = log.details["changements"]
        self.assertEqual((ch["ville"]["avant"], ch["ville"]["apres"]), ("Exemple", "Autre ville"))
        self.assertEqual(ch["nir"]["apres"], "(masqué)")
        self.assertNotIn("190017500000000", str(log.details))

    def test_scripts_non_journalises(self):
        self.b.ville = "Sans agent"
        self.b.save()   # aucun agent connecté (scripts d'installation, démo)
        self.assertFalse(AuditLog.objects.filter(action="UPDATE").exists())

    def test_acces_au_journal(self):
        journal.journaliser("READ", "Consultation", objet=self.b, user=self.ts)
        cl = Client(HTTP_HOST="localhost")
        cl.force_login(self.ts)
        self.assertEqual(cl.get("/journal-activite/").status_code, 403)
        cl.force_login(self.cadre)
        r = cl.get(f"/journal-activite/?beneficiaire={self.b.code_interne}")
        self.assertContains(r, "ESSAI")
        r = cl.get("/journal-activite/?export=csv")
        self.assertIn("Consultation", r.content.decode())
        cl.force_login(self.cadre_autre)
        self.assertNotContains(cl.get(f"/journal-activite/?beneficiaire={self.b.code_interne}"), "Lucie</a>")

    def test_purge(self):
        ancien = journal.journaliser("READ", "Ancienne consultation", objet=self.b, user=self.ts)
        AuditLog.objects.filter(pk=ancien.pk).update(timestamp=timezone.now() - timedelta(days=400))
        journal.journaliser("READ", "Récente", objet=self.b, user=self.ts)
        self.assertEqual(journal.purger(), 1)
        self.assertEqual(AuditLog.objects.count(), 1)
