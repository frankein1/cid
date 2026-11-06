# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/tests_stats.py
"""Statistiques de l'accompagnement : calculs, secret statistique, périmètres cadre / direction, CSV. Données fictives."""
from datetime import date, time
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase

from beneficiaire import stats_accompagnement as st
from beneficiaire.models import Beneficiaire, BudgetFoyer, EntretienSocial, TypeAccompagnement
from core.models import Capacite, Profil, User
from mds.models import MDS, UserMDSProfile
from planning.models import Atelier, ParticipantAtelier as P, SeanceAtelier

D, F = date(2026, 1, 1), date(2026, 12, 31)


class StatsTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.m1 = MDS.objects.create(code_mds="TS1", nom="MDS UN", adresse="1 rue A", code_postal="13110", ville="Port-de-Bouc")
        self.m2 = MDS.objects.create(code_mds="TS2", nom="MDS DEUX", adresse="1 rue B", code_postal="13500", ville="Martigues")
        self.as1 = self.agent("lina", self.m1, "MDS_AGENTS_SOCIAUX")
        self.cadre = self.agent("hugo", self.m1, "MDS_RESPONSABLE")
        self.usagers = [self.usager(i, self.m1) for i in range(7)]
        rsa, logement = TypeAccompagnement.objects.get(code="rsa"), TypeAccompagnement.objects.get(code="logement")
        for i, b in enumerate(self.usagers):
            e = EntretienSocial.objects.create(beneficiaire=b, date=date(2026, 3, 1 + i), mode="RDV", duree_minutes=60,
                                               auteur=self.as1, objet="Entretien fictif",
                                               synthese_privee="SECRET-PRIVE", suite_a_donner="x" if i == 0 else "",
                                               echeance=date(2026, 3, 2) if i == 0 else None)
            e.types.set([rsa] if i < 3 else [logement])
        EntretienSocial.objects.create(beneficiaire=self.usagers[0], date=date(2025, 5, 1), auteur=self.as1, objet="Ancien")
        for i, b in enumerate(self.usagers[:6]):
            ch = {"v": 2, "lignes": {"loyer": {"payee": "400", "non_payee": "100" if i < 2 else "0"}}, "precisions": {}}
            BudgetFoyer.objects.create(beneficiaire=b, date_etabli=date(2026, 4, 1), nb_personnes_foyer=1, charges=ch,
                                       ressources={"v": 2, "lignes": {"rsa": {"demandeur": str(600 + 100 * i), "conjoint": "0", "autres": "0"}}, "precisions": {}})
        s = SeanceAtelier.objects.create(atelier=Atelier.objects.create(nom="Cuisine", mds=self.m1), mds=self.m1,
                                         date=date(2026, 5, 4), heure_debut=time(14), heure_fin=time(16), places=4)
        for i, b in enumerate(self.usagers[:4]):
            P.objects.create(seance=s, beneficiaire=b, presence=P.VENU if i < 3 else P.ABSENT)
        P.objects.create(seance=s, nom="EXTERIEUR", liste=P.ATTENTE)

    def agent(self, login, mds, profil):
        u = User.objects.create_user(login, password="x", matricule=login.upper(), first_name=login.title())
        u.profils.add(Profil.objects.get(code=profil))
        if mds:
            UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True)
        return u

    def usager(self, i, mds):
        return Beneficiaire.objects.create(code_interne=f"ST-{mds.code_mds}-{i}", civilite="MME", nom="ESSAI",
                                           prenom=f"Emma{i}", date_naissance=date(1980 + i, 1, 1), adresse="3 rue C",
                                           code_postal="13110", ville="Port-de-Bouc", mds=mds)

    def test_calculs(self):
        r = st.calculer(st.Perimetre([self.m1.pk], True), D, F)
        a = r["activite"]
        self.assertEqual((a["entretiens"], a["heures"], a["file_active"], a["nouveaux"]), (7, 7.0, 7, 6))
        self.assertEqual((a["legaux"], a["suites_retard"]), (3, 1))
        self.assertIn(("Accompagnement RSA (insertion) (légal)", 3, "< 5"), a["par_type"])   # secret statistique
        self.assertEqual(a["par_agent"][0][1], 7)
        b = r["budgets"]
        self.assertEqual((b["n"], b["impayes"], b["part_impayes"]), (6, "< 5", "—"))
        self.assertEqual(r["public"]["civilites"], [("Mme", "7")])
        at = r["ateliers"]["total"]
        self.assertEqual(at[1:], (1, 4, "100 %", "75 %", 1, "0 %"))

    def test_cadre_et_csv_sans_texte_libre(self):
        c = Client(HTTP_HOST="localhost")
        c.force_login(self.cadre)
        r = c.get("/beneficiaire/statistiques/accompagnement/?annee=2026")
        self.assertContains(r, "Par agent")
        self.assertNotContains(r, "Comparaison des MDS")
        r = c.get("/beneficiaire/statistiques/accompagnement/?annee=2026&format=csv")
        self.assertIn(b"File active", r.content)
        self.assertNotIn(b"SECRET-PRIVE", r.content)
        self.assertNotIn(b"Entretien fictif", r.content)
        # le cadre ne peut pas viser une autre MDS
        r = c.get(f"/beneficiaire/statistiques/accompagnement/?annee=2026&mds={self.m2.pk}")
        self.assertEqual(r.context["perimetre"], "MDS UN")

    def test_direction_sans_detail_par_agent(self):
        self.assertTrue(Capacite.objects.filter(code="stats_departement").exists())
        dir_ = self.agent("noe", None, "DIR_DIRECTION")
        c = Client(HTTP_HOST="localhost")
        c.force_login(dir_)
        r = c.get("/beneficiaire/statistiques/accompagnement/?annee=2026")
        self.assertContains(r, "Comparaison des MDS")
        self.assertNotContains(r, "Par agent")
        self.assertEqual([l[0] for l in r.context["comparaison"]], ["MDS DEUX", "MDS UN"])
        self.assertNotContains(c.get(f"/beneficiaire/statistiques/accompagnement/?annee=2026&mds={self.m1.pk}"), "Par agent")

    def test_agent_refuse(self):
        c = Client(HTTP_HOST="localhost")
        c.force_login(self.as1)
        self.assertEqual(c.get("/beneficiaire/statistiques/accompagnement/").status_code, 403)
