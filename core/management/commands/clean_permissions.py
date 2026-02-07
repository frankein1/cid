# core/management/commands/clean_permissions.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.db import transaction
from core.models import Profil, User


class Command(BaseCommand):
    help = "Nettoie complètement les groupes, profils et associations utilisateurs"

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirmer la suppression (sinon mode dry-run)',
        )

    def handle(self, *args, **options):
        confirm = options['confirm']
        
        if not confirm:
            self.stdout.write(self.style.WARNING(
                "⚠️  MODE DRY-RUN - Aucune modification ne sera effectuée"
            ))
            self.stdout.write(self.style.WARNING(
                "   Utilisez --confirm pour effectuer réellement les suppressions\n"
            ))
        
        # Compter ce qui va être supprimé
        nb_groupes = Group.objects.count()
        nb_profils = Profil.objects.count()
        nb_users_avec_profils = User.objects.filter(profils__isnull=False).distinct().count()
        nb_users_avec_groupes = User.objects.filter(groups__isnull=False).distinct().count()
        
        self.stdout.write("📊 État actuel de la base :")
        self.stdout.write(f"   - Groupes Django : {nb_groupes}")
        self.stdout.write(f"   - Profils métier : {nb_profils}")
        self.stdout.write(f"   - Utilisateurs avec profils : {nb_users_avec_profils}")
        self.stdout.write(f"   - Utilisateurs avec groupes : {nb_users_avec_groupes}")
        self.stdout.write("")
        
        if not confirm:
            self.stdout.write(self.style.WARNING(
                "👆 Pour effectuer le nettoyage, relancez avec : "
                "python manage.py clean_permissions --confirm"
            ))
            return
        
        # Confirmation interactive supplémentaire
        self.stdout.write(self.style.WARNING(
            "\n⚠️  ATTENTION : Cette opération va supprimer TOUTES les données suivantes :"
        ))
        self.stdout.write(f"   • {nb_groupes} groupe(s) Django")
        self.stdout.write(f"   • {nb_profils} profil(s) métier")
        self.stdout.write(f"   • Toutes les associations utilisateurs ↔ profils")
        self.stdout.write(f"   • Toutes les associations utilisateurs ↔ groupes")
        self.stdout.write("")
        
        reponse = input("Êtes-vous sûr de vouloir continuer ? (tapez 'OUI' en majuscules) : ")
        
        if reponse != "OUI":
            self.stdout.write(self.style.ERROR("❌ Opération annulée"))
            return
        
        self.stdout.write(self.style.SUCCESS("\n🧹 Nettoyage en cours...\n"))
        
        with transaction.atomic():
            # 1. Retirer tous les profils des utilisateurs
            self.stdout.write("   1. Suppression des associations User ↔ Profil...")
            for user in User.objects.all():
                user.profils.clear()
            self.stdout.write(self.style.SUCCESS(f"      ✓ {nb_users_avec_profils} utilisateurs traités"))
            
            # 2. Retirer tous les groupes des utilisateurs
            self.stdout.write("   2. Suppression des associations User ↔ Group...")
            for user in User.objects.all():
                user.groups.clear()
            self.stdout.write(self.style.SUCCESS(f"      ✓ {nb_users_avec_groupes} utilisateurs traités"))
            
            # 3. Supprimer tous les profils
            self.stdout.write("   3. Suppression des Profils métier...")
            Profil.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f"      ✓ {nb_profils} profils supprimés"))
            
            # 4. Supprimer tous les groupes
            self.stdout.write("   4. Suppression des Groupes Django...")
            Group.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f"      ✓ {nb_groupes} groupes supprimés"))
        
        self.stdout.write(self.style.SUCCESS("\n✅ Nettoyage terminé avec succès !"))
        self.stdout.write("")
        self.stdout.write("📌 Prochaine étape : python manage.py install --force")
