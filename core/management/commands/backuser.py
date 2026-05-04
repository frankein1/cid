# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# core/management/commands/backup_user_profils.py
import json
from django.core.management.base import BaseCommand
from core.models import User

class Command(BaseCommand):
    help = "Sauvegarde les associations User ↔ Profil avant clean"

    def handle(self, *args, **options):
        backup = {}
        
        for user in User.objects.all():
            profils = list(user.profils.values_list('code', flat=True))
            if profils:
                backup[user.username] = profils
        
        with open('user_profils_backup.json', 'w') as f:
            json.dump(backup, f, indent=2)
        
        self.stdout.write(self.style.SUCCESS(
            f"✅ {len(backup)} utilisateurs sauvegardés dans user_profils_backup.json"
        ))
