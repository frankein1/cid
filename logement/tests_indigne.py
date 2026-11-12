# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/tests_indigne.py
"""Signalement d'habitat indigne : création, rubriques contrôlées, signatures (TS pour la VAD, cadre pour la fiche),
envoi au PDLHI, suivi, clôture et cloisonnement entre MDS. Données fictives."""
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase

from beneficiaire.models import Beneficiaire
from core.models import Profil, User
from mds.models import MDS, UserMDSProfile

from .models import SignalementHabitatIndigne
from .services.indigne import champs_valides, valeur_propre


class LogementIndigneTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.mds = MDS.objects.create(code_mds="TI1", nom="MDS INDIGNE", adresse="1 rue A", code_postal="13110",
                                      ville="Port-de-Bouc", email="mds@exemple.fr")
        self.autre = MDS.objects.create(code_mds="TI2", nom="MDS AUTRE", adresse="2 rue B", code_postal="13500",
                                        ville="Martigues", email="autre@exemple.fr")
        self.ts = self.agent("amina", self.mds, "MDS_AGENTS_SOCIAUX")
        self.cadre = self.agent("hugo", self.mds, "MDS_RESPONSABLE")
        self.mds.responsable = self.cadre
        self.mds.save()
        self.hors = self.agent("lea", self.autre, "MDS_AGENTS_SOCIAUX")
        self.b = Beneficiaire.objects.create(code_interne="IN-1", civilite="MME", nom="ESSAI", prenom="Clara",
                                             date_naissance="1990-01-01", adresse="3 rue C", code_postal="13110",
                                             ville="Port-de-Bouc", mds=self.mds)

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

    def nouveau(self, code=None, origine="VAD"):
        data = {"origine": origine}
        if code:
            data["code_interne"] = code
        self.client_de(self.ts).post("/logement/indigne/nouveau/", data)
        return SignalementHabitatIndigne.objects.latest('pk')

    def test_creation_usager_et_hors_suivi(self):
        s = self.nouveau(code="IN-1", origine="BAILLEUR")
        self.assertEqual((s.beneficiaire, s.mds, s.origine), (self.b, self.mds, 'BAILLEUR'))
        s2 = self.nouveau()
        self.assertIsNone(s2.beneficiaire)
        self.assertEqual(s2.mds, self.mds)

    def test_rubriques_controlees_et_texte_tronque(self):
        s = self.nouveau(code="IN-1")
        champs = champs_valides()
        self.assertEqual(valeur_propre('rongeurs', 'nsp', champs), 'nsp')
        self.assertEqual(valeur_propre('rongeurs', 'peut-etre', champs), '')
        self.assertEqual(valeur_propre('menuiseries_vetuste', 'mauvais', champs), 'mauvais')
        self.assertEqual(valeur_propre('bail_date', 'x' * 400, champs), 'x' * 300)
        data = {"origine": "VAD", "rongeurs": "oui", "punaises": "n'importe", "bail_date": "01/02/2020",
                "permis_ville": "on", "rapport_vad": "Visite conforme."}
        self.client_de(self.ts).post(f"/logement/indigne/{s.pk}/modifier/", data)
        s.refresh_from_db()
        self.assertEqual(s.donnees["rongeurs"], "oui")
        self.assertEqual(s.donnees["punaises"], "")
        self.assertTrue(s.permis_ville)
        self.assertFalse(s.permis_logement)
        self.assertEqual(s.rapport_vad, "Visite conforme.")

    def test_signatures_par_role_puis_envoi(self):
        s = self.nouveau(code="IN-1")
        c_ts, c_cadre = self.client_de(self.ts), self.client_de(self.cadre)
        c_ts.post(f"/logement/indigne/{s.pk}/action/", {"action": "signer_vad"})
        s.refresh_from_db()
        self.assertFalse(s.vad_signee, "pas de signature sur un rapport vide")
        c_ts.post(f"/logement/indigne/{s.pk}/modifier/", {"origine": "VAD", "rapport_vad": "Logement humide."})
        c_ts.post(f"/logement/indigne/{s.pk}/action/", {"action": "signer_vad"})
        c_ts.post(f"/logement/indigne/{s.pk}/action/", {"action": "signer_fiche"})
        s.refresh_from_db()
        self.assertTrue(s.vad_signee)
        self.assertFalse(s.fiche_signee, "la fiche est signée par le cadre, pas par le TS")
        # envoi refusé sans fiche signée
        c_ts.post(f"/logement/indigne/{s.pk}/action/", {"action": "envoyer"})
        s.refresh_from_db()
        self.assertEqual(s.statut, SignalementHabitatIndigne.BROUILLON)
        c_cadre.post(f"/logement/indigne/{s.pk}/action/", {"action": "signer_fiche"})
        c_ts.post(f"/logement/indigne/{s.pk}/action/", {"action": "envoyer", "date_envoi": "2026-11-10"})
        s.refresh_from_db()
        self.assertEqual(s.statut, SignalementHabitatIndigne.ENVOYE)
        self.assertEqual(s.date_envoi.isoformat(), "2026-11-10")

    def test_modification_apres_signature_retire_les_signatures(self):
        s = self.nouveau(code="IN-1")
        self.client_de(self.ts).post(f"/logement/indigne/{s.pk}/modifier/", {"origine": "VAD", "rapport_vad": "A"})
        self.client_de(self.ts).post(f"/logement/indigne/{s.pk}/action/", {"action": "signer_vad"})
        self.client_de(self.cadre).post(f"/logement/indigne/{s.pk}/action/", {"action": "signer_fiche"})
        s.refresh_from_db()
        self.assertTrue(s.vad_signee and s.fiche_signee)
        self.client_de(self.ts).post(f"/logement/indigne/{s.pk}/modifier/", {"origine": "VAD", "rapport_vad": "B"})
        s.refresh_from_db()
        self.assertFalse(s.vad_signee, "rapport modifié : signature TS retirée")
        self.assertTrue(s.fiche_signee, "fiche inchangée : signature cadre conservée")
        self.client_de(self.ts).post(f"/logement/indigne/{s.pk}/modifier/", {"origine": "VAD", "surface": "18"})
        s.refresh_from_db()
        self.assertFalse(s.fiche_signee, "fiche modifiée : signature cadre retirée")

    def test_suivi_cloture_et_figement(self):
        s = self.nouveau(code="IN-1")
        self.client_de(self.ts).post(f"/logement/indigne/{s.pk}/modifier/", {"origine": "VAD", "rapport_vad": "A"})
        self.client_de(self.ts).post(f"/logement/indigne/{s.pk}/action/", {"action": "signer_vad"})
        self.client_de(self.cadre).post(f"/logement/indigne/{s.pk}/action/", {"action": "signer_fiche"})
        self.client_de(self.ts).post(f"/logement/indigne/{s.pk}/action/", {"action": "envoyer"})
        c = self.client_de(self.ts)
        r = c.get(f"/logement/indigne/{s.pk}/modifier/")
        self.assertEqual(r.status_code, 302, "envoyé : plus modifiable")
        c.post(f"/logement/indigne/{s.pk}/action/", {"action": "suivi", "reponse_pdlhi": "Visite prévue",
                                                      "enquete_salubrite": "on", "bascule_dalo": "on",
                                                      "suite": "Relogement engagé"})
        s.refresh_from_db()
        self.assertTrue(s.enquete_salubrite and s.bascule_dalo)
        self.assertEqual(s.reponse_pdlhi, "Visite prévue")
        c.post(f"/logement/indigne/{s.pk}/action/", {"action": "clore"})
        s.refresh_from_db()
        self.assertEqual(s.statut, SignalementHabitatIndigne.CLOS)

    def test_cloisonnement_entre_mds(self):
        s = self.nouveau(code="IN-1")
        self.assertEqual(self.client_de(self.hors).get(f"/logement/indigne/{s.pk}/").status_code, 403)
        self.assertNotContains(self.client_de(self.hors).get("/logement/indigne/"), f"/logement/indigne/{s.pk}/")
        self.assertContains(self.client_de(self.ts).get("/logement/indigne/"), f"/logement/indigne/{s.pk}/")

    def test_entree_dans_le_menu(self):
        self.assertContains(self.client_de(self.ts).get("/logement/indigne/"), "Logement indigne")

    def test_vad_signee_va_au_journal_et_au_planning(self):
        from datetime import date, time
        from beneficiaire.models_journal import EntretienSocial
        from planning.models import CreneauRdv
        rdv = CreneauRdv.objects.create(date=date(2026, 11, 5), heure_debut=time(9), heure_fin=time(9, 30),
                                        beneficiaire=self.b, mds=self.mds, agent=self.ts, modalite='VAD',
                                        statut='VENU_RECU')
        s = self.nouveau(code="IN-1")
        c = self.client_de(self.ts)
        c.post(f"/logement/indigne/{s.pk}/modifier/", {"origine": "VAD", "creneau": rdv.pk,
                                                        "rapport_vad": "Humidité dans la chambre."})
        c.post(f"/logement/indigne/{s.pk}/action/", {"action": "signer_vad"})
        s.refresh_from_db()
        e = s.entretien
        self.assertIsNotNone(e)
        self.assertEqual((e.mode, e.creneau, e.synthese, e.date), (EntretienSocial.VAD, rdv, "Humidité dans la chambre.", rdv.date))
        self.assertEqual(self.b.entretiens.count(), 1)
        self.assertIn(s, rdv.signalements_indigne.all())
        # rapport modifié : signature retirée et entrée du journal retirée
        c.post(f"/logement/indigne/{s.pk}/modifier/", {"origine": "VAD", "creneau": rdv.pk, "rapport_vad": "Autre texte."})
        s.refresh_from_db()
        self.assertFalse(s.vad_signee)
        self.assertEqual(self.b.entretiens.count(), 0)

    def test_rdv_d_un_autre_usager_refuse(self):
        from datetime import date, time
        from planning.models import CreneauRdv
        autre = Beneficiaire.objects.create(code_interne="IN-2", civilite="M.", nom="AUTRE", prenom="Paul",
                                            date_naissance="1980-01-01", adresse="4 rue D", code_postal="13110",
                                            ville="Port-de-Bouc", mds=self.mds)
        rdv = CreneauRdv.objects.create(date=date(2026, 11, 5), heure_debut=time(9), heure_fin=time(9, 30),
                                        beneficiaire=autre, mds=self.mds, agent=self.ts, modalite='VAD')
        s = self.nouveau(code="IN-1")
        self.client_de(self.ts).post(f"/logement/indigne/{s.pk}/modifier/", {"origine": "VAD", "creneau": rdv.pk})
        s.refresh_from_db()
        self.assertIsNone(s.creneau)

    def test_bouton_sur_fiche_usager(self):
        self.assertContains(self.client_de(self.ts).get(f"/beneficiaire/{self.b.code_interne}/"),
                            'id="indigne-nouveau"')

