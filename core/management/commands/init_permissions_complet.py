# core/management/commands/init_permissions_complet.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from core.models import Profil, Capacite
from core.models.configuration import Configuration

# Imports des modèles pour les ContentTypes
from AidFi.models.m_afase import DemandeAFASE, DecisionAFASE
from beneficiaire.models import Beneficiaire
from ged.models import DocumentGED
from mds.models import MDS
from planning.models import CreneauRdv

# Modèles supplémentaires AidFi
try:
    from AidFi.models import (
        TypeAide, PieceJustificative, CAPCheque, RegieUrgence, PieceObligatoire
    )
    AIDFI_INSTALLED = True
except ImportError:
    AIDFI_INSTALLED = False


class Command(BaseCommand):
    help = "Initialise la matrice globale : Capacités CORE + Permissions Django"

    def get_perms(self, model_class, actions):
        """Récupère les permissions standards (view, add, change, delete)."""
        ct = ContentType.objects.get_for_model(model_class)
        return Permission.objects.filter(
            content_type=ct,
            codename__in=[f"{a}_{model_class._meta.model_name}" for a in actions]
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("  🔐 INITIALISATION DE LA MATRICE DE SÉCURITÉ GLOBALE"))
        self.stdout.write(self.style.SUCCESS("=" * 70))

        # ========================================
        # ÉTAPE 1 : Créer les capacités CORE (incluant AidFi maintenant)
        # ========================================
        self.stdout.write("\n[1/3] 📋 Création des capacités métier...")
        # C'est ici que la fusion se fait : init_capacites.py contient maintenant tout
        call_command('init_capacites')

        # ========================================
        # ÉTAPE 2 : Configuration des profils
        # ========================================
        self.stdout.write("\n[2/3] 👥 Configuration des profils...")

        # MATRICE DE CONFIGURATION
        profils_config = {
            "MDS_ADMINISTRATIFS": {
                "nom": "MDS Administratifs",
                "description": "Secrétariat : Accueil, création de dossiers et rendez-vous",
                "capacites": [
                    'peut_voir',
                    'peut_lister',
                    'peut_creer',
                    'peut_voir_stats',
                ],
                "perms": {
                    Beneficiaire: ["view", "add", "change"],
                    MDS: ["view"],
                    CreneauRdv: ["view", "add", "change", "delete"],
                    DocumentGED: ["view", "add"],
                },
                "additional_models": {
                    TypeAide: ["view"] if AIDFI_INSTALLED else None,
                    PieceJustificative: ["view"] if AIDFI_INSTALLED else None,
                    CAPCheque: ["view"] if AIDFI_INSTALLED else None,
                    RegieUrgence: ["view"] if AIDFI_INSTALLED else None,
                    PieceObligatoire: ["view"] if AIDFI_INSTALLED else None,
                },
            },

            "MDS_AGENTS_SOCIAUX": {
                "nom": "Agents Sociaux MDS",
                "description": "Travailleurs Sociaux : AFASE + Instruction dossiers",
                "capacites": [
                    'peut_voir',
                    'peut_lister',
                    'peut_creer',
                    'peut_modifier',
                    'peut_instruire',
                    'ged_televerser',
                    # Ajout possible de capacités AidFi spécifiques si besoin
                    'peut_gestion_aides_aidfi', 
                ],
                "perms": {
                    Beneficiaire: ["view", "add", "change"],
                    MDS: ["view"],
                    CreneauRdv: ["view", "add", "change", "delete"],
                    DocumentGED: ["view", "add", "change"],
                    DemandeAFASE: ["view", "add", "change"],
                },
                "additional_models": {
                    TypeAide: ["view", "add", "change"] if AIDFI_INSTALLED else None,
                    PieceJustificative: ["view", "add", "change"] if AIDFI_INSTALLED else None,
                    CAPCheque: ["view", "add", "change"] if AIDFI_INSTALLED else None,
                    RegieUrgence: ["view", "add", "change"] if AIDFI_INSTALLED else None,
                    PieceObligatoire: ["view", "add", "change"] if AIDFI_INSTALLED else None,
                },
            },

            "MDS_CADRES": {
                "nom": "Cadres MDS",
                "description": "Cadres : Décision AFASE + Gestion complète",
                "capacites": [
                    'peut_voir',
                    'peut_lister',
                    'peut_creer',
                    'peut_modifier',
                    'peut_instruire',
                    'peut_valider',
                    'peut_decider',
                    'peut_voir_stats',
                    'ged_televerser',
                    'ged_valider',
                    'ged_supprimer',
                    'planning_generer',
                    'planning_bloquer',
                    'planning_exporter',
                    'peut_gestion_aides_aidfi',
                    'peut_valider_cheque_aidfi',
                ],
                "perms": {
                    Beneficiaire: ["view", "add", "change", "delete"],
                    MDS: ["view", "change"],
                    CreneauRdv: ["view", "add", "change", "delete"],
                    DocumentGED: ["view", "add", "change", "delete"],
                    DemandeAFASE: ["view", "add", "change", "delete"],
                    DecisionAFASE: ["add", "change", "delete"],
                },
                "additional_models": {
                    TypeAide: ["view", "add", "change", "delete"] if AIDFI_INSTALLED else None,
                    PieceJustificative: ["view", "add", "change", "delete"] if AIDFI_INSTALLED else None,
                    CAPCheque: ["view", "add", "change", "delete"] if AIDFI_INSTALLED else None,
                    RegieUrgence: ["view", "add", "change", "delete"] if AIDFI_INSTALLED else None,
                    PieceObligatoire: ["view", "add", "change", "delete"] if AIDFI_INSTALLED else None,
                },
            },

            "SUPER_ADMIN": {
                "nom": "Super Administrateur",
                "description": "Administration totale du système",
                "capacites": [
                    'peut_voir',
                    'peut_lister',
                    'peut_creer',
                    'peut_modifier',
                    'peut_supprimer',
                    'peut_instruire',
                    'peut_valider',
                    'peut_decider',
                    'peut_administrer',
                    'peut_configurer',
                    'peut_gerer_utilisateurs',
                    'peut_voir_stats',
                    'ged_televerser',
                    'ged_valider',
                    'ged_supprimer',
                    'planning_generer',
                    'planning_bloquer',
                    'planning_exporter',
                    'peut_gestion_aides_aidfi',
                    'peut_valider_cheque_aidfi',
                ],
                "all_perms": True,
                "additional_models": {},
            }
        }

        # Application de la configuration
        for code_profil, config in profils_config.items():
            self.stdout.write(f"\n  🔧 Configuration de {config['nom']}...")

            # 1. Créer/Mettre à jour le Profil
            profil, created = Profil.objects.update_or_create(
                code=code_profil,
                defaults={
                    "nom": config["nom"],
                    "description": config["description"],
                    "actif": True,
                }
            )

            status = self.style.SUCCESS("✅ CRÉÉ") if created else self.style.WARNING("📝 MAJ")
            self.stdout.write(f"     {status}")

            # 2. Attribuer les capacités CORE
            capacites_codes = config.get("capacites", [])
            if capacites_codes:
                capacites = Capacite.objects.filter(code__in=capacites_codes, actif=True)
                profil.capacites.clear()
                profil.capacites.add(*capacites)
                self.stdout.write(f"     → {capacites.count()} capacités métier")

                # Afficher les capacités manquantes
                capacites_trouvees = set(capacites.values_list('code', flat=True))
                capacites_manquantes = set(capacites_codes) - capacites_trouvees
                if capacites_manquantes:
                    self.stdout.write(
                        self.style.WARNING(
                            f"     ⚠️  Capacités manquantes : {', '.join(capacites_manquantes)}"
                        )
                    )

            # 3. Créer/Mettre à jour le Groupe Django
            groupe, _ = Group.objects.get_or_create(name=code_profil)
            groupe.permissions.clear()

            # 4. Attribuer les permissions Django
            if config.get("all_perms"):
                total_perms = Permission.objects.count()
                groupe.permissions.add(*Permission.objects.all())
                self.stdout.write(f"     → {total_perms} permissions Django (TOUTES)")
            else:
                total_perms = 0
                for model, actions in config.get("perms", {}).items():
                    perms = self.get_perms(model, actions)
                    groupe.permissions.add(*perms)
                    total_perms += perms.count()
                
                # Permissions sur modèles supplémentaires (AidFi)
                for model_class, actions in config.get("additional_models", {}).items():
                    if model_class and actions:  # Skip None values
                        perms = self.get_perms(model_class, actions)
                        groupe.permissions.add(*perms)
                        total_perms += perms.count()
                
                self.stdout.write(f"     → {total_perms} permissions Django")

            # 5. Lier le profil au groupe
            profil.groupes.clear()
            profil.groupes.add(groupe)
            self.stdout.write(f"     → Profil lié au groupe Django")

        # ========================================
        # ÉTAPE 3 : Initialisation AFASE
        # ========================================
        self.stdout.write("\n[3/3] 💰 Initialisation AFASE...")
        try:
            call_command('init_afase')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  → AFASE ignorée : {e}"))

        # ========================================
        # RÉSUMÉ FINAL
        # ========================================
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 70))
        self.stdout.write(self.style.SUCCESS("  ✅ INITIALISATION TERMINÉE"))
        self.stdout.write(self.style.SUCCESS("=" * 70))

        self.stdout.write("\n📊 RÉSUMÉ :")
        self.stdout.write(f"  • Capacités métier actives : {Capacite.objects.filter(actif=True).count()}")
        self.stdout.write(f"  • Profils configurés : {Profil.objects.filter(actif=True).count()}")
        self.stdout.write(f"  • Groupes Django : {Group.objects.count()}")
        self.stdout.write(f"  • Permissions Django totales : {Permission.objects.count()}")

        # Détail par profil
        self.stdout.write("\n📋 DÉTAIL PAR PROFIL :")
        for profil in Profil.objects.filter(actif=True).order_by('code'):
            nb_caps = profil.capacites.count()
            nb_perms = profil.groupes.first().permissions.count() if profil.groupes.exists() else 0
            self.stdout.write(f"  • {profil.nom}")
            self.stdout.write(f"    - {nb_caps} capacités métier")
            self.stdout.write(f"    - {nb_perms} permissions Django")
