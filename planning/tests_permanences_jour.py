# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# planning/tests_permanences_jour.py
"""Permanences du jour (accueil) : périmètre de la MDS, rendez-vous traités masqués, issue, PDF et envoi. Données fictives."""
from datetime import date, time
from io import StringIO

from django.core import mail
from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from beneficiaire.models import Beneficiaire
from core.models import Profil, User
from mds.models import MDS, MDSReception, UserMDSProfile
from planning.models import CreneauRdv

JOUR = date(2026, 11, 27)


class PermanencesDuJourTests(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.mds = MDS.objects.create(code_mds="TP1", nom="MDS ESSAI A", adresse="1 rue A", code_postal="13110",
                                      ville="Port-de-Bouc")
        self.autre = MDS.objects.create(code_mds="TP2", nom="MDS ESSAI B", adresse="1 rue B", code_postal="13500",
                                        ville="Martigues")
        self.salle = MDSReception.objects.create(mds=self.mds, nom="Salle A")
        self.salle_autre = MDSReception.objects.create(mds=self.autre, nom="Salle B")
        self.accueil = self.utilisateur("accueil", self.mds)
        self.accueil_autre = self.utilisateur("accueil2", self.autre)
        self.client_accueil = Client()
        self.client_accueil.force_login(self.accueil)
        self.usager = self.beneficiaire("AT-1", "DUPONT", "Lina", "13110", "Port-de-Bouc")
        self.usager2 = self.beneficiaire("AT-2", "MARTIN", "Paul", "13500", "Martigues")
        self.rdv_a_traiter = self.rdv(self.salle, self.usager, time(9), "RESERVE")
        self.rdv_traite = self.rdv(self.salle, self.usager2, time(10), "VENU_RECU")
        self.rdv_autre_mds = self.rdv(self.salle_autre, self.usager2, time(11), "RESERVE")

    def utilisateur(self, login, mds):
        u = User.objects.create_user(login, password="x", matricule=login.upper(), email=f"{login}@example.com")
        u.profils.add(Profil.objects.get(code="MDS_AGENTS_SOCIAUX"))
        UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True)
        return u

    def beneficiaire(self, code, nom, prenom, cp, ville):
        return Beneficiaire.objects.create(code_interne=code, civilite="MME", nom=nom, prenom=prenom,
                                           date_naissance=date(1990, 1, 1), adresse="3 rue C",
                                           code_postal=cp, ville=ville, telephone_mobile="0600000000")

    def rdv(self, salle, usager, heure, statut):
        return CreneauRdv.objects.create(date=JOUR, heure_debut=heure, heure_fin=time(heure.hour, 30),
                                         salle=salle, mds=salle.mds, beneficiaire=usager, agent=self.accueil,
                                         statut=statut)

    def test_liste_limitee_a_la_mds_et_masque_les_traites(self):
        r = self.client_accueil.get(f"/planning/permanences-du-jour/{JOUR.isoformat()}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([l['pk'] for l in r.context['lignes']], [self.rdv_a_traiter.pk])
        self.assertContains(r, "DUPONT Lina")
        self.assertNotContains(r, "MARTIN Paul")

    def test_afficher_les_traites(self):
        r = self.client_accueil.get(f"/planning/permanences-du-jour/{JOUR.isoformat()}/?traites=1")
        self.assertEqual([l['pk'] for l in r.context['lignes']], [self.rdv_traite.pk])

    def test_champs_demandes_presents(self):
        ligne = self.client_accueil.get(f"/planning/permanences-du-jour/{JOUR.isoformat()}/").context['lignes'][0]
        self.assertEqual(ligne['code'], "AT-1")
        self.assertEqual(ligne['naissance'], "01/01/1990")
        self.assertEqual(ligne['cp_ville'], "13110 Port-de-Bouc")
        self.assertEqual(ligne['telephone'], "0600000000")
        self.assertEqual(ligne['lieu'], "Salle A")
        self.assertIn("Permanence", ligne['motif'])

    def test_issue_par_l_accueil_de_la_mds(self):
        self.client_accueil.post(f"/planning/rdv/{self.rdv_a_traiter.pk}/issue/", {'statut': 'ABSENT'})
        self.rdv_a_traiter.refresh_from_db()
        self.assertEqual(self.rdv_a_traiter.statut, 'ABSENT')

    def test_issue_refusee_hors_de_la_mds(self):
        c = Client()
        c.force_login(self.accueil_autre)
        r = c.post(f"/planning/rdv/{self.rdv_a_traiter.pk}/issue/", {'statut': 'ABSENT'})
        self.assertEqual(r.status_code, 403)
        self.rdv_a_traiter.refresh_from_db()
        self.assertEqual(self.rdv_a_traiter.statut, 'RESERVE')

    def test_pdf(self):
        r = self.client_accueil.get(f"/planning/permanences-du-jour/{JOUR.isoformat()}/pdf/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertTrue(b''.join(r.streaming_content).startswith(b'%PDF'))

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_envoi_mail_avec_pdf(self):
        r = self.client_accueil.post(f"/planning/permanences-du-jour/{JOUR.isoformat()}/mail/",
                                     {'email': 'agent@example.com'}, follow=True)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['agent@example.com'])
        self.assertEqual(mail.outbox[0].attachments[0][2], 'application/pdf')
        self.assertContains(r, "PDF envoyé")

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_envoi_mail_adresse_incorrecte_refusee(self):
        self.client_accueil.post(f"/planning/permanences-du-jour/{JOUR.isoformat()}/mail/", {'email': 'pas-une-adresse'})
        self.assertEqual(len(mail.outbox), 0)
