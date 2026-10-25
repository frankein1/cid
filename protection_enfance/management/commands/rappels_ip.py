# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/management/commands/rappels_ip.py
"""Envoie les rappels IP (point intermédiaire, échéance dépassée). Les listes IP le font aussi à l'ouverture."""
from django.core.management.base import BaseCommand

from protection_enfance.services.ip_circuit import envoyer_rappels


class Command(BaseCommand):
    help = "Rappels des IP : point intermédiaire atteint, délai de 3 mois dépassé"

    def handle(self, *args, **options):
        n = envoyer_rappels()
        self.stdout.write(self.style.SUCCESS(f"{n} rappel(s) envoyé(s)."))
