# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/tests_expulsion_commissions.py
"""Commissions de la prévention des expulsions : séance, ordre du jour, actualisation préremplie, visa, envoi, avis,
convocation avant commission, passerelles. Données fictives."""
from datetime import timedelta

from django.core import mail
from django.test import override_settings
from django.utils import timezone

from .models import CommissionExpulsion as K, ConvocationExpulsion as C, DossierExpulsion as D, PassageCommission as P
from .models import EnvoiDossier, EtapeExpulsion
from .tests_expulsion import _Base


class CommissionsTests(_Base):
    def setUp(self):
        super().setUp()
        self.nouveau(mds=self.mds.pk, code_usager="EX-1", loyer="650", charges="50", loyer_total="700", dette="2400")
        self.d = D.objects.get()
        self.d.referent = self.ts
        self.d.save()
        EtapeExpulsion.objects.create(dossier=self.d, type_etape="JUGEMENT", date=timezone.localdate() - timedelta(days=200),
                                      commentaire="Résiliation, délai de 3 mois (fictif)")
        self.ts_c = self.client_de(self.ts)

    def seance(self, client=None, **extra):
        donnees = {"type_commission": "PREFECTORALE", "nom": "Commission préfectorale (fictif)",
                   "date": (timezone.localdate() + timedelta(days=20)).isoformat(),
                   "date_limite": (timezone.localdate() + timedelta(days=10)).isoformat(),
                   "email": "commission@example.com", "mds": [self.mds.pk]}
        donnees.update(extra)
        return (client or self.client_de(self.sl_agent)).post("/logement/expulsions/commissions/nouvelle/", donnees)

    def test_seance_inscription_actualisation_preremplie(self):
        self.assertEqual(self.seance().status_code, 302)
        k = K.objects.get()
        # un agent de la MDS ne crée pas de séance ; le cadre de la MDS, oui
        self.assertEqual(self.seance(self.ts_c).status_code, 403)
        self.assertEqual(self.seance(self.client_de(self.cadre), nom="CAPEX locale (fictif)",
                                     type_commission="LOCALE").status_code, 302)
        r = self.ts_c.post(f"/logement/expulsions/commissions/{k.pk}/inscrire/", {"dossier": self.d.pk, "retour": "dossier"})
        self.assertRedirects(r, f"/logement/expulsions/{self.d.pk}/", fetch_redirect_response=False)
        p = P.objects.get()
        a = p.actualisation
        self.assertEqual((a["loyer_hc"], a["charges"], a["dette_montant"], a["num_caf"] if "num_caf" in a else ""),
                         ("650", "50", "2400", ""))
        self.assertIn("Jugement", a["historique_dette"])
        self.assertIn("ESSAI", a["parent1"])
        odj = self.ts_c.get(f"/logement/expulsions/commissions/{k.pk}/ordre-du-jour.pdf")
        self.assertTrue(odj.content.startswith(b"%PDF"))
        # un agent d'une autre MDS ne voit pas le dossier dans l'ordre du jour
        r = self.client_de(self.ts_autre).get(f"/logement/expulsions/commissions/{k.pk}/")
        self.assertEqual(r.status_code, 403)                                     # séance d'une autre MDS

    def test_visa_envoi_et_avis(self):
        self.seance()
        k = K.objects.get()
        from .services.commissions import inscrire
        p, _ = inscrire(k, self.d, self.ts)
        self.ts_c.post(f"/logement/expulsions/passage/{p.pk}/", dict(p.actualisation, evaluation="Situation fictive."))
        self.ts_c.post(f"/logement/expulsions/passage/{p.pk}/action/", {"action": "demander_visa"})
        self.assertEqual(self.ts_c.post(f"/logement/expulsions/passage/{p.pk}/action/", {"action": "viser"}).status_code, 403)
        self.client_de(self.cadre).post(f"/logement/expulsions/passage/{p.pk}/action/", {"action": "viser"})
        p.refresh_from_db()
        self.assertEqual(p.statut, P.VISEE)
        r = self.ts_c.get(f"/logement/envoi/actualisation/{p.pk}/")
        self.assertContains(r, "commission@example.com")
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            self.ts_c.post(f"/logement/envoi/actualisation/{p.pk}/", {"action": "mail", "destinataire": "commission@example.com",
                                                                       "objet": "Actualisation", "message": "Bonjour"})
        p.refresh_from_db()
        self.assertEqual((p.statut, len(mail.outbox)), (P.TRANSMISE, 1))
        self.assertTrue(EnvoiDossier.objects.filter(nature="Actualisation", mode="MAIL").exists())
        # avis : le Service Logement (ou le cadre) ; l'étape s'ajoute au dossier
        self.assertEqual(self.ts_c.post(f"/logement/expulsions/passage/{p.pk}/action/",
                                        {"action": "avis", "avis": "DELAI"}).status_code, 403)
        self.client_de(self.sl_agent).post(f"/logement/expulsions/passage/{p.pk}/action/",
                                           {"action": "avis", "avis": "DELAI", "avis_detail": "Revoir dans 6 mois."})
        p.refresh_from_db()
        self.assertEqual(p.avis, "DELAI")
        e = EtapeExpulsion.objects.get(dossier=self.d, type_etape="COMMISSION_PREFECTORALE")
        self.assertIn("Délai supplémentaire", e.commentaire)
        r = self.client_de(self.sl_cadre).get("/logement/expulsions/statistiques/")
        self.assertEqual(r.context["s"]["par_avis"], [("Délai supplémentaire", 1)])

    def test_convocation_avant_commission_ne_compte_pas_pour_la_carence(self):
        self.seance()
        k = K.objects.get()
        from .services.commissions import inscrire
        p, _ = inscrire(k, self.d, self.ts)
        j = timezone.localdate() + timedelta(days=5)
        for _ in range(2):
            self.ts_c.post(f"/logement/expulsions/passage/{p.pk}/action/",
                           {"action": "convoquer", "date": j.isoformat(), "heure": "09:00", "agent": self.ts.pk})
        self.assertEqual(list(C.objects.order_by('pk').values_list("type_convocation", flat=True)), ["COM_1", "COM_2"])
        for c in C.objects.all():
            self.ts_c.post(f"/logement/expulsions/convocation/{c.pk}/noter/", {"statut": "ABSENT"})
            pdf = self.ts_c.get(f"/logement/expulsions/convocation/{c.pk}/courrier.pdf")
            self.assertTrue(pdf.content.startswith(b"%PDF"))
        from .services.expulsion_mds import carence_possible
        self.assertFalse(carence_possible(self.d))

    def test_passerelles_depuis_le_dossier(self):
        r = self.ts_c.get(f"/logement/expulsions/{self.d.pk}/")
        self.assertTrue(r.context["passerelles"])
        self.assertContains(r, "FSL maintien ou concordat")
        self.assertFalse(self.client_de(self.sl_agent).get(f"/logement/expulsions/{self.d.pk}/").context["passerelles"])
