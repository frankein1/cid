<!-- docs/ANONYMISATION.md -->
# Copie anonymisée de la base

La commande `anonymiser_base` transforme une **copie** de la base en base de test réaliste : mêmes volumes, même structure de dossiers et de familles, aucune donnée nominative. Elle est inspirée de l'anonymiseur de Mon Suivi Social. Le code est dans `core/management/commands/anonymiser_base.py`.

> ⚠️ **Jamais sur la production.** L'opération est irréversible. Elle se lance sur une copie restaurée de la base, connectée à un CID de test.

## Lancer
```
CID_ANONYMISATION_AUTORISEE=1 python manage.py anonymiser_base --base <nom de la copie> --confirmer
```
Trois verrous empêchent l'erreur :
- la variable `CID_ANONYMISATION_AUTORISEE=1` doit être posée sur le serveur de la copie ;
- `--base` doit être exactement le nom de la base à laquelle CID est connecté ;
- `--confirmer` doit être présent.

## Ce qui est fait
| Données | Traitement |
|---|---|
| Usagers | Nom et prénom fictifs, et une même famille garde un même nom. Date de naissance décalée de ± 45 jours, pour que l'âge reste réaliste. Adresse fictive dans la **même commune**. Téléphones, courriel, NIR, n° CAF, France Travail, fiscal, GENESIS et PMI effacés |
| Textes libres | Remplacés par « [texte anonymisé] » partout : RDV, aides, contrats, IP, messages, liens familiaux… |
| Noms, téléphones et courriels ailleurs | Effacés ou remplacés (signalants, tiers, contacts…) |
| Données reçues des API | Vidées |
| Agents | Identifiants et noms fictifs, mots de passe rendus inutilisables. Les **super-administrateurs sont conservés** |
| Documents de la GED | Titres anonymisés et documents **détachés de leurs fichiers, sans rien supprimer dans le stockage**. Une copie de base pointe souvent vers le même stockage que la production |
| Journal d'activité, sessions, jetons RDV-Solidarités | Supprimés |
| Paramétrage (MDS, référentiels, modèles de courriers, actions d'insertion…) | Intact |

## Limite
Un nom propre écrit dans un champ inattendu peut subsister. Avant de transmettre une copie, il faut en vérifier un échantillon.
