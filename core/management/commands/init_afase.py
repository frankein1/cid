# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# core/management/commands/init_afase.py
from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from AidFi.models.m_afase import DemandeAFASE

class Command(BaseCommand):
    help = "Initialise AFASE : ContentTypes + permissions spécifiques"

    def handle(self, *args, **options):
        self.stdout.write("🚀 Initialisation AFASE...")

        # 1. Créer ContentTypes pour AFASE
        ct_demande = ContentType.objects.get_for_model(DemandeAFASE)
        self.stdout.write(self.style.SUCCESS(f"  ✓ ContentType DemandeAFASE: {ct_demande}"))

        # 2. Permissions par défaut déjà créées par Django
        perms = ContentType.objects.get_for_model(DemandeAFASE).permission_set.all()
        self.stdout.write(self.style.SUCCESS(f"  ✓ {perms.count()} permissions AFASE prêtes"))

        self.stdout.write(self.style.SUCCESS("✅ AFASE prête pour les profils !"))
