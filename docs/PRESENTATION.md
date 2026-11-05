<!-- docs/PRESENTATION.md -->
# CID — présentation

CID est une application web destinée aux agents des Maisons départementales de la solidarité (MDS). Elle réunit le dossier de l'usager, les rendez-vous, les documents et les circuits propres au Département.

La démonstration ne contient que des données fictives (voir `DONNEES_FICTIVES.md`).

## Modules

- **Fiche usager** : identité, foyer et liens familiaux, points d'attention, documents (GED), messages, historique.
- **Agenda** : permanences, visites à domicile, réunions ; vue depuis la fiche usager.
- **Aides financières (AFASE)** : demande, contrôle, inspecteur, régie.
- **Protection de l'enfance** : informations préoccupantes et suivi ASE, avec accès réservés.
- **RSA – Insertion** (`INSERTION.md`) : contrats, prescriptions, commission de réorientation, file active et statistiques.
- **Modèles de courriers** (`MODELES_COURRIERS.md`).

## Échanges avec d'autres services

| Service | État |
|---|---|
| API Particulier (situation CAF/MSA, France Travail) | en service sur le bac à sable (données fictives) |
| **RDV Service Public** (ANCT) | **passerelle présente, désactivée : prête à l'activation après obtention des identifiants ANCT et test sur leur environnement de démonstration** (`RDV_SERVICE_PUBLIC.md`) |

## Licence

AGPL v3, réutilisation commerciale interdite (`../LICENCE.md`). Les parties reprises de Mon Suivi Social v2 (ANCT) le sont sous licence MIT.
