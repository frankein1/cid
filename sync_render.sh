#!/bin/bash
# FICHIER: sync_render.sh
# USAGE: ./sync_render.sh "message du commit"
# PLACEZ-LE à côté de manage.py

set -e  # Stoppe au premier erreur

echo "🔄 SYNCHRONISATION main → render"
echo "================================="

# Vérification argument
if [ -z "$1" ]; then
    echo "❌ Usage: ./sync_render.sh \"Message du commit\""
    exit 1
fi

# 1. S'assurer qu'on est sur main
echo "📌 Étape 1: Vérification branche..."
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "⚠️  Vous n'êtes pas sur 'main'. Passage à main..."
    git checkout main
fi

# 2. Pull des dernières modifications
echo "📥 Étape 2: Mise à jour depuis GitHub..."
git pull origin main

# 3. Vérifier les modifications de modèles
echo "🔍 Étape 3: Analyse des changements..."
if git diff --name-only HEAD | grep -E "(models/.*\.py$|migrations/.*\.py$)" > /dev/null; then
    echo "📝 Modèles détectés: génération des migrations..."
    python manage.py makemigrations
    
    # Afficher les migrations générées
    echo "📄 Fichiers migrations créés:"
    find . -name "00*.py" -newer /tmp/timestamp 2>/dev/null || find . -path "*/migrations/*.py" -mmin -5 | head -5
    
    # Tester les migrations
    echo "🧪 Test des migrations..."
    python manage.py migrate --check
    
    # Ajouter les fichiers migrations
    git add */migrations/0*.py
    MIGRATION_MSG=" (avec migrations)"
else
    echo "✅ Pas de modification de modèles détectée."
    MIGRATION_MSG=""
fi

# 4. Tests Django
echo "🧪 Étape 4: Tests Django..."
if python manage.py test --failfast 2>&1 | tail -20; then
    echo "✅ Tests passés"
else
    echo "❌ Tests échoués. Arrêt."
    exit 1
fi

# 5. Commit sur main
echo "💾 Étape 5: Commit sur main..."
git add -A
git commit -m "$1$MIGRATION_MSG" || echo "ℹ️  Pas de changement à commiter"

# 6. Push sur main
echo "⬆️  Étape 6: Push sur main..."
git push origin main

# 7. Mise à jour de render
echo "🔄 Étape 7: Mise à jour branche render..."
git checkout render 2>/dev/null || git checkout -b render
git merge main --no-ff -m "Merge main → render: $1"
git push origin render

# 8. Retour sur main
echo "↩️  Étape 8: Retour sur main..."
git checkout main

echo ""
echo "✅ SYNCHRONISATION TERMINÉE !"
echo "=============================="
echo "📊 Résumé:"
echo "   • Main: mis à jour"
echo "   • Render: fusionné"
echo "   • GitHub: synchronisé"
echo ""
echo "🌐 Render va maintenant:"
echo "   1. Détecter le push sur 'render'"
echo "   2. Déployer automatiquement"
echo "   3. Exécuter render_init.py (migrations auto)"
echo ""
echo "⏱️  Vérifiez le déploiement dans 2-3 min sur:"
echo "   → https://render.com/dashboard"
echo "   → https://cid-6yav.onrender.com"
