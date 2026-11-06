# Statistiques de l'accompagnement

Menu **Accompagnement › Statistiques de l'accompagnement** (`/beneficiaire/statistiques/accompagnement/`).

## Trois usages, une page
| Qui | Périmètre | Détail par agent |
|---|---|---|
| Cadre de MDS (capacité `peut_valider`) | ses MDS | oui (pilotage de l'équipe) |
| Rapport d'activité annuel | lien « Rapport annuel : 2026, 2025… », bouton **Imprimer / PDF**, **CSV** | selon qui l'édite |
| Direction (capacité `stats_departement`, profils DIR_DIRECTION et DIR_CADRE ; administrateurs) | tout le département, ou une MDS ; **tableau de comparaison des MDS** | **jamais** |

La capacité `stats_departement` est créée par la migration `beneficiaire/0012` et donnée aux profils de direction.

## Contenu
- **Activité** (entretiens du journal) : nombre, heures, **file active** (personnes distinctes vues), dont vues pour la
  première fois, part d'accompagnement **légal**, suites à donner ouvertes et en retard ; par type d'accompagnement
  (entretiens et personnes), par mode, orientations vers les partenaires ; par agent pour le cadre.
- **Public** (personnes vues) : tranches d'âge, civilité, 10 premières communes.
- **Budgets du foyer** (dernier budget de chaque foyer établi sur la période) : tranches de reste à vivre, médiane,
  foyers avec impayés (et postes), foyers avec dettes, dette médiane.
- **Ateliers** : séances, inscrits, taux de remplissage, taux de présence, liste d'attente (besoin non couvert), part
  des personnes extérieures.

## Règles
- **Secret statistique** : un effectif de 1 à 4 personnes ou foyers s'affiche « < 5 », sans pourcentage ni médiane qui
  permettraient de le retrouver (médianes calculées à partir de 5 foyers).
- **Aucun texte libre** n'est compté ni exporté ; jamais la synthèse privée.
- Un entretien est compté dans la **MDS actuelle** de l'usager.
- Les chiffres valent ce que vaut la saisie : sans entretiens notés, la file active est sous-estimée.
- Les rendez-vous, aides, RSA et IP gardent leurs propres pages de statistiques (menu Cadre, RSA – Insertion, IP).
