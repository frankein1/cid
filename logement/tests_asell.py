# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/tests_asell.py
"""Orientation ASELL : fiche généraliste ou renforcée préremplie (usager, dossier d'expulsion), envoi à l'opérateur,
réponse, droits. Données fictives."""
from datetime import timedelta

from django.core import mail
from django.test import override_settings
from django.utils import timezone

from .models import DossierExpulsion as D, EnvoiDossier, EtapeExpulsion, OperateurASELL, OrientationASELL as A
from .tests_expulsion import _Base


class AsellTests(_Base):
    def setUp(self):
        super().setUp()
        self.ts_c = self.client_de(self.ts)
        self.b.telephone_mobile, self.b.numero_caf = "0600000001", "7654321"
        self.b.save()
        self.op = OperateurASELL.objects.create(nom="Association Exemple (fictif)", email="asell@example.com")
        OperateurASELL.objects.create(nom="Opérateur renforcé (fictif)", email="renforce@example.com", generaliste=False)

    def nouvelle(self, client=None, **donnees):
        base = {"type_mesure": "GENERALISTE", "volet": "ACCES"}
        base.update(donnees)
        return (client or self.ts_c).post(f"/logement/asell/nouvelle/{self.b.code_interne}/", base)

    def test_generaliste_preremplie_envoi_reponse(self):
        self.assertEqual(self.nouvelle(self.client_de(self.ts_autre)).status_code, 403)
        self.nouvelle()
        a = A.objects.get()
        v = a.donnees
        self.assertEqual((v["nom_prenom"], v["num_caf"], v["telephone"], v["composition"], v["fsl_en_cours"], v["asell_deja"]),
                         ("ESSAI Clara", "7654321", "0600000001", "Personne isolée", "non", "non"))
        self.nouvelle()                                                  # le brouillon est repris
        self.assertEqual(A.objects.count(), 1)
        r = self.ts_c.get(f"/logement/asell/{a.pk}/")
        self.assertContains(r, "Association Exemple")
        self.assertNotContains(r, "Opérateur renforcé")                  # opérateurs du type de mesure seulement
        # pas d'envoi sans opérateur ni évaluation
        r = self.ts_c.get(f"/logement/envoi/asell/{a.pk}/")
        self.assertRedirects(r, f"/logement/asell/{a.pk}/", fetch_redirect_response=False)
        self.ts_c.post(f"/logement/asell/{a.pk}/", dict(
            {k: x for k, x in v.items() if isinstance(x, str)}, operateur=self.op.pk, volet="ACCES",
            motifs=["Absence de logement", "Autre", "Inconnu"], evaluation="Situation fictive.", statut_logement="Hébergement"))
        a.refresh_from_db()
        self.assertEqual((a.operateur, a.donnees["motifs"]), (self.op, ["Absence de logement", "Autre"]))
        self.assertTrue(self.ts_c.get(f"/logement/asell/{a.pk}/fiche.pdf").content.startswith(b"%PDF"))
        self.assertContains(self.ts_c.get(f"/logement/envoi/asell/{a.pk}/"), "asell@example.com")
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            self.ts_c.post(f"/logement/envoi/asell/{a.pk}/", {"action": "mail", "destinataire": "asell@example.com",
                                                               "objet": "Orientation", "message": "Bonjour"})
        a.refresh_from_db()
        self.assertEqual((a.statut, len(mail.outbox)), (A.ENVOYEE, 1))
        self.assertTrue(EnvoiDossier.objects.filter(nature="ASELL", mode="MAIL").exists())
        self.assertEqual(self.ts_c.post(f"/logement/asell/{a.pk}/", {"evaluation": "x"}).status_code, 403)   # envoyée
        self.ts_c.post(f"/logement/asell/{a.pk}/action/", {"action": "reponse", "reponse": "ACCORD", "detail": "Début en décembre"})
        a.refresh_from_db()
        self.assertEqual(a.reponse, "ACCORD")
        self.assertEqual(self.client_de(self.ts_autre).get(f"/logement/asell/{a.pk}/").status_code, 403)
        # la fiche suivante sait qu'une mesure a déjà été demandée
        self.nouvelle(type_mesure="RENFORCE", volet="MAINTIEN")
        self.assertEqual(A.objects.latest('pk').donnees["asell_deja"], "oui")
        self.assertContains(self.ts_c.get(f"/beneficiaire/{self.b.code_interne}/"), "asell-nouvelle")

    def test_renforce_depuis_le_dossier_d_expulsion(self):
        self.nouveau(mds=self.mds.pk, code_usager="EX-1", dette="2400", loyer_total="700", type_bailleur="SOCIAL",
                     proprietaire="Office HLM Exemple (fictif)")
        d = D.objects.get()
        j = timezone.localdate()
        EtapeExpulsion.objects.create(dossier=d, type_etape="ASSIGNATION", date=j - timedelta(days=90))
        EtapeExpulsion.objects.create(dossier=d, type_etape="COMMANDEMENT_QUITTER", date=j - timedelta(days=10))
        self.assertContains(self.ts_c.get(f"/logement/expulsions/{d.pk}/"), "Orientation ASELL renforcé")
        self.nouvelle(type_mesure="RENFORCE", volet="MAINTIEN", dossier_expulsion=d.pk)
        a = A.objects.get()
        v = a.donnees
        self.assertEqual(a.dossier_expulsion, d)
        self.assertEqual((v["statut_logement"], v["bailleur"], v["dette_montant"], v["loyer"], v["motifs"]),
                         ("Parc public", "Office HLM Exemple (fictif)", "2400", "700", ["Dette locative"]))
        self.assertEqual((v["assignation_date"], v["commandement_quitter_date"], v["fsl_deja"]),
                         (f"{j - timedelta(days=90):%d/%m/%Y}", f"{j - timedelta(days=10):%d/%m/%Y}", "non"))
        d.refresh_from_db()
        self.assertEqual(d.historique[-1]["action"], "Orientation ASELL préparée")
        self.ts_c.post(f"/logement/asell/{a.pk}/action/", {"action": "supprimer"})
        self.assertFalse(A.objects.exists())
