#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

command -v psql >/dev/null || {
  echo "❌ psql introuvable. Installe PostgreSQL."
  exit 1
}

if [ ! -f "$ENV_FILE" ]; then
  echo "❌ Erreur : fichier .env introuvable."
  echo "   attendu ici : $ENV_FILE"
  exit 1
fi

# ==============================================
# ✅ Lecture robuste du .env (sans source)
# ==============================================

get_env() {
  grep -E "^[[:space:]]*$1[[:space:]]*=" "$ENV_FILE" \
    | head -n1 \
    | sed -E "s/^[^=]+=//" \
    | sed -E "s/[[:space:]]+#.*$//" \
    | tr -d '"' \
    | tr -d "'" \
    | xargs
}

DB_NAME=$(get_env DB_NAME)
DB_USER=$(get_env DB_USER)
DB_PASSWORD=$(get_env DB_PASSWORD)

# ==============================================
# ✅ Validation stricte anti injection
# ==============================================

regex="^[a-zA-Z_][a-zA-Z0-9_]+$"

if [[ ! "$DB_NAME" =~ $regex ]]; then
  echo "❌ Erreur : DB_NAME invalide : $DB_NAME"
  exit 1
fi

if [[ ! "$DB_USER" =~ $regex ]]; then
  echo "❌ Erreur : DB_USER invalide : $DB_USER"
  exit 1
fi

if [ -z "$DB_PASSWORD" ]; then
  echo "❌ Erreur : DB_PASSWORD vide."
  exit 1
fi

if [[ "$DB_PASSWORD" == *"'"* ]]; then
  echo "❌ Erreur : DB_PASSWORD ne doit pas contenir d'apostrophe"
  exit 1
fi

# ==============================================
# ✅ Confirmation explicite
# ==============================================

echo ""
echo "⚠️ Création PostgreSQL :"
echo ""

read -p "Créer la base PostgreSQL (yes/no) ? " confirm

if [ "$confirm" != "yes" ]; then
  echo "Annulé."
  exit 0
fi

# ==============================================
# ✅ Création USER si absent
# ==============================================

sudo -u postgres psql -v ON_ERROR_STOP=1 <<EOF
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
      CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
   END IF;
END
\$\$;
EOF

# ==============================================
# ✅ Création DB si absente (hors transaction)
# ==============================================

DB_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME';")

if [ "$DB_EXISTS" != "1" ]; then
  echo "✅ Base absente → création..."

  sudo -u postgres createdb \
    -O "$DB_USER" \
    -E UTF8 \
    "$DB_NAME"
else
  echo "ℹ️ Base déjà existante."
fi

# ==============================================
# ✅ Grant final
# ==============================================

sudo -u postgres psql -v ON_ERROR_STOP=1 <<EOF
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF
