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
from insertion.models import (ActionInsertion, ContratInsertion as C, LigneActionContrat, PoleInsertion,
                              PrescriptionInsertion as P, QuestionAction, TypeActionInsertion)
from insertion.services import contrat_circuit as circuit
from insertion.services import contrat_pdf
from mds.models import MDS, UserMDSProfile


class _Base(TestCase):
    """Comptes, pôle, bénéficiaire et actions fictifs communs aux tests du module."""
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

class ContratTests(_Base):
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
        self.assertNotIn(c, acces.contrats_visibles(self.cadre))   # en préparation : pas encore au pôle
        circuit.transmettre(c, self.ts)
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



class PrescriptionTests(_Base):

    def _presc(self, action=None, **champs):
        from insertion.services import prescription_circuit as pc
        p = pc.creer(self.benef, self.ts, action or self.action)
        p.consentement, p.objectifs = True, "Objectif"
        for k, v in champs.items():
            setattr(p, k, v)
        p.save()
        return pc, p

    def test_creation_rattachee_au_contrat(self):
        c = self._pret()
        pc, p = self._presc()
        self.assertEqual((p.contrat, p.statut, p.pole), (c, P.BROUILLON, self.pole))

    def test_question_obligatoire_bloque_l_envoi(self):
        q = QuestionAction.objects.create(action=self.action, libelle="Permis", obligatoire=True)
        pc, p = self._presc()
        with self.assertRaises(circuit.ErreurCircuit):
            pc.adresser(p, self.ts)
        pc.enregistrer_reponses(p, {q.pk: "oui"})
        pc.adresser(p, self.ts)
        self.assertEqual(p.statut, P.EN_ATTENTE)

    def test_consentement_obligatoire(self):
        pc, p = self._presc(consentement=False)
        with self.assertRaises(circuit.ErreurCircuit):
            pc.adresser(p, self.ts)

    def test_validation_pole_puis_retour_et_ligne_du_contrat(self):
        c = self._pret()
        nouvelle = ActionInsertion.objects.create(code="T-ACT3", libelle="Action validée par le pôle",
                                                  type_action=TypeActionInsertion.objects.first(), validation_pole=True)
        pc, p = self._presc(nouvelle)
        pc.adresser(p, self.ts)
        self.assertEqual(p.statut, P.A_VALIDER)
        self.assertFalse(c.lignes.filter(action=nouvelle).exists())   # pas de ligne avant le porteur
        self.assertFalse(acces.peut_valider_prescription(self.medecin, p))
        with self.assertRaises(circuit.ErreurCircuit):
            pc.valider(p, self.admin, False, "")   # motif obligatoire
        pc.valider(p, self.admin, True)
        self.assertEqual(p.statut, P.EN_ATTENTE)
        ligne = c.lignes.get(action=nouvelle)
        self.assertEqual(ligne.prescription, p)
        pc.noter_retour(p, self.admin, issue=P.INTEGREE, date_entree=date(2026, 11, 10))
        with self.assertRaises(circuit.ErreurCircuit):   # arrêt sans motif
            pc.noter_retour(p, self.ts, issue=P.ARRETEE, date_sortie=date(2027, 1, 5))
        pc.noter_retour(p, self.ts, issue=P.REORIENTEE, date_sortie=date(2027, 1, 5), reorientation="FRANCE_TRAVAIL")
        ligne.refresh_from_db()
        self.assertEqual((ligne.date_entree, ligne.date_sortie), (date(2026, 11, 10), date(2027, 1, 5)))
        self.assertIn("France Travail", ligne.motif_sortie)

    def test_transitions_impossibles(self):
        pc, p = self._presc()
        pc.adresser(p, self.ts)
        with self.assertRaises(circuit.ErreurCircuit):   # pas de sortie avant l'entrée
            pc.noter_retour(p, self.ts, issue=P.TERMINEE, date_sortie=date(2027, 1, 5))

    def test_droits_et_reponses_restreintes(self):
        q = QuestionAction.objects.create(action=self.action, libelle="Grille santé", restreinte=True)
        pc, p = self._presc()
        pc.enregistrer_reponses(p, {q.pk: "oui"})
        self.assertNotIn(p, acces.prescriptions_visibles(self.admin))   # brouillon : pas au pôle
        pc.adresser(p, self.ts)
        self.assertIn(p, acces.prescriptions_visibles(self.admin))
        self.assertNotIn(p, acces.prescriptions_visibles(self.ts_b))
        self.assertFalse(acces.voit_reponses_restreintes(self.admin, p))
        self.assertTrue(acces.voit_reponses_restreintes(self.medecin, p))
        self.assertTrue(acces.voit_reponses_restreintes(self.ts, p))
        cl = Client(HTTP_HOST="localhost")
        cl.force_login(self.admin)
        self.assertNotIn("<span class=\"whitespace-pre-line\">oui", cl.get(f"/insertion/prescriptions/{p.pk}/").content.decode())
        self.assertEqual(cl.get(f"/insertion/prescriptions/{p.pk}/modifier/").status_code, 403)

    def test_saisie_web_et_pdf(self):
        q = QuestionAction.objects.create(action=self.action, libelle="Besoins", type_reponse=QuestionAction.CHOIX_MULTIPLE,
                                          choix="A\nB\nC")
        cl = Client(HTTP_HOST="localhost")
        cl.force_login(self.ts)
        r = cl.post(f"/insertion/beneficiaire/{self.benef.code_interne}/prescriptions/nouvelle/", {"action": self.action.pk})
        p = P.objects.get(beneficiaire=self.benef)
        self.assertRedirects(r, f"/insertion/prescriptions/{p.pk}/modifier/", fetch_redirect_response=False)
        r = cl.post(f"/insertion/prescriptions/{p.pk}/modifier/", {
            "demande_par": "TS", "objectifs": "Emploi", "freins": ["MOBILITE", "GARDE"], f"q_{q.pk}": ["A", "C"],
            "consentement": "on", "suite": "adresser"})
        self.assertEqual(r.status_code, 302)
        p.refresh_from_db()
        self.assertEqual((p.statut, p.freins, p.reponses.get().valeur), (P.EN_ATTENTE, ["MOBILITE", "GARDE"], "A\nC"))
        self.assertEqual(cl.get(f"/insertion/prescriptions/{p.pk}/fiche.pdf").status_code, 200)
        r = cl.post(f"/insertion/prescriptions/{p.pk}/retour/", {"issue": "INTEGREE", "date_entree": "2026-11-12",
                                                                  "premier_rdv_issue": "PRESENT"})
        p.refresh_from_db()
        self.assertEqual((p.statut, p.date_entree), (P.INTEGREE, date(2026, 11, 12)))


class FicheLiaisonTests(_Base):
    def _texte_pdf(self, p):
        import subprocess
        from insertion.services.prescription_pdf import fiche_pdf
        return subprocess.run(["pdftotext", "-", "-"], input=fiche_pdf(p).read(), capture_output=True).stdout.decode()

    def test_nir_seulement_si_l_action_le_demande(self):
        from insertion.services import prescription_circuit as pc
        Beneficiaire.objects.filter(pk=self.benef.pk).update(nir="290017500000000")
        self.benef.refresh_from_db()
        p = pc.creer(self.benef, self.ts, self.action)
        self.assertNotIn("290017500000000", self._texte_pdf(p))
        ActionInsertion.objects.filter(pk=self.action.pk).update(fiche_avec_nir=True)
        p.action.refresh_from_db()
        self.assertIn("290017500000000", self._texte_pdf(p))


class ReorientationTests(_Base):
    def _demande(self, **champs):
        from insertion.services import reorientation_circuit as rc
        d = rc.creer(self.benef, self.ts)
        d.motif, d.orientation_proposee = "Projet emploi", "FRANCE_TRAVAIL"
        for k, v in champs.items():
            setattr(d, k, v)
        d.save()
        return rc, d

    def _ft(self):
        from insertion.models import OrganismeOrientation
        return OrganismeOrientation.objects.create(nom="France Travail (essai)", categorie="FRANCE_TRAVAIL")

    def test_inscription_puis_commission_reprend_les_attentes(self):
        from insertion.models import DemandeReorientation as D
        rc, d = self._demande(motif="")
        with self.assertRaises(circuit.ErreurCircuit):   # motif obligatoire
            rc.inscrire(d, self.ts)
        d.motif = "Projet emploi"
        d.save()
        rc.inscrire(d, self.ts)
        self.assertEqual((d.statut, d.commission), (D.INSCRITE, None))   # pas encore de commission
        c, n = rc.creer_commission(self.pole, self.admin, date=timezone.localdate() + timedelta(days=10))
        d.refresh_from_db()
        self.assertEqual((n, d.commission), (1, c))
        rc2, d2 = self._demande()
        rc2.inscrire(d2, self.ts)
        self.assertEqual(d2.commission, c)   # rejoint la prochaine commission en préparation

    def test_decisions_cloture_et_file_active(self):
        from insertion.models import DemandeReorientation as D
        from insertion.services.commission_pdf import releve_pdf
        from insertion.views_contrats import _filtrer
        ft = self._ft()
        # contrat validé, échu : il est dans les « échus »… jusqu'à la réorientation
        contrat = self._pret()
        circuit.transmettre(contrat, self.ts)
        debut = timezone.localdate() - timedelta(days=200)
        circuit.decider(contrat, self.cadre, decision=C.VALIDE, date_decision=debut, date_debut=debut, duree_mois=6)
        self.assertIn(contrat, _filtrer(C.objects.all(), "expires"))
        rc, d = self._demande()
        rc.inscrire(d, self.ts)
        c, _ = rc.creer_commission(self.pole, self.admin, date=timezone.localdate())
        d.refresh_from_db()
        with self.assertRaises(circuit.ErreurCircuit):   # clôture impossible sans décision
            rc.cloturer(c, self.admin)
        with self.assertRaises(circuit.ErreurCircuit):   # acceptée sans organisme
            rc.decider(d, self.cadre, decision=D.ACCEPTEE)
        rc.decider(d, self.cadre, decision=D.ACCEPTEE, organisme_retenu=ft, date_effet=timezone.localdate())
        rc.cloturer(c, self.cadre)
        d.refresh_from_db()
        self.assertEqual(d.statut, D.ACCEPTEE)
        self.assertNotIn(contrat, _filtrer(C.objects.all(), "expires"))
        self.assertTrue(releve_pdf(c).read(4) == b"%PDF")

    def test_ajournement_passe_a_la_suivante(self):
        from insertion.models import DemandeReorientation as D
        rc, d = self._demande()
        rc.inscrire(d, self.ts)
        c, _ = rc.creer_commission(self.pole, self.admin, date=timezone.localdate())
        d.refresh_from_db()
        with self.assertRaises(circuit.ErreurCircuit):   # motif obligatoire
            rc.decider(d, self.admin, decision=D.AJOURNEE)
        rc.decider(d, self.admin, decision=D.AJOURNEE, motif="À revoir")
        suivante, _ = rc.creer_commission(self.pole, self.admin, date=timezone.localdate() + timedelta(days=90))
        rc.cloturer(c, self.admin)
        d.refresh_from_db()
        self.assertEqual((d.statut, d.commission, d.nb_ajournements, d.decision), (D.INSCRITE, suivante, 1, ""))
        self.assertEqual(c.examens.get().decision, D.AJOURNEE)   # le relevé de la 1re commission le garde

    def test_droits(self):
        from insertion.models import DemandeReorientation as D
        rc, d = self._demande()
        self.assertNotIn(d, acces.reorientations_visibles(self.admin))   # brouillon : pas au pôle
        rc.inscrire(d, self.ts)
        self.assertIn(d, acces.reorientations_visibles(self.admin))
        self.assertNotIn(d, acces.reorientations_visibles(self.medecin))
        self.assertNotIn(d, acces.reorientations_visibles(self.ts_b))
        self.assertTrue(acces.peut_gerer_commission(self.cadre, self.pole))
        self.assertFalse(acces.peut_gerer_commission(self.ts, self.pole))
        c, _ = rc.creer_commission(self.pole, self.admin, date=timezone.localdate())
        cl = Client(HTTP_HOST="localhost")
        cl.force_login(self.ts)
        self.assertEqual(cl.get(f"/insertion/commissions/{c.pk}/").status_code, 404)
        self.assertEqual(cl.post(f"/insertion/commissions/{c.pk}/cloturer/").status_code, 404)

    def test_parcours_web(self):
        from insertion.models import DemandeReorientation as D
        ft = self._ft()
        cl = Client(HTTP_HOST="localhost")
        cl.force_login(self.ts)
        cl.post(f"/insertion/beneficiaire/{self.benef.code_interne}/reorientation/nouvelle/")
        d = D.objects.get(beneficiaire=self.benef)
        r = cl.post(f"/insertion/reorientations/{d.pk}/modifier/", {
            "motif": "Emploi", "orientation_proposee": "FRANCE_TRAVAIL", "organisme_propose": ft.pk,
            "avis_personne": "ACCORD", "suite": "inscrire"})
        self.assertEqual(r.status_code, 302)
        d.refresh_from_db()
        self.assertEqual(d.statut, D.INSCRITE)
        cl.force_login(self.admin)
        r = cl.post("/insertion/commissions/", {"pole": self.pole.pk, "date": "2026-12-15", "lieu": "Salle"})
        c = self.pole.commissions_reorientation.get()
        r = cl.post(f"/insertion/commissions/{c.pk}/dossier/{d.pk}/decision/", {
            f"d{d.pk}-decision": "ACCEPTEE", f"d{d.pk}-organisme_retenu": ft.pk, f"d{d.pk}-date_effet": "2027-01-01"})
        cl.post(f"/insertion/commissions/{c.pk}/cloturer/")
        d.refresh_from_db()
        self.assertEqual((d.statut, d.organisme_retenu), (D.ACCEPTEE, ft))
        self.assertEqual(cl.get(f"/insertion/reorientations/{d.pk}/notification.pdf").status_code, 200)
        self.assertEqual(cl.get(f"/insertion/commissions/{c.pk}/ordre-du-jour.pdf").status_code, 200)
