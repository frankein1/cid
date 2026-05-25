from django.core.management.base import BaseCommand
from django.core.management import call_command
from core.models import Profil, Capacite


class Command(BaseCommand):
    help = "Initialise les profils métier (sans permissions Django, sans doublon)"

    def handle(self, *args, **options):
        self.stdout.write("🔧 Initialisation des profils métier...")

        # 1. S’assurer que les capacités existent
        call_command('init_capacites')

        # 2. S’assurer que AFASE est initialisé
        call_command('init_afase')

        # 3. Définition des profils (code, nom, capacités)
        PROFILS = [
            {
                "code": "MDS_ADMINISTRATIFS",
                "nom": "MDS Administratifs",
                "capacites": [
                    'peut_voir', 'peut_lister', 'peut_creer', 'peut_voir_stats'
                ]
            },
            {
                "code": "MDS_AGENTS_SOCIAUX",
                "nom": "Agents Sociaux MDS",
                "capacites": [
                    'peut_voir', 'peut_lister', 'peut_creer', 'peut_modifier',
                    'peut_instruire', 'ged_televerser', 'peut_gestion_aides_aidfi'
                ]
            },
            {
                "code": "MDS_CADRES",
                "nom": "Cadres MDS",
                "capacites": [
                    'peut_voir', 'peut_lister', 'peut_creer', 'peut_modifier',
                    'peut_instruire', 'peut_valider', 'peut_decider', 'peut_voir_stats',
                    'ged_televerser', 'ged_valider', 'ged_supprimer',
                    'planning_generer', 'planning_bloquer', 'planning_exporter',
                    'peut_gestion_aides_aidfi', 'peut_valider_cheque_aidfi'
                ]
            },
            {
                "code": "SUPER_ADMIN",
                "nom": "Super Administrateur",
                "capacites": "__all__"
            }
        ]

        for p in PROFILS:
            profil, created = Profil.objects.get_or_create(
                code=p["code"],
                defaults={"nom": p["nom"], "actif": True}
            )

            if not created:
                profil.nom = p["nom"]
                profil.actif = True
                profil.save()

            # Attribution des capacités
            if p["capacites"] == "__all__":
                profil.capacites.set(Capacite.objects.filter(actif=True))
            else:
                capacites = Capacite.objects.filter(code__in=p["capacites"], actif=True)
                profil.capacites.set(capacites)

            self.stdout.write(self.style.SUCCESS(f"✅ {profil.nom} ({len(profil.capacites.all())} capacités)"))

        self.stdout.write(self.style.SUCCESS("\n✅ Profils initialisés avec succès."))