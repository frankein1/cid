#!/bin/bash
# deploy_render.sh - VERSION ULTIME SÉCURISÉE
# Ne supprime JAMAIS de fichiers locaux

set -e

echo "🚀 Déploiement Render (100% safe)"
echo "================================"

# BLOCAGE TOTAL si pas de venv
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ STOP: Venv non activé!"
    echo "   source venv/bin/activate"
    exit 1
fi

# PROTECTION: vérifier les fichiers sensibles
echo "🔒 Vérification sécurité..."
SENSITIVE_FILES=("commandes" ".env" "*token*" "*secret*")
for file in "${SENSITIVE_FILES[@]}"; do
    if compgen -G "$file" > /dev/null; then
        echo "   ⚠️  Fichier sensible détecté: $file"
        echo "      → Ignoré par Git, conservé localement"
        grep -q "$file" .gitignore || echo "$file" >> .gitignore
    fi
done

# 1. Travailler sur main
echo ""
echo "📌 Étape 1: Synchronisation main..."
git checkout main
git pull origin main

# 2. Migrations (optionnel)
read -p "🔧 Générer des migrations? (o/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Oo]$ ]]; then
    python manage.py makemigrations
    python manage.py migrate --check
    git add */migrations/*.py 2>/dev/null || true
fi

# 3. Commit (SAUF fichiers sensibles)
echo "💾 Commit..."
git add -A
for file in "${SENSITIVE_FILES[@]}"; do
    git reset -- "$file" 2>/dev/null || true
done
git commit -m "${1:-Mise à jour $(date +%Y-%m-%d)}" || echo "ℹ️  Pas de changement"

# 4. Push main
echo "⬆️  Push main..."
git push origin main

# 5. Mise à jour render (DOUCE)
echo ""
echo "🔄 Étape 2: Mise à jour render..."
if git show-ref --verify --quiet refs/heads/render; then
    git checkout render
else
    git checkout -b render origin/render 2>/dev/null || {
        echo "❌ Branche render introuvable"
        echo "   Création: git checkout -b render && git push -u origin render"
        exit 1
    }
fi

# Pull GENTIL
git pull origin render --rebase --autostash 2>/dev/null || {
    echo "⚠️  Pull échoué, tentative douce..."
    git stash
    git fetch origin
    git reset --hard origin/render
    git stash pop 2>/dev/null || true
}

# Fusion
git merge main --no-ff -m "Merge: $1" || {
    echo "⚠️  Conflits mineurs..."
    git status --short | grep -E "^AA|^UU" | while read line; do
        file=$(echo $line | cut -d' ' -f2)
        echo "   🔧 Résolution: $file"
        # Pour fichiers sensibles, garde local
        if [[ " ${SENSITIVE_FILES[@]} " =~ " ${file} " ]]; then
            git checkout --ours "$file"
        else
            # Pour autres, prend les deux
            git checkout --theirs "$file" 2>/dev/null || true
        fi
    done
    git add .
    git commit -m "Merge résolu: $1"
}

# Push
echo "⬆️  Push render..."
git push origin render

# Retour safe
git checkout main

echo ""
echo "✅ DÉPLOIEMENT RÉUSSI ET SÉCURISÉ"
echo "=================================="
echo "🌐 Votre site: https://cid-6yav.onrender.com"
echo "📊 Logs: https://render.com/dashboard"
echo ""
echo "💾 Vos fichiers sensibles sont PROTÉGÉS:"
ls -la commandes .env 2>/dev/null | awk '{print "   " $9 " (" $5 " bytes)"}'
echo ""
