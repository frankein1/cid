# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/tests/test_conservation.py
"""Durées de conservation : modèle CSV pour le DPO, import tout-ou-rien, application (usagers, journal, annuaire,
expulsions). Données fictives."""
from datetime import date, timedelta
from decimal import Decimal

from django.test import Client, TestCase
from django.utils import timezone

from core import conservation as C
from core.models import AuditLog, Configuration, DureeConservation, User


def csv(*lignes):
    tete = ";".join(C.COLONNES)
    corps = []
    for code, base, depart, arch, sort in lignes:
        corps.append(";".join([code, "", "", "", "", "", base, depart, arch, sort, "", ""]))
    return ("﻿" + "\n".join([tete] + corps)).encode("utf-8")


class ConservationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("adm", password="x", matricule="ADM")

    def test_modele_csv_et_valeurs_par_defaut(self):
        texte = C.modele_csv()
        self.assertTrue(texte.startswith("﻿code;traitement"))
        self.assertIn("USAGER_DOSSIER;Dossier usager;", texte)
        self.assertEqual(texte.count("\n"), len(C.TRAITEMENTS) + 1)
        self.assertEqual((C.mois("USAGER_DOSSIER"), C.mois("USAGER_DOSSIER", "archivage")), (36, 12))
        self.assertIsNone(C.mois("EXPULSION_DOSSIER"))

    def test_import_tout_ou_rien(self):
        n, erreurs = C.importer(csv(("USAGER_DOSSIER", "24", "dernière activité", "6", "suppression"),
                                    ("JOURNAL_ACTIVITE", "2 ans", "", "", "")), self.admin)
        self.assertEqual(n, 0)
        self.assertIn("n'est pas un nombre entier de mois", erreurs[0])
        self.assertFalse(DureeConservation.objects.exists())               # rien d'enregistré
        n, erreurs = C.importer(csv(("USAGER_DOSSIER", "24", "dernière activité", "6", "Suppression"),
                                    ("EXPULSION_DOSSIER", "60", "clôture", "", "anonymisation"),
                                    ("IP", "", "", "", "")), self.admin)        # ligne vide : CID garde son réglage
        self.assertEqual((n, erreurs), (2, []))
        self.assertEqual((C.mois("USAGER_DOSSIER"), C.mois("USAGER_DOSSIER", "archivage")), (24, 6))
        self.assertEqual(C.sort_final("EXPULSION_DOSSIER"), "ANONYMISATION")
        self.assertEqual(C.mois("IP"), 36)
        _, erreurs = C.importer(csv(("INCONNU", "1", "", "", "")), self.admin)
        self.assertIn("inconnu", erreurs[0])

    def test_priorite_valeur_importee_puis_ancienne_cle(self):
        from beneficiaire import archivage
        Configuration.objects.create(cle="RGPD_ARCHIVAGE_ANS", valeur="2")
        self.assertEqual(archivage.delai_archivage_mois(), 24)
        DureeConservation.objects.create(code="USAGER_DOSSIER", base_active_mois=18)
        self.assertEqual(archivage.delai_archivage_mois(), 18)

    def test_recherches_annuaire_purgees_plus_tot(self):
        from core import journal
        DureeConservation.objects.create(code="ANNUAIRE_RECHERCHES", base_active_mois=3)
        vieux = timezone.now() - timedelta(days=150)
        for desc in ("Annuaire des usagers : recherche", "Consultation : dossier"):
            a = AuditLog.objects.create(action="READ", description=desc)
            AuditLog.objects.filter(pk=a.pk).update(timestamp=vieux)
        journal.purger()
        self.assertEqual(list(AuditLog.objects.values_list("description", flat=True)), ["Consultation : dossier"])

    def test_admin_import_et_modele(self):
        c = Client(HTTP_HOST="localhost")
        c.force_login(self.admin)
        self.assertEqual(c.get("/admin/core/dureeconservation/").status_code, 200)
        self.assertEqual(DureeConservation.objects.count(), len(C.TRAITEMENTS))
        r = c.get("/admin/core/dureeconservation/modele.csv")
        self.assertIn("text/csv", r["Content-Type"])
        from django.core.files.uploadedfile import SimpleUploadedFile
        r = c.post("/admin/core/dureeconservation/importer/",
                   {"fichier": SimpleUploadedFile("d.csv", csv(("JOURNAL_ACTIVITE", "6", "", "", "")))})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(DureeConservation.objects.get(code="JOURNAL_ACTIVITE").base_active_mois, 6)


class ExpulsionsConservationTests(TestCase):
    def setUp(self):
        from logement.models import DossierExpulsion as D, EtapeExpulsion
        from mds.models import MDS
        self.mds = MDS.objects.create(code_mds="CO1", nom="MDS ESSAI", adresse="1 rue A", code_postal="13110",
                                      ville="Port-de-Bouc")
        j = timezone.localdate()
        self.vieux = D.objects.create(nom="ESSAI", prenom="Clara", adresse="3 rue C", mds=self.mds, dette=Decimal("900"),
                                      numero_allocataire="0000001", statut=D.CLOS, date_cloture=j - timedelta(days=800),
                                      caf={"qf": "500"})
        EtapeExpulsion.objects.create(dossier=self.vieux, type_etape="JUGEMENT", date=j - timedelta(days=900),
                                      commentaire="Commentaire nominatif fictif")
        self.recent = D.objects.create(nom="RECENT", statut=D.CLOS, date_cloture=j - timedelta(days=30), mds=self.mds)
        self.ouvert = D.objects.create(nom="OUVERT", mds=self.mds)

    def regle(self, sort):
        DureeConservation.objects.create(code="EXPULSION_DOSSIER", base_active_mois=12, archivage_mois=12,
                                         sort_final=sort)

    def test_rien_sans_duree(self):
        from logement.services.conservation import purger
        self.assertEqual(purger(), {'pieces': 0, 'dossiers': 0, 'a_verser': 0})

    def test_anonymisation(self):
        from logement.services.conservation import purger
        self.regle("ANONYMISATION")
        self.assertEqual(purger()["dossiers"], 1)
        self.vieux.refresh_from_db()
        self.assertEqual((self.vieux.nom, self.vieux.adresse, self.vieux.numero_allocataire, self.vieux.caf),
                         ("ANONYME", "", "", {}))
        self.assertEqual((self.vieux.dette, self.vieux.ville), (Decimal("900.00"), ""))
        self.assertEqual(self.vieux.etapes.get().commentaire, "")
        self.assertEqual(self.vieux.etapes.count(), 1)                   # les étapes restent (statistiques)
        self.recent.refresh_from_db()
        self.assertEqual(self.recent.nom, "RECENT")
        self.assertEqual(purger()["dossiers"], 0)                        # déjà anonymisé

    def test_suppression_et_versement(self):
        from logement.models import DossierExpulsion as D
        from logement.services.conservation import a_verser, purger
        self.regle("ARCHIVES")
        self.assertEqual(purger()["a_verser"], 1)
        self.assertEqual(list(a_verser()), [self.vieux])
        DureeConservation.objects.filter(code="EXPULSION_DOSSIER").update(sort_final="SUPPRESSION")
        purger()
        self.assertEqual(set(D.objects.values_list("nom", flat=True)), {"RECENT", "OUVERT"})
