# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

# mds/tests_organisation.py

"""MDS de territoire et de proximité, fonctions, accès du CODIR, pilote des IP, intitulé sous la signature."""

from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase

from core.models import Profil, User
from mds.fonctions import fonction_de, nom_et_fonction
from mds.models import MDS, UserMDSProfile
from protection_enfance.models.m_ip import cadre_ip


class OrganisationTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.t = MDS.objects.create(code_mds="TT1", nom="MDS TERRE", adresse="1 rue A", code_postal="13110",
                                    ville="Port-de-Bouc")
        self.p = MDS.objects.create(code_mds="TP1", nom="MDS PROCHE", adresse="1 rue B", code_postal="13500",
                                    ville="Martigues", type_mds=MDS.PROXIMITE, mds_territoire=self.t)
        self.autre = MDS.objects.create(code_mds="TT2", nom="MDS AILLEURS", adresse="1 rue C", code_postal="13001",
                                        ville="Marseille")

    def agent(self, login, mds, profil="MDS_CADRES", fonction=""):
        u = User.objects.create_user(login, password="x", matricule=login.upper(), first_name="Test",
                                     last_name=login.upper())
        u.profils.add(Profil.objects.get(code=profil))
        ump = UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True, fonction=fonction)
        return u, ump

    def test_proximite_doit_etre_rattachee(self):
        m = MDS(code_mds="TP9", nom="X", adresse="a", code_postal="13000", ville="v", type_mds=MDS.PROXIMITE)
        with self.assertRaises(ValidationError):
            m.clean()

    def test_intitule_propose_et_corrigeable(self):
        _, ump = self.agent("dir1", self.t, fonction=UserMDSProfile.DIRECTEUR)
        self.assertEqual(ump.role_specifique, "Directeur de la MDS de territoire TERRE")
        ump.role_specifique = "Directrice de la MDS de territoire de Terre"
        ump.save()
        ump.refresh_from_db()
        self.assertEqual(ump.intitule, "Directrice de la MDS de territoire de Terre")

    def test_codir_voit_la_proximite_sans_gerer_ses_comptes(self):
        dir1, ump = self.agent("dir1", self.t, fonction=UserMDSProfile.DIRECTEUR)
        h = UserMDSProfile.objects.get(user=dir1, mds=self.p)
        self.assertEqual(h.herite_de, ump)
        self.assertTrue(dir1.a_acces_mds(self.p))
        self.assertFalse(dir1.a_acces_mds(self.autre))
        self.assertFalse(h.peut_gerer_utilisateurs)
        self.assertFalse(self.p.peut_gerer_comptes(dir1))
        self.assertEqual(h.intitule, ump.intitule)
        # désactivé à la MDS de territoire → plus d'accès à la MDSp
        ump.actif = False
        ump.save()
        self.assertFalse(UserMDSProfile.objects.get(pk=h.pk).actif)
        # fonction hors CODIR → l'accès hérité disparaît
        ump.actif, ump.fonction = True, UserMDSProfile.AUTRE
        ump.save()
        self.assertFalse(UserMDSProfile.objects.filter(pk=h.pk).exists())

    def test_agent_de_proximite_ne_voit_pas_le_territoire(self):
        as1, _ = self.agent("asp1", self.p, profil="MDS_AGENTS_SOCIAUX")
        self.assertFalse(as1.a_acces_mds(self.t))
        tas, _ = self.agent("ast1", self.t, profil="MDS_AGENTS_SOCIAUX")
        self.assertFalse(tas.a_acces_mds(self.p))

    def test_rattachement_change(self):
        dir1, _ = self.agent("dir1", self.t, fonction=UserMDSProfile.DIRECTEUR)
        self.p.mds_territoire = self.autre
        self.p.save()
        self.assertFalse(dir1.a_acces_mds(self.p))
        dir2, _ = self.agent("dir2", self.autre, fonction=UserMDSProfile.DIRECTEUR)
        self.assertTrue(dir2.a_acces_mds(self.p))

    def test_rattachement_propre_prime(self):
        med, _ = self.agent("med1", self.p, profil="MDS_AGENTS_SOCIAUX")
        UserMDSProfile.objects.create(user=med, mds=self.t, actif=True, fonction=UserMDSProfile.MEDECIN_PMI)
        direct = UserMDSProfile.objects.get(user=med, mds=self.p)
        self.assertIsNone(direct.herite_de)

    def test_pilote_des_ip(self):
        resp_t, _ = self.agent("respt", self.t)
        self.t.responsable = resp_t
        self.t.save()
        self.assertEqual(cadre_ip(self.t), resp_t)
        adj, _ = self.agent("adjenf", self.t, fonction=UserMDSProfile.ADJOINT_ENFANCE)
        self.assertEqual(cadre_ip(self.t), adj)
        # en MDSp : le cadre de proximité, jamais un membre du CODIR par son accès hérité
        cp, _ = self.agent("cprox", self.p, fonction=UserMDSProfile.CADRE_PROXIMITE)
        self.assertEqual(cadre_ip(self.p), cp)

    def test_fonction_sous_la_signature(self):
        adj, ump = self.agent("adjprev", self.t, fonction=UserMDSProfile.ADJOINT_PREVENTION)
        self.assertEqual(fonction_de(adj, self.t), "Adjoint prévention de la MDS de territoire TERRE")
        self.assertEqual(fonction_de(adj, self.p), "Adjoint prévention de la MDS de territoire TERRE")
        self.assertEqual(nom_et_fonction(adj, self.t), "Test ADJPREV – Adjoint prévention de la MDS de territoire TERRE")
        sans, _ = self.agent("sansf", self.t)
        self.assertEqual(nom_et_fonction(sans, self.t), "Test SANSF")

    def test_acces_herite_non_modifiable_depuis_la_proximite(self):
        admin = User.objects.create_superuser("adm", password="x", matricule="ADM")
        dir1, _ = self.agent("dir1", self.t, fonction=UserMDSProfile.DIRECTEUR)
        c = Client(HTTP_HOST="localhost")
        c.force_login(admin)
        r = c.get(f"/mds/{self.p.id}/utilisateurs/{dir1.id}/modifier/")
        self.assertIn(r.status_code, (302, 404))


class DemoOrganisationTests(TestCase):
    """organiser_mds_demo corrige un jeu existant (ancien « Chef de service (propriétaire) »)."""
    def test_demo_sans_proprietaire(self):
        from core.management.commands.init_demo import organiser_mds_demo
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        m1 = MDS.objects.create(code_mds="MDSTEST1", nom="MDS TEST 01", adresse="a", code_postal="13110", ville="v")
        m2 = MDS.objects.create(code_mds="MDSTEST2", nom="MDS TEST 02", adresse="b", code_postal="13500", ville="w")
        comptes = {}
        for login, mds, profil, nom in (("chef_mds1", m1, "MDS_CADRES", "de service (propriétaire)"),
                                        ("cadre_mds1", m1, "MDS_CADRES", "MDS 1"),
                                        ("chef_mds2", m2, "MDS_RESPONSABLE", "MDS 2"),
                                        ("as1_mds2", m2, "MDS_AGENTS_SOCIAUX", "MDS 2")):
            u = User.objects.create_user(login, password="x", matricule=login.upper(), first_name="Chef", last_name=nom)
            u.profils.add(Profil.objects.get(code=profil))
            UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True,
                                          role_specifique="Chef de service" if login == "chef_mds1" else "")
            comptes[login] = u
        m1.responsable, m2.responsable = comptes["chef_mds1"], comptes["chef_mds2"]
        m1.save(); m2.save()
        organiser_mds_demo()
        organiser_mds_demo()   # rejouable
        chef = User.objects.get(username="chef_mds1")
        self.assertEqual(chef.get_full_name(), "Responsable MDS 1")
        m2.refresh_from_db()
        self.assertEqual((m2.type_mds, m2.mds_territoire), (MDS.PROXIMITE, m1))
        self.assertEqual(fonction_de(chef, m1), "Directeur de la MDS de territoire TEST 01")
        self.assertTrue(chef.a_acces_mds(m2))
        self.assertTrue(comptes["cadre_mds1"].a_acces_mds(m2))
        self.assertEqual(cadre_ip(m2), comptes["chef_mds2"])
        self.assertFalse(comptes["as1_mds2"].a_acces_mds(m1))


class FormulaireMDSTests(TestCase):
    def test_modifier_la_mds_garde_configuration_et_communes(self):
        from mds.forms import MDSForm
        m = MDS.objects.create(code_mds="TC1", nom="MDS CONF", adresse="a", code_postal="13110", ville="v",
                               configuration={"cle": 1}, communes=["13077"], latitude=43.4, longitude=4.98)
        data = {k: getattr(m, k) for k in ("code_mds", "nom", "adresse", "code_postal", "ville", "telephone", "email",
                                           "nb_agents_max", "type_mds")}
        data["active"] = True
        f = MDSForm(data, instance=m)
        self.assertTrue(f.is_valid(), f.errors)
        f.save()
        m.refresh_from_db()
        self.assertEqual((m.configuration, m.communes, float(m.latitude)), ({"cle": 1}, ["13077"], 43.4))
