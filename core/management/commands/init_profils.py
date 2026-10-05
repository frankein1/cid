# 📁 Emplacement : core/management/commands/init_profils.py
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
        CAPACITES_CADRE = [
            'peut_voir', 'peut_lister', 'peut_creer', 'peut_modifier',
            'peut_instruire', 'peut_valider', 'peut_decider', 'peut_voir_stats',
            'ged_televerser', 'ged_valider', 'ged_supprimer',
            'planning_generer', 'planning_bloquer', 'planning_exporter',
            'peut_gestion_aides_aidfi', 'peut_valider_cheque_aidfi',
            'peut_consulter_tous_usagers',
        ]

        PROFILS = [
            {
                "code": "MDS_ADMINISTRATIFS",
                "nom": "MDS Administratifs",
                "capacites": [
                    'peut_voir', 'peut_lister', 'peut_creer', 'peut_voir_stats',
                    'peut_consulter_tous_usagers',
                ]
            },
            {
                "code": "MDS_AGENTS_SOCIAUX",
                "nom": "Agents Sociaux MDS",
                "capacites": [
                    'peut_voir', 'peut_lister', 'peut_creer', 'peut_modifier',
                    'peut_instruire', 'ged_televerser', 'peut_gestion_aides_aidfi',
                    'peut_consulter_tous_usagers',
                ]
            },
            {
                "code": "MDS_CADRES",
                "nom": "Cadres MDS",
                "capacites": CAPACITES_CADRE
            },

            # ---------------- ENCADREMENT MDS (droits de cadre) ----------------
            {"code": "MDS_RESPONSABLE", "nom": "Responsable de MDS", "capacites": CAPACITES_CADRE},
            {"code": "MDS_ADJOINT_RESPONSABLE", "nom": "Adjoint au responsable de MDS", "capacites": CAPACITES_CADRE},
            {"code": "MDS_DIRECTION_TERRITOIRE", "nom": "Direction de MDS de territoire", "capacites": CAPACITES_CADRE},
            {"code": "MDS_ADJOINT_PREVENTION", "nom": "Adjoint prévention sociale", "capacites": CAPACITES_CADRE},
            {"code": "MDS_ADJOINT_ENFANCE_FAMILLE", "nom": "Adjoint enfance famille", "capacites": CAPACITES_CADRE},

            # ---------------- MDS DE TERRITOIRE : droits à définir ----------------
            {"code": "MDS_MEDECIN_REFERENT", "nom": "Médecin référent", "capacites": []},
            {"code": "MDS_SECRETARIAT_GENERAL", "nom": "Secrétariat général", "capacites": []},

            # ---------------- DIRECTIONS (DEF, DITAS, PMI...) : droits à définir ----------------
            {"code": "DIR_DIRECTION", "nom": "Direction (directions centrales)", "capacites": []},
            {"code": "DIR_CADRE", "nom": "Cadre de direction", "capacites": []},
            {"code": "DIR_SECRETARIAT", "nom": "Secrétariat de direction", "capacites": []},

            # ---------------- DGA SOLIDARITÉS : droits à définir ----------------
            {"code": "DGA_DIRECTION", "nom": "Direction générale adjointe", "capacites": []},
            {"code": "DGA_ADJOINT", "nom": "Adjoint DGA", "capacites": []},
            {"code": "DGA_CHARGE_MISSION", "nom": "Chargé de mission DGA", "capacites": []},
            {"code": "DGA_SECRETARIAT", "nom": "Secrétariat DGA", "capacites": []},

            # ---------------- ADMINISTRATION DES COMPTES (sans accès aux dossiers) ----------------
            {"code": "GESTIONNAIRE_ACCES", "nom": "Gestionnaire des accès", "capacites": ['peut_gerer_acces']},

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