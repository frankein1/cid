#!/bin/bash
# FICHIER: sync_render.sh - VERSION AVEC GESTION CONFLITS
# USAGE: ./sync_render.sh "message du commit"

set -e

echo "🔄 SYNCHRONISATION main → render"
echo "================================="

if [ -z "$1" ]; then
    echo "❌ Usage: ./sync_render.sh \"Message du commit\""
    exit 1
fi

# === VÉRIFICATION VENV ===
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ ERREUR: Environnement virtuel non activé!"
    echo ""
    echo "📋 PROCÉDURE:"
    echo "   1. cd /srv/django/si-ditas"
    echo "   2. source venv/bin/activate  # Ou le chemin de votre venv"
    echo "   3. ./sync_render.sh \"Votre message\""
    echo ""
    exit 1
else
    echo "✅ Venv activé: $(basename $VIRTUAL_ENV)"
fi

# 1. S'assurer qu'on est sur main
echo ""
echo "📌 Étape 1: Vérification branche..."
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "none")
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "⚠️  Passage à main..."
    git checkout main 2>/dev/null || { echo "❌ Branche main introuvable"; exit 1; }
fi

# 2. Pull des dernières modifications
echo "📥 Étape 2: Mise à jour depuis GitHub..."
git pull origin main

# 3. Supprimer .env et commandes du suivi Git si présents
echo "🧹 Étape 3: Nettoyage des fichiers sensibles..."
if git ls-files .env --error-unmatch 2>/dev/null; then
    echo "   🗑️  Suppression de .env du suivi Git..."
    git rm --cached .env 2>/dev/null || true
fi
if git ls-files commandes --error-unmatch 2>/dev/null; then
    echo "   🗑️  Suppression de commandes du suivi Git..."
    git rm --cached commandes 2>/dev/null || true
fi

# 4. Vérifier les modifications de modèles
echo ""
echo "🔍 Étape 4: Analyse des changements..."
if git diff --name-only HEAD | grep -E "(models/.*\.py$|migrations/.*\.py$)" > /dev/null; then
    echo "📝 Modèles détectés: génération des migrations..."
    python manage.py makemigrations
    
    NEW_MIGRATIONS=$(find . -path "*/migrations/*.py" -mmin -5 2>/dev/null | head -5)
    if [ -n "$NEW_MIGRATIONS" ]; then
        echo "📄 Fichiers migrations créés:"
        echo "$NEW_MIGRATIONS"
    fi
    
    echo "🧪 Test des migrations..."
    python manage.py migrate --check
    
    git add */migrations/0*.py 2>/dev/null || true
    MIGRATION_MSG=" (avec migrations)"
else
    echo "✅ Pas de modification de modèles détectée."
    MIGRATION_MSG=""
fi

# 5. Tests Django
echo ""
echo "🧪 Étape 5: Tests Django..."
if python manage.py test --failfast 2>&1 | tail -20; then
    echo "✅ Tests passés"
else
    echo "❌ Tests échoués. Arrêt."
    exit 1
fi

# 6. Commit sur main
echo ""
echo "💾 Étape 6: Commit sur main..."
git add -A
git commit -m "$1$MIGRATION_MSG" || echo "ℹ️  Pas de changement à commiter"

# 7. Push sur main
echo "⬆️  Étape 7: Push sur main..."
git push origin main

# 8. Préparation branche render
echo ""
echo "🔄 Étape 8: Préparation branche render..."
if git show-ref --verify --quiet refs/heads/render; then
    echo "📌 Branche render locale trouvée"
    git checkout render
else
    echo "📌 Création branche render depuis distant..."
    git fetch origin
    git checkout -b render origin/render 2>/dev/null || git checkout -b render
fi

# 9. Stratégie de fusion pour éviter conflits .env/commandes
echo "🔧 Configuration fusion sans conflit..."
echo ".env merge=ours" > .gitattributes
echo "commandes merge=ours" >> .gitattributes
git add .gitattributes

# 10. Fusion et push
echo "🔄 Fusion de main dans render..."
git merge main --no-ff -m "Merge main → render: $1" || {
    echo "⚠️  Conflits détectés, résolution automatique..."
    # Pour .env et commandes, on garde la version render
    git checkout --ours .env 2>/dev/null || true
    git checkout --ours commandes 2>/dev/null || true
    git add .env commandes 2>/dev/null || true
    git commit -m "Merge résolu: $1"
}

echo "⬆️  Push sur origin render..."
git push origin render

# 11. Retour sur main et nettoyage
echo "↩️  Étape 11: Retour sur main..."
git checkout main
rm -f .gitattributes

echo ""
echo "✅ SYNCHRONISATION TERMINÉE !"
echo "=============================="
echo "⏱️  Render va déployer automatiquement..."
echo ""
echo "📊 Pour suivre le déploiement:"
echo "   1. https://render.com/dashboard"
echo "   2. Cliquez sur votre service 'cid'"
echo "   3. Vérifiez les logs du déploiement"
echo ""
echo "🌐 Votre site: https://cid-6yav.onrender.com"
echo ""
echo "🔄 Prochaine mise à jour:"
echo "   ./sync_render.sh \"Description des modifications\""
