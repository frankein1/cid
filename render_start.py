#!/usr/bin/env python
"""
Script de démarrage pour Render - VERSION CORRIGÉE PORT
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

# --- Étape 1 : Migrations (non bloquant) ---
print("📦 Étape 1: Migrations...")
try:
    from django.core.management import call_command
    call_command('migrate', '--noinput', verbosity=0)
    print("✅ Migrations OK")
except Exception as e:
    print(f"⚠️  Migrations warning (continuing): {e}")

# --- Étape 2 : Superuser (non bloquant) ---
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

# --- Étape 3 : Permissions (non bloquant) ---
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

# --- Étape 4 : Démarrer Gunicorn (CORRIGÉ PORT) ---
print("🚀 Étape 4: Lancement Gunicorn...")

# ✅ LIRE LA VARIABLE PORT DEPUIS L'ENVIRONNEMENT
render_port = os.environ.get('PORT', '8000')  # 8000 en fallback local

try:
    from gunicorn.app.wsgiapp import run
    
    # Construire les arguments avec la VRAIE valeur du port
    bind_address = f"0.0.0.0:{render_port}"
    print(f"   → Binding sur {bind_address}")
    
    os.environ['GUNICORN_CMD_ARGS'] = f'--bind {bind_address} --timeout 120'
    run()
except ImportError:
    print("⚠️  Gunicorn non installé, installation...")
    os.system('pip install gunicorn')
    from gunicorn.app.wsgiapp import run
    bind_address = f"0.0.0.0:{render_port}"
    os.environ['GUNICORN_CMD_ARGS'] = f'--bind {bind_address} --timeout 120'
    run()
except Exception as e:
    print(f"❌ Gunicorn failed: {e}")
    sys.exit(1)
