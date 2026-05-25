# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

#!/usr/bin/env python
"""
Script de démarrage pour Render - VERSION AVEC MIGRATIONS GLOBALES
"""
import os
import sys
import django

print("🔧 [Render] Démarrage...")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cid.settings")

try:
    django.setup()
    print("✅ Django setup OK")
except Exception as e:
    print(f"❌ Django setup FAILED: {e}")
    sys.exit(1)

# --- Étape 0 : Installation unique ---
print("🔧 [Render] Exécution de l'installation...")
from django.core.management import call_command
call_command('install', interactive=False)


# --- Étape 1 : Migrations automatiques (TOUTES les apps) ---
print("📦 Étape 1: Création et application des migrations...")
try:
    from django.core.management import call_command
    
    # Détecte les changements dans TOUTES les applications
    call_command('makemigrations', '--noinput', verbosity=1)
    
    # Applique toutes les migrations (si nouvelles)
    call_command('migrate', '--noinput', verbosity=1)
    
    print("✅ Migrations OK")
except Exception as e:
    print(f"⚠️  Erreur migrations (on continue): {e}")

# --- Étape 2 : Superuser ---
print("👤 Étape 2: Superuser...")
try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin1234!")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    
    if not User.objects.filter(username=ADMIN_USERNAME).exists():
        User.objects.create_superuser(
            username=ADMIN_USERNAME,
            password=ADMIN_PASSWORD,
            email=ADMIN_EMAIL,
            matricule="ADMIN_RENDER"
        )
        print(f"✅ Superuser '{ADMIN_USERNAME}' créé")
    else:
        print(f"ℹ️ Superuser '{ADMIN_USERNAME}' existe déjà")
except Exception as e:
    print(f"⚠️  Superuser warning (continuing): {e}")

# --- Étape 3 : Permissions ---
print("🔐 Étape 3: Permissions...")
try:
    from core.models import Profil
    from django.core.management import call_command
    
    if Profil.objects.count() == 0:
        print("⚠️  Aucun profil détecté. Initialisation...")
        call_command('init_permissions_complet', verbosity=0)
        print("✅ Permissions initialisées")
    else:
        print(f"✅ {Profil.objects.count()} profils déjà présents")
except Exception as e:
    print(f"⚠️  Permissions warning (continuing): {e}")

# --- Étape 4 : Démarrer Gunicorn ---
print("🚀 Étape 4: Lancement Gunicorn...")

render_port = os.environ.get('PORT', '8000')
bind_address = f"0.0.0.0:{render_port}"

print(f"   → Binding sur {bind_address}")

cmd = [
    "gunicorn",
    "cid.wsgi:application",
    "--bind", bind_address,
    "--timeout", "120",
    "--workers", "2",
    "--access-logfile", "-",
    "--error-logfile", "-"
]

try:
    os.execvp(cmd[0], cmd)
except Exception as e:
    print(f"❌ Erreur critique lors du lancement de Gunicorn: {e}")
    sys.exit(1)
