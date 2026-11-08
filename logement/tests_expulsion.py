# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/tests_expulsion.py
"""Prévention des expulsions : profils du Service Logement, affectation à la MDS, suivi, étapes, statistiques.
Données fictives."""
from datetime import date, timedelta
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from beneficiaire.models import Beneficiaire
from core.models import Profil, User
from mds.models import MDS, UserMDSProfile
from messagerie.models import Message

from .models import DossierExpulsion as D, EtapeExpulsion
from .models.m_expulsion import treve_hivernale


class ExpulsionTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.mds = MDS.objects.create(code_mds="EX1", nom="MDS ESSAI", adresse="1 rue A", code_postal="13110",
                                      ville="Port-de-Bouc")
        self.autre = MDS.objects.create(code_mds="EX2", nom="MDS AUTRE", adresse="2 rue B", code_postal="13500",
                                        ville="Martigues")
        self.ts = self.agent("amina", "MDS_AGENTS_SOCIAUX", self.mds)
        self.cadre = self.agent("hugo", "MDS_RESPONSABLE", self.mds)
        self.mds.responsable = self.cadre
        self.mds.save()
        self.ts_autre = self.agent("nora", "MDS_AGENTS_SOCIAUX", self.autre)
        self.sl_agent = self.agent("sl_agent", "SL_AGENT_ADMINISTRATIF")
        self.sl_cadre = self.agent("sl_cadre", "SL_CADRE")
        self.sl_secr = self.agent("sl_secr", "SL_SECRETARIAT")
        self.b = Beneficiaire.objects.create(code_interne="EX-1", civilite="MME", nom="ESSAI", prenom="Clara",
                                             date_naissance=date(1990, 1, 1), adresse="3 rue C", code_postal="13110",
                                             ville="Port-de-Bouc", mds=self.mds)

    def agent(self, login, profil, mds=None):
        u = User.objects.create_user(login, password="x", matricule=login.upper(), first_name=login.title(),
                                     last_name="ESSAI")
        u.profils.add(Profil.objects.get(code=profil))
        if mds:
            UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True)
        return u

    def client_de(self, u):
        c = Client(HTTP_HOST="localhost")
        c.force_login(u)
        return c

    def nouveau(self, **extra):
        donnees = {"origine": "SL_CAF", "date_reception": timezone.localdate().isoformat(), "nom": "ESSAI",
                   "prenom": "Clara", "adresse": "3 rue C", "code_postal": "13110", "ville": "Port-de-Bouc",
                   "loyer_total": "700", "dette": "2500", "date_audience": (timezone.localdate() + timedelta(days=20)).isoformat(),
                   "dec_present": "on", "caf_qf": "540", "caf_commentaire": "Fiche fictive"}
        donnees.update(extra)
        return self.client_de(self.sl_agent).post("/logement/expulsions/nouveau/", donnees)

    def test_profils_service_logement(self):
        for code, caps in (("SL_CADRE", {"expulsion_sl_gestion", "expulsion_sl_pilotage", "expulsion_sl_stats"}),
                           ("SL_SECRETARIAT", {"expulsion_sl_stats"}),
                           ("SL_AGENT_ADMINISTRATIF", {"expulsion_sl_gestion"})):
            self.assertEqual(set(Profil.objects.get(code=code).capacites.values_list("code", flat=True)), caps)

    def test_saisie_par_le_sl_et_affectation_previent_la_mds(self):
        r = self.nouveau(mds=self.mds.pk)
        d = D.objects.get()
        self.assertRedirects(r, f"/logement/expulsions/{d.pk}/", fetch_redirect_response=False)
        self.assertTrue(d.numero.startswith(f"EXP-{timezone.localdate().year}-"))
        self.assertEqual(d.mds, self.mds)
        self.assertEqual(d.decision, {"present": True})
        self.assertEqual(d.caf["qf"], "540")
        self.assertTrue(Message.objects.filter(destinataire=self.cadre, object_id=d.pk).exists())
        self.assertIn("Référent social à désigner par la MDS.", d.alertes())

    def test_visibilite_par_mds(self):
        self.nouveau(mds=self.mds.pk)
        d = D.objects.get()
        self.assertEqual(self.client_de(self.ts).get(f"/logement/expulsions/{d.pk}/").status_code, 200)
        self.assertEqual(self.client_de(self.ts_autre).get(f"/logement/expulsions/{d.pk}/").status_code, 403)
        self.assertEqual(self.client_de(self.sl_cadre).get(f"/logement/expulsions/{d.pk}/").status_code, 200)
        # le secrétariat du SL : statistiques seulement
        self.assertEqual(self.client_de(self.sl_secr).get(f"/logement/expulsions/{d.pk}/").status_code, 403)
        self.assertRedirects(self.client_de(self.sl_secr).get("/logement/expulsions/"), "/logement/expulsions/statistiques/",
                             fetch_redirect_response=False)
        r = self.client_de(self.sl_secr).get("/logement/expulsions/statistiques/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["s"]["total"], 1)
        self.assertNotContains(r, "Amina")   # aucune donnée par agent

    def test_suivi_mds_referent_rattachement_etape_cloture(self):
        self.nouveau(mds=self.mds.pk)
        d = D.objects.get()
        c = self.client_de(self.ts)
        url = f"/logement/expulsions/{d.pk}/action/"
        c.post(url, {"action": "prendre"})
        c.post(url, {"action": "rattacher", "beneficiaire": self.b.pk})
        d.refresh_from_db()
        self.assertEqual((d.referent, d.beneficiaire), (self.ts, self.b))
        r = c.get(reverse("beneficiaire:detail_beneficiaire", args=[self.b.code_interne]))
        self.assertContains(r, d.numero)        # encart « Logement » de la fiche usager
        jour = timezone.localdate() - timedelta(days=3)
        c.post(url, {"action": "etape", "type_etape": "COMMANDEMENT_QUITTER", "date": jour.isoformat()})
        e = EtapeExpulsion.objects.get(dossier=d)
        self.assertEqual(e.echeance, jour + timedelta(days=60))
        # un agent d'une autre MDS ne peut rien faire
        self.assertEqual(self.client_de(self.ts_autre).post(url, {"action": "cloturer", "motif_cloture": "AUTRE"}).status_code, 403)
        c.post(url, {"action": "cloturer", "motif_cloture": "APUREMENT"})
        d.refresh_from_db()
        self.assertEqual((d.statut, d.motif_cloture), (D.CLOS, "APUREMENT"))
        self.assertTrue(Message.objects.filter(destinataire=self.sl_agent, object_id=d.pk).exists())
        self.assertEqual(d.alertes(), [])

    def test_affectation_reservee_au_sl_et_suppression_au_cadre_sl(self):
        self.nouveau()
        d = D.objects.get()
        self.assertIn("À affecter à une MDS.", d.alertes())
        url = f"/logement/expulsions/{d.pk}/action/"
        self.assertEqual(self.client_de(self.cadre).post(url, {"action": "affecter", "mds": self.mds.pk}).status_code, 403)
        self.client_de(self.sl_agent).post(url, {"action": "affecter", "mds": self.autre.pk})
        d.refresh_from_db()
        self.assertEqual(d.mds, self.autre)
        self.assertEqual(self.client_de(self.sl_agent).post(url, {"action": "supprimer"}).status_code, 403)
        self.client_de(self.sl_cadre).post(url, {"action": "supprimer"})
        self.assertFalse(D.objects.exists())

    def test_mds_cree_un_dossier_dans_sa_mds(self):
        r = self.client_de(self.ts).post("/logement/expulsions/nouveau/", {
            "origine": "MDS", "date_reception": timezone.localdate().isoformat(), "nom": "ESSAI",
            "mds": self.mds.pk})
        self.assertEqual(r.status_code, 302)
        d = D.objects.get()
        self.assertEqual((d.mds, d.referent), (self.mds, self.ts))
        # une MDS qui n'est pas la sienne est refusée par le formulaire
        r = self.client_de(self.ts).post("/logement/expulsions/nouveau/", {
            "origine": "MDS", "date_reception": timezone.localdate().isoformat(), "nom": "AUTRE", "mds": self.autre.pk})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(D.objects.count(), 1)

    def test_fiche_pdf_et_decision_saisie_par_la_mds(self):
        self.nouveau(mds=self.mds.pk)
        d = D.objects.get()
        r = self.client_de(self.ts).post(f"/logement/expulsions/{d.pk}/modifier/", {
            "origine": "SL_CAF", "date_reception": d.date_reception.isoformat(), "nom": "ESSAI", "mds": self.mds.pk,
            "date_decision": timezone.localdate().isoformat(), "dec_suspension_clause": "on", "dec_accord_delai": "on",
            "dec_duree_delai": "24"})
        self.assertEqual(r.status_code, 302)
        d.refresh_from_db()
        self.assertIn("Accord de délai : 24 mois", d.libelles_decision())
        self.assertTrue(Message.objects.filter(destinataire=self.sl_agent, objet__icontains="décision").exists())
        r = self.client_de(self.ts).get(f"/logement/expulsions/{d.pk}/fiche.pdf")
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))

    def test_treve_hivernale(self):
        self.assertTrue(treve_hivernale(date(2026, 12, 15)))
        self.assertTrue(treve_hivernale(date(2027, 3, 31)))
        self.assertFalse(treve_hivernale(date(2027, 4, 1)))
