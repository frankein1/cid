# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/management/commands/importer_pages_envois.py
"""Importe le minimum de pages par type de dossier depuis un CSV (séparateur « ; »). Même logique que l'écran
d'import de l'admin (logement.services.envoi.importer_regles)."""
from django.core.management.base import BaseCommand, CommandError

from logement.services.envoi import importer_regles


class Command(BaseCommand):
    help = "Importe le minimum de pages par type de dossier depuis un fichier CSV."

    def add_arguments(self, parser):
        parser.add_argument('fichier', help="Chemin du fichier CSV (séparateur « ; »)")

    def handle(self, *args, **options):
        try:
            with open(options['fichier'], encoding='utf-8-sig', newline='') as f:
                texte = f.read()
        except OSError as e:
            raise CommandError(f"Fichier illisible : {e}")
        try:
            crees, maj = importer_regles(texte)
        except ValueError as e:
            raise CommandError(str(e))
        self.stdout.write(f"{crees} type(s) créé(s), {maj} mis à jour.")
