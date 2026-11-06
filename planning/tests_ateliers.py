# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# planning/tests_ateliers.py
"""Ateliers collectifs : places, liste d'attente, condition d'âge, présences, accès, exports. Données fictives."""
from datetime import date, time
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase

from beneficiaire.models import Beneficiaire
from core.models import Profil, User
from mds.models import MDS, UserMDSProfile
from planning import ateliers as regles
from planning.models import Atelier, ParticipantAtelier as P, SeanceAtelier


class _Base(TestCase):
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.mds = MDS.objects.create(code_mds="TA1", nom="MDS ESSAI A", adresse="1 rue A", code_postal="13110",
                                      ville="Port-de-Bouc")
        self.autre = MDS.objects.create(code_mds="TA2", nom="MDS ESSAI B", adresse="1 rue B", code_postal="13500",
                                        ville="Martigues")
        self.agente = self.agent("nora", self.mds, "MDS_AGENTS_SOCIAUX")
        self.atelier = Atelier.objects.create(nom="Cuisine à petit prix", mds=self.mds)
        self.s = SeanceAtelier.objects.create(atelier=self.atelier, mds=self.mds, date=date(2026, 11, 20),
                                              heure_debut=time(14), heure_fin=time(16), places=2)
        self.b = [self.usager(i, date(1990 + i, 1, 1)) for i in range(4)]

    def agent(self, login, mds, profil):
        u = User.objects.create_user(login, password="x", matricule=login.upper())
        u.profils.add(Profil.objects.get(code=profil))
        UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True)
        return u

    def usager(self, i, naissance, mds=None):
        return Beneficiaire.objects.create(code_interne=f"AT-{i}", civilite="MME", nom="ESSAI", prenom=f"Lina{i}",
                                           date_naissance=naissance, adresse="3 rue C", code_postal="13110",
                                           ville="Port-de-Bouc", mds=mds or self.mds)


class ReglesTests(_Base):
    def test_places_et_liste_attente(self):
        p = [regles.inscrire(self.s, self.agente, beneficiaire=b) for b in self.b[:3]]
        self.assertEqual([x.liste for x in p], [P.PRINCIPALE, P.PRINCIPALE, P.ATTENTE])
        self.assertEqual(self.s.places_restantes, 0)
        promu = regles.retirer(p[0])
        self.assertEqual(promu.pk, p[2].pk)
        self.assertEqual(P.objects.get(pk=p[2].pk).liste, P.PRINCIPALE)
        self.assertEqual(self.s.inscrits().count(), 2)

    def test_doublon_et_seance_annulee(self):
        regles.inscrire(self.s, self.agente, beneficiaire=self.b[0])
        with self.assertRaises(regles.ErreurAtelier):
            regles.inscrire(self.s, self.agente, beneficiaire=self.b[0])
        self.s.statut = SeanceAtelier.ANNULEE
        self.s.save()
        with self.assertRaises(regles.ErreurAtelier):
            regles.inscrire(self.s, self.agente, beneficiaire=self.b[1])

    def test_condition_age(self):
        self.s.condition_age, self.s.age_limite = SeanceAtelier.MOINS_DE, 25
        self.s.save()
        jeune = self.usager(9, date(2005, 6, 1))
        self.assertIsNone(regles.controle_age(self.s, jeune.date_naissance))
        with self.assertRaises(regles.ErreurAtelier):
            regles.inscrire(self.s, self.agente, beneficiaire=self.b[0])           # 36 ans
        regles.inscrire(self.s, self.agente, beneficiaire=self.b[0], forcer_age=True)
        regles.inscrire(self.s, self.agente, beneficiaire=jeune)

    def test_externe_presences_bilan(self):
        self.s.payant, self.s.tarif = True, 2
        self.s.save()
        with self.assertRaises(regles.ErreurAtelier):
            regles.inscrire(self.s, self.agente, telephone="0600000000")            # nom ou prénom obligatoire
        e = regles.inscrire(self.s, self.agente, prenom="Adam", nom="ROCHE", type=P.ACCOMPAGNANT)
        u = regles.inscrire(self.s, self.agente, beneficiaire=self.b[0])
        self.assertEqual(e.montant, 2)
        regles.noter_presences(self.s, {str(e.pk): P.VENU, str(u.pk): P.ABSENT})
        b = regles.bilan(self.s)
        self.assertEqual((b["inscrits"], b["presents"], b["absents"]), (2, 1, 1))


class VuesTests(_Base):
    def client_de(self, u):
        c = Client(HTTP_HOST="localhost")
        c.force_login(u)
        return c

    def test_parcours_agent(self):
        c = self.client_de(self.agente)
        self.assertContains(c.get("/planning/ateliers/"), "Cuisine à petit prix")
        url = f"/planning/ateliers/seance/{self.s.pk}/"
        self.assertContains(c.get(url + "?q=Lina1"), "Lina1")
        for b in self.b[:3]:
            c.post(url + "action/", {"action": "inscrire_usager", "beneficiaire": b.pk})
        c.post(url + "action/", {"action": "inscrire_externe", "nom": "ROCHE", "prenom": "Adam"})
        self.assertEqual(self.s.inscrits().count(), 2)
        self.assertEqual(self.s.attente().count(), 2)
        p = self.s.inscrits().first()
        c.post(url + "action/", {"action": "presences", f"presence_{p.pk}": P.VENU})
        self.assertEqual(P.objects.get(pk=p.pk).presence, P.VENU)
        r = c.get(url + "emargement.pdf")
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))
        r = c.get(url + "emargement.csv")
        self.assertIn(b"Lina0", r.content)
        self.assertContains(c.get(f"/beneficiaire/{self.b[0].code_interne}/"), "Ateliers collectifs")

    def test_creation_seance(self):
        c = self.client_de(self.agente)
        r = c.post("/planning/ateliers/seance/nouvelle/", {
            "atelier": self.atelier.pk, "mds": self.mds.pk, "date": "2026-12-03", "heure_debut": "09:00",
            "heure_fin": "11:00", "places": "", "payant": "on", "tarif": ""})
        self.assertContains(r, "Indiquez le tarif")
        r = c.post("/planning/ateliers/seance/nouvelle/", {
            "atelier": self.atelier.pk, "mds": self.mds.pk, "date": "2026-12-03", "heure_debut": "09:00",
            "heure_fin": "11:00"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(SeanceAtelier.objects.count(), 2)

    def test_autre_mds_refusee(self):
        etrangere = self.agent("samir", self.autre, "MDS_AGENTS_SOCIAUX")
        c = self.client_de(etrangere)
        self.assertEqual(c.get(f"/planning/ateliers/seance/{self.s.pk}/").status_code, 403)
        r = c.get("/planning/ateliers/")
        self.assertEqual(list(r.context["a_venir"]), [])
        self.assertNotIn(self.atelier, list(r.context["ateliers"]))
        # un usager d'une autre MDS ne peut pas être inscrit depuis la séance
        hors = self.usager(8, date(1980, 1, 1), mds=self.autre)
        self.client_de(self.agente).post(f"/planning/ateliers/seance/{self.s.pk}/action/",
                                         {"action": "inscrire_usager", "beneficiaire": hors.pk})
        self.assertFalse(P.objects.filter(beneficiaire=hors).exists())
