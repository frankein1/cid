# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/test_rdvsp_invitations.py
"""RDV-Solidarités étape 2 : invitations mensuelles, envoi, suspension. RDV-Solidarités simulé, données fictives."""
import os
from datetime import date, datetime, timedelta
from unittest import mock

from django.core import mail
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from beneficiaire.models import Beneficiaire
from connecteurs import rdv_service_public as api
from connecteurs import rdvsp_invitations as inv
from connecteurs.models import (CampagneInvitations, InvitationRSA, LienUsagerRDVSP, ParametresRDVSP, RdvRDVSP,
                                ReservationEnLigne)
from connecteurs.test_rdvsp_synchro import ENV, FauxMRS, _Base
from insertion.models import ContratInsertion as C
from insertion.services import contrat_circuit
from messagerie.models import Message


class FauxMRSInvitations(FauxMRS):
    def __call__(self, client, methode, chemin, **kw):
        if chemin == "/users" and methode == "POST":
            self.appels.append((methode, chemin, kw.get("json")))
            self.n += 1
            return {"user": {"id": self.n}}
        if chemin.endswith("/rdv_invitation_token"):
            self.appels.append((methode, chemin, None))
            return {"invitation_token": f"jeton-{chemin.split('/')[2]}"}
        return super().__call__(client, methode, chemin, **kw)


@mock.patch.dict(os.environ, ENV)
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class InvitationsTests(_Base):
    def setUp(self):
        env = mock.patch.dict(os.environ, ENV)   # le décorateur de classe ne couvre pas setUp
        env.start()
        self.addCleanup(env.stop)
        super().setUp()
        self.p.stop()
        self.mrs = FauxMRSInvitations()
        self.p = mock.patch.object(api.Client, "appel", autospec=True, side_effect=self.mrs)
        self.p.start()
        self.publier()                                     # lieu et motif publiés (lieu_sp_id connu)
        self.benef.email = "lucie.essai@exemple.test"
        self.benef.save()
        self.sans_mail = Beneficiaire.objects.create(code_interne="T-RSA2", civilite="M.", nom="ESSAI", prenom="Noé",
                                                     date_naissance=date(1985, 2, 2), adresse="4 rue D",
                                                     code_postal="13110", ville="Port-de-Bouc", mds=self.mds)
        self.c1 = self.contrat(self.benef, 10)
        self.c2 = self.contrat(self.sans_mail, 20)
        self.contrat(Beneficiaire.objects.create(code_interne="T-LOIN", civilite="M.", nom="LOIN", prenom="Tom",
                                                 date_naissance=date(1980, 1, 1), adresse="5 rue E", code_postal="13110",
                                                 ville="Port-de-Bouc", mds=self.mds), 120)    # pas encore à renouveler

    def contrat(self, b, jours_restants):
        c = contrat_circuit.creer(b, self.agent)
        fin = timezone.localdate() + timedelta(days=jours_restants)
        C.objects.filter(pk=c.pk).update(statut=C.VALIDE, date_debut=fin - timedelta(days=180), date_fin=fin)
        return C.objects.get(pk=c.pk)

    def test_calendrier(self):
        # 1er lundi de novembre 2026 = 2 novembre ; envoi le mardi 3 à 18 h
        self.assertEqual(inv.jour_preparation(date(2026, 11, 20)), date(2026, 11, 2))
        prevu = timezone.localtime(inv.envoi_prevu(date(2026, 11, 1)))
        self.assertEqual((prevu.date(), prevu.hour), (date(2026, 11, 3), 18))

    def test_preparation_et_message_au_referent(self):
        with self.captureOnCommitCallbacks(execute=True):
            campagne, cree = inv.preparer()
        self.assertTrue(cree)
        self.assertEqual(sorted(i.beneficiaire.code_interne for i in campagne.invitations.all()), ["T-RSA", "T-RSA2"])
        self.assertTrue(all(i.referent == self.agent and i.cochee for i in campagne.invitations.all()))
        m = Message.objects.get(destinataire=self.agent)
        self.assertIn("Invitations RSA", m.objet)
        self.assertEqual(inv.preparer()[1], False)                         # une seule fois par mois

    def test_suspendu_exclu(self):
        inv.suspendre(self.benef, self.agent, True)
        campagne, _ = inv.preparer(prevenir=False)
        self.assertEqual([i.beneficiaire for i in campagne.invitations.all()], [self.sans_mail])

    def test_validation_par_le_referent(self):
        campagne, _ = inv.preparer(prevenir=False)
        garde = campagne.invitations.get(beneficiaire=self.benef)
        c = Client(HTTP_HOST="localhost")
        c.force_login(self.agent)
        r = c.get(reverse("connecteurs:invitations_rsa"))
        self.assertContains(r, "ESSAI")
        c.post(reverse("connecteurs:invitations_rsa"), {"campagne": campagne.pk, "ids": [garde.pk]})
        self.assertEqual({i.beneficiaire.code_interne: i.cochee for i in campagne.invitations.all()},
                         {"T-RSA": True, "T-RSA2": False})

    def test_envoi(self):
        campagne, _ = inv.preparer(prevenir=False)
        LienUsagerRDVSP.objects.filter(beneficiaire=self.benef).delete()
        bilan = inv.envoyer_campagne(campagne)
        self.assertEqual(bilan, {"courriels": 1, "courriers": 1, "erreurs": 0})
        # usagers créés dans RDV-Solidarités, dans l'organisation de la MDS
        self.assertEqual([a[2]["organisation_ids"] for a in self.mrs.appels if a[:2] == ("POST", "/users")], [[7], [7]])
        i = campagne.invitations.get(beneficiaire=self.benef)
        self.assertTrue(i.lien.startswith("https://mrs.exemple.test/prendre_rdv?invitation_token=jeton-"))
        self.assertIn("organisation_ids%5B%5D=7", i.lien)
        self.assertEqual(i.mode, InvitationRSA.COURRIEL)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["lucie.essai@exemple.test"])
        self.assertIn(i.lien, mail.outbox[0].body)
        nom, pdf, _ = mail.outbox[0].attachments[0]
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(campagne.invitations.get(beneficiaire=self.sans_mail).mode, InvitationRSA.COURRIER)
        campagne.refresh_from_db()
        self.assertIsNotNone(campagne.envoyee_le)
        self.assertEqual(inv.envoyer_campagne(campagne)["courriels"], 0)     # relance : pas de doublon
        # le courrier se télécharge
        c = Client(HTTP_HOST="localhost")
        c.force_login(self.agent)
        r = c.get(reverse("connecteurs:invitation_courrier", args=[i.pk]))
        self.assertEqual(r["Content-Type"], "application/pdf")

    def test_traiter_selon_le_calendrier(self):
        def a(*args):
            return timezone.make_aware(datetime(*args))
        self.assertFalse(inv.a_traiter(a(2026, 11, 1, 10)))                  # dimanche 1er : trop tôt
        self.assertIsNone(inv.traiter(a(2026, 11, 1, 10)).get("preparee"))
        self.assertTrue(inv.a_traiter(a(2026, 11, 2, 10)))                   # 1er lundi : préparation
        self.assertTrue(inv.traiter(a(2026, 11, 2, 10))["preparee"])
        campagne = CampagneInvitations.objects.get()
        self.assertFalse(inv.a_traiter(a(2026, 11, 3, 17, 59)))              # mardi avant 18 h : rien ne part
        res = inv.traiter(a(2026, 11, 3, 18, 1))                             # mardi soir : envoi tel quel
        self.assertEqual(res[str(campagne)], {"courriels": 1, "courriers": 1, "erreurs": 0})
        self.assertFalse(inv.a_traiter(a(2026, 11, 4, 9)))

    def test_suspension_depuis_la_fiche_et_incidents(self):
        debut = timezone.now() + timedelta(days=3)
        RdvRDVSP.objects.create(rdv_sp_id=1, beneficiaire=self.benef, debut=debut, fin=debut + timedelta(minutes=30),
                                statut_sp="excused", annule_le=debut - timedelta(hours=5))
        RdvRDVSP.objects.create(rdv_sp_id=2, beneficiaire=self.benef, debut=debut, fin=debut + timedelta(minutes=30),
                                statut_sp="excused", annule_le=debut - timedelta(days=4))     # pas tardive
        RdvRDVSP.objects.create(rdv_sp_id=3, beneficiaire=self.benef, debut=debut, fin=debut + timedelta(minutes=30),
                                statut_sp="noshow")
        i = inv.incidents(self.benef)
        self.assertEqual((len(i["annulations_tardives"]), len(i["absences"]), i["a_examiner"]), (1, 1, True))
        c = Client(HTTP_HOST="localhost")
        c.force_login(self.admin)
        r = c.get(reverse("beneficiaire:detail_beneficiaire", args=["T-RSA"]))
        self.assertContains(r, 'id="reservation-en-ligne"')
        self.assertContains(r, "1 annul. tardive")
        c.post(reverse("connecteurs:reservation_en_ligne", args=["T-RSA"]), {"suspendue": "1"})
        self.assertTrue(ReservationEnLigne.objects.get(beneficiaire=self.benef).suspendue)
        self.assertTrue(inv.est_suspendu(self.benef))
        c.post(reverse("connecteurs:reservation_en_ligne", args=["T-RSA"]), {"suspendue": "0"})
        self.assertFalse(inv.est_suspendu(self.benef))
