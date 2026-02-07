# core/management/commands/install.py

import sys
import os
import shutil
import importlib
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.apps import apps
from decouple import Config, RepositoryEnv

class Command(BaseCommand):
    help = "Installation SI-DITAS - Version Industrielle (Registre Django)"

    def handle(self, *args, **options):
        env = Config(RepositoryEnv(".env"))
        user_model_path = "core/models/user.py"

        self.stdout.write("\n🚀 INITIALISATION INDUSTRIELLE SI-DITAS")

        # --- [1] PRÉPARATION DES MODULES VIA LE REGISTRE DJANGO ---
        self.stdout.write("    - Analyse des applications et nettoyage...")
        
        # On boucle sur toutes les apps installées
        for app_config in apps.get_app_configs():
            # On ne traite que tes apps locales (celles dans /srv/django/si-ditas/)
            if not app_config.path.startswith(os.getcwd()):
                continue

            # Chemin du dossier migrations de l'app
            mig_dir = os.path.join(app_config.path, 'migrations')
            
            # 1. Création forcée du package migrations s'il manque
            if not os.path.exists(mig_dir):
                os.makedirs(mig_dir)
                with open(os.path.join(mig_dir, '__init__.py'), 'w') as f: pass
                self.stdout.write(f"      📁 Packagé : {app_config.label}")

            # 2. Nettoyage des fichiers de migrations existants (00*.py)
            for f in os.listdir(mig_dir):
                if f.startswith('00'):
                    os.remove(os.path.join(mig_dir, f))

            # 3. Nettoyage des caches (important pour importlib.reload)
            pycache = os.path.join(app_config.path, '__pycache__')
            if os.path.exists(pycache):
                shutil.rmtree(pycache)

        # --- [2] GESTION DU CYCLE CORE/MDS ---
        with open(user_model_path, "r") as f:
            original_content = f.read()

        try:
            self.stdout.write("    - Neutralisation du cycle (mds_principale)...")
            neutralized = original_content.replace("mds_principale =", "mds_principale_HIDDEN =")
            with open(user_model_path, "w") as f:
                f.write(neutralized)

            # Rechargement forcé du modèle User modifié
            if 'core.models.user' in sys.modules:
                importlib.reload(sys.modules['core.models.user'])

            # --- [3] GÉNÉRATION DES MIGRATIONS ---
            self.stdout.write("    - Génération de l'état initial (Toutes apps)...")
            # Django va maintenant tout voir car les dossiers migrations/__init__.py existent partout
            call_command("makemigrations", interactive=False)

            # Restauration du champ original
            with open(user_model_path, "w") as f:
                f.write(original_content)
            
            if 'core.models.user' in sys.modules:
                importlib.reload(sys.modules['core.models.user'])

            # Création du pont mds_principale
            call_command("makemigrations", "core", interactive=False)

            # --- [4] APPLICATION DES SCHÉMAS ---
            self.stdout.write("    - Application PostgreSQL...")
            # On applique core 0001 (le User sans MDS)
            call_command("migrate", "core", "0001", interactive=False)
            # Puis on applique TOUT le reste (incluant planning, beneficiaire, etc.)
            call_command("migrate", interactive=False) 

            self.stdout.write(self.style.SUCCESS("✅ Base de données synchronisée."))

        except Exception as e:
            # En cas de crash, on remet toujours le fichier user.py au propre
            with open(user_model_path, "w") as f:
                f.write(original_content)
            raise e

        # --- [5] INITIALISATIONS MÉTIER ---
        self.stdout.write("    - Initialisations des données...")
        try:
            # On importe ici pour éviter des soucis de chargement au début du script
            from core.models import User
            from planning.init_planning_config import init_planning_config
            
            init_planning_config()
            call_command("init_permissions_complet")
            
            admin_user = env("ADMIN_USERNAME", default="admin")
            if not User.objects.filter(username=admin_user).exists():
                User.objects.create_superuser(
                    username=admin_user,
                    email=env("ADMIN_EMAIL", default="admin@example.com"),
                    password=env("ADMIN_PASSWORD"),
                    matricule="ADMIN_INIT"
                )
                self.stdout.write(self.style.SUCCESS(f"✅ Admin '{admin_user}' créé"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erreur Init : {e}"))

        self.stdout.write(self.style.SUCCESS("\n🎉 SI-DITAS EST OPÉRATIONNEL"))
