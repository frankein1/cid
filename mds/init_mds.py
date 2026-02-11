# mds/init_mds.py -- Initialisation Render Safe

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
        "code": "MDS01",
        "nom": "MDS Port-de-Bouc",
        "adresse": "12 rue des Amandiers",
        "cp": "13110",
        "ville": "Port-de-Bouc",
        "tel": "0491450000",
        "email": "mds.portdebouc@example.com",
    },
    {
        "code": "MDS02",
        "nom": "MDS Fos-sur-Mer",
        "adresse": "8 avenue des Pins",
        "cp": "13270",
        "ville": "Fos-sur-Mer",
        "tel": "0491452000",
        "email": "mds.fos@example.com",
    },
    {
        "code": "MDS03",
        "nom": "MDS Martigues",
        "adresse": "20 quai Général Leclerc",
        "cp": "13500",
        "ville": "Martigues",
        "tel": "0491453000",
        "email": "mds.martigues@example.com",
    }
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
            for jour in range(5):   # lundi → vendredi
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
# 2. AGENTS (FAUX AGENTS DE DEMO)
# ===========================================================

FAUX_AGENTS = [
    ("agent1", "Agent Social", "MDS01", "Agents Sociaux MDS"),
    ("agent2", "Agent Social", "MDS02", "Agents Sociaux MDS"),
    ("admin_mds", "Administratif MDS", "MDS01", "MDS Administratifs"),
    ("cadre1", "Cadre MDS", "MDS03", "Cadres MDS"),
]

def init_mds_agents():
    result = []

    for username, role, code_mds, profil in FAUX_AGENTS:

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": f"{username}@example.com",
                "password": "pbkdf2_sha256$260000$fake$fake",
                "is_active": True,
                "matricule": username.upper()
            }
        )

        mds = MDS.objects.filter(code_mds=code_mds).first()
        if not mds:
            result.append(f"[ERR] MDS {code_mds} introuvable")
            continue

        UserMDSProfile.objects.update_or_create(
            user=user,
            mds=mds,
            defaults={
                "principale": True,
                "peut_gerer_utilisateurs": (role == "Cadre MDS"),
                "actif": True,
                "role_specifique": role,
            }
        )

        result.append(f"{username} → {code_mds} ({profil})")

    return "\n".join(result)


# ===========================================================
# APPEL PRINCIPAL (pour install.py)
# ===========================================================
def init_mds():
    log = []
    log.append("📌 Création des structures MDS")
    log.append(init_mds_structures())
    log.append("\n📌 Création des faux agents MDS")
    log.append(init_mds_agents())
    return "\n".join(log)
