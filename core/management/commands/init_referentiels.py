# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/management/commands/init_referentiels.py
"""
Référentiels de base remplis par des migrations : types de danger des IP, motifs d'accord et de refus des AFASE.
Une migration ne repasse jamais : si la base a été vidée (flush, remise à zéro, nouvelle base avec les tables déjà
créées), ces listes restaient vides, et le jeu de démonstration échouait (« Précisez le ou les types de danger »).
Lancée par « install » à chaque démarrage : ne crée que les lignes manquantes, ne modifie jamais l'existant.
"""
import importlib

from django.apps import apps
from django.core.management.base import BaseCommand

REMPLISSAGES = [
    ("protection_enfance.migrations.0003_dangers_et_adultes_existants", "types_danger", "protection_enfance.TypeDanger"),
    ("AidFi.migrations.0014_referentiel_aide_decision", "motifs", "AidFi.ReferentielMotifAFASE"),
    ("AidFi.migrations.0015_delais_notifications", "motifs_refus", "AidFi.MotifRefusAFASE"),
]


class Command(BaseCommand):
    help = "Complète les référentiels de base (types de danger, motifs AFASE) s'ils ont été vidés"

    def handle(self, *args, **options):
        for module, fonction, modele in REMPLISSAGES:
            m = apps.get_model(modele)
            avant = m.objects.count()
            getattr(importlib.import_module(module), fonction)(apps, None)
            self.stdout.write(f"✅ {m._meta.verbose_name_plural} : {m.objects.count() - avant} ajouté(s), "
                              f"{m.objects.count()} au total")
