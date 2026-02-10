# core/management/commands/install.py - VERSION RENDER

import sys
import os
import shutil
import importlib
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.apps import apps

class Command(BaseCommand):
    help = "Installation SI-DITAS - Version Render (variables d'environnement)"

    def get_env(self, key, default=None):
        """Récupère les variables depuis l'environnement Render (pas de .env)"""
        value = os.environ.get(key, default)
        self.stdout.write(f"      🔧 {key} = {'***' if 'PASSWORD' in key else value}")
        return value

    def handle(self, *args, **options):
        user_model_path = "core/models/user.py"

        self.stdout.write("\n🚀 INITIALISATION SI-DITAS SUR RENDER")
        self.stdout.write("    ===================================")

        # --- [1] RÉCUPÉRATION DES CONFIGURATIONS RENDER ---
        admin_username = self.get_env('ADMIN_USERNAME', 'admin')
        admin_password = self.get_env('ADMIN_PASSWORD')  # DOIT être défini sur Render!
        admin_email = self.get_env('ADMIN_EMAIL', 'admin@example.com')
        
        if not admin_password:
            self.stdout.write(self.style.ERROR("❌ ADMIN_PASSWORD non défini sur Render!"))
            self.stdout.write("   → Ajoutez ADMIN_PASSWORD dans: Render → Settings → Environment")
            return

        # --- [2] PRÉPARATION DES MODULES ---
        self.stdout.write("\n    📦 Préparation des applications...")
        
        for app_config in apps.get_app_configs():
            if not app_config.path.startswith(os.getcwd()):
                continue

            mig_dir = os.path.join(app_config.path, 'migrations')
            
            # Création du dossier migrations
            if not os.path.exists(mig_dir):
                os.makedirs(mig_dir)
                with open(os.path.join(mig_dir, '__init__.py'), 'w') as f: 
                    f.write('# Render init\n')
                self.stdout.write(f"      ✅ {app_config.label}")

            # Nettoyage des anciennes migrations
            for f in os.listdir(mig_dir):
                if f.startswith('00') and f.endswith('.py'):
                    os.remove(os.path.join(mig_dir, f))

            # Nettoyage des caches
            pycache = os.path.join(app_config.path, '__pycache__')
            if os.path.exists(pycache):
                shutil.rmtree(pycache)

        # --- [3] GESTION DU CYCLE CORE/MDS ---
        self.stdout.write("\n    🔄 Gestion des modèles...")
        
        try:
            with open(user_model_path, "r") as f:
                original_content = f.read()

            # Neutralisation temporaire
            neutralized = original_content.replace("mds_principale =", "mds_principale_HIDDEN =")
            with open(user_model_path, "w") as f:
                f.write(neutralized)

            # Rechargement
            if 'core.models.user' in sys.modules:
                importlib.reload(sys.modules['core.models.user'])

            # --- [4] MIGRATIONS ---
            self.stdout.write("    📝 Génération des migrations...")
            call_command("makemigrations", interactive=False)

            # Restauration
            with open(user_model_path, "w") as f:
                f.write(original_content)
            
            if 'core.models.user' in sys.modules:
                importlib.reload(sys.modules['core.models.user'])

            # Migration pour le champ mds_principale
            call_command("makemigrations", "core", interactive=False)

            # --- [5] APPLICATION À LA BASE DE DONNÉES ---
            self.stdout.write("    🗄️  Application à PostgreSQL (Alwaysdata)...")
            call_command("migrate", "core", "0001", interactive=False)
            call_command("migrate", interactive=False)

            self.stdout.write(self.style.SUCCESS("    ✅ Base synchronisée avec Alwaysdata"))

        except Exception as e:
            # Restauration en cas d'erreur
            if 'original_content' in locals():
                with open(user_model_path, "w") as f:
                    f.write(original_content)
            self.stdout.write(self.style.ERROR(f"    ❌ Erreur migration: {e}"))
            raise

        # --- [6] INITIALISATION DES DONNÉES ---
        self.stdout.write("\n    🎯 Initialisation des données...")
        
        try:
            from core.models import User
            from planning.init_planning_config import init_planning_config
            
            init_planning_config()
            call_command("init_permissions_complet")
            
            if not User.objects.filter(username=admin_username).exists():
                User.objects.create_superuser(
                    username=admin_username,
                    email=admin_email,
                    password=admin_password,
                    matricule="ADMIN_RENDER"
                )
                self.stdout.write(self.style.SUCCESS(f"    ✅ Admin '{admin_username}' créé"))
            else:
                self.stdout.write(f"    ℹ️  Admin '{admin_username}' existe déjà")
                
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"    ⚠️  Erreur initialisation: {e}"))

        self.stdout.write(self.style.SUCCESS("\n🎉 SI-DITAS OPÉRATIONNEL SUR RENDER"))
        self.stdout.write("   👉 Accédez à: https://cid-6yav.onrender.com")
        self.stdout.write("   🔐 Connectez-vous avec:", admin_username, "/", "******")
