# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/tests_rgpd.py
"""Archivage RGPD : proposition, masquage, lecture seule, désarchivage, effacement. Données entièrement fictives."""
from datetime import date, time
from io import StringIO

from dateutil.relativedelta import relativedelta
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from beneficiaire import archivage as rgpd
from beneficiaire.models import Beneficiaire, LienFamilial, OperationRGPD
from core.models import Configuration, Profil, User
from mds.models import MDS, UserMDSProfile
from planning.models import CreneauRdv


class RGPDTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        cls.mds = MDS.objects.create(code_mds="T1", nom="MDS Essai", adresse="1 rue A", code_postal="13000", ville="Exemple")
        cls.mds_b = MDS.objects.create(code_mds="T2", nom="MDS Autre", adresse="2 rue B", code_postal="13000", ville="Exemple")

        def compte(nom, profil, mds):
            u = User.objects.create_user(nom, password="x", first_name=nom, matricule=nom.upper())
            u.profils.add(Profil.objects.get(code=profil))
            UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True)
            return u
        cls.cadre = compte("cadre", "MDS_RESPONSABLE", cls.mds)
        cls.cadre_b = compte("cadre_b", "MDS_RESPONSABLE", cls.mds_b)
        cls.ts = compte("ts", "MDS_AGENTS_SOCIAUX", cls.mds)
        cls.admin = User.objects.create_superuser("su", password="x", matricule="SU")

    def setUp(self):
        self.c = Client(HTTP_HOST="localhost")

    def usager(self, code, inactif_mois=0, mds=None):
        b = Beneficiaire.objects.create(code_interne=code, civilite="MME", nom="ESSAI", prenom="Lucie",
                                        date_naissance=date(1980, 1, 1), adresse="3 rue C", code_postal="13000",
                                        ville="Exemple", mds=mds or self.mds)
        if inactif_mois:
            ancien = timezone.now() - relativedelta(months=inactif_mois)
            Beneficiaire.tous.filter(pk=b.pk).update(date_creation=ancien, date_modification=ancien)
            b.refresh_from_db()
        return b

    def test_proposition(self):
        vieux = self.usager("T-VIEUX", 40)
        recent = self.usager("T-RECENT", 10)
        ailleurs = self.usager("T-AILLEURS", 40, self.mds_b)
        ids = [b.pk for b, _ in rgpd.candidats({self.mds.pk})]
        self.assertEqual(ids, [vieux.pk])
        self.assertNotIn(recent.pk, ids)
        self.assertNotIn(ailleurs.pk, ids)

    def test_activite_recente_ailleurs_dans_le_dossier(self):
        vieux = self.usager("T-VIEUX", 40)
        CreneauRdv.objects.create(date=timezone.localdate() - relativedelta(months=5), heure_debut=time(9),
                                  heure_fin=time(9, 30), beneficiaire=vieux, mds=self.mds, statut="VENU_RECU")
        self.assertEqual(rgpd.candidats({self.mds.pk}), [])

    def test_jamais_si_suivi_enfance(self):
        vieux = self.usager("T-VIEUX", 40)
        rdv = CreneauRdv.objects.create(date=timezone.localdate(), heure_debut=time(9), heure_fin=time(9, 30),
                                        beneficiaire=vieux, mds=self.mds, domaine="ENFANCE")
        CreneauRdv.objects.filter(pk=rdv.pk).update(date=timezone.localdate() - relativedelta(years=4),
                                                    date_creation=timezone.now() - relativedelta(years=4),
                                                    date_modification=timezone.now() - relativedelta(years=4))
        self.assertEqual(rgpd.candidats({self.mds.pk}), [])
        with self.assertRaises(rgpd.ErreurRGPD):
            rgpd.archiver(vieux, self.cadre, "FIN_SUIVI")

    def test_delai_reglable(self):
        self.usager("T-VIEUX", 30)
        self.assertEqual(rgpd.candidats({self.mds.pk}), [])
        Configuration.objects.create(cle="RGPD_ARCHIVAGE_ANS", valeur="2", type_valeur="INTEGER")
        self.assertEqual(len(rgpd.candidats({self.mds.pk})), 1)

    def test_archivage_masque_et_lecture_seule(self):
        vieux = self.usager("T-VIEUX", 40)
        enfant = self.usager("T-ENFANT")
        LienFamilial.objects.create(personne_a=enfant, personne_b=vieux, type_lien="PARENT",
                                    date_debut=date.today() - relativedelta(years=5))  # lien ancien
        self.c.force_login(self.cadre)
        r = self.c.post(reverse("beneficiaire:rgpd_archiver"), {"ids": [vieux.pk], "motif": "FIN_SUIVI"})
        self.assertEqual(r.status_code, 302)
        vieux = Beneficiaire.tous.get(pk=vieux.pk)
        self.assertEqual((vieux.statut, vieux.statut_avant_archivage, vieux.archive_par), ("ARCHIVE", "ACTIF", self.cadre))
        self.assertFalse(Beneficiaire.objects.filter(pk=vieux.pk).exists())          # masqué partout
        self.c.force_login(self.ts)
        self.assertEqual(self.c.get(reverse("beneficiaire:detail_beneficiaire", args=["T-VIEUX"])).status_code, 404)
        self.assertFalse(vieux.peut_etre_modifie_par(self.admin))                      # lecture seule
        self.assertEqual([m["personne"] for m in enfant.reseau_familial()], [])        # absent du réseau familial
        op = OperationRGPD.objects.get(action=OperationRGPD.ARCHIVAGE)
        self.assertEqual((op.mds, op.par, op.motif), (self.mds, self.cadre, "FIN_SUIVI"))

    def test_archiver_refuse_hors_proposition(self):
        recent = self.usager("T-RECENT", 2)
        ailleurs = self.usager("T-AILLEURS", 40, self.mds_b)
        self.c.force_login(self.cadre)
        self.c.post(reverse("beneficiaire:rgpd_archiver"), {"ids": [recent.pk, ailleurs.pk], "motif": "FIN_SUIVI"})
        self.assertEqual(Beneficiaire.tous.filter(statut="ARCHIVE").count(), 0)

    def test_droits(self):
        self.c.force_login(self.ts)
        self.assertEqual(self.c.get(reverse("beneficiaire:rgpd_archivage")).status_code, 403)
        self.c.force_login(self.cadre)
        self.assertEqual(self.c.get(reverse("beneficiaire:rgpd_archivage")).status_code, 200)
        self.assertEqual(self.c.get(reverse("beneficiaire:rgpd_effacement")).status_code, 403)
        vieux = self.usager("T-VIEUX", 40, self.mds_b)
        rgpd.archiver(vieux, self.cadre_b, "FIN_SUIVI")
        self.assertEqual(self.c.get(reverse("beneficiaire:rgpd_dossier", args=["T-VIEUX"])).status_code, 403)

    def test_desarchivage(self):
        vieux = self.usager("T-VIEUX", 40)
        Beneficiaire.tous.filter(pk=vieux.pk).update(statut="SORTI")
        vieux.refresh_from_db()
        rgpd.archiver(vieux, self.cadre, "FIN_SUIVI")
        self.c.force_login(self.cadre)
        r = self.c.get(reverse("beneficiaire:rgpd_dossier", args=["T-VIEUX"]))
        self.assertContains(r, 'id="bandeau-archive"')
        r = self.c.post(reverse("beneficiaire:rgpd_dossier", args=["T-VIEUX"]), {"motif": "RETOUR"})
        self.assertEqual(Beneficiaire.objects.get(pk=vieux.pk).statut, "SORTI")
        self.assertTrue(OperationRGPD.objects.filter(action=OperationRGPD.DESARCHIVAGE).exists())

    def test_effacement(self):
        vieux = self.usager("T-VIEUX", 40)
        rdv = CreneauRdv.objects.create(date=timezone.localdate() - relativedelta(years=4), heure_debut=time(9),
                                        heure_fin=time(9, 30), beneficiaire=vieux, mds=self.mds)
        ancien = timezone.now() - relativedelta(years=4)
        CreneauRdv.objects.filter(pk=rdv.pk).update(date_creation=ancien, date_modification=ancien)
        rgpd.archiver(vieux, self.cadre, "SANS_NOUVELLES")
        self.assertEqual(list(rgpd.effacables()), [])                                 # trop récent
        Beneficiaire.tous.filter(pk=vieux.pk).update(date_archivage=timezone.now() - relativedelta(months=13))
        self.assertEqual([b.pk for b in rgpd.effacables()], [vieux.pk])
        self.c.force_login(self.admin)
        r = self.c.get(reverse("beneficiaire:rgpd_effacement"))
        self.assertContains(r, "T-VIEUX")
        self.c.post(reverse("beneficiaire:rgpd_effacement"), {"ids": [vieux.pk], "confirmation": "non"})
        self.assertTrue(Beneficiaire.tous.filter(pk=vieux.pk).exists())               # pas confirmé
        self.c.post(reverse("beneficiaire:rgpd_effacement"), {"ids": [vieux.pk], "confirmation": "EFFACER"})
        self.assertFalse(Beneficiaire.tous.filter(pk=vieux.pk).exists())
        trace = OperationRGPD.objects.get(action=OperationRGPD.EFFACEMENT)
        self.assertIsNone(trace.beneficiaire)
        self.assertEqual((trace.mds, trace.motif, trace.par), (self.mds, "SANS_NOUVELLES", self.admin))
        # le RDV rattaché reste dans l'agenda de la MDS (lien SET_NULL), sans l'usager
        self.assertIsNone(CreneauRdv.objects.get(pk=rdv.pk).beneficiaire)
        self.assertIsNone(OperationRGPD.objects.get(action=OperationRGPD.ARCHIVAGE).beneficiaire)

    def test_page_archivage_cadre(self):
        self.usager("T-VIEUX", 40)
        self.c.force_login(self.cadre)
        r = self.c.get(reverse("beneficiaire:rgpd_archivage"))
        self.assertContains(r, "T-VIEUX")
        self.assertNotContains(r, 'id="lien-effacement"')
