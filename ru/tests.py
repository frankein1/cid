# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# ru/tests.py
from datetime import date
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from core.signature import initiales_utilisateur, libelle_signature
from .models import DemandeRelationUsager, FicheRetourSAS
from .views import _peut_modifier_traitement


class DelaiRUTests(SimpleTestCase):
    def test_delai_ordinaire_est_un_mois_calendaire(self):
        demande = DemandeRelationUsager(
            date_reception=date(2026, 1, 31),
            date_notification_mds=date(2026, 1, 31),
            priorite=DemandeRelationUsager.Priorite.ORDINAIRE,
        )
        self.assertEqual(demande.date_echeance, date(2026, 2, 28))

    def test_delai_signale_est_de_quinze_jours_calendaires(self):
        demande = DemandeRelationUsager(
            date_reception=date(2026, 1, 31),
            date_notification_mds=date(2026, 1, 31),
            priorite=DemandeRelationUsager.Priorite.SIGNALEE,
        )
        self.assertEqual(demande.date_echeance, date(2026, 2, 15))

    def test_aucune_echeance_avant_envoi_mds(self):
        demande = DemandeRelationUsager(date_reception=date(2026, 1, 1))
        self.assertIsNone(demande.date_echeance)


class SignatureCommuneTests(SimpleTestCase):
    def test_initiales_et_libelle_signature(self):
        agent = SimpleNamespace(first_name="Élise", last_name="Martin", username="emartin")
        self.assertEqual(initiales_utilisateur(agent), "ÉM")
        self.assertEqual(libelle_signature(agent), "É. Martin")

    def test_prenom_seul_garde_l_identifiant(self):
        agent = SimpleNamespace(first_name="Élise", last_name="", username="emartin")
        self.assertEqual(libelle_signature(agent), "emartin")

    def test_signature_sans_nom_utilise_identifiant(self):
        agent = SimpleNamespace(first_name="", last_name="", username="ruadmin")
        self.assertEqual(initiales_utilisateur(agent), "RUADMIN"[:2])
        self.assertEqual(libelle_signature(agent), "ruadmin")


class RUAccessTests(SimpleTestCase):
    def test_mds_ne_voit_pas_une_demande_avant_notification(self):
        user = SimpleNamespace(
            is_authenticated=True, is_superuser=False,
            a_la_capacite=lambda code: code == "peut_voir",
            a_acces_mds=lambda mds: True,
        )
        demande = DemandeRelationUsager(mds_id=1, date_notification_mds=None)
        self.assertFalse(demande.peut_etre_vu_par(user))

    def test_sas_peut_voir_une_saisine_en_attente_de_transmission(self):
        user = SimpleNamespace(
            is_authenticated=True, is_superuser=False,
            a_la_capacite=lambda code: code == "ru_gerer_sas",
        )
        demande = DemandeRelationUsager(mds_id=1, date_notification_mds=None)
        self.assertTrue(demande.peut_etre_vu_par(user))


class FicheRetourSASTests(SimpleTestCase):
    def test_reorientation_exige_un_service_destinataire(self):
        fiche = FicheRetourSAS(
            type_reponse=FicheRetourSAS.REORIENTATION,
            service_reoriente="",
            synthese_reponse="Réponse communiquée.",
        )
        with self.assertRaises(ValidationError):
            fiche.clean()


class VerrouAvantVisaTests(SimpleTestCase):
    def _cadre(self):
        return SimpleNamespace(
            pk=1, is_authenticated=True, is_superuser=False,
            a_la_capacite=lambda code: code in {"peut_voir", "peut_valider"},
            a_acces_mds=lambda mds: True,
        )

    def test_cadre_peut_corriger_avant_visa_seulement(self):
        cadre = self._cadre()
        for statut, attendu in [
            (DemandeRelationUsager.Statut.A_TRAITER_MDS, True),
            (DemandeRelationUsager.Statut.EN_EVALUATION, True),
            (DemandeRelationUsager.Statut.A_VALIDER_CADRE, True),
            (DemandeRelationUsager.Statut.A_VALIDER_SAS, False),
            (DemandeRelationUsager.Statut.CLOTUREE, False),
        ]:
            demande = SimpleNamespace(
                mds_id=1, mds=SimpleNamespace(pk=1), statut=statut, agent_assigne_id=None,
                est_cloturee=statut == DemandeRelationUsager.Statut.CLOTUREE,
            )
            self.assertEqual(_peut_modifier_traitement(cadre, demande), attendu, statut)
