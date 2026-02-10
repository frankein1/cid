#!/usr/bin/env python
"""
Script d'initialisation pour Render
Exécute automatiquement votre commande d'installation au démarrage
"""

import os
import sys
import django
import subprocess

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cid.settings')
django.setup()

def run_installation():
    """Exécute votre commande d'installation personnalisée"""
    print("🚀 Démarrage de l'installation SI-DITAS sur Render...")
    
    try:
        # Méthode 1 : Appel direct comme dans votre code
        from django.core.management import call_command
        call_command("install")
        print("✅ Installation terminée avec succès !")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de l'installation : {e}")
        
        # Méthode 2 : Tentative via subprocess (plus robuste)
        print("🔄 Tentative alternative...")
        try:
            result = subprocess.run(
                [sys.executable, "manage.py", "install"],
                capture_output=True,
                text=True
            )
            print("Sortie :", result.stdout)
            if result.stderr:
                print("Erreurs :", result.stderr)
            return result.returncode == 0
        except Exception as e2:
            print(f"❌ Échec complet : {e2}")
            return False

if __name__ == "__main__":
    success = run_installation()
    sys.exit(0 if success else 1)
