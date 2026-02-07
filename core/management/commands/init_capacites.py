from django.core.management.base import BaseCommand
from core.models.capacite import Capacite

CAPACITES = [
    # Lecture
    ('peut_voir', 'Voir'),
    ('peut_voir_stats', 'Voir statistiques'),
    ('peut_lister', 'Lister'),

    # CRUD
    ('peut_creer', 'Créer'),
    ('peut_modifier', 'Modifier'),
    ('peut_supprimer', 'Supprimer'),

    # Instruction / décision
    ('peut_instruire', 'Instruire'),
    ('peut_valider', 'Valider'),
    ('peut_decider', 'Décider'),
    ('peut_gerer_finance', 'Gérer finance'),
    ('peut_verser', 'Verser des aides'),

    # Administration
    ('peut_administrer', 'Administrer'),
    ('peut_configurer', 'Configurer'),
    ('peut_gerer_utilisateurs', 'Gérer les utilisateurs'),

    # GED
    ('ged_televerser', 'GED – Téléverser'),
    ('ged_valider', 'GED – Valider'),
    ('ged_supprimer', 'GED – Supprimer'),

    # Planning
    ('planning_generer', 'Planning – Générer'),
    ('planning_bloquer', 'Planning – Bloquer'),
    ('planning_exporter', 'Planning – Exporter'),
]

class Command(BaseCommand):
    help = "Initialise les capacités CORE"

    def handle(self, *args, **options):
        for code, nom in CAPACITES:
            cap, created = Capacite.objects.get_or_create(
                code=code,
                defaults={'nom': nom}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"✓ {code}"))
            else:
                self.stdout.write(f"• {code} existe déjà")
