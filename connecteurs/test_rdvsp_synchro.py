# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/test_rdvsp_synchro.py
"""
Synchronisation des agendas CID ↔ RDV-Solidarités, avec un RDV-Solidarités SIMULÉ (FauxMRS) qui répond
comme le vrai (formats relevés sur le banc d'essai .github/workflows/essai-rdv-solidarites.yml).
Données entièrement fictives.
"""
import hashlib
import hmac
import json
import os
from datetime import date, datetime, time, timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from beneficiaire.models import Beneficiaire
from connecteurs import rdv_service_public as api
from connecteurs import rdvsp_synchro as sync
from connecteurs.models import (AbsenceRDVSP, AvisRDVSP, CompteRDVSP, LienUsagerRDVSP, MdsRDVSP, MotifRDVSP,
                                ParametresRDVSP, PlageRDVSP, RdvRDVSP)
from core.models import User
from mds.models import MDS, DemiJourneeReception, UserMDSProfile
from planning.models import CreneauRdv, JourBloque

SECRET = "secret-avis-essai"
ENV = {"RDVSP_ACTIF": "1", "RDVSP_URL": "https://mrs.exemple.test", "RDVSP_CLIENT_ID": "cid",
       "RDVSP_CLIENT_SECRET": "s", "RDVSP_SECRET_AVIS": SECRET}


class FauxMRS:
    """Répond comme RDV-Solidarités : identifiants croissants, réponses parfois sans enveloppe."""
    def __init__(self):
        self.appels, self.n = [], 100

    def __call__(self, client, methode, chemin, **kw):
        self.appels.append((methode, chemin, kw.get("json")))
        self.n += 1
        if methode == "DELETE":
            return {}
        if chemin == "/lieux":
            return {"id": self.n, "name": kw["json"]["name"]}              # sans enveloppe (constaté)
        if chemin == "/motifs":
            return {"id": self.n, "name": kw["json"]["name"]}
        if chemin == "/plage_ouvertures":
            return {"plage_ouverture": {"id": self.n}}
        if chemin == "/absences":
            return {"absence": {"id": self.n}}
        return {}

    def faits(self, methode, chemin=None):
        return [a for a in self.appels if a[0] == methode and (chemin is None or a[1].startswith(chemin))]


def signer(corps):
    return hmac.new(SECRET.encode(), corps, hashlib.sha256).hexdigest()


@mock.patch.dict(os.environ, ENV)
class _Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        cls.mds = MDS.objects.create(code_mds="T1", nom="MDS Essai", adresse="1 rue A", code_postal="13110", ville="Port-de-Bouc")
        cls.autre = MDS.objects.create(code_mds="T2", nom="MDS Fermée", adresse="2 rue B", code_postal="13000", ville="Exemple")
        cls.agent = User.objects.create_user("as1", password="x", first_name="Inès", last_name="ESSAI",
                                             email="ines.essai@cid.test", matricule="AS1")
        UserMDSProfile.objects.create(user=cls.agent, mds=cls.mds, actif=True, principale=True)
        cls.admin = User.objects.create_superuser("su", password="x", matricule="SU", email="su@cid.test")
        CompteRDVSP.objects.create(utilisateur=cls.admin, agent_id="1", jeton_acces="A", jeton_renouvellement="R",
                                   expire_le=timezone.now() + timedelta(days=365))
        p = ParametresRDVSP.get()
        p.compte_synchro = cls.admin
        p.save()
        cls.mds_sp = MdsRDVSP.objects.create(mds=cls.mds, organisation_sp_id=7, en_ligne=True)
        MdsRDVSP.objects.create(mds=cls.autre, organisation_sp_id=8, en_ligne=False)
        cls.motif = MotifRDVSP.objects.get_or_create(nom="Renouvellement RSA")[0]
        cls.lundi = DemiJourneeReception.objects.create(agent=cls.agent, mds=cls.mds, jour_semaine=0,
                                                        type_demi_journee="MATIN", heure_debut=time(9),
                                                        heure_fin=time(12))
        DemiJourneeReception.objects.create(agent=cls.agent, mds=cls.autre, jour_semaine=1, type_demi_journee="MATIN",
                                            heure_debut=time(9), heure_fin=time(12))     # MDS non ouverte en ligne
        cls.benef = Beneficiaire.objects.create(code_interne="T-RSA", civilite="MME", nom="ESSAI", prenom="Lucie",
                                                date_naissance=date(1990, 1, 1), adresse="3 rue C",
                                                code_postal="13110", ville="Port-de-Bouc", mds=cls.mds)
        LienUsagerRDVSP.objects.create(beneficiaire=cls.benef, usager_rdvsp_id="55")

    def setUp(self):
        self.mrs = FauxMRS()
        self.p = mock.patch.object(api.Client, "appel", autospec=True, side_effect=self.mrs)
        self.p.start()
        self.addCleanup(lambda: self.p.stop())   # self.p peut être remplacé par une sous-classe

    def publier(self):
        with self.captureOnCommitCallbacks(execute=True):
            return sync.synchroniser()

    def lundi_publie(self):
        return PlageRDVSP.objects.get().premier_jour


@mock.patch.dict(os.environ, ENV)
class SynchroTests(_Base):
    # --- 1. Publication -------------------------------------------------------
    def test_publication(self):
        b = self.publier()
        self.assertEqual((b["publiees"], b["erreurs"]), (1, []))
        lieu = self.mrs.faits("POST", "/lieux")
        self.assertEqual(lieu[0][2]["external_reference"], {"external_id": f"cid-mds-{self.mds.pk}"})
        motif = self.mrs.faits("POST", "/motifs")[0][2]
        self.assertEqual((motif["min_public_booking_delay"], motif["max_public_booking_delay"], motif["bookable_by"]),
                         (48 * 3600, 15 * 86400, "agents_and_prescripteurs_and_invited_users"))
        plage = self.mrs.faits("POST", "/plage_ouvertures")[0][2]
        r = json.loads(plage["recurrence"])
        self.assertEqual((r["every"], r["on"], plage["agent_email"]), ("week", ["monday"], "ines.essai@cid.test"))
        self.assertEqual((plage["start_time"], plage["end_time"]), ("09:00", "12:00"))
        self.assertEqual(plage["motif_external_ids"], [f"cid-motif-{self.motif.pk}-mds-{self.mds.pk}"])
        p = PlageRDVSP.objects.get()
        self.assertEqual(p.premier_jour.weekday(), 0)
        self.assertEqual(p.dernier_jour, p.premier_jour + timedelta(weeks=7))
        self.assertEqual(r["until"], p.dernier_jour.isoformat())
        # Relancée tout de suite : rien à refaire
        self.publier()
        self.assertEqual(len(self.mrs.faits("POST", "/plage_ouvertures")), 1)
        self.assertEqual(len(self.mrs.faits("POST", "/lieux")), 1)

    def test_prolongation(self):
        self.publier()
        p = PlageRDVSP.objects.get()
        with self.captureOnCommitCallbacks(execute=True):
            b = sync.synchroniser(aujourd_hui=p.dernier_jour - timedelta(days=10))
        self.assertEqual(b["prolongees"], 1)
        nouvelle = PlageRDVSP.objects.order_by("-premier_jour").first()
        self.assertEqual(nouvelle.premier_jour, p.dernier_jour + timedelta(days=7))

    def test_retrait_et_modification(self):
        self.publier()
        DemiJourneeReception.objects.filter(pk=self.lundi.pk).update(heure_fin=time(11, 30))
        b = self.publier()
        self.assertEqual((b["neutralisees"], b["publiees"]), (1, 1))
        absence = self.mrs.faits("POST", "/absences")[0][2]
        self.assertEqual(json.loads(absence["recurrence"])["on"], ["monday"])
        self.assertTrue(PlageRDVSP.objects.filter(neutralisee=True).exists())
        self.assertEqual(AbsenceRDVSP.objects.get().raison, AbsenceRDVSP.RETRAIT)

    # --- 2. Blocages ----------------------------------------------------------
    def test_creneau_pris_dans_cid_est_bloque_puis_libere(self):
        self.publier()
        jour = self.lundi_publie()
        with self.captureOnCommitCallbacks(execute=True):
            cr = CreneauRdv.objects.create(date=jour, heure_debut=time(10), heure_fin=time(10, 30), agent=self.agent,
                                           mds=self.mds, statut="RESERVE")
        a = AbsenceRDVSP.objects.get(raison=AbsenceRDVSP.CRENEAU)
        self.assertEqual((a.date, a.heure_debut), (jour, time(10)))
        with self.captureOnCommitCallbacks(execute=True):
            cr.statut = "DISPONIBLE"
            cr.save()
        self.assertFalse(AbsenceRDVSP.objects.exists())
        self.assertEqual(len(self.mrs.faits("DELETE", "/absences")), 1)

    def test_creneau_hors_permanence_publiee_ignore(self):
        self.publier()
        mardi = self.lundi_publie() + timedelta(days=1)
        with self.captureOnCommitCallbacks(execute=True):
            CreneauRdv.objects.create(date=mardi, heure_debut=time(10), heure_fin=time(10, 30), agent=self.agent,
                                      statut="RESERVE")
        self.assertFalse(AbsenceRDVSP.objects.exists())

    def test_jour_bloque(self):
        self.publier()
        with self.captureOnCommitCallbacks(execute=True):
            jb = JourBloque.objects.create(date=self.lundi_publie(), raison=JourBloque.RAISON_CHOICES[0][0])
        self.assertEqual(AbsenceRDVSP.objects.get().raison, AbsenceRDVSP.JOUR_BLOQUE)
        with self.captureOnCommitCallbacks(execute=True):
            jb.delete()
        self.assertFalse(AbsenceRDVSP.objects.exists())

    # --- 3. Retour des RDV ----------------------------------------------------
    def avis(self, rdv_id, debut, statut="unknown", par="user", evenement="created", annule=None):
        corps = json.dumps({"meta": {"model": "Rdv", "event": evenement}, "data": {
            "id": rdv_id, "status": statut, "created_by": par, "created_by_type": "User" if par == "user" else "Agent",
            "starts_at": debut.strftime("%Y-%m-%d %H:%M:%S +0100"),
            "ends_at": (debut + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S +0100"),
            "duration_in_min": 30, "cancelled_at": annule, "organisation": {"id": 7},
            "motif": {"name": "Renouvellement RSA"}, "agents": [{"email": "INES.essai@cid.test"}],
            "users": [{"id": 55}], "lieu": {"name": "MDS Essai"}}}).encode()
        c = Client(HTTP_HOST="localhost")
        with self.captureOnCommitCallbacks(execute=True):
            return c.post(reverse("connecteurs:rdvsp_avis"), corps, content_type="application/json",
                          HTTP_X_LAPIN_SIGNATURE=signer(corps))

    def test_signature_obligatoire(self):
        c = Client(HTTP_HOST="localhost")
        r = c.post(reverse("connecteurs:rdvsp_avis"), b'{"meta":{}}', content_type="application/json",
                   HTTP_X_LAPIN_SIGNATURE="faux")
        self.assertEqual(r.status_code, 403)
        self.assertFalse(AvisRDVSP.objects.exists())

    def test_rdv_en_ligne_plafond_et_annulation(self):
        self.publier()
        jour = self.lundi_publie()
        # créneaux CID disponibles, générés par l'agenda
        for h in (time(9), time(9, 30), time(10)):
            CreneauRdv.objects.create(date=jour, heure_debut=h, heure_fin=(datetime.combine(jour, h) + timedelta(minutes=30)).time(),
                                      agent=self.agent, mds=self.mds, statut="DISPONIBLE")
        d1 = datetime.combine(jour, time(9, 30))
        self.assertEqual(self.avis(901, d1).status_code, 200)
        cr = CreneauRdv.objects.get(date=jour, heure_debut=time(9, 30))
        self.assertEqual((cr.statut, cr.beneficiaire, cr.domaine), ("RESERVE", self.benef, "INSERTION"))
        self.assertIn("réservé en ligne", cr.description)
        self.assertFalse(AbsenceRDVSP.objects.filter(raison=AbsenceRDVSP.CRENEAU).exists())   # pas de boucle
        self.assertFalse(AbsenceRDVSP.objects.filter(raison=AbsenceRDVSP.PLAFOND).exists())
        # 2e RDV en ligne dans la demi-journée → plafond atteint → demi-journée fermée en ligne
        self.avis(902, datetime.combine(jour, time(10)))
        a = AbsenceRDVSP.objects.get(raison=AbsenceRDVSP.PLAFOND)
        self.assertEqual((a.heure_debut, a.heure_fin), (time(9), time(12)))
        # Annulation en ligne → le créneau est annulé, un créneau libre est recréé, la demi-journée rouverte
        self.avis(901, d1, statut="excused", annule=timezone.now().strftime("%Y-%m-%d %H:%M:%S +0100"))
        cr.refresh_from_db()
        self.assertEqual(cr.statut, "ANNULE_USAGER")
        self.assertTrue(CreneauRdv.objects.filter(date=jour, heure_debut=time(9, 30), statut="DISPONIBLE").exists())
        self.assertFalse(AbsenceRDVSP.objects.filter(raison=AbsenceRDVSP.PLAFOND).exists())
        self.assertIsNotNone(RdvRDVSP.objects.get(rdv_sp_id=901).annule_le)

    def test_rdv_pris_par_un_agent_ne_compte_pas_dans_le_plafond(self):
        self.publier()
        jour = self.lundi_publie()
        self.avis(911, datetime.combine(jour, time(9)), par="agent")
        self.avis(912, datetime.combine(jour, time(9, 30)), par="agent")
        self.assertFalse(AbsenceRDVSP.objects.filter(raison=AbsenceRDVSP.PLAFOND).exists())
        self.assertEqual(CreneauRdv.objects.filter(statut="RESERVE").count(), 2)   # créés s'il n'y avait pas de créneau

    def test_usager_inconnu_a_rapprocher(self):
        self.publier()
        corps_avis = self.avis(921, datetime.combine(self.lundi_publie(), time(11)))
        self.assertEqual(corps_avis.status_code, 200)
        LienUsagerRDVSP.objects.all().delete()
        self.avis(922, datetime.combine(self.lundi_publie(), time(11, 30)))
        self.assertTrue(RdvRDVSP.objects.get(rdv_sp_id=922).a_rapprocher)

    # --- 4. Statuts -----------------------------------------------------------
    def test_statut_venu_renvoye(self):
        self.publier()
        jour = self.lundi_publie()
        self.avis(931, datetime.combine(jour, time(9)))
        cr = RdvRDVSP.objects.get(rdv_sp_id=931).creneau
        with self.captureOnCommitCallbacks(execute=True):
            cr.statut = "VENU_RECU"
            cr.save()
        self.assertEqual(self.mrs.faits("PATCH", "/rdvs/931/update_status")[0][2], {"status": "seen"})
        self.assertEqual(RdvRDVSP.objects.get(rdv_sp_id=931).statut_sp, "seen")

    # --- Administration -------------------------------------------------------
    def test_declarer_et_boutons(self):
        c = Client(HTTP_HOST="localhost")
        c.force_login(self.admin)
        r = c.post(reverse("connecteurs:rdvsp_declarer"), follow=True)
        self.assertContains(r, "adresse de CID déclarée")
        envoi = self.mrs.faits("POST", "/organisations/7/webhook_endpoints")[0][2]
        self.assertEqual((envoi["secret"], envoi["subscriptions"]), (SECRET, ["rdv"]))
        self.assertTrue(envoi["target_url"].endswith("/connecteurs/rdv-service-public/avis/"))
        r = c.post(reverse("connecteurs:rdvsp_synchroniser"), follow=True)
        self.assertContains(r, "1 permanence(s) publiée(s)")
        self.assertContains(c.get(reverse("connecteurs:rdvsp_etat")), 'id="rdvsp-synchro"')


class DesactiveeTests(TestCase):
    @mock.patch.dict(os.environ, {"RDVSP_ACTIF": "", "RDVSP_SECRET_AVIS": SECRET})
    def test_rien_ne_part(self):
        agent = User.objects.create_user("a", password="x", matricule="A", email="a@cid.test")
        with mock.patch.object(api.Client, "appel") as appel, self.captureOnCommitCallbacks(execute=True):
            CreneauRdv.objects.create(date=date.today() + timedelta(days=3), heure_debut=time(9),
                                      heure_fin=time(9, 30), agent=agent, statut="RESERVE")
        appel.assert_not_called()
        r = Client(HTTP_HOST="localhost").post(reverse("connecteurs:rdvsp_avis"), b"{}",
                                               content_type="application/json", HTTP_X_LAPIN_SIGNATURE=signer(b"{}"))
        self.assertEqual(r.status_code, 404)


@mock.patch.dict(os.environ, ENV)
class ReprisesTests(_Base):
    """Base CID réinitialisée : lieu et motif existent déjà dans RDV-Solidarités sous la même référence."""
    def setUp(self):
        super().setUp()
        def deja(client, methode, chemin, **kw):
            if methode == "POST" and chemin in ("/lieux", "/motifs"):
                raise api.RDVSPErreur("RDV Service Public a refusé la demande (422) : external_id est déjà utilisé")
            if chemin == "/lieux":
                return {"lieux": [{"id": 41, "name": "Autre", "organisation_id": 7},
                                  {"id": 42, "name": "MDS Essai", "organisation_id": 7}]}
            if chemin == "/organisations/7/motifs":
                return {"motifs": [{"id": 43, "name": "Renouvellement RSA", "organisation_id": 7}]}
            return self.mrs(client, methode, chemin, **kw)
        self.p.stop()
        self.p = mock.patch.object(api.Client, "appel", autospec=True, side_effect=deja)
        self.p.start()

    def test_reprise_de_l_existant(self):
        b = self.publier()
        self.assertEqual((b["publiees"], b["erreurs"]), (1, []))
        self.assertEqual(MdsRDVSP.objects.get(mds=self.mds).lieu_sp_id, 42)
        from connecteurs.models import MotifRDVSPPublie
        self.assertEqual(MotifRDVSPPublie.objects.get().motif_sp_id, 43)

    def test_prefixe(self):
        with mock.patch.dict(os.environ, {"RDVSP_PREFIXE": "cid13-demo"}):
            self.assertEqual(MdsRDVSP.objects.get(mds=self.mds).reference_lieu, f"cid13-demo-mds-{self.mds.pk}")


@mock.patch.dict(os.environ, ENV)
class LieuxExternesTests(_Base):
    def setUp(self):
        super().setUp()
        self.mardi = DemiJourneeReception.objects.create(
            agent=self.agent, mds=self.mds, jour_semaine=1, type_demi_journee="APRES_MIDI", heure_debut=time(14),
            heure_fin=time(16, 30), type_lieu="EXTERNE", lieu_externe="CCAS de Port-de-Bouc")

    def test_non_publie_sans_adresse_puis_publie(self):
        self.publier()
        self.assertEqual(PlageRDVSP.objects.count(), 1)                        # seulement le lundi en MDS
        self.assertEqual(sync.lieux_externes_non_declares(), [("MDS Essai", "CCAS de Port-de-Bouc")])
        from connecteurs.models import LieuExterneRDVSP
        lieu = LieuExterneRDVSP.objects.create(mds_sp=self.mds_sp, nom="ccas de port-de-bouc",
                                               adresse="1 place de la Mairie, 13110 Port-de-Bouc")
        self.publier()
        self.assertEqual(sync.lieux_externes_non_declares(), [])
        p = PlageRDVSP.objects.get(demi_journee=self.mardi)
        self.assertEqual(p.lieu_externe, lieu)
        envoi = [a for a in self.mrs.faits("POST", "/lieux") if a[2]["name"] == "ccas de port-de-bouc"][0][2]
        self.assertEqual(envoi["address"], "1 place de la Mairie, 13110 Port-de-Bouc")
        plage = self.mrs.faits("POST", "/plage_ouvertures")[-1][2]
        self.assertEqual(plage["lieu_external_id"], f"cid-lieu-{lieu.pk}")
        # L'agent change de lieu : la permanence est retirée puis republiée en MDS
        DemiJourneeReception.objects.filter(pk=self.mardi.pk).update(type_lieu="MDS", lieu_externe="")
        b = self.publier()
        self.assertEqual((b["neutralisees"], b["publiees"]), (1, 1))
