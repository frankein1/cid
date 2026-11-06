# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/tests_journal.py
"""Journal de l'accompagnement : saisie, synthèse privée, sources du parcours, suites à donner, accès. Données fictives."""
from datetime import date, time
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase

from beneficiaire import journal as jr
from beneficiaire.models import Beneficiaire, BudgetFoyer, EntretienSocial, TypeAccompagnement
from core.models import Profil, User
from mds.models import MDS, UserMDSProfile
from planning.models import CreneauRdv


class JournalTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.mds = MDS.objects.create(code_mds="TJ1", nom="MDS ESSAI", adresse="1 rue A", code_postal="13110",
                                      ville="Port-de-Bouc")
        self.autre = MDS.objects.create(code_mds="TJ2", nom="MDS AUTRE", adresse="1 rue B", code_postal="13500",
                                        ville="Martigues")
        self.redac = self.agent("rose", self.mds)
        self.collegue = self.agent("paul", self.mds)
        self.b = Beneficiaire.objects.create(code_interne="JO-1", civilite="MME", nom="ESSAI", prenom="Jade",
                                             date_naissance=date(1988, 3, 1), adresse="3 rue C", code_postal="13110",
                                             ville="Port-de-Bouc", mds=self.mds)
        self.url = "/beneficiaire/JO-1/journal/"

    def agent(self, login, mds):
        u = User.objects.create_user(login, password="x", matricule=login.upper(), first_name=login.title())
        u.profils.add(Profil.objects.get(code="MDS_AGENTS_SOCIAUX"))
        UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True)
        return u

    def client_de(self, u):
        c = Client(HTTP_HOST="localhost")
        c.force_login(u)
        return c

    def saisir(self, **extra):
        rsa = TypeAccompagnement.objects.get(code="rsa")
        return self.client_de(self.redac).post(self.url + "entretien/", {
            "date": "2026-11-03", "heure": "10:00", "mode": "RDV", "duree_minutes": "45", "objet": "Point RSA",
            "types": [rsa.pk], "synthese": "Synthèse partagée fictive", "synthese_privee": "Note privée fictive",
            "suite_a_donner": "Envoyer le contrat", "echeance": "2026-11-10", **extra})

    def test_referentiel_installe(self):
        self.assertTrue(TypeAccompagnement.objects.filter(code="rsa", legal=True).exists())
        self.assertFalse(TypeAccompagnement.objects.get(code="logement").legal)

    def test_saisie_et_synthese_privee(self):
        self.assertEqual(self.saisir().status_code, 302)
        e = EntretienSocial.objects.get()
        self.assertEqual((e.auteur, e.legal), (self.redac, True))
        r = self.client_de(self.redac).get(self.url)
        self.assertContains(r, "Note privée fictive")
        self.assertContains(r, "légal")
        r = self.client_de(self.collegue).get(self.url)
        self.assertContains(r, "Synthèse partagée fictive")
        self.assertNotContains(r, "Note privée fictive")              # lisible par son seul auteur
        # le collègue ne peut pas modifier l'entretien d'un autre
        self.assertEqual(self.client_de(self.collegue).get(self.url + f"entretien/{e.pk}/").status_code, 403)
        self.assertContains(self.client_de(self.collegue).get(f"/beneficiaire/JO-1/"), "Point RSA")

    def test_suites_a_donner(self):
        self.saisir()
        e = EntretienSocial.objects.get()
        c = self.client_de(self.redac)
        self.assertContains(c.get("/beneficiaire/journal/mes-suites/"), "Envoyer le contrat")
        self.assertEqual(self.client_de(self.collegue).post(f"/beneficiaire/journal/entretien/{e.pk}/suite-faite/").status_code, 403)
        c.post(f"/beneficiaire/journal/entretien/{e.pk}/suite-faite/")
        self.assertNotContains(c.get("/beneficiaire/journal/mes-suites/"), "Envoyer le contrat")

    def test_sources_du_parcours_et_compte_rendu(self):
        rdv = CreneauRdv.objects.create(date=date(2026, 11, 2), heure_debut=time(9), heure_fin=time(9, 45), mds=self.mds,
                                        agent=self.redac, beneficiaire=self.b, statut="VENU_RECU", type_rdv="PERMANENCE")
        CreneauRdv.objects.create(date=date(2026, 11, 2), heure_debut=time(11), heure_fin=time(11, 45), mds=self.mds,
                                  agent=self.redac, beneficiaire=self.b, statut="VENU_RECU", domaine="IP")
        BudgetFoyer.objects.create(beneficiaire=self.b, date_etabli=date(2026, 11, 1))
        lignes = jr.journal(self.b, self.redac)
        self.assertEqual(sorted(l.genre for l in lignes), ["budget", "rdv"])          # le RDV IP n'apparaît pas
        r = self.client_de(self.redac).get(self.url)
        self.assertContains(r, f"?creneau={rdv.pk}")                                  # « Rédiger le compte rendu »
        r = self.client_de(self.redac).get(self.url + f"entretien/?creneau={rdv.pk}")
        self.assertContains(r, 'value="2026-11-02"')
        self.saisir(creneau=str(rdv.pk))
        self.assertEqual(EntretienSocial.objects.get().creneau, rdv)
        self.assertNotContains(self.client_de(self.redac).get(self.url), f"?creneau={rdv.pk}")
        self.assertEqual([l.genre for l in jr.journal(self.b, self.redac, genres=["budget"])], ["budget"])

    def test_autre_mds_refusee(self):
        c = self.client_de(self.agent("noe", self.autre))
        self.assertEqual(c.get(self.url).status_code, 403)
        self.assertEqual(c.post(self.url + "entretien/", {"objet": "x"}).status_code, 403)
