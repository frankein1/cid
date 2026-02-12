# core/management/commands/install.py - VERSION RENDER SAFE

import os
import sys
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.apps import apps

class Command(BaseCommand):
    help = "Installation SI-DITAS - Version Render SÉCURISÉE"

    def add_arguments(self, parser):
        parser.add_argument(
            '--etape',
            type=str,
            default='',
            help='Étape spécifique : migrations | core | mds | planning | superuser'
        )

    def get_env(self, key, default=None):
        """Récupère les variables depuis l'environnement Render (pas de .env)"""
        value = os.environ.get(key, default)
        self.stdout.write(f"      🔧 {key} = {'***' if 'PASSWORD' in key else value}")
        return value

    def handle(self, *args, **options):

        etape = options.get("etape")

        self.stdout.write("\n🚀 INSTALLATION SI-DITAS / MODE RENDER SAFE")
        self.stdout.write("    ===========================================")

        admin_username = self.get_env('ADMIN_USERNAME', 'admin')
        admin_password = self.get_env('ADMIN_PASSWORD')
        admin_email = self.get_env('ADMIN_EMAIL', 'admin@example.com')

        if not admin_password:
            self.stdout.write(self.style.ERROR("❌ ADMIN_PASSWORD manquant"))
            return

        # ============================================================
        # ETAPE A : MIGRATIONS
        # ============================================================
        if etape in ("", "migrations"):
            self.stdout.write("\n📌 Étape : MIGRATIONS")
            try:
                call_command("migrate", interactive=False)
                self.stdout.write(self.style.SUCCESS("   ✅ Migrations appliquées"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Erreur migrations: {e}"))
                return

        # ============================================================
        # ETAPE B : CORE (permissions, capacités, profils…)
        # ============================================================
        if etape in ("", "core"):
            self.stdout.write("\n📌 Étape : INITIALISATION CORE")

            try:
                # Import tardif = évite les charges trop lourdes
                call_command("init_permissions_complet")

                try:
                    from AidFi.init_capacites import init_capacites
                    init_capacites()
                    self.stdout.write("   - Capacités OK")
                except:
                    pass

                try:
                    from core.init_profils import init_profils
                    init_profils()
                    self.stdout.write("   - Profils OK")
                except:
                    pass

                self.stdout.write(self.style.SUCCESS("   ✅ Initialisation CORE OK"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Erreur CORE: {e}"))
                return

        # ============================================================
        # ETAPE C : MDS
        # ============================================================
        if etape in ("", "mds"):
            self.stdout.write("\n📌 Étape : INITIALISATION MDS")
            try:
                from mds.init_mds import init_mds
                log = init_mds()
                self.stdout.write(log)
                self.stdout.write(self.style.SUCCESS("   ✅ MDS OK"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Erreur MDS: {e}"))
                return

        # ============================================================
        # ETAPE D : PLANNING
        # ============================================================
        if etape in ("", "planning"):
            self.stdout.write("\n📌 Étape : INITIALISATION PLANNING")

            try:
                from planning.init_planning_config import init_planning_config
                init_planning_config()
                self.stdout.write(self.style.SUCCESS("   ✅ Planning OK"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Erreur Planning: {e}"))
                return

        # ============================================================
        # ETAPE E : SUPERUSER
        # ============================================================
        if etape in ("", "superuser"):
            self.stdout.write("\n📌 Étape : CRÉATION SUPERUSER")

            from core.models import User

            try:
                if not User.objects.filter(username=admin_username).exists():
                    User.objects.create_superuser(
                        username=admin_username,
                        email=admin_email,
                        password=admin_password,
                        matricule="ADMIN_RENDER"
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f"   ✅ Superuser '{admin_username}' créé"
                    ))
                else:
                    self.stdout.write(f"   ℹ️ Superuser '{admin_username}' existe déjà")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Erreur Superuser: {e}"))
                return

        self.stdout.write(self.style.SUCCESS("\n🎉 INSTALLATION ÉTAPE TERMINÉE"))
