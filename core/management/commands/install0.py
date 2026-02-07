# core/management/commands/install.py
import sys
import subprocess
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction
from core.models import User
from planning.init_planning_config import init_planning_config

class Command(BaseCommand):
    help = "Installation complète : Dépendances, Base de données, Profils, Admin + AFASE."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Nettoyage complet avant installation.")
        parser.add_argument("--skip-deps", action="store_true", help="Sauter l'installation des dépendances.")

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("      🚀 SI-DITAS : INSTALLATION AUTOMATISÉE      "))
        self.stdout.write(self.style.SUCCESS("=" * 60))

        if not options["skip_deps"]:
            self.stdout.write("\n[1/7] Installation des dépendances...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

        if options["force"]:
            self.stdout.write("\n[2/7] Nettoyage de la base...")
            call_command("clean_permissions", confirm=True)

        # BASE + CONFIG + PERMISSIONS + AFASE (ATOMIQUE)
        with transaction.atomic():
            self.stdout.write("\n[3/7] Migration de la base de données...")
            call_command("migrate", interactive=False)

            self.stdout.write("🔧 Initialisation du planning...")
            init_planning_config()
            self.stdout.write(self.style.SUCCESS("  ✓ Configuration planning OK"))

            self.stdout.write("\n[4/7] Profils métiers et permissions...")
            call_command("init_permissions_complet")

            # ✅ AJOUT AFASE
            self.stdout.write("\n[5/7] Initialisation AFASE...")
            try:
                call_command("init_afase")
                self.stdout.write(self.style.SUCCESS("  ✓ AFASE initialisée"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  → AFASE ignorée: {e}"))

        # ADMIN
        self.stdout.write("\n[6/7] Création du compte administrateur...")
        from decouple import config
        from getpass import getpass

        admin_user = config("ADMIN_USERNAME", default=None)
        admin_pass = config("ADMIN_PASSWORD", default=None)
        admin_mail = config("ADMIN_EMAIL", default="admin@cd13.fr")

        if not admin_user:
            admin_user = input("Nom d'utilisateur admin (ou vide pour 'Admin') : ") or "Admin"

        if not admin_pass:
            admin_pass = getpass("Mot de passe admin (obligatoire) : ")
            if not admin_pass:
                self.stdout.write(self.style.ERROR("❌ Installation interrompue"))
                return

        if not User.objects.filter(username=admin_user).exists():
            User.objects.create_superuser(
                username=admin_user,
                email=admin_mail,
                password=admin_pass,
                matricule=f"ADMIN_{admin_user.upper()}"
            )
            self.stdout.write(self.style.SUCCESS(f"  ✓ Admin '{admin_user}' créé."))
        else:
            self.stdout.write(self.style.WARNING(f"  → L'utilisateur '{admin_user}' existe déjà."))

        self.stdout.write(self.style.SUCCESS("\n🎉 INSTALLATION TERMINÉE AVEC SUCCÈS"))

