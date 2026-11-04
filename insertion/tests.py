# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/tests.py
"""Contrat RSA : circuit (transmission, réception, avis médical, commission), droits, alertes, PDF.
Données entièrement fictives."""
from datetime import date, timedelta
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase
from django.utils import timezone

from beneficiaire.models import Beneficiaire
from core.models import Profil, User
from insertion import acces
from insertion.models import ActionInsertion, ContratInsertion as C, LigneActionContrat, PoleInsertion, TypeActionInsertion
from insertion.services import contrat_circuit as circuit
from insertion.services import contrat_pdf
from mds.models import MDS, UserMDSProfile


class ContratTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for cmd in ("init_capacites", "init_profils", "init_insertion"):
            call_command(cmd, stdout=StringIO())
        cls.mds = MDS.objects.create(code_mds="T1", nom="MDS Essai", adresse="1 rue A", code_postal="13000", ville="Exemple")
        cls.mds_b = MDS.objects.create(code_mds="T2", nom="MDS Autre", adresse="2 rue B", code_postal="13000", ville="Exemple")

        def compte(nom, profil, mds=None):
            u = User.objects.create_user(nom, password="x", first_name=nom, matricule=nom.upper())
            u.profils.add(Profil.objects.get(code=profil))
            if mds:
                UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True)
            return u
        cls.ts = compte("ts", "MDS_AGENTS_SOCIAUX", cls.mds)
        cls.ts_b = compte("ts_b", "MDS_AGENTS_SOCIAUX", cls.mds_b)
        cls.admin = compte("adm", "POLE_INSERTION_ADMINISTRATIF")
        cls.cadre = compte("cad", "POLE_INSERTION_CADRE")
        cls.medecin = compte("med", "POLE_INSERTION_MEDECIN")
        cls.pole = PoleInsertion.objects.create(code="PI-T", nom="Pôle essai")
        cls.pole.mds.add(cls.mds)
        cls.pole.membres.add(cls.admin, cls.cadre, cls.medecin)
        cls.benef = Beneficiaire.objects.create(code_interne="T-AAA", civilite="MME", nom="ESSAI", prenom="Lucie",
                                                date_naissance=date(1990, 1, 1), adresse="3 rue C", code_postal="13000",
                                                ville="Exemple", mds=cls.mds)
        cls.action = ActionInsertion.objects.create(code="T-ACT", libelle="Action essai",
                                                    type_action=TypeActionInsertion.objects.first())
        cls.action2 = ActionInsertion.objects.create(code="T-ACT2", libelle="Action essai 2",
                                                     type_action=TypeActionInsertion.objects.first())

    def _pret(self, nature="SOCIAL", **champs):
        c = circuit.creer(self.benef, self.ts)
        c.nature, c.date_signature, c.accord_allocataire, c.objectifs = nature, timezone.localdate(), True, "Objectif"
        for k, v in champs.items():
            setattr(c, k, v)
        c.save()
        LigneActionContrat.objects.create(contrat=c, action=self.action)
        LigneActionContrat.objects.create(contrat=c, action=self.action2)
        return c

    def test_creation_preremplie(self):
        c = circuit.creer(self.benef, self.ts)
        self.assertEqual((c.pole, c.mds, c.statut, c.heures_activite_hebdo), (self.pole, self.mds, C.BROUILLON, 15))
        self.assertTrue(c.historique.exists())

    def test_transmission_bloquee_si_incomplet(self):
        c = circuit.creer(self.benef, self.ts)
        with self.assertRaises(circuit.ErreurCircuit):
            circuit.transmettre(c, self.ts)

    def test_circuit_complet_et_messages(self):
        from messagerie.models import Message
        c = self._pret()
        circuit.transmettre(c, self.ts)
        self.assertTrue(Message.objects.filter(destinataire=self.admin, object_id=c.pk).exists())
        circuit.receptionner(c, self.admin)
        self.assertTrue(Message.objects.filter(destinataire=self.cadre, object_id=c.pk).exists())
        debut = date(2026, 11, 10)
        circuit.decider(c, self.cadre, decision=C.VALIDE, date_decision=debut, date_debut=debut, duree_mois=6)
        c.refresh_from_db()
        self.assertEqual((c.statut, c.date_fin), (C.VALIDE, date(2027, 5, 9)))
        msg = Message.objects.get(destinataire=self.ts, object_id=c.pk)
        self.assertEqual(msg.beneficiaire, self.benef)
        # Les messages au pôle ne pointent pas vers la fiche de l'usager
        self.assertIsNone(Message.objects.filter(destinataire=self.admin).first().beneficiaire)

    def test_valide_sauf_action_force_la_duree(self):
        c = self._pret()
        circuit.transmettre(c, self.ts)
        ligne = c.lignes.first()
        with self.assertRaises(circuit.ErreurCircuit):   # motif obligatoire
            circuit.decider(c, self.cadre, decision=C.VALIDE_SAUF_ACTION, date_decision=date(2026, 11, 1),
                            date_debut=date(2026, 11, 1), non_retenues={ligne.pk: ""})
        circuit.decider(c, self.cadre, decision=C.VALIDE_SAUF_ACTION, date_decision=date(2026, 11, 1),
                        date_debut=date(2026, 11, 1), duree_mois=12, non_retenues={ligne.pk: "Complet"})
        c.refresh_from_db()
        self.assertEqual((c.duree_validee_mois, c.date_fin), (3, date(2027, 1, 31)))
        self.assertTrue(c.lignes.get(pk=ligne.pk).non_retenue)

    def test_ajournement_rend_modifiable(self):
        c = self._pret()
        circuit.transmettre(c, self.ts)
        with self.assertRaises(circuit.ErreurCircuit):   # motif obligatoire
            circuit.decider(c, self.cadre, decision=C.AJOURNE, date_decision=date(2026, 11, 1))
        circuit.decider(c, self.cadre, decision=C.AJOURNE, date_decision=date(2026, 11, 1), motif="À préciser")
        c.refresh_from_db()
        self.assertTrue(c.modifiable)
        circuit.transmettre(c, self.ts)
        c.refresh_from_db()
        self.assertEqual((c.statut, c.decision), (C.TRANSMIS, ""))

    def test_contrat_sante_certificat_et_avis(self):
        c = self._pret(nature="SANTE")
        self.assertTrue(c.certificat_obligatoire)   # moins de 60 ans
        with self.assertRaises(circuit.ErreurCircuit):   # mode de transmission du certificat manquant
            circuit.transmettre(c, self.ts)
        c.certificat_mode = "PLI"
        c.save()
        circuit.transmettre(c, self.ts)
        circuit.receptionner(c, self.admin)
        with self.assertRaises(circuit.ErreurCircuit):   # la commission attend l'avis
            circuit.decider(c, self.cadre, decision=C.VALIDE, date_decision=date(2026, 11, 1),
                            date_debut=date(2026, 11, 1), duree_mois=6)
        with self.assertRaises(circuit.ErreurCircuit):   # avis défavorable motivé
            circuit.donner_avis(c, self.medecin, certificat_recu_le=date(2026, 11, 1), avis="DEFAVORABLE", motivation="")
        circuit.donner_avis(c, self.medecin, certificat_recu_le=date(2026, 11, 1), avis="FAVORABLE", motivation="")
        circuit.decider(c, self.cadre, decision=C.VALIDE, date_decision=date(2026, 11, 2),
                        date_debut=date(2026, 11, 2), duree_mois=6)

    def test_alertes_et_renouvellement(self):
        c = self._pret()
        circuit.transmettre(c, self.ts)
        debut = timezone.localdate() - timedelta(days=170)
        circuit.decider(c, self.cadre, decision=C.VALIDE, date_decision=debut, date_debut=debut, duree_mois=6)
        c.refresh_from_db()
        self.assertEqual(c.alerte, "renouveler")
        suite = circuit.creer(self.benef, self.ts, C.PROLONGEMENT, c)
        self.assertEqual(suite.lignes.count(), 2)   # actions en cours reprises
        self.assertIsNone(C.objects.get(pk=c.pk).alerte)

    def test_droits(self):
        c = self._pret()
        self.assertIn(c, acces.contrats_visibles(self.ts))
        self.assertNotIn(c, acces.contrats_visibles(self.ts_b))
        self.assertIn(c, acces.contrats_visibles(self.cadre))
        self.assertTrue(acces.est_cadre_pole(self.cadre, c))
        self.assertFalse(acces.est_cadre_pole(self.admin, c))
        self.assertFalse(acces.peut_rediger(self.cadre, self.benef))
        cl = Client(HTTP_HOST="localhost")
        cl.force_login(self.ts_b)
        self.assertEqual(cl.get(f"/insertion/contrats/{c.pk}/").status_code, 404)
        cl.force_login(self.admin)
        self.assertEqual(cl.get(f"/insertion/contrats/{c.pk}/").status_code, 200)
        self.assertEqual(cl.post(f"/insertion/contrats/{c.pk}/decision/", {}).status_code, 403)
        self.assertEqual(cl.get(f"/insertion/contrats/{c.pk}/modifier/").status_code, 403)

    def test_saisie_web_et_pdf(self):
        cl = Client(HTTP_HOST="localhost")
        cl.force_login(self.ts)
        r = cl.post(f"/insertion/beneficiaire/{self.benef.code_interne}/contrats/nouveau/", {"type_contrat": "OUVERTURE"})
        c = C.objects.get(beneficiaire=self.benef)
        self.assertRedirects(r, f"/insertion/contrats/{c.pk}/modifier/", fetch_redirect_response=False)
        page = cl.get(f"/insertion/contrats/{c.pk}/modifier/")
        self.assertEqual(page.status_code, 200)
        donnees = {k: v for k, v in page.context["form"].initial.items() if v not in (None, False)}
        donnees.update({"type_contrat": "OUVERTURE", "nature": "EMPLOI", "duree_proposee_mois": 6,
                        "heures_activite_hebdo": 15, "objectifs": "Emploi", "date_signature": "2026-11-04",
                        "accord_allocataire": "on", "suite": "transmettre", "lignes-TOTAL_FORMS": 2,
                        "lignes-INITIAL_FORMS": 0, "lignes-0-action": self.action.pk})
        donnees.pop("conjoint", None)
        r = cl.post(f"/insertion/contrats/{c.pk}/modifier/", donnees)
        self.assertEqual(r.status_code, 302)
        c.refresh_from_db()
        self.assertEqual((c.statut, c.lignes.count()), (C.TRANSMIS, 1))
        for pdf in (contrat_pdf.contrat_pdf(c), contrat_pdf.courrier_medecin_pdf(c)):
            self.assertTrue(pdf.read(4) == b"%PDF")
        self.assertEqual(cl.get(f"/insertion/contrats/{c.pk}/contrat.pdf").status_code, 200)
