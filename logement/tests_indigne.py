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
from .services import indigne_stats
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
        c_ts.post(f"/logement/indigne/{s.pk}/modifier/", {"origine": "VAD", "date_saisine": "2026-11-02", "rapport_vad": "Logement humide."})
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
        self.client_de(self.ts).post(f"/logement/indigne/{s.pk}/modifier/", {"origine": "VAD", "date_saisine": "2026-11-02", "rapport_vad": "A"})
        self.client_de(self.ts).post(f"/logement/indigne/{s.pk}/action/", {"action": "signer_vad"})
        self.client_de(self.cadre).post(f"/logement/indigne/{s.pk}/action/", {"action": "signer_fiche"})
        s.refresh_from_db()
        self.assertTrue(s.vad_signee and s.fiche_signee)
        self.client_de(self.ts).post(f"/logement/indigne/{s.pk}/modifier/", {"origine": "VAD", "date_saisine": "2026-11-02", "rapport_vad": "B"})
        s.refresh_from_db()
        self.assertFalse(s.vad_signee, "rapport modifié : signature TS retirée")
        self.assertTrue(s.fiche_signee, "fiche inchangée : signature cadre conservée")
        self.client_de(self.ts).post(f"/logement/indigne/{s.pk}/modifier/", {"origine": "VAD", "date_saisine": "2026-11-02", "surface": "18"})
        s.refresh_from_db()
        self.assertFalse(s.fiche_signee, "fiche modifiée : signature cadre retirée")

    def test_suivi_cloture_et_figement(self):
        s = self.nouveau(code="IN-1")
        self.client_de(self.ts).post(f"/logement/indigne/{s.pk}/modifier/", {"origine": "VAD", "date_saisine": "2026-11-02", "rapport_vad": "A"})
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
        c.post(f"/logement/indigne/{s.pk}/modifier/", {"origine": "VAD", "date_saisine": "2026-11-02", "creneau": rdv.pk,
                                                        "rapport_vad": "Humidité dans la chambre."})
        c.post(f"/logement/indigne/{s.pk}/action/", {"action": "signer_vad"})
        s.refresh_from_db()
        e = s.entretien
        self.assertIsNotNone(e)
        self.assertEqual((e.mode, e.creneau, e.synthese, e.date), (EntretienSocial.VAD, rdv, "Humidité dans la chambre.", rdv.date))
        self.assertEqual(self.b.entretiens.count(), 1)
        self.assertIn(s, rdv.signalements_indigne.all())
        # rapport modifié : signature retirée et entrée du journal retirée
        c.post(f"/logement/indigne/{s.pk}/modifier/", {"origine": "VAD", "date_saisine": "2026-11-02", "creneau": rdv.pk, "rapport_vad": "Autre texte."})
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

    def _rdv_cadre(self, decalage=7):
        from datetime import timedelta
        from django.utils import timezone
        return timezone.localdate() + timedelta(days=decalage)

    def test_introduction_reprend_famille_saisine_et_visite(self):
        from datetime import date, time
        from planning.models import CreneauRdv
        s = self.nouveau(code="IN-1")
        s.date_saisine = date(2026, 11, 2)
        s.save()
        rdv = CreneauRdv.objects.create(date=date(2026, 11, 5), heure_debut=time(9), heure_fin=time(9, 30),
                                        beneficiaire=self.b, mds=self.mds, agent=self.ts, modalite='VAD')
        s.creneau = rdv
        s.save()
        page = self.client_de(self.ts).get(f"/logement/indigne/{s.pk}/modifier/")
        self.assertContains(page, "la famille ESSAI a contacté nos services")
        self.assertContains(page, "La MDS a été saisie le 02/11/2026.")
        self.assertContains(page, "réalisé le 05/11/2026 en présence de la famille")
        s.refresh_from_db()
        self.assertEqual(s.rapport_vad, "", "l'introduction est proposée, pas enregistrée")

    def test_rapport_garde_sauts_de_ligne_et_puces(self):
        s = self.nouveau(code="IN-1")
        texte = "Intro.\r\n\r\n> Humidité dans la chambre.\r\n> Fenêtre sans joint."
        self.client_de(self.ts).post(f"/logement/indigne/{s.pk}/modifier/", {"origine": "VAD", "rapport_vad": texte})
        s.refresh_from_db()
        self.assertEqual(s.rapport_vad, "Intro.\n\n> Humidité dans la chambre.\n> Fenêtre sans joint.")

    def test_signature_exige_date_de_saisine_et_passe_la_visite_realisee(self):
        from datetime import date, time
        from planning.models import CreneauRdv
        s = self.nouveau(code="IN-1")
        rdv = CreneauRdv.objects.create(date=date(2026, 11, 5), heure_debut=time(9), heure_fin=time(9, 30),
                                        beneficiaire=self.b, mds=self.mds, agent=self.ts, modalite='VAD',
                                        statut='RESERVE')
        c = self.client_de(self.ts)
        c.post(f"/logement/indigne/{s.pk}/modifier/", {"origine": "VAD", "rapport_vad": "Texte.", "creneau": rdv.pk})
        c.post(f"/logement/indigne/{s.pk}/action/", {"action": "signer_vad"})
        s.refresh_from_db()
        self.assertFalse(s.vad_signee, "pas de signature sans date de saisine")
        c.post(f"/logement/indigne/{s.pk}/modifier/", {"origine": "VAD", "rapport_vad": "Texte.", "creneau": rdv.pk,
                                                        "date_saisine": "2026-11-02"})
        c.post(f"/logement/indigne/{s.pk}/action/", {"action": "signer_vad"})
        s.refresh_from_db()
        rdv.refresh_from_db()
        self.assertTrue(s.vad_signee)
        self.assertEqual(rdv.statut, 'VENU_RECU')

    def test_note_pdf_a4(self):
        import io
        from pypdf import PdfReader
        s = self.nouveau(code="IN-1")
        self.client_de(self.ts).post(f"/logement/indigne/{s.pk}/modifier/", {
            "origine": "VAD", "date_saisine": "2026-11-02", "rapport_vad": "Intro.\n\n> Humidité dans la chambre."})
        self.client_de(self.ts).post(f"/logement/indigne/{s.pk}/action/", {"action": "signer_vad"})
        r = self.client_de(self.ts).get(f"/logement/indigne/{s.pk}/note-vad.pdf")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b'%PDF'))
        texte = PdfReader(io.BytesIO(r.content)).pages[0].extract_text()
        self.assertIn("Visite à Domicile, lutte contre le mal logement", texte)
        self.assertIn("Humidité dans la chambre", texte)
        self.assertIn("Direction des Territoires et de l'Action Sociale", texte)
        self.assertEqual(self.client_de(self.hors).get(f"/logement/indigne/{s.pk}/note-vad.pdf").status_code, 403)

    def test_rdv_vad_depuis_le_signalement(self):
        from planning.models import CreneauRdv
        s = self.nouveau(code="IN-1")
        d = self._rdv_cadre()
        self.client_de(self.ts).post(f"/logement/indigne/{s.pk}/action/", {
            "action": "creer_rdv_vad", "date": d.isoformat(), "heure_debut": "10:00", "heure_fin": "10:30"})
        s.refresh_from_db()
        self.assertIsNotNone(s.creneau)
        self.assertEqual((s.creneau.modalite, s.creneau.nature, s.creneau.beneficiaire, s.creneau.agent),
                         ('VAD', 'VAD', self.b, self.ts))
        self.assertEqual(CreneauRdv.objects.filter(beneficiaire=self.b).count(), 1)

    def test_rdv_vad_refuses(self):
        from datetime import date, time, timedelta
        from django.utils import timezone
        from planning.models import CreneauRdv
        from .models import SignalementHabitatIndigne as SHI
        c = self.client_de(self.ts)
        s = self.nouveau(code="IN-1")
        futur = self._rdv_cadre()
        essais = [
            {"date": futur, "heure_debut": "08:30", "heure_fin": "09:00"},                   # avant 9h
            {"date": timezone.localdate() - timedelta(days=3), "heure_debut": "10:00", "heure_fin": "10:30"},  # passé
        ]
        for e in essais:
            c.post(f"/logement/indigne/{s.pk}/action/", dict(action="creer_rdv_vad", **{k: (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in e.items()}))
        s.refresh_from_db()
        self.assertIsNone(s.creneau)
        # date antérieure à la saisine
        s.date_saisine = futur
        s.save()
        c.post(f"/logement/indigne/{s.pk}/action/", {"action": "creer_rdv_vad", "date": (futur - timedelta(days=1)).isoformat(),
                                                    "heure_debut": "10:00", "heure_fin": "10:30"})
        s.refresh_from_db()
        self.assertIsNone(s.creneau)
        # conflit avec un autre rendez-vous de l'agent
        CreneauRdv.objects.create(date=futur, heure_debut=time(10), heure_fin=time(11), beneficiaire=self.b,
                                  mds=self.mds, agent=self.ts, modalite='MDS')
        c.post(f"/logement/indigne/{s.pk}/action/", {"action": "creer_rdv_vad", "date": futur.isoformat(),
                                                    "heure_debut": "10:00", "heure_fin": "10:30"})
        s.refresh_from_db()
        self.assertIsNone(s.creneau)
        # usager d'une autre MDS
        autre_usager = Beneficiaire.objects.create(code_interne="IN-3", civilite="M.", nom="HORS", prenom="Luc",
                                                   date_naissance="1975-01-01", adresse="5 rue E", code_postal="13500",
                                                   ville="Martigues", mds=self.autre)
        s3 = SHI.objects.create(beneficiaire=autre_usager, mds=self.mds, origine='VAD', cree_par=self.ts)
        c.post(f"/logement/indigne/{s3.pk}/action/", {"action": "creer_rdv_vad", "date": futur.isoformat(),
                                                     "heure_debut": "14:00", "heure_fin": "14:30"})
        s3.refresh_from_db()
        self.assertIsNone(s3.creneau)
        self.assertEqual(CreneauRdv.objects.filter(beneficiaire=autre_usager).count(), 0)



class LogementIndigneStatsTests(TestCase):
    """Statistiques de l'habitat indigne : comptage, « je ne sais pas » à part, périmètre par MDS, export CSV agrégé."""

    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.mds = MDS.objects.create(code_mds="ST1", nom="MDS STATS", adresse="1 rue A", code_postal="13110",
                                      ville="Port-de-Bouc", email="mds@exemple.fr")
        self.autre = MDS.objects.create(code_mds="ST2", nom="MDS AUTRE", adresse="2 rue B", code_postal="13500",
                                        ville="Martigues", email="autre@exemple.fr")
        self.ts = self.agent("sophie", self.mds)
        self.hors = self.agent("bruno", self.autre)
        self.admin = User.objects.create_superuser("admin_stats", password="x", matricule="ADMSTATS",
                                                   first_name="Admin", last_name="ESSAI")
        self.b = Beneficiaire.objects.create(code_interne="ST-1", civilite="MME", nom="ESSAI", prenom="Clara",
                                             date_naissance="1990-01-01", adresse="3 rue C", code_postal="13110",
                                             ville="Port-de-Bouc", mds=self.mds)
        SignalementHabitatIndigne.objects.create(
            beneficiaire=self.b, mds=self.mds, origine='VAD', statut='ENVOYE', date_envoi="2026-10-01",
            enquete_salubrite=True, bascule_dalo=True, permis_ville=True,
            donnees={'statut_occupant': 'locataire', 'eclairage_communs': 'nsp', 'humidite': 'oui', 'chauffage': 'non'})
        SignalementHabitatIndigne.objects.create(
            mds=self.mds, origine='COMMUNE', statut='ENVOYE', donnees={'statut_occupant': 'sans_titre'})
        SignalementHabitatIndigne.objects.create(
            mds=self.autre, origine='LOCATAIRE', statut='BROUILLON', donnees={'humidite': 'oui'})

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

    def test_comptage_et_je_ne_sais_pas_a_part(self):
        s = indigne_stats.statistiques(self.admin)
        synthese = dict(s['synthese'])
        self.assertEqual(synthese['Signalements'], 3)
        self.assertEqual(synthese['Envoyés au PDLHI'], 1)
        self.assertEqual(synthese['Enquête de salubrité'], 1)
        self.assertEqual(synthese['Hors suivi MDS (renvoyés au CIAS ou CCAS)'], 2)
        ligne = next(l for bloc in s['reponses'] for l in bloc['lignes'] if l['label'].startswith("Éclairage"))
        self.assertEqual(dict(ligne['choix']), {'Oui': 0, 'Non': 0, 'Je ne sais pas': 1})
        self.assertEqual(ligne['sans'], 2)

    def test_perimetre_par_mds(self):
        s = indigne_stats.statistiques(self.ts)
        self.assertEqual(dict(s['synthese'])['Signalements'], 2)
        self.assertEqual(s['par_mds'], [])  # pas de vue départementale
        self.assertEqual(dict(indigne_stats.statistiques(self.hors)['synthese'])['Signalements'], 1)

    def test_acces_refuse_sans_habilitation(self):
        self.assertEqual(self.client_de(self.ts).get("/logement/indigne/statistiques/").status_code, 403)

    def test_export_csv_agrege_sans_identite(self):
        rep = self.client_de(self.admin).get("/logement/indigne/statistiques/?format=csv")
        self.assertEqual(rep.status_code, 200)
        self.assertTrue(rep['Content-Type'].startswith('text/csv'))
        contenu = rep.content.decode('utf-8-sig')
        self.assertIn('Signalements;3', contenu)
        self.assertNotIn('ESSAI', contenu)
        self.assertNotIn('Clara', contenu)

    def test_page_statistiques_accessible_au_departement(self):
        self.assertEqual(self.client_de(self.admin).get("/logement/indigne/statistiques/").status_code, 200)
