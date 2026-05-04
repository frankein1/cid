# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# protection_enfance/tests/test_ip.py
from django.test import TestCase
from protection_enfance.models.informations_preoccupantes import InformationPreoccupante, NumeroCounter
from protection_enfance.services.ip_manager import IPManager

class IPTests(TestCase):
    def test_generate_numero_and_create(self):
        ip = IPManager.creer_information({'enfant_nom':'Test Kid','description':'desc'})
        self.assertTrue(ip.numero.startswith('D13-'))
        self.assertEqual(InformationPreoccupante.objects.count(), 1)
