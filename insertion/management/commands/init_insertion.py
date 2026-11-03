# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/management/commands/init_insertion.py
"""
Types d'actions d'insertion (typologie commune à toutes les MDS). Idempotent : crée les types manquants,
ne modifie jamais un type existant (libellé ou ordre ajustés en administration). Lancé par « install ».
"""
from django.core.management.base import BaseCommand

TYPES = [
    ("accompagnement-global", "Accompagnement global et socioprofessionnel"),
    ("projet-professionnel", "Construction du projet professionnel"),
    ("emploi", "Accès à l'emploi"),
    ("formation", "Formation et qualification"),
    ("savoirs-de-base", "Savoirs de base, français, illettrisme"),
    ("iae", "Insertion par l'activité économique (chantiers, SIAE)"),
    ("creation-activite", "Création ou reprise d'activité"),
    ("sante", "Santé, handicap, accès aux soins"),
    ("remobilisation", "Remobilisation sociale et lien social"),
    ("mobilite", "Mobilité"),
    ("garde-enfants", "Garde d'enfants"),
    ("logement", "Logement et cadre de vie"),
    ("budget-droits", "Budget et accès aux droits"),
    ("benevolat", "Bénévolat et citoyenneté"),
    ("savoir-etre", "Savoir-être, codes socioculturels, culture"),
    ("publics-specifiques", "Publics spécifiques (jeunes, seniors, femmes, gens du voyage, détention…)"),
]


class Command(BaseCommand):
    help = "Crée les types d'actions d'insertion manquants (module RSA – Insertion)"

    def handle(self, *args, **options):
        from insertion.models import TypeActionInsertion
        crees = 0
        for ordre, (code, libelle) in enumerate(TYPES, start=1):
            _, cree = TypeActionInsertion.objects.get_or_create(code=code, defaults={"libelle": libelle, "ordre": ordre * 10})
            crees += cree
        self.stdout.write(self.style.SUCCESS(f"✅ Types d'actions d'insertion : {crees} créé(s), "
                                             f"{TypeActionInsertion.objects.count()} au total"))
