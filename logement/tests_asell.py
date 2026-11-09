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
from django.test import TestCase
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
        self.op = OperateurASELL.objects.create(sigle="AE (fictif)", nom="Association Exemple (fictif)",
                                                emails="asell@example.com", thematique="GENERALISTE", territoire="Département")
        OperateurASELL.objects.create(sigle="OR (fictif)", nom="Opérateur renforcé (fictif)", emails="renforce@example.com",
                                      thematique="RENFORCE", territoire="Département")

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
        self.assertContains(r, "AE (fictif)")
        self.assertNotContains(r, "OR (fictif)")                         # opérateurs du type de mesure seulement
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


class OperateursAsellTests(TestCase):
    """Liste des opérateurs : rattachement à la commune ou à l'arrondissement, import avec cellules fusionnées."""

    def test_rattachement_commune_arrondissement_departement(self):
        from types import SimpleNamespace as NS
        from .services import asell_operateurs as AO
        op = lambda t: OperateurASELL(sigle="X", territoire=t)                       # noqa: E731
        aubagne = NS(code_postal="13400", ville="AUBAGNE")
        self.assertTrue(AO.couvre(op("Communes de Aubagne, Auriol et La Penne"), aubagne.code_postal, aubagne.ville))
        self.assertFalse(AO.couvre(op("Gardanne, Biver"), aubagne.code_postal, aubagne.ville))
        self.assertTrue(AO.couvre(op("Département"), "13400", "AUBAGNE"))
        self.assertTrue(AO.couvre(op("St Mitre les Remparts"), "13920", "SAINT MITRE LES REMPARTS"))
        self.assertTrue(AO.couvre(op("13ème et 14ème arrondissements de Marseille"), "13013", "MARSEILLE"))
        self.assertFalse(AO.couvre(op("1er, 2ème et 3ème arrondissements de Marseille"), "13013", "MARSEILLE"))
        self.assertTrue(AO.couvre(op("Marseille"), "13008", "MARSEILLE"))
        self.assertFalse(AO.couvre(op("Résidence sociale ACPM - 13013 Marseille"), "13013", "MARSEILLE"))

    def test_import_cellules_fusionnees(self):
        from .services import asell_operateurs as AO
        entete = "Sigle opérateurs;Nom opérateurs;Adresse;Code postal et ville;Téléphone;Adresses mail;Territoires;Nature;Thématique;Complément thématique\n"
        corps = ("AAA;Association A;1 rue X;13003 MARSEILLE;04;a@a.example.com;Marseille;ASELL;Généraliste;\n"
                 ";;;;;;Résidence A - 1 rue Y;;Généraliste;à public spécifique Résidence A\n"
                 ";;;;;;;;Renforcé;\n"
                 "BBB;Association B;2 rue Z;13100 AIX;04;;Aix en Provence;ASC;Ateliers Recherche Logement;\n")
        n, anciens, erreurs, avertissements = AO.importer((entete + corps).encode("utf-8"), "liste_2025.csv")
        self.assertEqual((n, anciens, erreurs), (4, 0, []))
        self.assertEqual(OperateurASELL.objects.filter(sigle="AAA", thematique="RENFORCE", territoire="Marseille").count(), 1)
        self.assertEqual(OperateurASELL.objects.get(territoire__startswith="Résidence").public_specifique, "Résidence A")
        self.assertEqual(OperateurASELL.objects.get(sigle="BBB").nature, "ASC")
        self.assertEqual(OperateurASELL.objects.first().annee, 2025)
        self.assertEqual(OperateurASELL.objects.get(sigle="AAA", thematique="GENERALISTE", public_specifique="").territoire, "Marseille")
        self.assertTrue(any("sans sigle" in a for a in avertissements))
        # un nouvel import désactive l'ancienne liste sans l'effacer
        n2, anciens2, erreurs2, _ = AO.importer((entete + "CCC;C;;;;;Autre;ASELL;Généraliste;\n").encode(), "x.csv")
        self.assertEqual((n2, anciens2, erreurs2), (1, 4, []))
        self.assertEqual(OperateurASELL.objects.filter(actif=True).count(), 1)
        # fichier invalide : rien n'est enregistré
        n3, _, erreurs3, _ = AO.importer(("Nom;Autre\nX;Y\n").encode(), "bad.csv")
        self.assertTrue(erreurs3 and n3 == 0 and OperateurASELL.objects.filter(actif=True).count() == 1)
