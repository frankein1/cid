# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/tests_dalo.py
"""Recours DALO : alerte « hors délais » au 6e mois après le dépôt (configurable), affichée sur la fiche usager.
Données fictives."""
import io
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import Client, SimpleTestCase, TestCase, override_settings
from pypdf import PdfReader

from beneficiaire.models import Beneficiaire
from core.models import Profil, User
from mds.models import MDS, UserMDSProfile

from .models import DemandeLogementSocial, RecoursDALO


class AlerteDaloTests(SimpleTestCase):
    def dl(self, **kw):
        base = dict(dalo_depose=True, dalo_date=date(2026, 3, 15), dalo_etat='EN_COURS')
        base.update(kw)
        return DemandeLogementSocial(**base)

    def test_six_mois_puis_notification_le_mois_suivant(self):
        dl = self.dl()
        self.assertIsNone(dl.dalo_hors_delais(date(2026, 9, 30)), "6e mois atteint, pas encore notifiable")
        self.assertEqual(dl.dalo_hors_delais(date(2026, 10, 1)), date(2026, 9, 15))

    @override_settings(LOGEMENT_DALO_DELAI_MOIS=3)
    def test_delai_configurable_a_trois_mois(self):
        dl = self.dl()
        self.assertIsNone(dl.dalo_hors_delais(date(2026, 6, 30)))
        self.assertEqual(dl.dalo_hors_delais(date(2026, 7, 1)), date(2026, 6, 15))

    def test_pas_d_alerte_si_pas_depose_ou_decide(self):
        self.assertIsNone(self.dl(dalo_depose=False).dalo_hors_delais(date(2026, 12, 1)))
        self.assertIsNone(self.dl(dalo_date=None).dalo_hors_delais(date(2026, 12, 1)))
        self.assertIsNone(self.dl(dalo_etat='ACCEPTE').dalo_hors_delais(date(2026, 12, 1)))
        self.assertIsNone(self.dl(dalo_etat='REFUSE').dalo_hors_delais(date(2026, 12, 1)))


class AlerteDaloAffichageTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.mds = MDS.objects.create(code_mds="TD1", nom="MDS DALO", adresse="1 rue A", code_postal="13110",
                                      ville="Port-de-Bouc", email="mds@exemple.fr")
        u = User.objects.create_user("amina", password="x", matricule="AMINA", first_name="Amina", last_name="ESSAI")
        u.profils.add(Profil.objects.get(code="MDS_AGENTS_SOCIAUX"))
        UserMDSProfile.objects.create(user=u, mds=self.mds, actif=True, principale=True)
        self.ts = u
        self.b = Beneficiaire.objects.create(code_interne="DA-1", civilite="MME", nom="USAGER", prenom="Clara",
                                             date_naissance="1990-01-01", adresse="3 rue C", code_postal="13110",
                                             ville="Port-de-Bouc", mds=self.mds)
        DemandeLogementSocial.objects.create(beneficiaire=self.b, nud="NUD123", dalo_depose=True,
                                             dalo_date=date(2025, 1, 10), dalo_etat='EN_COURS')

    def test_bandeau_sur_la_fiche_usager(self):
        c = Client(HTTP_HOST="localhost")
        c.force_login(self.ts)
        self.assertContains(c.get(f"/beneficiaire/{self.b.code_interne}/"), "hors délais depuis")


class RecoursDaloCerfaTests(TestCase):
    """Masque Cerfa 15036*02 : préremplissage, enregistrement, PDF relu, cloisonnement entre MDS."""

    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.mds = MDS.objects.create(code_mds="DA1", nom="MDS DALO", adresse="1 rue A", code_postal="13110",
                                      ville="Port-de-Bouc", email="mds@exemple.fr")
        self.autre = MDS.objects.create(code_mds="DA2", nom="MDS AUTRE", adresse="2 rue B", code_postal="13500",
                                        ville="Martigues", email="autre@exemple.fr")
        self.ts = self.agent("nadia", self.mds)
        self.hors = self.agent("karim", self.autre)
        self.b = Beneficiaire.objects.create(code_interne="DA-1", civilite="MME", nom="ESSAI", prenom="Clara",
                                             nom_naissance="ESSAI", date_naissance=date(1990, 1, 1),
                                             adresse="12 rue des Lilas", code_postal="13110",
                                             ville="Port-de-Bouc", telephone_mobile="06 12 34 56 78",
                                             mds=self.mds)
        DemandeLogementSocial.objects.create(beneficiaire=self.b, nud="123456789")

    def agent(self, login, mds):
        u = User.objects.create_user(login, password="x", matricule=login.upper(), first_name=login.title(),
                                     last_name="ESSAI")
        u.profils.add(Profil.objects.get(code="MDS_AGENTS_SOCIAUX"))
        UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True)
        return u

    def client_de(self, u):
        c = Client(HTTP_HOST="localhost")
        c.force_login(u)
        return c

    def test_formulaire_prerempli_depuis_la_fiche(self):
        rep = self.client_de(self.ts).get("/logement/dalo/DA-1/")
        self.assertEqual(rep.status_code, 200)
        r = rep.context['r']  # préremplissage en mémoire, non enregistré tant que l'AS n'a pas validé
        self.assertFalse(RecoursDALO.objects.filter(beneficiaire=self.b).exists() and
                         RecoursDALO.objects.get(beneficiaire=self.b).nud)
        self.assertEqual((r.civilite, r.nom_naissance, r.nud), ('MME', 'ESSAI', '123456789'))
        self.assertEqual((r.adresse_numero, r.adresse_voie), ('12', 'rue des Lilas'))
        self.assertEqual(r.date_naissance, '01/01/1990')

    def test_enregistrement_et_valeurs_controlees(self):
        self.client_de(self.ts).post("/logement/dalo/DA-1/", {
            'civilite': 'MME', 'nationalite': 'FR', 'logement': 'PRIVE',
            'situations': ['DEPOURVU', 'INSALUBRE', 'PAS_UN_CODE'],
            'personnes': "Dupont;Léo;02/03/2015;Enfant\r\nDupont;Mia;05/06/2018;Enfant",
            'argumentaire': "Ligne 1\r\nLigne 2"})
        r = RecoursDALO.objects.get(beneficiaire=self.b)
        self.assertEqual(r.nationalite, 'FR')
        self.assertEqual(sorted(r.situations), ['DEPOURVU', 'INSALUBRE'])
        self.assertEqual(r.argumentaire, "Ligne 1\nLigne 2")
        self.assertEqual(r.modifie_par, self.ts)

    def test_pdf_lisible_avec_champs_et_cases(self):
        r = RecoursDALO.objects.get_or_create(beneficiaire=self.b)[0]
        r.nationalite, r.situations = 'FR', ['DEPOURVU']
        r.personnes = "Dupont;Léo;02/03/2015;Enfant"
        r.save()
        rep = self.client_de(self.ts).get("/logement/dalo/DA-1/cerfa.pdf")
        self.assertEqual(rep.status_code, 200)
        self.assertEqual(rep['Content-Type'], 'application/pdf')
        champs = PdfReader(io.BytesIO(rep.content)).get_fields()
        self.assertEqual(str(champs['1. Nom de naissance'].get('/V')), 'ESSAI')
        self.assertEqual(str(champs['2. Numéro unique d\'enregistrement'].get('/V')), '123456789')
        self.assertEqual(str(champs['1. Date de naissance'].get('/V')), '01011990')
        self.assertEqual(str(champs['1. Téléphone portable'].get('/V')), '0612345678')
        self.assertEqual(str(champs['5. Date naissance L1'].get('/V')), '02032015')
        self.assertEqual(str(champs['Case à cocher 8'].get('/V')), '/Oui')
        self.assertEqual(str(champs['Case à cocher 38'].get('/V')), '/Oui')
        self.assertNotIn('Case à cocher 9', [k for k, v in champs.items() if v.get('/V') == '/Oui'])

    def test_acces_refuse_hors_mds(self):
        self.assertEqual(self.client_de(self.hors).get("/logement/dalo/DA-1/").status_code, 403)
        self.assertEqual(self.client_de(self.hors).get("/logement/dalo/DA-1/cerfa.pdf").status_code, 403)
