from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from mds.models import MDS, HoraireMDS, UserMDSProfile, MDSReception
from django.utils import timezone
from datetime import time

User = get_user_model()

# ===========================================================
# DONNÉES PAR DÉFAUT POUR TES MDS
# ===========================================================

MDS_LIST = [
    {
        "code": "MDSTEST1",
        "nom": "MDS TEST 01",
        "adresse": "12 rue des Amandiers",
        "cp": "13110",
        "ville": "Port-de-Bouc",
        "tel": "0491450000",
        "email": "mds.portdebouc@example.com",
    },
    
]

# ===========================================================
# 1. CRÉATION MDS
# ===========================================================

def init_mds_structures():
    result = []

    for item in MDS_LIST:
        mds, created = MDS.objects.update_or_create(
            code_mds=item["code"],
            defaults={
                "nom": item["nom"],
                "adresse": item["adresse"],
                "code_postal": item["cp"],
                "ville": item["ville"],
                "telephone": item["tel"],
                "email": item["email"],
                "active": True,
                "date_ouverture": timezone.now().date(),
            }
        )
        result.append(f"{mds.code_mds} : {'CREATED' if created else 'UPDATED'}")

        # Création horaires (seulement si absent)
        if mds.horaires.count() == 0:
            for jour in range(5):
                HoraireMDS.objects.create(
                    mds=mds,
                    jour=jour,
                    heure_ouverture=time(9, 0),
                    heure_fermeture=time(17, 0),
                )

        # Création salle de réception par défaut
        if mds.salles_reception.count() == 0:
            MDSReception.objects.create(
                mds=mds,
                nom="Accueil principal",
                type_salle="ACCUEIL",
                capacite=3,
                horaire_debut=time(9, 0),
                horaire_fin=time(17, 0),
            )

    return "\n".join(result)


# ===========================================================
# FONCTION D’INITIALISATION PRINCIPALE
# ===========================================================

def init_mds():
    log = []
    log.append("📌 Création des structures MDS")
    log.append(init_mds_structures())
    return "\n".join(log)

# ===========================================================
# COMMANDE DJANGO
# ===========================================================

class Command(BaseCommand):
    help = "Initialise la MDS de test"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(init_mds()))
