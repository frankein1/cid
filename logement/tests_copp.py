# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/tests_copp.py
"""Demande de logement social, commission des publics prioritaires, envoi par mail / impression, papier économisé,
visa du cadre. Données fictives ; aucun vrai formulaire."""
import io
from datetime import date, timedelta
from io import StringIO

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from beneficiaire.models import Beneficiaire, BudgetFoyer, LienFamilial
from core.models import Profil, User
from mds.models import MDS, SignatureAgent, UserMDSProfile

from .models import (CommissionPublicsPrioritaires, DemandeFSL, DemandeLogementSocial, EnvoiDossier, SaisineCOPP)
from .services import circuit, copp, envoi
from .services.placements_fsl import valeurs, visa


def png():
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', (60, 20), 'white').save(buf, 'PNG')
    return buf.getvalue()


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class LogementCOPPTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.mds = MDS.objects.create(code_mds="TC1", nom="MDS ESSAI", adresse="1 rue A", code_postal="13110",
                                      ville="Port-de-Bouc", email="mds@exemple.fr")
        self.prox = MDS.objects.create(code_mds="TC2", nom="MDS PROCHE", adresse="2 rue B", code_postal="13500",
                                       ville="Martigues", type_mds=MDS.PROXIMITE, mds_territoire=self.mds)
        self.ts = self.agent("amina", self.mds, "MDS_AGENTS_SOCIAUX")
        self.cadre = self.agent("hugo", self.mds, "MDS_RESPONSABLE")
        self.mds.responsable = self.cadre
        self.mds.save()
        self.b = Beneficiaire.objects.create(code_interne="CO-1", civilite="MME", nom="ESSAI", prenom="Clara",
                                             date_naissance=date(1990, 1, 1), adresse="3 rue C", code_postal="13110",
                                             ville="Port-de-Bouc", mds=self.mds, numero_caf="1234567", nir="290010000000000")
        self.c = Beneficiaire.objects.create(code_interne="CO-2", civilite="M.", nom="ESSAI", prenom="Yanis",
                                             date_naissance=date(1988, 5, 5), adresse="3 rue C", code_postal="13110",
                                             ville="Port-de-Bouc", mds=self.mds)
        LienFamilial.objects.create(personne_a=self.b, personne_b=self.c, type_lien="CONJOINT", vit_au_foyer=True)
        BudgetFoyer.objects.create(beneficiaire=self.b, nb_personnes_foyer=2, ressources={"v": 2, "lignes": {
            "salaire": {"demandeur": "1200", "conjoint": "0", "autres": "0"},
            "chomage": {"demandeur": "0", "conjoint": "600", "autres": "0"},
            "logement": {"demandeur": "200", "conjoint": "0", "autres": "0"}}, "precisions": {}},
            charges={"v": 2, "lignes": {"loyer": {"payee": "650", "non_payee": "0"}}, "precisions": {}},
            dettes=[{"creancier": "Fournisseur fictif", "montant": "300"}])
        self.seance = CommissionPublicsPrioritaires.objects.create(date=timezone.localdate() + timedelta(days=30),
                                                                   date_limite_depot=timezone.localdate() + timedelta(days=12))
        self.seance.mds.add(self.mds)

    def agent(self, login, mds, profil):
        u = User.objects.create_user(login, password="x", matricule=login.upper(), first_name=login.title(),
                                     last_name="ESSAI")
        u.profils.add(Profil.objects.get(code=profil))
        UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True)
        return u

    def client_de(self, u):
        c = Client(HTTP_HOST="localhost")
        c.force_login(u)
        return c

    def test_demande_logement_social(self):
        r = self.client_de(self.ts).post("/logement/demande/CO-1/", {
            "nud": "NUD-ESSAI", "date_creation": (timezone.localdate() - timedelta(days=3 * 365 + 40)).isoformat(),
            "dalo_depose": "on", "dalo_etat": "EN_COURS", "communes": ["Martigues", "", "Fos-sur-Mer"], "pmr": "on"})
        self.assertEqual(r.status_code, 302)
        dl = DemandeLogementSocial.objects.get(beneficiaire=self.b)
        self.assertEqual(dl.communes_souhaitees, ["Martigues", "Fos-sur-Mer"])
        self.assertTrue(dl.anciennete().startswith("3 ans"))
        self.assertGreater(dl.prochain_renouvellement(), timezone.localdate())
        self.assertContains(self.client_de(self.ts).get("/beneficiaire/CO-1/"), "NUD-ESSAI")

    def test_saisine_preremplie_et_pieces(self):
        DemandeLogementSocial.objects.create(beneficiaire=self.b, nud="NUD-ESSAI", date_creation=date(2021, 3, 1),
                                             dalo_depose=True, dalo_etat="REFUSE", communes_souhaitees=["Martigues"])
        self.client_de(self.ts).post("/logement/copp/nouvelle/CO-1/")
        s = SaisineCOPP.objects.get()
        dn = s.donnees
        self.assertEqual(s.commission, self.seance)
        self.assertEqual(dn["nud"], "NUD-ESSAI")
        self.assertEqual(dn["demandeur"]["nir"], "290010000000000")
        self.assertEqual(dn["conjoint"]["prenom"], "Yanis")
        self.assertIn("Salaire 1 200,00 €", dn["nature_ressources_demandeur"])
        self.assertEqual(dn["endettement"], "OUI")
        self.assertEqual(dn["dalo"]["etat"], "REFUSE")
        fichier = SimpleUploadedFile("identite.pdf", b"%PDF-1.4 essai fictif", content_type="application/pdf")
        r = self.client_de(self.ts).post(f"/logement/copp/{s.pk}/modifier/", {
            "motif_DALO_REFUSE": "on", "motif_VIOLENCES": "on", "motif_AUTRE": "on", "motif_autre": "Situation fictive",
            "rapport_social": "Rapport fictif.", "commission": self.seance.pk, "type_piece": ["CI"],
            "nouvelles_pieces": [fichier]})
        self.assertEqual(r.status_code, 302)
        s.refresh_from_db()
        self.assertEqual(s.motifs, ["DALO_REFUSE", "VIOLENCES", "AUTRE"])
        self.assertIn("Situation fictive", s.libelles_motifs())
        self.assertEqual(s.pieces.count(), 1)                         # déposée dans la GED de l'usager
        pdf, mode = copp.dossier(s)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(mode, "trame CID")

    def test_envoi_par_mail_et_compteur(self):
        self.client_de(self.ts).post("/logement/copp/nouvelle/CO-1/")
        s = SaisineCOPP.objects.get()
        s.motifs, s.rapport_social = ["SURNOMBRE"], "Rapport fictif."
        s.save()
        c = self.client_de(self.ts)
        r = c.get(f"/logement/envoi/copp/{s.pk}/")
        objet = "MDST - Port-de-Bouc - Fiche saisine rapport social et justificatifs pour COPP - ESSAI Clara"
        self.assertContains(r, objet)
        r = c.post(f"/logement/envoi/copp/{s.pk}/", {"action": "mail", "destinataire": "copp@exemple.fr",
                                                      "objet": objet, "message": "Bonjour"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, objet)
        self.assertEqual(mail.outbox[0].attachments[0][0][-4:], ".pdf")
        s.refresh_from_db()
        self.assertEqual(s.statut, SaisineCOPP.ENVOYEE)
        e = EnvoiDossier.objects.get()
        self.assertEqual((e.mode, e.mds), (EnvoiDossier.MAIL, self.mds))
        self.assertGreater(e.pages, 0)
        self.assertFalse(hasattr(e, 'agent'))                         # jamais par agent
        stats = envoi.papier_evite()
        self.assertEqual(stats["pages_evitees"], e.pages)
        self.assertContains(c.get("/logement/papier-economise/"), "pages économisées")

    def test_objet_mds_proximite(self):
        self.b.mds = self.prox
        self.assertTrue(envoi.objet_mail(self.prox, "X", self.b).startswith("MDSP - Martigues - X"))

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.dummy.EmailBackend')
    def test_messagerie_non_reglee(self):
        self.client_de(self.ts).post("/logement/copp/nouvelle/CO-1/")
        s = SaisineCOPP.objects.get()
        s.motifs, s.rapport_social = ["SURNOMBRE"], "Rapport fictif."
        s.save()
        c = self.client_de(self.ts)
        r = c.post(f"/logement/envoi/copp/{s.pk}/", {"action": "mail", "destinataire": "copp@exemple.fr"})
        self.assertContains(r, "J'ai envoyé le dossier par mail")
        self.assertFalse(EnvoiDossier.objects.exists())
        c.post(f"/logement/envoi/copp/{s.pk}/", {"action": "mail_confirme", "pages": "6"})
        self.assertEqual(EnvoiDossier.objects.get().pages, 6)

    def test_fsl_visa_imprimer_et_signature(self):
        self.client_de(self.ts).post("/logement/fsl/nouvelle/CO-1/", {"type_aide": "ACCES"})
        d = DemandeFSL.objects.get()
        d.avis = "FAVORABLE"
        d.pieces = {c: "FOURNIE" for c in d.pieces}
        d.save()
        self.assertEqual(self.client_de(self.ts).get(f"/logement/envoi/fsl/{d.pk}/").status_code, 302)  # pas de visa
        circuit.demander_visa(d, self.ts)
        circuit.avis_cadre(d, self.cadre, True, "")                     # dossier complet : pas de note
        self.assertEqual(d.statut, DemandeFSL.VALIDEE)
        self.assertEqual(visa(d)[0][:9], "Visa H.E.")
        self.assertIsNone(visa(d)[1])                                  # pas de signature validée
        SignatureAgent.objects.create(user=self.cadre, image=png(), validee=True)
        self.assertEqual(valeurs(d, "FSL_ACCES")["visa_image"]["image"][:4], b"\x89PNG")
        r = self.client_de(self.ts).post(f"/logement/envoi/fsl/{d.pk}/", {"action": "imprimer"})
        self.assertTrue(r["Location"].endswith("?imprimer=1"))
        d.refresh_from_db()
        self.assertEqual(d.statut, DemandeFSL.ENVOYEE)
        self.assertEqual(EnvoiDossier.objects.get().mode, EnvoiDossier.IMPRIME)
        self.assertEqual(envoi.papier_evite()["pages_evitees"], 0)

    def test_acces(self):
        autre_mds = MDS.objects.create(code_mds="TC9", nom="MDS AUTRE", adresse="x", code_postal="13001", ville="Marseille")
        dehors = self.agent("ines", autre_mds, "MDS_AGENTS_SOCIAUX")
        self.assertEqual(self.client_de(dehors).post("/logement/copp/nouvelle/CO-1/").status_code, 403)
        self.assertEqual(self.client_de(dehors).get("/logement/demande/CO-1/").status_code, 403)
