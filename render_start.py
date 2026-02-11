import os
import subprocess
import django

print("🔧 [Render] Applying migrations...")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cid.settings")
django.setup()

try:
    subprocess.run(
        ["python", "manage.py", "migrate", "--noinput"],
        check=True
    )
    print("✅ [Render] Migrations applied successfully.")
except Exception as e:
    print("❌ [Render] Migration error:", e)

print("🚀 [Render] Starting gunicorn...")
subprocess.run(["gunicorn", "cid.wsgi:application"])
