# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/management/commands/rappels_aides.py
"""Rappels de délais des AFASE (ajournement 15 jours, demande réputée refusée à 2 mois). À lancer chaque jour."""
from django.core.management.base import BaseCommand

from AidFi.services.afase_delais import envoyer_tous_les_rappels


class Command(BaseCommand):
    help = "Envoie les rappels de délais des AFASE (une seule fois chacun)."

    def handle(self, *args, **options):
        n = envoyer_tous_les_rappels()
        self.stdout.write(self.style.SUCCESS(f"{n} rappel(s) envoyé(s)."))
