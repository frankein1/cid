<!-- README.md -->
# CID

CID est une application web Django pour les agents des Maisons départementales de la solidarité (MDS) : dossier de l'usager, rendez-vous, documents, circuits propres au Département.

- **Pour qui ?** Les équipes sociales d'une collectivité, et les développeurs qui veulent comprendre ou reprendre le logiciel.
- **Données :** le dépôt ne contient que des données **fictives**, pour la démonstration et l'apprentissage. Ne pas y déposer de données réelles.
- **Présentation détaillée des modules :** `docs/PRESENTATION.md`.
- **Contribuer :** `CONTRIBUTING.md`. **Sécurité :** `SECURITY.md` et `docs/SECURITE.md`. **Licence :** AGPL v3 (`LICENCE.md`).

## Installation (développement local)

Prérequis : Python 3.10 ou plus récent (`runtime.txt`), PostgreSQL.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
# créer un fichier .env avec les variables ci-dessous
python manage.py migrate
python manage.py install --no-input   # profils, MDS fictives, types de données
python manage.py init_demo            # données de démonstration (facultatif)
python manage.py runserver
```

Variables utiles : `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `ALWAYSDATA_NAME` / `ALWAYSDATA_USER` / `ALWAYSDATA_PASSWORD` / `ALWAYSDATA_HOST` (base PostgreSQL) ou `DATABASE_URL` (hébergement type Render). Les valeurs par défaut ne servent qu'au développement.

## Architecture

- **Django** : une application par domaine (`beneficiaire`, `ged`, `planning`, `insertion`, `logement`, `protection_enfance`, `adultevul`, `ru`, `connecteurs`, etc.). `core` contient les utilisateurs, profils, capacités, journal et outils communs.
- **Base** : PostgreSQL.
- **Documents** : GED chiffrée (`docs/CHIFFREMENT_GED.md`), stockage SeaweedFS ou équivalent.
- **Calcul des droits** : moteur OpenFisca, installé dans un environnement séparé à cause de ses dépendances (`requirements-openfisca.txt`, `docs/SIMULATION_DROITS.md`).
- **Intégrations** : ProConnect, API Particulier (bac à sable), RDV Service Public (passerelle désactivée par défaut).

## Documentation

Le dossier `docs/` contient une note par module et par sujet transversal (RGPD, journal, chiffrement, rôles, données fictives). Les pages d'aide utilisateur sont dans `docs/aide/`.

## Limites connues

- Projet en développement : certains modules sont complets, d'autres partiels. Voir `docs/PRESENTATION.md`.
- Pas d'audit de sécurité externe à ce jour (`docs/SECURITE.md`).
- Le paramétrage (MDS, profils, circuits) est propre au Département qui déploie l'outil.
