# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/tests.py
"""Passerelle RDV Service Public : désactivée par défaut ; circuit OAuth et API simulés (aucun appel réel).
Données entièrement fictives."""
import os
from datetime import date, timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from beneficiaire.models import Beneficiaire
from connecteurs import rdv_service_public as rdvsp
from connecteurs.models import AppelRDVSP, CompteRDVSP, LienUsagerRDVSP
from core.models import Profil, User
from mds.models import MDS, UserMDSProfile

CONF = {"RDVSP_ACTIF": "1", "RDVSP_URL": "https://rdvsp.exemple.test", "RDVSP_CLIENT_ID": "cid-essai",
        "RDVSP_CLIENT_SECRET": "secret-essai"}
VIDE = {k: "" for k in CONF}


def rep(code=200, json=None):
    r = mock.Mock(status_code=code, content=b"{}" if json is not None else b"")
    r.json.return_value = json or {}
    return r


class _Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        cls.mds = MDS.objects.create(code_mds="T1", nom="MDS Essai", adresse="1 rue A", code_postal="13000", ville="Exemple")
        cls.ts = User.objects.create_user("ts", password="x", first_name="Inès", matricule="TS")
        cls.ts.profils.add(Profil.objects.get(code="MDS_AGENTS_SOCIAUX"))
        UserMDSProfile.objects.create(user=cls.ts, mds=cls.mds, actif=True, principale=True)
        cls.benef = Beneficiaire.objects.create(code_interne="T-RDV", civilite="MME", nom="ESSAI", prenom="Lucie",
                                                date_naissance=date(1990, 1, 1), adresse="3 rue C",
                                                code_postal="13000", ville="Exemple", mds=cls.mds,
                                                email="lucie.essai@exemple.test")

    def setUp(self):
        self.c = Client(HTTP_HOST="localhost")
        self.c.force_login(self.ts)

    def relier(self, expire=timedelta(hours=2)):
        return CompteRDVSP.objects.create(utilisateur=self.ts, agent_id="42", jeton_acces="A",
                                          jeton_renouvellement="R", expire_le=timezone.now() + expire)


@mock.patch.dict(os.environ, VIDE)
class DesactiveeTests(_Base):
    def test_inactive_par_defaut(self):
        self.assertFalse(rdvsp.est_actif())
        self.assertIn("RDVSP_ACTIF=1", rdvsp.manques())

    def test_aucun_appel_ni_bouton(self):
        with mock.patch("connecteurs.rdv_service_public.requests") as req:
            r = self.c.get(reverse("beneficiaire:detail_beneficiaire", args=["T-RDV"]))
            self.assertNotContains(r, 'id="rdvsp-planifier"')
            r = self.c.post(reverse("connecteurs:rdvsp_planifier", args=["T-RDV"]))
            self.assertEqual(r.status_code, 302)
            self.assertIn("T-RDV", r.url)
            self.c.get(reverse("connecteurs:rdvsp_connexion"))
            req.request.assert_not_called()
            req.post.assert_not_called()

    def test_client_refuse(self):
        with self.assertRaises(rdvsp.RDVSPErreur):
            rdvsp.Client(self.ts)

    def test_page_etat_admin(self):
        su = User.objects.create_superuser("su", password="x", matricule="SU")
        self.c.force_login(su)
        r = self.c.get(reverse("connecteurs:rdvsp_etat"))
        self.assertContains(r, "Passerelle présente, désactivée")
        self.assertContains(r, "RDVSP_CLIENT_SECRET")
        self.c.force_login(self.ts)
        self.assertEqual(self.c.get(reverse("connecteurs:rdvsp_etat")).status_code, 302)


@mock.patch.dict(os.environ, CONF)
class ActiveeTests(_Base):
    def test_bouton_visible(self):
        r = self.c.get(reverse("beneficiaire:detail_beneficiaire", args=["T-RDV"]))
        self.assertContains(r, 'id="rdvsp-planifier"')

    def test_connexion_oauth(self):
        r = self.c.get(reverse("connecteurs:rdvsp_connexion") + "?suite=T-RDV")
        self.assertTrue(r.url.startswith("https://rdvsp.exemple.test/oauth/authorize?"))
        etat = self.c.session["rdvsp_etat"]
        self.assertIn(f"state={etat}", r.url)
        # mauvais état : refusé, rien d'enregistré
        r = self.c.get(reverse("connecteurs:rdvsp_retour") + "?code=X&state=faux")
        self.assertFalse(CompteRDVSP.objects.exists())
        # bon état
        self.c.get(reverse("connecteurs:rdvsp_connexion") + "?suite=T-RDV")
        etat = self.c.session["rdvsp_etat"]
        with mock.patch("connecteurs.rdv_service_public.requests.post",
                        return_value=rep(json={"access_token": "A", "refresh_token": "R", "expires_in": 7200})) as p, \
                mock.patch("connecteurs.rdv_service_public.requests.request",
                           return_value=rep(json={"agent": {"id": 42}})):
            r = self.c.get(reverse("connecteurs:rdvsp_retour") + f"?code=C0DE&state={etat}")
        self.assertEqual(p.call_args.kwargs["data"]["grant_type"], "authorization_code")
        compte = CompteRDVSP.objects.get(utilisateur=self.ts)
        self.assertEqual(compte.agent_id, "42")
        self.assertIn("T-RDV", r.url)
        self.assertTrue(AppelRDVSP.objects.filter(action="CONNEXION", reussi=True).exists())

    def test_planifier_sans_compte_renvoie_vers_connexion(self):
        r = self.c.post(reverse("connecteurs:rdvsp_planifier", args=["T-RDV"]))
        self.assertIn(reverse("connecteurs:rdvsp_connexion"), r.url)

    def test_planifier_cree_le_lien_usager(self):
        self.relier()
        plan = {"rdv_plan": {"id": 7, "url": "https://rdvsp.exemple.test/plan/7", "user_id": 99}}
        with mock.patch("connecteurs.rdv_service_public.requests.request", return_value=rep(json=plan)) as req:
            r = self.c.post(reverse("connecteurs:rdvsp_planifier", args=["T-RDV"]))
        self.assertEqual(r.url, "https://rdvsp.exemple.test/plan/7")
        corps = req.call_args.kwargs["json"]
        self.assertEqual(corps["user"]["last_name"], "ESSAI")
        self.assertEqual(corps["user"]["birth_date"], "1990-01-01")
        self.assertNotIn("id", corps["user"])
        self.assertEqual(req.call_args.kwargs["headers"]["Authorization"], "Bearer A")
        self.assertEqual(LienUsagerRDVSP.objects.get(beneficiaire=self.benef).usager_rdvsp_id, "99")
        # 2e fois : usager mis à jour puis plan avec son identifiant
        with mock.patch("connecteurs.rdv_service_public.requests.request", return_value=rep(json=plan)) as req:
            self.c.post(reverse("connecteurs:rdvsp_planifier", args=["T-RDV"]))
        self.assertEqual([c.args[0] for c in req.call_args_list], ["PATCH", "POST"])
        self.assertEqual(req.call_args.kwargs["json"]["user"]["id"], "99")

    def test_jeton_expire_renouvele(self):
        self.relier(expire=-timedelta(minutes=1))
        with mock.patch("connecteurs.rdv_service_public.requests.post",
                        return_value=rep(json={"access_token": "B", "refresh_token": "R2", "expires_in": 7200})) as p, \
                mock.patch("connecteurs.rdv_service_public.requests.request", return_value=rep(json={"rdvs": []})) as req:
            LienUsagerRDVSP.objects.create(beneficiaire=self.benef, usager_rdvsp_id="99")
            self.assertEqual(rdvsp.rdvs_usager(self.ts, self.benef), [])
        self.assertEqual(p.call_args.kwargs["data"]["grant_type"], "refresh_token")
        self.assertEqual(req.call_args.kwargs["headers"]["Authorization"], "Bearer B")

    def test_jeton_refuse_redemande_connexion(self):
        self.relier()
        with mock.patch("connecteurs.rdv_service_public.requests.request", return_value=rep(401)):
            r = self.c.post(reverse("connecteurs:rdvsp_planifier", args=["T-RDV"]))
        self.assertIn(reverse("connecteurs:rdvsp_connexion"), r.url)
        self.assertFalse(CompteRDVSP.objects.exists())

    def test_service_indisponible(self):
        self.relier()
        with mock.patch("connecteurs.rdv_service_public.requests.request", return_value=rep(503)):
            r = self.c.post(reverse("connecteurs:rdvsp_planifier", args=["T-RDV"]), follow=True)
        self.assertContains(r, "a refusé la demande (503)")
        self.assertTrue(AppelRDVSP.objects.filter(action="PLAN_RDV", reussi=False).exists())

    def test_changer_statut(self):
        self.relier()
        with self.assertRaises(rdvsp.RDVSPErreur):
            rdvsp.changer_statut(self.ts, 5, "inconnu")
        with mock.patch("connecteurs.rdv_service_public.requests.request",
                        return_value=rep(json={"rdv": {"id": 5, "status": "seen"}})) as req:
            self.assertEqual(rdvsp.changer_statut(self.ts, 5, "seen")["status"], "seen")
        self.assertTrue(req.call_args.args[1].endswith("/api/v1/rdvs/5/update_status"))
