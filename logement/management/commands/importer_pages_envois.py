# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/management/commands/importer_pages_envois.py
"""Importe le minimum de pages par type de dossier (CSV, séparateur « ; ») : code ; libellé ; pages_dossier ;
pages_pieces_jointes. Une ligne existante est mise à jour, une nouvelle est créée. Les lignes absentes ne sont pas
supprimées. Chaque structure peut adapter le fichier à ses propres pages et le réimporter."""
import csv

from django.core.management.base import BaseCommand, CommandError

from logement.models import ReglePagesEnvoi

COLONNES = ('code', 'libelle', 'pages_dossier', 'pages_pieces_jointes')


class Command(BaseCommand):
    help = "Importe le minimum de pages par type de dossier depuis un fichier CSV."

    def add_arguments(self, parser):
        parser.add_argument('fichier', help="Chemin du fichier CSV (séparateur « ; »)")

    def handle(self, *args, **options):
        try:
            with open(options['fichier'], encoding='utf-8-sig', newline='') as f:
                lignes = list(csv.DictReader(f, delimiter=';'))
        except OSError as e:
            raise CommandError(f"Fichier illisible : {e}")
        if not lignes or any(c not in (lignes[0].keys()) for c in COLONNES):
            raise CommandError("En-tête attendu : " + ";".join(COLONNES))
        crees = maj = 0
        for n, ligne in enumerate(lignes, start=2):
            try:
                code = ligne['code'].strip().upper()
                pages = (int(ligne['pages_dossier']), int(ligne['pages_pieces_jointes']))
                if not code or min(pages) < 0:
                    raise ValueError
            except (ValueError, TypeError, AttributeError):
                raise CommandError(f"Ligne {n} invalide : code vide ou pages non entières positives.")
            _, cree = ReglePagesEnvoi.objects.update_or_create(code=code, defaults={
                'libelle': ligne['libelle'].strip(), 'pages_dossier': pages[0], 'pages_pieces_jointes': pages[1]})
            crees, maj = crees + cree, maj + (not cree)
        self.stdout.write(f"{crees} type(s) créé(s), {maj} mis à jour.")
