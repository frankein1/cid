import os
import subprocess
import django

print("🔧 [Render] Applying migrations...")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cid.settings")
django.setup()

# --- Étape 1 : migrations ---
try:
    subprocess.run(
        ["python", "manage.py", "migrate", "--noinput"],
        check=True
    )
    print("✅ [Render] Migrations applied successfully.")
except Exception as e:
    print("❌ [Render] Migration error:", e)

# --- Étape 2 : création superuser automatique ---
from django.contrib.auth import get_user_model

User = get_user_model()

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin1234!")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")

print(f"👤 [Render] Checking superuser '{ADMIN_USERNAME}'...")

if not User.objects.filter(username=ADMIN_USERNAME).exists():
    print("🔨 [Render] Creating admin user...")
    User.objects.create_superuser(
        username=ADMIN_USERNAME,
        password=ADMIN_PASSWORD,
        email=ADMIN_EMAIL,
        matricule="ADMIN_RENDER"
    )
    print("✅ [Render] Superuser created.")
else:
    print("ℹ️ [Render] Superuser already exists.")

# --- Étape 3 : démarrer gunicorn ---
print("🚀 [Render] Starting gunicorn...")
subprocess.run(["gunicorn", "cid.wsgi:application"])
