# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/test_data_inclusion.py
"""data·inclusion : lecture des fichiers ouverts (au format réel : listes écrites à la Python), filtre départemental,
mise à jour, recherche par proximité, ajout à l'annuaire, droits. Structures et services FICTIFS."""
import csv
import io
from datetime import date
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import Client, TestCase

from beneficiaire.models import Beneficiaire, TypeAccompagnement
from connecteurs import data_inclusion as di
from connecteurs.models import ImportInclusion, ServiceInclusion
from core.models import Profil, User
from mds.models import MDS, UserMDSProfile
from partenaires.models import Partenaire

STRUCTURES = [
    {"id": "src--s1", "nom": "Association fictive du Golfe", "siret": "00000000000001", "code_postal": "13110",
     "code_insee": "13077", "commune": "Port-de-Bouc", "adresse": "1 quai fictif", "latitude": "43.405", "longitude": "4.985"},
    {"id": "src--s2", "nom": "Centre fictif de Martigues", "siret": "", "code_postal": "13500", "code_insee": "13056",
     "commune": "Martigues", "adresse": "2 rue fictive", "latitude": "43.404", "longitude": "5.048"},
    {"id": "src--s3", "nom": "Structure fictive lyonnaise", "siret": "", "code_postal": "69001", "code_insee": "69381",
     "commune": "Lyon", "adresse": "", "latitude": "45.76", "longitude": "4.83"},
]
SERVICES = [
    {"id": "src--v1", "source": "dora", "structure_id": "src--s1", "nom": "Aide au budget (fictif)", "type": "accompagnement",
     "thematiques": "['difficultes-financieres--accompagnement-budget', 'difficultes-financieres--surendettement']",
     "publics": "['familles']", "frais": "gratuit", "modes_accueil": "['en-presentiel']", "code_postal": "13110",
     "code_insee": "13077", "commune": "Port-de-Bouc", "latitude": "43.405", "longitude": "4.985", "date_maj": "2026-10-01",
     "courriel": "contact@exemple.invalid", "telephone": "0400000000", "zone_eligibilite": "['13']"},
    {"id": "src--v2", "source": "soliguide", "structure_id": "src--s2", "nom": "Épicerie fictive", "type": "aide-materielle",
     "description": "Première ligne, avec « guillemets »\nseconde ligne",
     "thematiques": "['equipement-et-alimentation--alimentation']", "publics": "", "frais": "payant",
     "modes_accueil": "['en-presentiel']", "code_postal": "13500", "commune": "Martigues", "latitude": "43.404",
     "longitude": "5.048", "date_maj": "2026-09-15", "zone_eligibilite": ""},
    {"id": "src--v3", "source": "dora", "structure_id": "src--s3", "nom": "Service lyonnais (fictif)", "type": "information",
     "thematiques": "['difficultes-financieres--accompagnement-budget']", "code_postal": "69001", "commune": "Lyon",
     "zone_eligibilite": "['69']"},
    {"id": "src--v4", "source": "france-travail", "structure_id": "", "nom": "Atelier en ligne (fictif)", "type": "atelier",
     "thematiques": '["numerique--acceder-a-une-connexion-internet"]', "modes_accueil": "['a-distance']",
     "zone_eligibilite": "['13056', '13077']"},
]


def _csv(rows):
    champs = sorted({k for r in rows for k in r})
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=champs)
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def ouvrir_factice(structures=STRUCTURES, services=SERVICES):
    fichiers = {di.URL_STRUCTURES: _csv(structures), di.URL_SERVICES: _csv(services)}
    return lambda url: iter(fichiers[url].encode("utf-8").splitlines())


class ImportTests(TestCase):
    def test_listes_au_format_reel(self):
        self.assertEqual(di.liste("['a', 'b']"), ["a", "b"])
        self.assertEqual(di.liste('["a"]'), ["a"])
        self.assertEqual(di.liste("a, b"), ["a", "b"])
        self.assertEqual(di.liste(""), [])
        self.assertEqual(di.liste("nan"), [])

    def test_import_filtre_et_mise_a_jour(self):
        t = di.importer(["13"], ouvrir=ouvrir_factice())
        self.assertEqual((t.erreur, t.structures, t.services), ("", 2, 3))     # Lyon écarté, l'atelier en ligne gardé
        s = ServiceInclusion.objects.get(di_id="src--v1")
        self.assertIn("seconde ligne", ServiceInclusion.objects.get(di_id="src--v2").description)   # texte sur 2 lignes
        self.assertEqual((s.structure_nom, s.thematiques[1], s.categories), (
            "Association fictive du Golfe", "difficultes-financieres--surendettement", ["difficultes-financieres"]))
        # deuxième import : un service disparu est retiré, un service modifié est mis à jour
        modif = [dict(SERVICES[0], nom="Aide au budget renommée (fictif)"), SERVICES[3]]
        t = di.importer(["13"], ouvrir=ouvrir_factice(services=modif))
        self.assertEqual((t.services, t.retires), (2, 1))
        self.assertEqual(ServiceInclusion.objects.get(di_id="src--v1").nom, "Aide au budget renommée (fictif)")

    def test_fichier_vide_ne_vide_pas_la_base(self):
        di.importer(["13"], ouvrir=ouvrir_factice())
        t = di.importer(["13"], ouvrir=ouvrir_factice(services=[]))
        self.assertEqual(t.retires, 0)
        self.assertEqual(ServiceInclusion.objects.count(), 3)

    def test_erreur_reseau_tracee(self):
        def panne(url):
            raise ConnectionError("pas de réseau")
        t = di.importer(["13"], ouvrir=panne)
        self.assertIn("pas de réseau", t.erreur)
        self.assertIsNotNone(t.fin)

    def test_commande(self):
        with mock.patch("connecteurs.management.commands.importer_data_inclusion.importer",
                        side_effect=lambda deps: di.importer(deps, ouvrir=ouvrir_factice())):
            out = StringIO()
            call_command("importer_data_inclusion", "--departements", "13", stdout=out)
        self.assertIn("3 services importés", out.getvalue())


class RechercheTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        di.importer(["13"], ouvrir=ouvrir_factice())
        self.mds = MDS.objects.create(code_mds="TD1", nom="MDS ESSAI", adresse="1 rue A", code_postal="13110",
                                      ville="Port-de-Bouc")
        self.agent = User.objects.create_user("ines", password="x", matricule="INES")
        self.agent.profils.add(Profil.objects.get(code="MDS_AGENTS_SOCIAUX"))
        UserMDSProfile.objects.create(user=self.agent, mds=self.mds, actif=True, principale=True)
        self.b = Beneficiaire.objects.create(code_interne="DI-1", civilite="MME", nom="ESSAI", prenom="Nora",
                                             date_naissance=date(1990, 1, 1), adresse="3 rue C", code_postal="13500",
                                             ville="Martigues", mds=self.mds)
        self.c = Client(HTTP_HOST="localhost")
        self.c.force_login(self.agent)

    def test_proximite_et_filtres(self):
        services, total, centre = di.rechercher(commune="Martigues")
        self.assertEqual(services[0].nom, "Épicerie fictive")                 # 0 km
        self.assertAlmostEqual(services[1].distance, 5.1, delta=0.5)          # Port-de-Bouc
        self.assertEqual(di.rechercher(gratuit=True)[1], 2)                    # le payant écarté
        self.assertEqual(di.rechercher(presentiel=True)[1], 2)                 # l'atelier en ligne écarté
        self.assertEqual([s.nom for s in di.rechercher(["difficultes-financieres"])[0]], ["Aide au budget (fictif)"])

    def test_depuis_l_entretien(self):
        budget = TypeAccompagnement.objects.get(code="budget")
        self.assertEqual(budget.thematiques_inclusion, ["difficultes-financieres"])    # correspondance installée
        r = self.c.get(f"/connecteurs/inclusion/?usager=DI-1&types={budget.pk}")
        self.assertEqual(r.context["commune"], "Martigues")
        self.assertEqual(r.context["choisies"], ["difficultes-financieres"])
        self.assertContains(r, "Aide au budget (fictif)")
        self.assertContains(self.c.get("/beneficiaire/DI-1/journal/entretien/"), "chercher-service")

    def test_ajout_annuaire_une_seule_fois(self):
        s = ServiceInclusion.objects.get(di_id="src--v1")
        self.c.post(f"/connecteurs/inclusion/{s.pk}/ajouter-annuaire/", {"retour": "https://ailleurs.example/"})
        self.c.post(f"/connecteurs/inclusion/{s.pk}/ajouter-annuaire/")
        p = Partenaire.objects.get(reference_inclusion="src--v1")
        self.assertEqual((p.organisme, p.service, p.thematique, p.ville), (
            "Association fictive du Golfe", "Aide au budget (fictif)", "BUDGET", "Port-de-Bouc"))
        self.assertContains(self.c.get("/connecteurs/inclusion/"), "Dans l'annuaire")

    def test_mise_a_jour_reservee_aux_administrateurs(self):
        self.assertEqual(self.c.get("/connecteurs/inclusion/mise-a-jour/").status_code, 403)
        su = User.objects.create_superuser("su", password="x", matricule="SU")
        c = Client(HTTP_HOST="localhost")
        c.force_login(su)
        with mock.patch("connecteurs.data_inclusion.threading.Thread") as fil:
            c.post("/connecteurs/inclusion/mise-a-jour/")
        fil.return_value.start.assert_called_once()
        ImportInclusion.objects.create(departements="13")          # une mise à jour en cours : pas de doublon
        with mock.patch("connecteurs.data_inclusion.threading.Thread") as fil:
            c.post("/connecteurs/inclusion/mise-a-jour/")
        fil.assert_not_called()
