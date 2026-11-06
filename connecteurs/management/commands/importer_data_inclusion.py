# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/management/commands/importer_data_inclusion.py
"""Met à jour l'offre d'insertion du territoire depuis les fichiers ouverts data·inclusion (à planifier chaque mardi :
les fichiers sont republiés le lundi).

    python manage.py importer_data_inclusion              # départements de DATA_INCLUSION_DEPARTEMENTS (13)
    python manage.py importer_data_inclusion --departements 13,84
"""
from django.core.management.base import BaseCommand, CommandError

from connecteurs.data_inclusion import departements, importer


class Command(BaseCommand):
    help = "Importe les services d'insertion du territoire depuis data·inclusion (fichiers ouverts)."

    def add_arguments(self, parser):
        parser.add_argument("--departements", default="")

    def handle(self, *args, **opts):
        deps = [d.strip() for d in opts["departements"].split(",") if d.strip()] or departements()
        t = importer(deps)
        if t.erreur:
            raise CommandError(t.erreur)
        self.stdout.write(self.style.SUCCESS(
            f"{t.structures} structures, {t.services} services importés, {t.retires} retirés ({', '.join(deps)})."))
