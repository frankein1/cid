# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# ru/tests.py
from datetime import date
from types import SimpleNamespace
from unittest import mock

from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import ValidationError
from django.test import RequestFactory, SimpleTestCase, TestCase

from core.signature import initiales_utilisateur, libelle_signature
from .models import DemandeRelationUsager, FicheRetourSAS
from .views import _peut_modifier_traitement, traitement


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


class TraitementRefusTests(TestCase):
    """Si la transmission est refusée, les modifications restent enregistrées et l'utilisateur le sait."""

    def _appel(self, exc):
        user = SimpleNamespace(
            pk=1, is_authenticated=True, is_superuser=False, is_active=True,
            a_la_capacite=lambda code: False,
        )
        demande = SimpleNamespace(pk=7, est_cloturee=False, agent_assigne=None)
        updated = mock.Mock(agent_assigne=None)
        form = mock.Mock(is_valid=mock.Mock(return_value=True))
        form.save.return_value = updated
        request = RequestFactory().post("/ru/7/traitement/", {"action": "soumettre"})
        request.user = user
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))
        with mock.patch("ru.views._demande_pour_user", return_value=demande), \
                mock.patch("ru.views._peut_modifier_traitement", return_value=True), \
                mock.patch("ru.views.TraitementRUForm", return_value=form), \
                mock.patch("ru.views.soumettre_evaluation", side_effect=exc):
            reponse = traitement(request, 7)
        return reponse, updated, [m.message for m in get_messages(request)]

    def test_saisie_conservee_et_manque_affiche(self):
        exc = ValidationError("Complétez la problématique repérée avant la transmission au cadre.")
        reponse, updated, messages_affiches = self._appel(exc)
        updated.save.assert_called_once()
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(len(messages_affiches), 1)
        self.assertIn("Modifications enregistrées", messages_affiches[0])
        self.assertIn("la transmission au cadre n'a pas été effectuée", messages_affiches[0])
        self.assertIn("Complétez la problématique", messages_affiches[0])
