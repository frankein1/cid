import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from core.models import User


class Command(BaseCommand):
    help = "Installation complète SI-DITAS (migrations, profils, MDS, planning, documents)"

    def handle(self, *args, **options):
        self.stdout.write("\n🚀 INSTALLATION SI-DITAS")
        self.stdout.write("=" * 40)

        # 1. Migrations
        self.stdout.write("\n📦 Migrations...")
        call_command('migrate', interactive=False)

        # 2. Profils + capacités + AFASE
        self.stdout.write("\n🔐 Profils et capacités...")
        call_command('init_profils')

        # 3. MDS par défaut
        self.stdout.write("\n🏢 MDS par défaut...")
        call_command('init_mds')

        # 4. Configuration planning
        self.stdout.write("\n📅 Configuration planning...")
        call_command('init_planning_config')

        # 5. Types de documents GED
        self.stdout.write("\n📄 Types de documents...")
        call_command('seed_document_types')

        # 6. Superuser (si ADMIN_PASSWORD défini)
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD')
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')

        if admin_password:
            self.stdout.write("\n👤 Superuser...")
            if not User.objects.filter(username=admin_username).exists():
                User.objects.create_superuser(
                    username=admin_username,
                    password=admin_password,
                    email=admin_email,
                    matricule="ADMIN_RENDER"
                )
                self.stdout.write(self.style.SUCCESS(f"   ✅ Superuser '{admin_username}' créé"))
            else:
                self.stdout.write(f"   ℹ️ Superuser '{admin_username}' existe déjà")

        self.stdout.write(self.style.SUCCESS("\n🎉 Installation terminée."))