# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/test_integration_rdvsp.py
"""
Essai de la synchronisation CID ↔ RDV-Solidarités contre une VRAIE copie de RDV-Solidarités.
Ne tourne que sur le banc d'essai GitHub (.github/workflows/essai-rdv-solidarites.yml), qui fournit
RDVSP_INTEGRATION=1, la copie lancée sur localhost:3000 et ses données fictives (SEED_JSON) ; ignoré ailleurs.

CID tourne ici comme un vrai serveur (port 8098) pour recevoir les avis signés de RDV-Solidarités.
"""
import json
import os
import subprocess
import time as chrono
import unittest
from datetime import date, datetime, time, timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import LiveServerTestCase
from django.utils import timezone

ACTIF = os.environ.get("RDVSP_INTEGRATION") == "1"


def _rails(*args):
    p = subprocess.run(["bin/rails", "runner", "../.github/rdvsp/agir.rb", *map(str, args)],
                       cwd=os.environ["MRS_DIR"], capture_output=True, text=True, timeout=240)
    if p.returncode:
        raise RuntimeError(p.stderr[:700] + " … " + p.stderr[-300:])
    return json.loads(p.stdout.strip().splitlines()[-1])


@unittest.skipUnless(ACTIF, "banc d'essai RDV-Solidarités uniquement")
class IntegrationRDVSolidarites(LiveServerTestCase):
    port = 8098
    host = "localhost"

    def setUp(self):
        from beneficiaire.models import Beneficiaire
        from connecteurs.models import CompteRDVSP, LienUsagerRDVSP, MdsRDVSP, ParametresRDVSP
        from core.models import User
        from mds.models import MDS, DemiJourneeReception, UserMDSProfile
        for cmd in ("init_capacites", "init_profils"):
            call_command(cmd, stdout=StringIO())
        self.seed = json.load(open(os.environ["SEED_JSON"]))
        self.env = mock.patch.dict(os.environ, {
            "RDVSP_ACTIF": "1", "RDVSP_URL": "http://localhost:3000", "RDVSP_CLIENT_ID": self.seed["client_id"],
            "RDVSP_CLIENT_SECRET": self.seed["client_secret"], "RDVSP_SECRET_AVIS": "secret-avis-integration",
            "RDVSP_PREFIXE": "cid-essai"})   # la sonde a déjà pris les références « cid-… »
        self.env.start()
        self.addCleanup(self.env.stop)
        self.mds = MDS.objects.create(code_mds="T2", nom="MDS TEST 02", adresse="2 rue des Essais", code_postal="13110",
                                      ville="Port-de-Bouc", latitude=43.405, longitude=4.987)
        self.agente = User.objects.create_user("ines", password="x", first_name="Inès", last_name="ESSAI",
                                               email=self.seed["agente_email"], matricule="INES")
        UserMDSProfile.objects.create(user=self.agente, mds=self.mds, actif=True, principale=True)
        self.admin = User.objects.create_superuser("synchro", password="x", matricule="SYN",
                                                   email=self.seed["agent_email"])
        CompteRDVSP.objects.create(utilisateur=self.admin, agent_id=str(self.seed["agent_id"]),
                                   jeton_acces=self.seed["jeton_cid"],
                                   jeton_renouvellement=self.seed["jeton_cid_renouvellement"],
                                   expire_le=timezone.now() + timedelta(minutes=100))
        p = ParametresRDVSP.get()
        p.compte_synchro, p.service_sp_id = self.admin, self.seed["service_id"]
        p.save()
        MdsRDVSP.objects.create(mds=self.mds, organisation_sp_id=self.seed["organisation2_id"], en_ligne=True)
        DemiJourneeReception.objects.create(agent=self.agente, mds=self.mds, jour_semaine=0, type_demi_journee="MATIN",
                                            heure_debut=time(9), heure_fin=time(12))
        self.benef = Beneficiaire.objects.create(code_interne="INT-RSA", civilite="MME", nom="ESSAI", prenom="Lucie",
                                                 date_naissance=date(1990, 1, 1), adresse="3 rue C",
                                                 code_postal="13110", ville="Port-de-Bouc", mds=self.mds)
        # usager côté RDV-Solidarités (étape 2 : créé par CID au moment de l'invitation)
        from connecteurs import rdv_service_public as api
        u = api.Client(self.admin).appel("POST", "/users", json={
            "organisation_ids": [self.seed["organisation2_id"]], "first_name": "Lucie", "last_name": "ESSAI",
            "birth_date": "1990-01-01"})
        self.usager_sp = (u.get("user") or u)["id"]
        LienUsagerRDVSP.objects.create(beneficiaire=self.benef, usager_rdvsp_id=str(self.usager_sp))

    def attendre(self, condition, delai=120):
        fin = chrono.time() + delai
        while chrono.time() < fin:
            if condition():
                return True
            chrono.sleep(1)
        return False

    def test_parcours_complet(self):
        from connecteurs import rdvsp_synchro as sync
        from connecteurs.models import AbsenceRDVSP, MotifRDVSPPublie, PlageRDVSP, RdvRDVSP
        from planning.models import CreneauRdv
        org = self.seed["organisation2_id"]

        # 1. Adresse de CID déclarée, permanences publiées
        res = sync.declarer_avis(f"{self.live_server_url}/connecteurs/rdv-service-public/avis/")
        self.assertEqual([e for _, e in res], [None], res)
        bilan = sync.synchroniser()
        self.assertEqual((bilan["publiees"], bilan["erreurs"]), (1, []), bilan)
        plages = _rails("plages", org)
        self.assertEqual(len(plages), 1, plages)
        self.assertIn("FREQ=WEEKLY", plages[0]["rrule"])
        self.assertIn("UNTIL", plages[0]["rrule"])          # publication limitée dans le temps
        self.assertEqual((plages[0]["agent"], plages[0]["motifs"]), (self.seed["agente_email"], ["Renouvellement RSA"]))
        lundi = PlageRDVSP.objects.get().premier_jour
        print(f"\n✅ Permanence publiée : {plages[0]['rrule']} ({plages[0]['start_time']}–{plages[0]['end_time']})")

        # 2. Créneau pris dans CID → bloqué dans RDV-Solidarités
        cr = CreneauRdv.objects.create(date=lundi, heure_debut=time(11), heure_fin=time(11, 30), agent=self.agente,
                                       mds=self.mds, statut="RESERVE", beneficiaire=self.benef)
        self.assertTrue(self.attendre(lambda: AbsenceRDVSP.objects.filter(creneau=cr).exists(), 30))
        absences = _rails("absences", self.seed["agente_email"])
        self.assertTrue(any(a["start_time"].startswith("11:00") for a in absences), absences)
        print("✅ Créneau pris dans CID bloqué dans RDV-Solidarités")

        # 3. L'usagère réserve en ligne → le RDV arrive dans l'agenda CID
        motif_id = MotifRDVSPPublie.objects.get().motif_sp_id
        from connecteurs.models import MdsRDVSP
        lieu_id = MdsRDVSP.objects.get(mds=self.mds).lieu_sp_id
        offset = datetime.combine(lundi, time(9)).astimezone().strftime("%z")
        offset = f"{offset[:3]}:{offset[3:]}"
        r1 = _rails("reserver", self.usager_sp, motif_id, lieu_id, self.seed["agente_id"],
                    f"{lundi}T09:30:00{offset}")["rdv_id"]
        self.assertTrue(self.attendre(lambda: RdvRDVSP.objects.filter(rdv_sp_id=r1).exists()), "aucun avis reçu")
        lien = RdvRDVSP.objects.get(rdv_sp_id=r1)
        self.assertTrue(lien.cree_par_usager)
        self.assertEqual((lien.creneau.statut, lien.creneau.beneficiaire, lien.creneau.heure_debut),
                         ("RESERVE", self.benef, time(9, 30)))
        print("✅ RDV pris en ligne reçu dans l'agenda CID, rattaché à l'usagère")

        # 4. 2e RDV en ligne → plafond atteint → demi-journée fermée en ligne
        r2 = _rails("reserver", self.usager_sp, motif_id, lieu_id, self.seed["agente_id"],
                    f"{lundi}T10:00:00{offset}")["rdv_id"]
        self.assertTrue(self.attendre(lambda: AbsenceRDVSP.objects.filter(raison=AbsenceRDVSP.PLAFOND).exists()))
        absences = _rails("absences", self.seed["agente_email"])
        self.assertTrue(any("Plafond" in a["title"] for a in absences), absences)
        print("✅ Plafond de 2 RDV en ligne : demi-journée fermée en ligne")

        # 5. Annulation en ligne → créneau CID annulé, demi-journée rouverte
        _rails("annuler", r1)
        self.assertTrue(self.attendre(lambda: RdvRDVSP.objects.get(rdv_sp_id=r1).annule_le is not None))
        self.assertTrue(self.attendre(lambda: not AbsenceRDVSP.objects.filter(raison=AbsenceRDVSP.PLAFOND).exists()))
        self.assertFalse(any("Plafond" in a["title"] for a in _rails("absences", self.seed["agente_email"])))
        self.assertEqual(RdvRDVSP.objects.get(rdv_sp_id=r1).creneau.statut, "ANNULE_USAGER")
        print("✅ Annulation en ligne reçue, demi-journée rouverte")

        # 6. « Venu » saisi dans CID → renvoyé à RDV-Solidarités
        c2 = RdvRDVSP.objects.get(rdv_sp_id=r2).creneau
        c2.statut = "VENU_RECU"
        c2.save()
        self.assertTrue(self.attendre(lambda: _rails("statut", r2)["status"] == "seen", 60))
        print("✅ Statut « venu » renvoyé à RDV-Solidarités")

        # 7. Étape 2 : invitation mensuelle → lien personnel accepté par RDV-Solidarités
        import requests
        from connecteurs import rdvsp_invitations as inv
        from insertion.models import ContratInsertion as C
        from insertion.services import contrat_circuit
        contrat = contrat_circuit.creer(self.benef, self.agente)
        fin = timezone.localdate() + timedelta(days=10)
        C.objects.filter(pk=contrat.pk).update(statut=C.VALIDE, date_debut=fin - timedelta(days=180), date_fin=fin)
        campagne, _ = inv.preparer(prevenir=False)
        self.assertEqual(campagne.invitations.count(), 1)
        bilan = inv.envoyer_campagne(campagne)
        self.assertEqual(bilan["erreurs"], 0, list(campagne.invitations.values_list("erreur", flat=True)))
        lien = campagne.invitations.get().lien
        page = requests.get(lien, timeout=60)   # suit les redirections : connexion de l'usager par son jeton
        self.assertEqual(page.status_code, 200, page.url)
        self.assertNotIn("invalide", page.text.lower()[:20000])
        self.assertIn("Renouvellement RSA", page.text)
        print(f"✅ Invitation : lien personnel accepté, le motif « Renouvellement RSA » est proposé ({page.url[:60]}…)")

        # 8. Demi-journée retirée dans CID → neutralisée dans RDV-Solidarités
        from mds.models import DemiJourneeReception
        DemiJourneeReception.objects.all().update(actif=False)
        bilan = sync.synchroniser()
        self.assertEqual((bilan["neutralisees"], bilan["erreurs"]), (1, []), bilan)
        self.assertTrue(any("retirée" in a["title"] for a in _rails("absences", self.seed["agente_email"])))
        print("✅ Permanence retirée dans CID neutralisée dans RDV-Solidarités")
