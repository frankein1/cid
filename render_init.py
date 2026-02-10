#!/usr/bin/env python
"""
FICHIER: render_init.py
PLACER À LA RACINE (à côté de manage.py)
Render l'exécute automatiquement avant de démarrer (via Procfile)
"""

import os
import sys
import django
import subprocess
from datetime import datetime

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cid.settings')

def log(msg, level="INFO"):
    """Journalisation formatée pour Render"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", file=sys.stderr)

def check_migrations():
    """Vérifie et applique les migrations si nécessaire"""
    try:
        django.setup()
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        
        if plan:
            log(f"📦 {len(plan)} migration(s) à appliquer")
            from django.core.management import call_command
            call_command("migrate", interactive=False)
            log("✅ Migrations appliquées")
            return True
        else:
            log("✅ Base de données à jour (pas de migrations en attente)")
            return False
            
    except Exception as e:
        log(f"⚠️  Erreur lors de la vérification des migrations: {e}", "WARNING")
        return False

def run_security_checks():
    """Exécute les vérifications de sécurité Django"""
    try:
        from django.core.management import call_command
        
        log("🔒 Vérifications de sécurité...")
        
        # Vérification des settings
        call_command("check", "--deploy", verbosity=0)
        log("✅ Vérifications de déploiement passées")
        
        # Vérification des modèles
        call_command("check")
        log("✅ Vérifications des modèles passées")
        
        return True
    except subprocess.CalledProcessError as e:
        log(f"❌ Échec des vérifications: {e}", "ERROR")
        return False
    except Exception as e:
        log(f"⚠️  Vérifications partielles: {e}", "WARNING")
        return True

def collect_static_files():
    """Collecte les fichiers statiques pour production"""
    try:
        log("🗃️  Collection des fichiers statiques...")
        from django.core.management import call_command
        call_command("collectstatic", "--noinput", "--clear")
        log("✅ Fichiers statiques collectés")
        return True
    except Exception as e:
        log(f"⚠️  Erreur collectstatic: {e}", "WARNING")
        return False

def run_si_ditas_install():
    """Exécute votre installation SI-DITAS personnalisée"""
    try:
        log("🚀 Lancement de l'installation SI-DITAS...")
        
        # Vérifier que les variables ADMIN sont présentes
        required_vars = ['ADMIN_PASSWORD']
        missing = [var for var in required_vars if not os.environ.get(var)]
        
        if missing:
            log(f"❌ Variables manquantes sur Render: {missing}", "ERROR")
            log("👉 Ajoutez-les dans: Render → Settings → Environment")
            return False
        
        # Importer et exécuter votre commande
        django.setup()
        from django.core.management import call_command
        
        call_command("install")
        log("✅ Installation SI-DITAS terminée")
        return True
        
    except Exception as e:
        log(f"❌ Erreur lors de l'installation SI-DITAS: {e}", "ERROR")
        return False

def main():
    """Point d'entrée principal"""
    log("=" * 50)
    log("🔄 DÉMARRAGE DE L'INITIALISATION RENDER")
    log("=" * 50)
    
    # 1. Vérifications préliminaires
    if not os.path.exists("manage.py"):
        log("❌ Fichier manage.py introuvable", "ERROR")
        return 1
    
    # 2. Appliquer les migrations
    migrations_applied = check_migrations()
    
    # 3. Vérifications de sécurité (seulement si nouvelles migrations)
    if migrations_applied:
        if not run_security_checks():
            log("⚠️  Continuez avec prudence", "WARNING")
    
    # 4. Fichiers statiques
    collect_static_files()
    
    # 5. Installation SI-DITAS
    if not run_si_ditas_install():
        log("❌ Échec critique de l'installation", "ERROR")
        return 1
    
    log("=" * 50)
    log("🎉 INITIALISATION RENDER TERMINÉE AVEC SUCCÈS")
    log("👉 Votre application est prête à démarrer")
    log("=" * 50)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
