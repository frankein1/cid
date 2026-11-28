# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/tests_expulsion_salle.py
"""Convocation d'expulsion : pas de courrier sans rendez-vous, salle réservée, lieu = mémo (MDS par défaut). Données fictives."""
from datetime import time, timedelta

from django.utils import timezone

from mds.models import MDSReception
from planning.models import CreneauRdv

from .models import ConvocationExpulsion as C, DossierExpulsion as D
from .services import expulsion_mds as M
from .tests_expulsion import _Base


class ConvocationExpulsionSalleTests(_Base):
    def setUp(self):
        super().setUp()
        self.nouveau(mds=self.mds.pk, code_usager="EX-1", loyer="650", charges="50", dette="2400",
                     tribunal="Tribunal judiciaire (fictif)")
        self.d = D.objects.get()
        self.d.referent = self.ts
        self.d.save()
        self.salle = MDSReception.objects.create(mds=self.mds, nom="Salle EX")
        self.jour = timezone.localdate() + timedelta(days=5)

    def quand(self, heure=time(10)):
        from datetime import datetime
        return timezone.make_aware(datetime.combine(self.jour, heure))

    def test_salle_reservee_refuse_la_convocation_sans_rdv(self):
        CreneauRdv.objects.create(date=self.jour, heure_debut=time(9), heure_fin=time(10, 30), mds=self.mds,
                                  salle=self.salle, agent=self.ts, nature='HORS_PERMANENCE', statut='RESERVE')
        with self.assertRaises(M.ConvocationImpossible):
            M.convoquer(self.d, self.ts, self.quand(time(10)), agent=self.ts, salle=self.salle)
        self.assertFalse(C.objects.exists())

    def test_lieu_par_defaut_la_mds_et_salle_reservee(self):
        conv = M.convoquer(self.d, self.ts, self.quand(), agent=self.ts, salle=self.salle)
        self.assertEqual(conv.rdv.salle, self.salle)
        self.assertTrue(conv.rdv.lieu_precis.startswith("MDS : "))
        self.assertEqual(conv.lieu, conv.rdv.lieu_precis)

    def test_lieu_saisi_devient_le_memo(self):
        conv = M.convoquer(self.d, self.ts, self.quand(), agent=self.ts, lieu="Domicile : 5 rue G")
        self.assertEqual(conv.rdv.lieu_precis, "Domicile : 5 rue G")
        self.assertEqual(conv.rdv.modalite, 'AUTRE')

    def test_duree_en_pas_de_dix_minutes(self):
        with self.assertRaises(M.ConvocationImpossible):
            M.convoquer(self.d, self.ts, self.quand(), agent=self.ts, duree=45)
        self.assertFalse(C.objects.exists())
