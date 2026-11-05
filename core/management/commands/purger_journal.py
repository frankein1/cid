# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/management/commands/purger_journal.py
"""Efface le journal d'activité plus ancien que la durée de conservation (12 mois par défaut,
clé de configuration JOURNAL_DUREE_MOIS). CID le fait aussi tout seul, une fois par jour, à la première connexion."""
from django.core.management.base import BaseCommand

from core import journal


class Command(BaseCommand):
    help = "Purge le journal d'activité au-delà de la durée de conservation"

    def handle(self, *args, **options):
        n = journal.purger()
        self.stdout.write(self.style.SUCCESS(f"✅ Journal d'activité : {n} ligne(s) effacée(s) "
                                             f"(conservation : {journal.duree_conservation_mois()} mois)"))
