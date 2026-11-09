# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/tests_dsf_delais.py
"""DSF : délais en jours ouvrés, critères du bordereau de carence (note MDS du 27/03/2023). Données fictives."""
from datetime import date, datetime, timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from .models import ConvocationExpulsion as C, DossierExpulsion as D, EtapeExpulsion
from .services import jours_ouvres as J
from .services.expulsion_mds import criteres_carence
from .tests_expulsion import _Base


class JoursOuvresTests(SimpleTestCase):
    def test_paques_et_feries_mobiles(self):
        self.assertEqual(J.paques(2026), date(2026, 4, 5))
        self.assertEqual(J.paques(2025), date(2025, 4, 20))
        self.assertIn(date(2026, 5, 14), J.feries(2026))            # Ascension
        self.assertIn(date(2026, 5, 25), J.feries(2026))            # Lundi de Pentecôte

    def test_ajouter_retrancher_sautent_week_end_et_feries(self):
        self.assertEqual(J.ajouter(date(2026, 5, 7), 1), date(2026, 5, 11))    # jeudi 7 → 8 mai férié → lundi 11
        self.assertEqual(J.retrancher(date(2026, 5, 11), 1), date(2026, 5, 7))
        self.assertEqual(J.ajouter(date(2026, 12, 11), 5), date(2026, 12, 18))  # une semaine ouvrée


class CarenceEtDelaisTests(_Base):
    def setUp(self):
        super().setUp()
        self.nouveau(mds=self.mds.pk, code_usager="EX-1", loyer="600", charges="40", dette="1800",
                     tribunal="Tribunal judiciaire (fictif)")
        self.d = D.objects.get()
        self.d.date_audience = date(2026, 12, 14)                               # un lundi
        self.d.save()

    def absences(self):
        for i, j in enumerate((date(2026, 11, 2), date(2026, 11, 20)), start=1):
            C.objects.create(dossier=self.d, type_convocation=C.DSF_1 if i == 1 else C.DSF_2,
                             date_rdv=timezone.make_aware(datetime.combine(j, datetime.min.time())),
                             statut=C.ABSENT)

    def test_criteres_carence_trois_conditions(self):
        self.absences()
        self.assertEqual(len(criteres_carence(self.d)), 1)                      # bailleur non sollicité
        self.d.questionnaire_bailleur_le = date(2026, 11, 3)
        self.assertEqual(criteres_carence(self.d), [])
        self.d.observations_locataire = True
        self.assertIn("le locataire a transmis des observations", criteres_carence(self.d))
        self.d.observations_locataire = False
        self.d.questionnaire_bailleur_retour = date(2026, 11, 25)
        self.assertIn("le bailleur a transmis des informations", criteres_carence(self.d))

    def test_echeances_en_jours_ouvres(self):
        self.absences()
        transmission = [e for libelle, e, _ in self.d.echeances_dsf() if libelle.startswith("Transmettre")][0]
        self.assertEqual(transmission, date(2026, 12, 7))                       # 5 jours ouvrés avant lundi 14
        self.assertEqual(len(self.d.echeances_dsf()), 3)                        # pas de signalement : pas d'entretien

    def test_alerte_entretien_apres_signalement(self):
        EtapeExpulsion.objects.create(dossier=self.d, type_etape='SIGNALEMENT', date=date(2026, 11, 2))
        libelles = [libelle for libelle, _, _ in self.d.echeances_dsf()]
        self.assertTrue(any(l.startswith("Proposer l'entretien") for l in libelles))
        premier = [e for libelle, e, _ in self.d.echeances_dsf() if libelle.startswith("Proposer")][0]
        self.assertEqual(premier, J.ajouter(date(2026, 11, 2), 15))
        self.d.date_audience = timezone.localdate() + timedelta(days=8)
        self.d.save()
        self.assertTrue(any("Transmettre le DSF" in a for a in self.d.alertes()))
