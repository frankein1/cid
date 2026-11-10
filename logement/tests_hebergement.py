# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/tests_hebergement.py
"""Hébergement d'urgence : ouverture depuis l'usager, démarches, fiche conseillée, préremplissage, visa du cadre,
envoi, réponse, renouvellement et échéances, clôture, durée de conservation. Données fictives."""
from datetime import date, timedelta

from django.core import mail
from django.test import override_settings
from django.utils import timezone

from beneficiaire.models import Beneficiaire, LienFamilial
from messagerie.models import Message

from .models import (DemarcheHebergement as M, DestinataireHebergement, DossierHebergement as D, EnvoiDossier,
                     FicheHebergement as F, StructureHebergement)
from .services import hebergement as H
from .tests_expulsion import _Base


class HebergementTests(_Base):
    def setUp(self):
        super().setUp()
        j = timezone.localdate()
        self.bebe = Beneficiaire.objects.create(code_interne="EX-2", civilite="M.", nom="ESSAI", prenom="Noam",
                                                date_naissance=j - timedelta(days=400), lieu_naissance="Martigues",
                                                adresse="3 rue C", code_postal="13110", ville="Port-de-Bouc", mds=self.mds)
        LienFamilial.objects.create(personne_a=self.b, personne_b=self.bebe, type_lien="ENFANT", vit_au_foyer=True)
        self.b.telephone_mobile = "0600000001"
        self.b.save()
        self.ts_c, self.cadre_c = self.client_de(self.ts), self.client_de(self.cadre)
        self.structure = StructureHebergement.objects.create(nom="Accueil fictif", ville="Martigues",
                                                             duree_initiale_jours=30, duree_renouvellement_jours=30)
        DestinataireHebergement.objects.create(nom="Service d'appui (fictif)", email="appui@example.com")

    def ouvrir(self):
        r = self.ts_c.post(f"/logement/hebergement/nouveau/{self.b.code_interne}/")
        d = D.objects.get()
        self.assertRedirects(r, f"/logement/hebergement/{d.pk}/", fetch_redirect_response=False)
        return d

    def action(self, d, client=None, **donnees):
        return (client or self.ts_c).post(f"/logement/hebergement/{d.pk}/action/", donnees)

    def fiche(self, d, type_fiche="SAS"):
        self.action(d, action="fiche", type_fiche=type_fiche)
        return d.fiches.filter(type_fiche=type_fiche).latest('pk')

    def test_ouverture_droits_et_dossier_unique(self):
        d = self.ouvrir()
        self.assertTrue(d.numero.startswith(f"HU-{timezone.localdate().year}-"))
        self.assertEqual((d.mds, d.statut), (self.mds, D.RECHERCHE))
        self.ouvrir()                                                    # le dossier ouvert est repris
        self.assertEqual(D.objects.count(), 1)
        autre = self.client_de(self.ts_autre)
        self.assertEqual(autre.get(f"/logement/hebergement/{d.pk}/").status_code, 403)
        self.assertEqual(autre.post(f"/logement/hebergement/nouveau/{self.b.code_interne}/").status_code, 403)
        self.assertNotContains(autre.get("/logement/hebergement/"), d.numero)
        self.assertContains(self.ts_c.get("/logement/hebergement/"), d.numero)
        self.assertContains(self.ts_c.get(f"/beneficiaire/{self.b.code_interne}/"), "hebergement-usager-encart")

    def test_fiche_conseillee_et_controles(self):
        d = self.ouvrir()
        self.assertEqual(H.fiche_conseillee(self.b)[0], F.SAS)          # mère isolée, enfant de moins de 3 ans
        self.assertEqual(len(H.controles(d, F.SAS)), 3)                 # 115, SIAO, centres maternels
        for t in ("115", "SIAO", "CENTRE_MATERNEL"):
            self.action(d, action="demarche", type_demarche=t, reponse="Pas de place")
        self.assertEqual(H.controles(d, F.SAS), [])
        self.bebe.date_naissance = date(2015, 5, 1)
        self.bebe.save()
        self.assertEqual(H.fiche_conseillee(self.b)[0], F.ETAT)
        m = M.objects.first()
        self.action(d, action="demarche_supprimer", demarche=m.pk)
        self.assertEqual(M.objects.count(), 2)

    def test_demande_preremplie_visa_envoi_accord(self):
        d = self.ouvrir()
        self.action(d, action="demarche", type_demarche="115", reponse="Pas de place")
        f = self.fiche(d)
        v = f.donnees
        self.assertEqual([(p["qualite"], p["prenom"]) for p in v["personnes"]], [("Mère", "Clara"), ("Enfant", "Noam")])
        self.assertEqual((v["telephone"], v["personnes"][1]["lieu"]), ("0600000001", "Martigues"))
        self.assertNotIn("ip", v)                                        # jamais prérempli
        donnees = {"p0_qualite": "Mère", "p0_autorite": "oui", "p0_nom": "ESSAI", "p0_prenom": "Clara",
                   "rev_rsa": "560", "rev_caf": "190", "rev_caf_detail": "PAJE", "ip": "non",
                   "parcours_logement": "Hébergée chez un tiers jusqu'en octobre (fictif).", "analyse": "Situation fictive."}
        self.ts_c.post(f"/logement/hebergement/fiche/{f.pk}/", donnees)
        f.refresh_from_db()
        self.assertEqual((f.donnees["rev_rsa"], f.donnees["ip"], len(f.donnees["personnes"])), ("560", "non", 1))
        # pas d'envoi sans le visa du cadre ; l'agent ne vise pas lui-même
        r = self.ts_c.get(f"/logement/envoi/hebergement/{f.pk}/")
        self.assertRedirects(r, f"/logement/hebergement/fiche/{f.pk}/", fetch_redirect_response=False)
        act = f"/logement/hebergement/fiche/{f.pk}/action/"
        self.ts_c.post(act, {"action": "demander_visa"})
        self.assertTrue(Message.objects.filter(destinataire=self.cadre, objet__startswith="Visa demandé").exists())
        self.assertEqual(self.ts_c.post(act, {"action": "viser"}).status_code, 403)
        self.cadre_c.post(act, {"action": "viser"})
        f.refresh_from_db()
        self.assertEqual((f.statut, f.cadre), (F.VISEE, self.cadre))
        pdf = self.ts_c.get(f"/logement/hebergement/fiche/{f.pk}/fiche.pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertContains(self.ts_c.get(f"/logement/envoi/hebergement/{f.pk}/"), "appui@example.com")
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            self.ts_c.post(f"/logement/envoi/hebergement/{f.pk}/", {"action": "mail", "destinataire": "appui@example.com",
                                                                     "objet": "Demande", "message": "Bonjour",
                                                                     "justification_pieces": "Pièces en cours (fictif)."})
        f.refresh_from_db()
        self.assertEqual((f.statut, len(mail.outbox)), (F.ENVOYEE, 1))
        self.assertTrue(EnvoiDossier.objects.filter(mode="MAIL").exists())
        # une fiche transmise ne se modifie plus
        self.assertEqual(self.ts_c.post(f"/logement/hebergement/fiche/{f.pk}/", donnees).status_code, 403)
        entree = timezone.localdate()
        self.ts_c.post(act, {"action": "reponse", "reponse": "ACCORD", "structure": self.structure.pk,
                             "date_entree": entree.isoformat()})
        d.refresh_from_db()
        self.assertEqual((d.statut, d.structure, d.date_fin_prevue), (D.HEBERGE, self.structure, entree + timedelta(days=30)))

    def test_modifier_apres_visa_redemande_le_visa(self):
        d = self.ouvrir()
        f = self.fiche(d, "ETAT")
        H.viser(f, self.cadre)
        self.ts_c.post(f"/logement/hebergement/fiche/{f.pk}/", {"situation_familiale": "Texte fictif."})
        f.refresh_from_db()
        self.assertEqual((f.statut, f.cadre), (F.BROUILLON, None))

    def test_renouvellement_echeance_et_alerte(self):
        d = self.ouvrir()
        j = timezone.localdate()
        f = self.fiche(d)
        f.donnees["parcours_logement"] = "Parcours fictif."
        f.save()
        H.viser(f, self.cadre)
        H.marquer_transmis(f, self.ts, "MAIL")
        H.enregistrer_reponse(f, self.ts, F.ACCORD, j - timedelta(days=80), date_entree=j - timedelta(days=80))
        d.refresh_from_db()
        self.assertEqual(d.date_fin_prevue, H.fin_apres(j - timedelta(days=80), 3))     # 3 mois, sans structure réglée
        d.referent = self.ts
        d.save()
        self.assertEqual(H.alerter(), 1)                                 # échéance dans moins de 3 semaines
        self.assertEqual(H.alerter(), 0)                                 # une seule fois par échéance
        self.assertTrue(Message.objects.filter(destinataire=self.ts, objet__contains="échéance").exists())
        self.assertContains(self.ts_c.get(f"/logement/hebergement/{d.pk}/"), "hebergement-echeance")
        r = self.fiche(d, "RENOUV")
        self.assertEqual((r.donnees["duree"], r.donnees["renouvellement_du"]), ("3 mois", f"{d.date_fin_prevue:%d/%m/%Y}"))
        self.assertEqual(r.donnees["parcours_logement"] if "parcours_logement" in r.donnees else "", "")
        self.assertEqual(len(r.donnees["personnes"]), 2)
        fin = d.date_fin_prevue
        H.viser(r, self.cadre)
        H.marquer_transmis(r, self.ts, "MAIL")
        H.enregistrer_reponse(r, self.ts, F.ACCORD, j)
        d.refresh_from_db()
        self.assertEqual(d.date_fin_prevue, H.fin_apres(fin, 3))
        self.assertEqual(H.duree_renouvellement(d), 2)                   # ensuite, par périodes de 2 mois
        # une demande ne se prépare pas pendant l'hébergement
        self.action(d, action="fiche", type_fiche="FINAL")
        self.assertTrue(d.fiches.filter(type_fiche="FINAL").exists())

    def test_cloture_efface_le_numero_du_titre(self):
        d = self.ouvrir()
        f = self.fiche(d, "ETAT")
        self.ts_c.post(f"/logement/hebergement/fiche/{f.pk}/", {"identite_numero": "0000000000", "identite_type": "Titre de séjour"})
        f.refresh_from_db()
        self.assertEqual(f.donnees["identite_numero"], "0000000000")
        self.action(d, action="cloturer", motif="PERSONNELLE")
        f.refresh_from_db()
        d.refresh_from_db()
        self.assertEqual((d.statut, "identite_numero" in f.donnees, f.donnees["identite_type"]), (D.CLOS, False, "Titre de séjour"))
        self.assertEqual(self.action(d, action="demarche", type_demarche="115").status_code, 403)   # clos : lecture seule
        self.action(d, action="rouvrir")
        d.refresh_from_db()
        self.assertEqual(d.statut, D.RECHERCHE)

    def test_statistiques_sans_donnee_par_agent(self):
        d = self.ouvrir()
        self.action(d, action="demarche", type_demarche="115")
        self.assertEqual(self.ts_c.get("/logement/hebergement/statistiques/").status_code, 403)
        r = self.cadre_c.get("/logement/hebergement/statistiques/")
        self.assertEqual((r.context["s"]["total"], r.context["s"]["par_demarche"]), (1, [("Appel au 115", 1)]))
        self.assertNotContains(r, "Amina")

    def test_duree_de_conservation(self):
        from core.models import DureeConservation
        from .services.conservation import purger_hebergement
        d = self.ouvrir()
        f = self.fiche(d)
        H.cloturer(d, self.ts, "LOGEMENT")
        D.objects.filter(pk=d.pk).update(date_cloture=timezone.localdate() - timedelta(days=800))
        self.assertEqual(purger_hebergement(), 0)                        # rien tant que le DPO n'a pas fixé la durée
        DureeConservation.objects.create(code="HEBERGEMENT_URGENCE", base_active_mois=12, archivage_mois=12,
                                         sort_final="ANONYMISATION")
        self.assertEqual(purger_hebergement(), 1)
        d.refresh_from_db()
        f.refresh_from_db()
        self.assertEqual((d.beneficiaire, d.historique, f.donnees, d.motif_cloture), (None, [], {}, "LOGEMENT"))
        self.assertEqual(self.cadre_c.get(f"/logement/hebergement/{d.pk}/").status_code, 200)
        DureeConservation.objects.filter(code="HEBERGEMENT_URGENCE").update(sort_final="SUPPRESSION")
        D.objects.filter(pk=d.pk).update(anonymise_le=None)
        purger_hebergement()
        self.assertFalse(D.objects.exists())

    def test_copie_de_test_anonymisee(self):
        """L'anonymiseur de base couvre le logement : fiches, démarches, dossiers d'expulsion."""
        import os
        from io import StringIO
        from unittest import mock
        from django.conf import settings
        from django.core.management import call_command
        from .models import DossierExpulsion
        d = self.ouvrir()
        self.action(d, action="demarche", type_demarche="115", reponse="Rappeler Mme ESSAI demain")
        f = self.fiche(d)
        self.nouveau(mds=self.mds.pk, numero_allocataire="1234567")
        with mock.patch.dict(os.environ, {"CID_ANONYMISATION_AUTORISEE": "1"}):
            call_command("anonymiser_base", "--base", settings.DATABASES["default"]["NAME"], "--confirmer", stdout=StringIO())
        f.refresh_from_db()
        e = DossierExpulsion.objects.get()
        self.assertEqual((f.donnees, M.objects.get().reponse, e.nom, e.numero_allocataire), ({}, "", "ANONYME", ""))
        self.assertEqual(StructureHebergement.objects.get().nom, "Accueil fictif")       # le paramétrage reste
