# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/tests_expulsion_mds.py
"""Prévention des expulsions, côté MDS : convocations, questionnaire bailleur, DSF (Cerfa), carence, visa, envoi.
Données fictives."""
from datetime import timedelta
from decimal import Decimal

from django.core import mail
from django.test import override_settings
from django.utils import timezone

from planning.models import CreneauRdv

from .models import ConvocationExpulsion as C, DestinataireExpulsion, DiagnosticExpulsion as G, DossierExpulsion as D
from .models import EnvoiDossier, EtapeExpulsion
from .services import dsf
from .tests_expulsion import _Base


class ExpulsionMDSTests(_Base):
    def setUp(self):
        super().setUp()
        self.nouveau(mds=self.mds.pk, code_usager="EX-1", loyer="650", charges="50", dette="2400",
                     tribunal="Tribunal judiciaire (fictif)")
        self.d = D.objects.get()
        self.d.referent = self.ts
        self.d.save()
        self.c = self.client_de(self.ts)

    def convoquer(self, jours=5):
        j = timezone.localdate() + timedelta(days=jours)
        return self.c.post(f"/logement/expulsions/{self.d.pk}/convoquer/",
                           {"date": j.isoformat(), "heure": "10:00", "agent": self.ts.pk})

    def test_convocations_agenda_courrier_et_carence(self):
        r = self.convoquer()
        self.assertEqual(r.status_code, 302)
        conv = C.objects.get()
        self.assertEqual(conv.type_convocation, C.DSF_1)
        self.assertEqual((conv.rdv.agent, conv.rdv.beneficiaire, conv.rdv.statut), (self.ts, self.b, 'RESERVE'))
        pdf = self.c.get(f"/logement/expulsions/convocation/{conv.pk}/courrier.pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.c.post(f"/logement/expulsions/convocation/{conv.pk}/noter/", {"statut": "ABSENT"})
        conv.refresh_from_db()
        self.assertEqual((conv.statut, CreneauRdv.objects.get().statut), ("ABSENT", "ABSENT"))
        self.convoquer(10)
        deuxieme = C.objects.order_by('-pk').first()
        self.assertEqual(deuxieme.type_convocation, C.DSF_2)
        self.c.post(f"/logement/expulsions/convocation/{deuxieme.pk}/noter/", {"statut": "ABSENT"})
        r = self.c.get(f"/logement/expulsions/{self.d.pk}/")
        self.assertTrue(r.context["carence_possible"])
        # un agent d'une autre MDS ne convoque pas
        self.assertEqual(self.client_de(self.ts_autre).post(f"/logement/expulsions/{self.d.pk}/convoquer/",
                                                             {"date": "2026-12-01", "heure": "10:00"}).status_code, 403)

    def test_dsf_prerempli_cerfa_rempli(self):
        self.c.post(f"/logement/expulsions/{self.d.pk}/diagnostic/", {"type_document": "DSF"})
        g = G.objects.get()
        self.assertEqual((g.donnees["Noms"], g.donnees["Montant dette"], g.donnees["Loyer"]), ("ESSAI", "2400", "650"))
        donnees = dict(g.donnees, **{"Salaire_net_1": "1000", "Evaluation sociale": "Évaluation fictive.",
                                     "Perte emploi": "1", "situation loca": "célibataire"})
        self.c.post(f"/logement/expulsions/diagnostic/{g.pk}/modifier/", donnees)
        g.refresh_from_db()
        self.assertTrue(g.donnees["Perte emploi"])
        self.assertEqual(dsf.calculs(g.donnees)["Taux_d_effort"], "70,0 %")      # (650 + 50) / 1000
        pdf = self.c.get(f"/logement/expulsions/diagnostic/{g.pk}/document.pdf").content
        from io import BytesIO
        from pypdf import PdfReader
        lecteur = PdfReader(BytesIO(pdf))
        self.assertEqual(len(lecteur.pages), 5)                                   # sans la notice
        champs = lecteur.get_fields()
        self.assertEqual(champs["Noms"]["/V"], "ESSAI")
        self.assertEqual(champs["TOTAL1"]["/V"], "1000")

    def test_visa_du_cadre_puis_envoi_au_greffe(self):
        DestinataireExpulsion.objects.create(nom="Greffe (fictif)", email="greffe@example.com")
        self.c.post(f"/logement/expulsions/{self.d.pk}/diagnostic/", {"type_document": "DSF"})
        g = G.objects.get()
        # pas d'envoi sans visa
        self.assertEqual(self.c.get(f"/logement/envoi/dsf/{g.pk}/").status_code, 302)
        self.c.post(f"/logement/expulsions/diagnostic/{g.pk}/action/", {"action": "demander_visa"})
        g.refresh_from_db()
        self.assertEqual(g.statut, G.A_VISER)
        # un agent ne vise pas ; le cadre de la MDS, oui
        self.assertEqual(self.c.post(f"/logement/expulsions/diagnostic/{g.pk}/action/", {"action": "viser"}).status_code, 403)
        self.client_de(self.cadre).post(f"/logement/expulsions/diagnostic/{g.pk}/action/", {"action": "viser"})
        g.refresh_from_db()
        self.assertEqual((g.statut, g.cadre), (G.VISE, self.cadre))
        r = self.c.get(f"/logement/envoi/dsf/{g.pk}/")
        self.assertContains(r, "greffe@example.com")
        self.assertIn("Diagnostic social et financier", r.context["objet"])
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            self.c.post(f"/logement/envoi/dsf/{g.pk}/", {"action": "mail", "destinataire": "greffe@example.com",
                                                         "objet": "DSF", "message": "Bonjour"})
        g.refresh_from_db()
        self.assertEqual(g.statut, G.ENVOYE)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].reply_to, [self.mds.email] if self.mds.email else [])
        self.assertTrue(EnvoiDossier.objects.filter(nature="DSF", mode="MAIL").exists())
        self.assertTrue(EtapeExpulsion.objects.filter(dossier=self.d, type_etape="DSF").exists())

    def test_carence_menage_inconnu_de_cid(self):
        self.d.beneficiaire = None
        self.d.numero_exploc = "EXPLOC-FICTIF"
        self.d.save()
        self.c.post(f"/logement/expulsions/{self.d.pk}/diagnostic/", {"type_document": "CARENCE"})
        g = G.objects.get()
        self.c.post(f"/logement/expulsions/diagnostic/{g.pk}/action/",
                    {"action": "demander_visa", "convocations": "05/11/2026, 19/11/2026"})
        self.client_de(self.cadre).post(f"/logement/expulsions/diagnostic/{g.pk}/action/", {"action": "viser"})
        r = self.c.get(f"/logement/envoi/dsf/{g.pk}/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("ESSAI", r.context["objet"])
        self.c.post(f"/logement/envoi/dsf/{g.pk}/", {"action": "imprimer"})
        g.refresh_from_db()
        self.assertEqual(g.statut, G.ENVOYE)
        self.assertTrue(EnvoiDossier.objects.filter(nature="Bordereau de carence", mode="IMPRIME").exists())

    def test_questionnaire_bailleur(self):
        retour = timezone.localdate() + timedelta(days=12)
        r = self.c.post(f"/logement/expulsions/{self.d.pk}/questionnaire/",
                        {"retour": retour.isoformat(), "email": "bailleur@example.com"})
        self.assertRedirects(r, f"/logement/envoi/bailleur/{self.d.pk}/", fetch_redirect_response=False)
        pdf = self.c.get(f"/logement/expulsions/{self.d.pk}/questionnaire.pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.c.post(f"/logement/envoi/bailleur/{self.d.pk}/", {"action": "imprimer"})
        self.d.refresh_from_db()
        self.assertEqual(self.d.questionnaire_bailleur_le, timezone.localdate())
        self.assertEqual(self.d.proprietaire_email, "bailleur@example.com")
        self.assertTrue(EtapeExpulsion.objects.filter(dossier=self.d, type_etape="QUESTIONNAIRE_BAILLEUR").exists())

    def test_modifier_apres_visa_le_fait_redemander(self):
        self.c.post(f"/logement/expulsions/{self.d.pk}/diagnostic/", {"type_document": "DSF"})
        g = G.objects.get()
        g.statut, g.cadre, g.date_validation_cadre = G.VISE, self.cadre, timezone.now()
        g.save()
        self.c.post(f"/logement/expulsions/diagnostic/{g.pk}/modifier/", dict(g.donnees, Loyer="700"))
        g.refresh_from_db()
        self.assertEqual((g.statut, g.cadre), (G.BROUILLON, None))

    def test_etat_des_cases_mal_encodees(self):
        self.assertEqual(dsf._etat(['/C閘ibataire', '/marié'], "célibataire"), '/C閘ibataire')
        self.assertEqual(dsf._etat(['/oui', '/non'], "non"), '/non')
        self.assertEqual(dsf.montant(Decimal("650.00")), "650")
