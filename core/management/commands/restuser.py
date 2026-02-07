# core/management/commands/restore_user_profils.py
import json
from django.core.management.base import BaseCommand
from core.models import User, Profil

class Command(BaseCommand):
    help = "Restaure les associations User ↔ Profil après install"

    def handle(self, *args, **options):
        try:
            with open('user_profils_backup.json', 'r') as f:
                backup = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR("❌ Fichier user_profils_backup.json introuvable"))
            return
        
        restored = 0
        errors = []
        
        for username, profils_codes in backup.items():
            try:
                user = User.objects.get(username=username)
                user.profils.clear()
                
                for code in profils_codes:
                    try:
                        profil = Profil.objects.get(code=code)
                        user.profils.add(profil)
                    except Profil.DoesNotExist:
                        errors.append(f"Profil {code} introuvable pour {username}")
                
                restored += 1
                self.stdout.write(f"✓ {username}")
            
            except User.DoesNotExist:
                errors.append(f"Utilisateur {username} introuvable")
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ {restored} utilisateurs restaurés"))
        
        if errors:
            self.stdout.write(self.style.WARNING(f"\n⚠️  {len(errors)} erreurs :"))
            for err in errors:
                self.stdout.write(f"  - {err}")
