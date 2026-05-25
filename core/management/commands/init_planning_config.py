# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# planning/init_planning_config.py
from django.core.management.base import BaseCommand
from planning.models import ConfigurationPlanning


def init_planning_config():
    """Fonction d'initialisation de la configuration du planning"""
    configs = [
        {
            'cle': 'DUREE_CRENEAU_MINUTES',
            'valeur': '30',
            'type_valeur': 'INTEGER',
            'description': 'Durée par défaut des créneaux en minutes'
        },
        {
            'cle': 'HEURE_DEBUT_MATIN',
            'valeur': '09:00',
            'type_valeur': 'TIME',
            'description': 'Heure de début des créneaux du matin'
        },
        {
            'cle': 'HEURE_FIN_MATIN',
            'valeur': '12:00',
            'type_valeur': 'TIME',
            'description': 'Heure de fin des créneaux du matin'
        },
        {
            'cle': 'HEURE_DEBUT_APRESMIDI',
            'valeur': '13:30',
            'type_valeur': 'TIME',
            'description': 'Heure de début des créneaux de l\'après-midi'
        },
        {
            'cle': 'HEURE_FIN_APRESMIDI',
            'valeur': '17:00',
            'type_valeur': 'TIME',
            'description': 'Heure de fin des créneaux de l\'après-midi'
        },
        {
            'cle': 'JOURS_GENERATION_AUTO',
            'valeur': '5',
            'type_valeur': 'INTEGER',
            'description': 'Nombre de jours ouvrés à générer automatiquement'
        },
        {
            'cle': 'ACTIVER_RAPPELS_EMAIL',
            'valeur': 'true',
            'type_valeur': 'BOOLEAN',
            'description': 'Activer les rappels par email pour les RDV'
        },
        {
            'cle': 'DELAI_RAPPEL_HEURES',
            'valeur': '24',
            'type_valeur': 'INTEGER',
            'description': 'Délai de rappel en heures avant le RDV'
        },
    ]
    
    for config_data in configs:
        config, created = ConfigurationPlanning.objects.get_or_create(
            cle=config_data['cle'],
            defaults={
                'valeur': config_data['valeur'],
                'type_valeur': config_data['type_valeur'],
                'description': config_data['description']
            }
        )
        
        if created:
            print(f"✓ Configuration créée : {config.cle}")
        else:
            print(f"⚠ Configuration existante : {config.cle}")
    
    print('\n✅ Configuration du planning initialisée avec succès !')
    return True


# Pour pouvoir l'appeler comme une commande management quand même
class Command(BaseCommand):
    help = 'Initialise la configuration du module planning'
    
    def handle(self, *args, **options):
        init_planning_config()
