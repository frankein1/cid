# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# adultevul/tests.py
from datetime import date, timedelta
from io import StringIO

from dateutil.relativedelta import relativedelta
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import TestCase

from core.models import Capacite, Profil, User
from mds.models import MDS, UserMDSProfile
from .models import SituationAdulteVulnerable
from .services import (
    cloturer, constituer_cellule, controler_rapport, creer_situation, decider, enregistrer_cellule,
    peut_evaluer, peut_piloter, qualifier, renvoyer_rapport, soumettre_rapport, valider_rapport,
)


class BaseAdulteVulnerable(TestCase):
    """Fixtures communes : deux MDS, cadres, évaluateur, directeur."""
    def setUp(self):
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.mds = MDS.objects.create(code_mds="AV1", nom="MDS AV A", adresse="1 rue A", code_postal="13110",
                                      ville="Port-de-Bouc")
        self.autre = MDS.objects.create(code_mds="AV2", nom="MDS AV B", adresse="1 rue B", code_postal="13500",
                                        ville="Martigues")
        self.cadre = self.agent("cadre", self.mds, "AV_PILOTE")
        self.ts = self.agent("ts", self.mds, "AV_EVALUATEUR")
        self.autre_cadre = self.agent("autre", self.autre, "AV_PILOTE")
        self.directeur = self.agent("dir", self.mds, None, capacites=["peut_decider"])

    def agent(self, login, mds, profil, capacites=()):
        u = User.objects.create_user(login, password="x", matricule=login.upper())
        if profil:
            u.profils.add(Profil.objects.get(code=profil))
        if capacites:
            tmp = Profil.objects.create(code=f"TEST_{login.upper()}", nom=login)
            tmp.capacites.set(Capacite.objects.filter(code__in=capacites))
            u.profils.add(tmp)
        UserMDSProfile.objects.create(user=u, mds=mds, actif=True, principale=True)
        return u

    def situation(self, **extra):
        data = dict(personne_nom="DUPONT", personne_prenom="Jeanne", faits="Retrouvée seule, dénutrie.",
                    mds=self.mds, origine="PARTICULIER", mode_recueil="TELEPHONE")
        data.update(extra)
        return SituationAdulteVulnerable(**data)

    def recueillie(self, **extra):
        return creer_situation(self.situation(**extra), self.ts)

    def qualifiee(self):
        s = self.recueillie()
        qualifier(s, self.cadre, True, "Carence de soins avérée")
        return s

    def cellule_complete(self, s, propositions=("ACCOMPAGNEMENT",), referents=None):
        data = dict(date_cellule=date.today(), urgence="DEUX_MOIS", plan_action="Visite à domicile, MASP à étudier",
                    propositions=list(propositions), argumentation="")
        return constituer_cellule(s, self.cadre, data, [self.ts] if referents is None else referents)


class CircuitAdulteVulnerableTests(BaseAdulteVulnerable):
    # --- recueil et qualification
    def test_recueil_numero_et_statut(self):
        s = self.recueillie()
        self.assertTrue(s.numero.startswith("AV-"))
        self.assertEqual(s.statut, "RECUE")
        self.assertEqual(s.historique.count(), 1)

    def test_recueil_refuse_hors_mds(self):
        autre = self.agent("hors", self.autre, "AV_EVALUATEUR")
        with self.assertRaises(PermissionDenied):
            creer_situation(self.situation(), autre)

    def test_qualification_reservee_au_cadre(self):
        s = self.recueillie()
        with self.assertRaises(PermissionDenied):
            qualifier(s, self.ts, True, "motif")
        with self.assertRaises(PermissionDenied):
            qualifier(s, self.autre_cadre, True, "motif")

    def test_qualification_exige_un_motif(self):
        s = self.recueillie()
        with self.assertRaises(ValidationError):
            qualifier(s, self.cadre, False, "  ")

    def test_non_qualifiee_puis_cloture(self):
        s = self.recueillie()
        qualifier(s, self.cadre, False, "Information non fondée après vérification")
        self.assertEqual(s.statut, "NON_QUALIFIEE")
        cloturer(s, self.cadre)
        self.assertEqual(s.statut, "CLOTUREE")

    # --- cellule
    def test_cellule_exige_qualification(self):
        s = self.recueillie()
        with self.assertRaises(PermissionDenied):
            self.cellule_complete(s)

    def test_cellule_constituee_passe_en_evaluation(self):
        s = self.qualifiee()
        self.cellule_complete(s)
        s.refresh_from_db()
        self.assertEqual(s.statut, "EVALUATION")
        self.assertEqual(s.cellule.referents.count(), 1)

    def test_delai_rapport_selon_urgence(self):
        s = self.qualifiee()
        cellule = self.cellule_complete(s)
        self.assertEqual(s.date_limite_rapport, cellule.date_cellule + relativedelta(months=2))
        cellule.urgence = "HUIT_JOURS"
        cellule.save()
        s.refresh_from_db()
        self.assertEqual(s.date_limite_rapport, cellule.date_cellule + timedelta(days=8))

    # --- rapport, visa, décision
    def test_rapport_incomplet_refuse_avec_la_liste(self):
        s = self.qualifiee()
        cellule = self.cellule_complete(s, propositions=(), referents=[])
        cellule.plan_action = ""
        cellule.save()
        self.assertEqual(controler_rapport(s), [
            "le référent de la situation", "le plan d'action", "au moins une proposition"])
        with self.assertRaises(ValidationError) as ctx:
            soumettre_rapport(s, self.cadre)
        self.assertIn("le référent de la situation", str(ctx.exception))
        s.refresh_from_db()
        self.assertEqual(s.statut, "EVALUATION")

    def test_classement_exige_argumentation_et_seul(self):
        s = self.qualifiee()
        cellule = self.cellule_complete(s, propositions=("CLASSEMENT", "ACCOMPAGNEMENT"))
        self.assertIn("le classement sans suite ne peut pas être combiné à une autre proposition",
                      controler_rapport(s))
        cellule.propositions = ["CLASSEMENT"]
        cellule.save()
        self.assertEqual(controler_rapport(s), ["l'argumentation du classement sans suite"])

    def test_rapport_complet_est_verrouille_apres_soumission(self):
        s = self.qualifiee()
        self.cellule_complete(s)
        soumettre_rapport(s, self.ts)
        s.refresh_from_db()
        self.assertEqual(s.statut, "RAPPORT")
        with self.assertRaises(PermissionDenied):
            enregistrer_cellule(s, self.ts, {"plan_action": "autre"}, [self.ts])

    def test_visa_puis_decision_puis_cloture(self):
        s = self.qualifiee()
        self.cellule_complete(s)
        soumettre_rapport(s, self.ts)
        with self.assertRaises(PermissionDenied):
            valider_rapport(s, self.autre_cadre)
        valider_rapport(s, self.cadre)
        s.refresh_from_db()
        self.assertEqual(s.statut, "VALIDEE")
        with self.assertRaises(PermissionDenied):
            decider(s, self.cadre, "décision")  # le cadre ne décide pas : seul le directeur
        decider(s, self.directeur, "Accompagnement non contractualisé retenu")
        s.refresh_from_db()
        self.assertEqual(s.statut, "DECIDEE")
        cloturer(s, self.cadre)
        s.refresh_from_db()
        self.assertEqual(s.statut, "CLOTUREE")

    def test_renvoi_rouvre_l_evaluation(self):
        s = self.qualifiee()
        self.cellule_complete(s)
        soumettre_rapport(s, self.ts)
        renvoyer_rapport(s, self.cadre, "Préciser la visite à domicile")
        s.refresh_from_db()
        self.assertEqual(s.statut, "EVALUATION")
        enregistrer_cellule(s, self.ts, {"plan_action": "Visite à domicile effectuée"}, [self.ts])

    def test_evaluateur_hors_referents_ne_peut_pas_soumettre(self):
        s = self.qualifiee()
        autre_ts = self.agent("ts2", self.mds, "AV_EVALUATEUR")
        self.cellule_complete(s)
        self.assertFalse(peut_evaluer(autre_ts, s))
        self.assertTrue(peut_evaluer(self.ts, s))
        self.assertTrue(peut_piloter(self.cadre, s))



class VuesAdulteVulnerableTests(BaseAdulteVulnerable):
    """Parcours complet par les pages : vérifie que les gabarits et les garde-fous fonctionnent."""

    def test_parcours_par_les_pages(self):
        self.client.force_login(self.ts)
        self.assertEqual(self.client.get('/adultevul/').status_code, 200)
        self.assertEqual(self.client.get('/adultevul/recueillir/').status_code, 200)
        reponse = self.client.post('/adultevul/recueillir/', {
            'date_reception': date.today().isoformat(), 'mode_recueil': 'ECRIT', 'origine': 'FAMILLE',
            'faits': 'Logement insalubre, personne isolée.', 'personne_nom': 'MARTIN', 'personne_prenom': 'Paul',
            'personne_adresse': '3 rue du Port', 'mds': self.mds.pk, 'elements': ['CARENCE'],
            'danger_immediat': 'on',
        })
        self.assertEqual(reponse.status_code, 302)
        s = SituationAdulteVulnerable.objects.get(personne_nom='MARTIN')
        self.assertEqual(s.elements, ['CARENCE'])
        self.assertTrue(s.danger_immediat)
        self.assertEqual(self.client.get(s.get_absolute_url()).status_code, 200)

        self.client.force_login(self.cadre)
        self.assertEqual(self.client.get(s.get_absolute_url()).status_code, 200)
        self.client.post(f'/adultevul/{s.pk}/qualifier/', {'qualifiee': 'oui', 'motif': 'Carence avérée'})
        s.refresh_from_db()
        self.assertEqual(s.statut, 'QUALIFIEE')
        self.assertEqual(self.client.get(f'/adultevul/{s.pk}/cellule/').status_code, 200)
        self.client.post(f'/adultevul/{s.pk}/cellule/', {
            'date_cellule': date.today().isoformat(), 'urgence': 'HUIT_JOURS', 'modalites': 'VAD',
            'plan_action': 'Visite à domicile', 'propositions': ['ACCOMPAGNEMENT'],
            'referents': [self.ts.pk], 'participants': 'Adjoint, TS',
        })
        s.refresh_from_db()
        self.assertEqual(s.statut, 'EVALUATION')
        self.assertEqual(s.cellule.propositions, ['ACCOMPAGNEMENT'])

        self.client.force_login(self.ts)
        self.client.post(f'/adultevul/{s.pk}/soumettre/')
        s.refresh_from_db()
        self.assertEqual(s.statut, 'RAPPORT')
        self.assertEqual(self.client.get(f'/adultevul/{s.pk}/cellule/').status_code, 302)

    def test_hors_mds_refuse(self):
        s = self.recueillie()
        self.client.force_login(self.autre_cadre)
        self.assertEqual(self.client.get(s.get_absolute_url()).status_code, 404)


class AnnexesAdulteVulnerableTests(BaseAdulteVulnerable):
    def setUp(self):
        super().setUp()
        self.s = qualifier_et_cellule(self)

    def test_annexes_pdf_generees(self):
        from io import BytesIO
        from .pdf import ANNEXES, rendre_annexe
        self.s.cellule.propositions = ["POLICE", "CLASSEMENT", "ACCOMPAGNEMENT"]
        self.s.cellule.argumentation = "Argumentation de test"
        self.s.cellule.save()
        for numero in ANNEXES:
            tampon = BytesIO()
            rendre_annexe(self.s, numero, tampon)
            self.assertTrue(tampon.getvalue().startswith(b"%PDF"), numero)

    def test_annexe_liee_a_une_proposition_seulement(self):
        from .pdf import annexe_disponible
        self.assertTrue(annexe_disponible(self.s, "1"))
        self.assertTrue(annexe_disponible(self.s, "2"))
        self.assertFalse(annexe_disponible(self.s, "4"))
        self.s.cellule.propositions = ["CLASSEMENT"]
        self.s.cellule.save()
        self.assertTrue(annexe_disponible(self.s, "4"))
        self.assertFalse(annexe_disponible(self.s, "5"))

    def test_telechargement_et_refus(self):
        self.client.force_login(self.ts)
        reponse = self.client.get(f"/adultevul/{self.s.pk}/annexe/1.pdf")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse["Content-Type"], "application/pdf")
        self.assertEqual(self.client.get(f"/adultevul/{self.s.pk}/annexe/4.pdf").status_code, 404)
        self.assertEqual(self.client.get(f"/adultevul/{self.s.pk}/annexe/99.pdf").status_code, 404)
        self.client.force_login(self.autre_cadre)
        self.assertEqual(self.client.get(f"/adultevul/{self.s.pk}/annexe/1.pdf").status_code, 404)


def qualifier_et_cellule(test):
    s = creer_situation(test.situation(), test.ts)
    qualifier(s, test.cadre, True, "Carence avérée")
    constituer_cellule(s, test.cadre, dict(date_cellule=date.today(), urgence="DEUX_MOIS",
                                           plan_action="Visite", propositions=["ACCOMPAGNEMENT"],
                                           argumentation=""), [test.ts])
    s.refresh_from_db()
    return s
