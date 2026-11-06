# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/test_droits.py
"""Import des droits : AEEH, paiements France Travail mois par mois, écarts CAF / fiche tracés, montants relevés sur
l'accès partenaire CAF, reprise dans le budget du foyer, réseau familial. Réponses au format des jeux de test
officiels de l'API Particulier (datagouv/apistration) ; personnes fictives."""
from datetime import date, timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import Client, TestCase

from beneficiaire.models import Beneficiaire, LienFamilial
from connecteurs import api_particulier as ap
from connecteurs.models import EcartSituation, PrestationRelevee, SituationExterne
from core.models import Profil, User
from mds.models import MDS, UserMDSProfile

J = date.today()


def _r(data, code=200):
    r = mock.Mock(status_code=code)
    r.json.return_value = {"data": data, "links": {}, "meta": {}}
    return r


def reponses(url, **kw):
    if "allocation_enfant_handicape" in url:
        return _r({"status": "allocataire", "date_debut_droit": "2023-06-15"})
    if "france_travail/statut" in url:
        return _r({"identifiant": "id", "inscription": {"date_debut": "2025-01-02", "date_fin": None,
                                                        "categorie": {"code": "1", "libelle": "Cat. 1"}}})
    if "france_travail/indemnites" in url:
        mois = [(J.replace(day=1) - timedelta(days=30 * k)).replace(day=1) for k in range(8)]
        return _r({"identifiant": "id", "paiements": [
            {"date_versement": d.isoformat(), "montant_total": 900.0, "montant_allocations": 850.0,
             "montant_aides": 50.0, "montant_autres": 0.0} for d in mois]})
    if "quotient_familial" in url:
        return _r({"allocataires": [{"nom_naissance": "ESSAI", "prenoms": "LINA", "date_naissance": "1988-04-02"}],
                   "enfants": [{"nom_naissance": "ESSAI", "prenoms": "NOE", "date_naissance": "2015-05-05"},
                               {"nom_naissance": "ESSAI", "prenoms": "JADE", "date_naissance": "2019-09-09"}],
                   "adresse": {"numero_libelle_voie": "3 RUE DES LILAS", "code_postal_ville": "13110 PORT DE BOUC"},
                   "quotient_familial": {"fournisseur": "CNAF", "valeur": 512, "annee": 2026, "mois": 10}})
    return _r({"est_beneficiaire": False})


class DroitsTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.mds = MDS.objects.create(code_mds="TX1", nom="MDS ESSAI", adresse="1 rue A", code_postal="13110", ville="Port-de-Bouc")
        self.as_ = User.objects.create_user("lea", password="x", matricule="LEA")
        self.as_.profils.add(Profil.objects.get(code="MDS_AGENTS_SOCIAUX"))
        UserMDSProfile.objects.create(user=self.as_, mds=self.mds, actif=True, principale=True)
        self.b = self.usager("DR-1", "Lina", date(1988, 4, 2), numero_france_travail="id1234")
        self.enfant = self.usager("DR-2", "Noé", date(2015, 5, 5))
        LienFamilial.objects.create(personne_a=self.b, personne_b=self.enfant, type_lien="ENFANT", vit_au_foyer=True,
                                    date_debut=date(2015, 5, 5))
        self.grandmere = self.usager("DR-3", "Rose", date(1950, 2, 2))
        LienFamilial.objects.create(personne_a=self.b, personne_b=self.grandmere, type_lien="TIERS", vit_au_foyer=False,
                                    date_debut=date(2020, 1, 1))
        self.c = Client(HTTP_HOST="localhost")
        self.c.force_login(self.as_)

    def usager(self, code, prenom, naissance, **extra):
        return Beneficiaire.objects.create(code_interne=code, civilite="MME", nom="ESSAI", prenom=prenom,
                                           nom_naissance="ESSAI", date_naissance=naissance, lieu_naissance="Marseille",
                                           code_insee_naissance="13055", adresse="3 rue des Lilas", code_postal="13110",
                                           ville="Port-de-Bouc", mds=self.mds, **extra)

    def actualiser(self, sources=None):
        with mock.patch("connecteurs.api_particulier.requests.get", side_effect=reponses) as g:
            ap.actualiser(self.b, self.as_, sources)
        return g

    def test_aeeh(self):
        self.actualiser(["AEEH"])
        s = SituationExterne.objects.get(source="AEEH")
        self.assertTrue(s.est_beneficiaire)
        self.assertIn("15/06/2023", s.resume)

    def test_paiements_france_travail_six_mois_apres_verification(self):
        g = self.actualiser(["FT_PAIEMENTS"])
        self.assertIn("france_travail/statut", g.call_args_list[0].args[0])      # statut vérifié d'abord
        s = SituationExterne.objects.get(source="FT_PAIEMENTS")
        self.assertEqual(len(s.donnees["paiements"]), 6)                          # 8 reçus, 6 gardés
        self.assertEqual(s.donnees["moyenne_mensuelle"], 900.0)
        r = self.c.get("/beneficiaire/DR-1/")
        self.assertContains(r, "dont aides 50,00")

    def test_pas_de_paiements_sans_statut(self):
        self.b.numero_france_travail = ""
        self.b.save()
        self.actualiser(["FT_PAIEMENTS"])
        self.assertEqual(SituationExterne.objects.get(source="FT_PAIEMENTS").statut_appel, "INCOMPLET")

    def test_ecart_enfant_trace_sans_donnees_caf(self):
        self.actualiser(["QUOTIENT_FAMILIAL"])
        e = EcartSituation.objects.get()
        self.assertEqual(e.nature, "ENFANT_INCONNU")
        self.assertIn("2019", e.detail)
        self.assertNotIn("JADE", e.detail)                                         # aucun nom de la CAF
        self.assertNotIn("enfants", SituationExterne.objects.get(source="QUOTIENT_FAMILIAL").donnees)
        self.actualiser(["QUOTIENT_FAMILIAL"])
        self.assertEqual(EcartSituation.objects.count(), 1)                        # pas de doublon tant qu'ouvert
        self.assertContains(self.c.get("/beneficiaire/DR-1/"), "Écart avec la CAF")
        self.c.post(f"/connecteurs/usager/DR-1/situation/ecart/{e.pk}/regle/", {"commentaire": "Enfant ajouté"})
        e.refresh_from_db()
        self.assertEqual((e.regle_par, e.commentaire), (self.as_, "Enfant ajouté"))   # trace gardée

    def test_aides_relevees_et_budget(self):
        self.actualiser(["FT_PAIEMENTS"])
        self.c.post("/connecteurs/usager/DR-1/situation/aides/", {
            "date_releve": "2026-11-05", "p_RSA": "1", "m_RSA": "635,70", "p_AL": "1", "m_AL": "280",
            "p_PRIME_ACTIVITE": "1", "m_PRIME_ACTIVITE": "187,40", "p_ASF": "1", "m_ASF": "199",
            "m_AF": "999"})                                                         # non cochée : ignorée
        self.assertEqual(PrestationRelevee.objects.count(), 4)
        r = self.c.get("/beneficiaire/DR-1/budget/nouveau/?depuis=caf")
        self.assertContains(r, "montants CAF relevés le 05/11/2026")
        self.assertContains(r, 'value="635.70"')
        self.assertContains(r, 'value="900.00"')                                  # chômage = moyenne FT
        # une ligne par aide : prime d'activité et ASF ont chacune la leur
        self.assertContains(r, 'name="r__prime_activite__demandeur" value="187.40"')
        self.assertContains(r, 'name="r__asf__demandeur" value="199.00"')

    def test_reseau_familial_et_bouton_caf(self):
        r = self.c.get("/beneficiaire/DR-1/")
        self.assertContains(r, "Accès partenaire CAF")
        self.assertContains(r, "Rose ESSAI")
        with mock.patch("connecteurs.api_particulier.requests.get", side_effect=reponses):
            r = self.c.post("/connecteurs/usager/DR-3/situation/actualiser/", {"source": "AAH", "retour": "DR-1"})
        self.assertTrue(r["Location"].startswith("/beneficiaire/DR-1/"))
        self.assertTrue(SituationExterne.objects.filter(beneficiaire=self.grandmere, source="AAH").exists())
