import os
import subprocess
import django

print("🔧 [Render] Applying migrations...")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cid.settings")
django.setup()

# --- Étape 1 : migrations rapides ---
try:
    subprocess.run(
        ["python", "manage.py", "migrate", "--noinput"],
        check=True
    )
    print("✅ Migrations OK.")
except Exception as e:
    print("❌ Migration error:", e)

# --- Étape 2 : créer superuser léger ---
from django.contrib.auth import get_user_model
User = get_user_model()

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin1234!")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")

print(f"👤 Vérification superuser '{ADMIN_USERNAME}'...")

try:
    if not User.objects.filter(username=ADMIN_USERNAME).exists():
        User.objects.create_superuser(
            username=ADMIN_USERNAME,
            password=ADMIN_PASSWORD,
            email=ADMIN_EMAIL,
            matricule="ADMIN_RENDER"
        )
        print("✅ Superuser créé.")
    else:
        print("ℹ️ Superuser existant.")
except Exception as e:
    print("⚠️ Impossible de créer le superuser :", e)

# --- Étape 3 : démarrer gunicorn ---
print("🚀 Lancement gunicorn...")
subprocess.run(["gunicorn", "cid.wsgi:application"])
