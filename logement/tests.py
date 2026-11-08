# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/tests.py
"""FSL accès : préremplissage, gestionnaire selon la commune, circuit (pièces manquantes → cadre), accès, PDF.
Données fictives ; le formulaire « officiel » des tests est un PDF fabriqué ici, jamais un vrai formulaire."""
import io
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase
from reportlab.pdfgen import canvas

from beneficiaire.models import Beneficiaire, BudgetFoyer, LienFamilial
from core.models import Profil, User
from mds.models import MDS, UserMDSProfile

from .models import DemandeFSL, FormulaireOfficiel, GestionnaireFSL
from .services import circuit, fsl
from .services.fsl_pdf import documents_du_dossier, dossier
from .services.pdf_officiel import remplir


def faux_formulaire():
    """PDF vierge fabriqué : quelques libellés du formulaire d'accès, aux places habituelles."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(1190, 842))
    c.setFont("Helvetica", 9)
    for x, y, t in [(636, 660, "BAILLEUR SOCIAL"), (742, 660, "BAILLEUR PRIVE"), (914, 645, "N° Allocataire CAF 13 : ......"),
                    (625, 615, "Nom(s) et Prénom du demandeur :"), (634, 360, "Célibataire"), (760, 360, "Vie maritale")]:
        c.drawString(x, y, t)
    c.showPage()
    c.drawString(17, 740, "Salaires")
    c.drawString(173, 765, "Demandeur")
    c.drawString(624, 290, "Nom du travailleur social : ........")
    c.save()
    return buf.getvalue()


class FSLTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.mds = MDS.objects.create(code_mds="TL1", nom="MDS ESSAI", adresse="1 rue A", code_postal="13110",
                                      ville="Port-de-Bouc", email="mds@exemple.fr")
        self.autre = MDS.objects.create(code_mds="TL2", nom="MDS AUTRE", adresse="1 rue B", code_postal="13500",
                                        ville="Martigues")
        self.ts = self.agent("amina", self.mds, "MDS_AGENTS_SOCIAUX")
        self.cadre = self.agent("hugo", self.mds, "MDS_RESPONSABLE")
        self.mds.responsable = self.cadre
        self.mds.save()
        self.dehors = self.agent("ines", self.autre, "MDS_AGENTS_SOCIAUX")
        self.metro = GestionnaireFSL.objects.create(nom="Gestionnaire A (fictif)", codes_postaux="13110, 13500",
                                                    parametres={"plafond_acces": 1000})
        self.dep = GestionnaireFSL.objects.create(nom="Gestionnaire B (fictif)", par_defaut=True)
        self.b = self.usager("FL-1", "Clara", date(1990, 1, 1))
        self.conjoint = self.usager("FL-2", "Yanis", date(1989, 5, 5))
        self.enfant = self.usager("FL-3", "Lou", date(2016, 3, 3))
        LienFamilial.objects.create(personne_a=self.b, personne_b=self.conjoint, type_lien="CONJOINT", vit_au_foyer=True)
        LienFamilial.objects.create(personne_a=self.enfant, personne_b=self.b, type_lien="PARENT", vit_au_foyer=True)
        BudgetFoyer.objects.create(beneficiaire=self.b, nb_personnes_foyer=3, ressources={"v": 2, "lignes": {
            "salaire": {"demandeur": "1200", "conjoint": "0", "autres": "0"},
            "chomage": {"demandeur": "0", "conjoint": "700", "autres": "0"},
            "familiales": {"demandeur": "140", "conjoint": "0", "autres": "0"},
            "logement": {"demandeur": "200", "conjoint": "0", "autres": "0"}}, "precisions": {}},
            charges={"v": 2, "lignes": {"loyer": {"payee": "600", "non_payee": "0"}}, "precisions": {}})

    def agent(self, login, mds, profil):
        u = User.objects.create_user(login, password="x", matricule=login.upper(), first_name=login.title(),
                                     last_name="ESSAI")
        u.profils.add(Profil.objects.get(code=profil))
        UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True)
        return u

    def usager(self, code, prenom, naissance):
        return Beneficiaire.objects.create(code_interne=code, civilite="MME", nom="ESSAI", prenom=prenom,
                                           date_naissance=naissance, adresse="3 rue C", code_postal="13110",
                                           ville="Port-de-Bouc", mds=self.mds, numero_caf="1234567")

    def client_de(self, u):
        c = Client(HTTP_HOST="localhost")
        c.force_login(u)
        return c

    def creer(self):
        r = self.client_de(self.ts).post("/logement/fsl/nouvelle/FL-1/")
        self.assertEqual(r.status_code, 302)
        return DemandeFSL.objects.get()

    def test_preremplissage(self):
        d = self.creer()
        dn = d.donnees
        self.assertEqual(d.gestionnaire, self.metro)
        self.assertEqual(dn["num_caf"], "1234567")
        self.assertEqual([p["role"] for p in dn["composition"]], ["DEMANDEUR", "CONJOINT", "ENFANT"])
        self.assertEqual(dn["ressources"]["salaires"], {"demandeur": "1200"})
        self.assertEqual(dn["ressources"]["france_travail"], {"conjoint": "700"})
        self.assertEqual(dn["ressources"]["prestations_familiales"], {"demandeur": "140"})
        self.assertEqual(dn["logement_anterieur"]["loyer"], "600")
        self.assertEqual(dn["logement_anterieur"]["al"], "200")
        self.assertEqual(dn["ts"]["email"], "mds@exemple.fr")      # courriel de la MDS, pas celui de l'agent

    def test_gestionnaire_par_defaut(self):
        self.assertEqual(GestionnaireFSL.pour_code_postal("13200"), self.dep)
        self.assertEqual(GestionnaireFSL.pour_code_postal("13500"), self.metro)

    def test_circuit_pieces_manquantes(self):
        d = self.creer()
        d.avis = "FAVORABLE"
        d.save()
        with self.assertRaises(circuit.CircuitError):
            circuit.envoyer(d, self.ts)                       # des pièces manquent
        circuit.demander_avis_cadre(d, self.ts)
        self.assertEqual(d.statut, DemandeFSL.A_VALIDER)
        c = self.client_de(self.cadre)
        c.post(f"/logement/fsl/{d.pk}/action/", {"action": "cadre_accepte", "note_cadre": ""})
        d.refresh_from_db()
        self.assertEqual(d.statut, DemandeFSL.A_VALIDER)      # note obligatoire
        c.post(f"/logement/fsl/{d.pk}/action/", {"action": "cadre_accepte", "note_cadre": "Bail transmis à la signature."})
        d.refresh_from_db()
        self.assertEqual(d.statut, DemandeFSL.VALIDEE)
        circuit.envoyer(d, self.ts)
        circuit.enregistrer_reponse(d, self.ts, DemandeFSL.ACCORDEE, date(2026, 11, 20), subvention=900)
        self.assertEqual(d.statut, DemandeFSL.ACCORDEE)
        self.assertTrue(any("Réponse du FSL" in h["action"] for h in d.historique))

    def test_acces(self):
        d = self.creer()
        self.assertEqual(self.client_de(self.dehors).get(f"/logement/fsl/{d.pk}/").status_code, 403)
        self.assertEqual(self.client_de(self.dehors).post("/logement/fsl/nouvelle/FL-1/").status_code, 403)
        self.assertEqual(self.client_de(self.ts).post(f"/logement/fsl/{d.pk}/action/",
                                                      {"action": "cadre_accepte", "note_cadre": "x"}).status_code, 403)
        r = self.client_de(self.ts).get(f"/logement/fsl/{d.pk}/modifier/")
        self.assertContains(r, "Ressources mensuelles du foyer")

    def test_saisie_et_alerte_plafond(self):
        d = self.creer()
        post = {"bailleur_type": "PRIVE", "comp_0_nom": "ESSAI", "comp_0_prenom": "Clara", "comp_0_role": "DEMANDEUR",
                "res_salaires_demandeur": "1200", "prop_caution": "600", "prop_premier_loyer": "650", "avis": "RESERVE",
                "piece_bail": "FOURNIE"}
        self.client_de(self.ts).post(f"/logement/fsl/{d.pk}/modifier/", post)
        d.refresh_from_db()
        self.assertEqual(d.donnees["proposition"], {"caution": "600", "premier_loyer": "650"})
        self.assertEqual(d.avis, "RESERVE")
        self.assertTrue(any("plafond" in a for a in fsl.alertes(d)))

    def test_dossier_trame_et_formulaire_officiel(self):
        d = self.creer()
        pdf, rapport = dossier(d)                        # aucun formulaire déposé : trame CID
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertIn("trame CID", [m for _, m, _ in rapport])
        FormulaireOfficiel.objects.create(gestionnaire=self.metro, code=FormulaireOfficiel.FORMULAIRE_ACCES,
                                          contenu=faux_formulaire())
        pdf, rapport = dossier(d)
        self.assertEqual(rapport[0][1], "officiel")

    def test_moteur_ancres(self):
        from .services.placements_fsl import placements
        d = self.creer()
        d.donnees.update({"bailleur_type": "PRIVE", "situation_familiale": "MARITALE"})
        from .services.placements_fsl import valeurs
        pdf, rapport = remplir(faux_formulaire(), placements(FormulaireOfficiel.FORMULAIRE_ACCES),
                               valeurs(d, FormulaireOfficiel.FORMULAIRE_ACCES))
        for cle in ("bailleur_prive", "num_caf", "demandeur", "sf_MARITALE", "res_salaires_demandeur", "ts_nom"):
            self.assertEqual(rapport[cle], "ok", cle)
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf)) as p:
            self.assertIn("ESSAI Clara – ESSAI Yanis", p.pages[0].extract_text())
            self.assertIn("1 200,00", p.pages[1].extract_text())

    def test_encart_fiche(self):
        r = self.client_de(self.ts).get("/beneficiaire/FL-1/")
        self.assertContains(r, "FSL énergie")

    def test_apercu_administration(self):
        admin = User.objects.create_superuser("adm", password="x", matricule="ADM")
        f = FormulaireOfficiel.objects.create(gestionnaire=self.metro, code=FormulaireOfficiel.FORMULAIRE_ACCES,
                                              contenu=faux_formulaire())
        r = self.client_de(admin).get(f"/admin/logement/formulaireofficiel/{f.pk}/apercu/")
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertIn("adresse_objet", r["X-CID-Champs-Non-Places"])     # libellé absent du faux formulaire

    def test_energie_instruction_administrative(self):
        BudgetFoyer.objects.update(charges={"v": 2, "lignes": {"loyer": {"payee": "600", "non_payee": "0"},
                                                               "electricite": {"payee": "60", "non_payee": "180"}},
                                            "precisions": {}})
        r = self.client_de(self.ts).post("/logement/fsl/nouvelle/FL-1/", {"type_aide": "ENERGIE"})
        self.assertEqual(r.status_code, 302)
        d = DemandeFSL.objects.get(type_aide="ENERGIE")
        self.assertEqual(d.donnees["dette_electricite"], "180")
        self.assertEqual(d.donnees["situation_logement"], "LOCATAIRE")
        self.assertIn("facture", d.pieces)
        post = {"distributeur": "Fournisseur fictif", "dette_electricite": "180", "dette_gaz": "0",
                "instruction_administrative": "on", "commentaire_administratif": "Régularisation (fictif).",
                **{f"piece_{c}": "FOURNIE" for c, _, _ in fsl.PIECES_FLUIDES}}
        self.client_de(self.ts).post(f"/logement/fsl/{d.pk}/modifier/", post)
        d.refresh_from_db()
        self.assertTrue(d.instruction_administrative)
        self.assertEqual([c for c, _ in documents_du_dossier(d)], [FormulaireOfficiel.FORMULAIRE_ENERGIE])
        circuit.envoyer(d, self.ts)                       # sans avis : instruction administrative < 500 €
        self.assertEqual(d.statut, DemandeFSL.ENVOYEE)
        pdf, rapport = dossier(d)
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_eau_au_dela_du_seuil_administratif(self):
        self.client_de(self.ts).post("/logement/fsl/nouvelle/FL-1/", {"type_aide": "EAU"})
        d = DemandeFSL.objects.get(type_aide="EAU")
        d.donnees["montant_facture"] = "620"
        d.instruction_administrative = True
        d.pieces = {c: "FOURNIE" for c in d.pieces}
        d.save()
        self.assertTrue(any("500" in a for a in fsl.alertes(d)))
        with self.assertRaises(circuit.CircuitError):
            circuit.envoyer(d, self.ts)

    def test_maintien_concordat(self):
        BudgetFoyer.objects.update(charges={"v": 2, "lignes": {"loyer": {"payee": "300", "non_payee": "300"}},
                                            "precisions": {}})
        self.client_de(self.ts).post("/logement/fsl/nouvelle/FL-1/", {"type_aide": "MAINTIEN"})
        d = DemandeFSL.objects.get(type_aide="MAINTIEN")
        self.assertEqual(d.donnees["logement"]["loyer"], "600")
        self.assertEqual(d.donnees["montant_dette"], "300")
        self.assertIn("releve_compte", d.pieces)
        post = {"bailleur_type": "PRIVE", "variante": "CONCORDAT", "montant_dette": "1800", "remise_dette": "OUI",
                "montant_remise": "300", "lg_loyer": "600", "lg_al": "200", "saisine_ccapex": "OUI",
                "comp_0_nom": "ESSAI", "comp_0_prenom": "Clara", "res_salaires_demandeur": "1200",
                "proposition_pret": "500", "proposition_subvention": "1000", "avis": "FAVORABLE"}
        self.client_de(self.ts).post(f"/logement/fsl/{d.pk}/modifier/", post)
        d.refresh_from_db()
        self.assertTrue(d.est_concordat)
        self.assertTrue(any("tiers" in a for a in fsl.alertes(d)))          # remise < 1/3 de la dette
        codes = [c for c, _ in documents_du_dossier(d)]
        for c in (FormulaireOfficiel.FORMULAIRE_MAINTIEN, FormulaireOfficiel.CONTRAT_PRET, FormulaireOfficiel.ENGAGEMENTS,
                  FormulaireOfficiel.CONVENTION_CONCORDAT, FormulaireOfficiel.IDENTIFICATION_LOGEMENT):
            self.assertIn(c, codes)
        attendues = {c for c, _, _ in fsl.pieces_attendues(d)}
        self.assertTrue({"convention_concordat", "ccapex", "kbis"} <= attendues)
        pdf, _ = dossier(d)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(d.total_propose, 1500)
