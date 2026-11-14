# Journal de l'accompagnement et notes personnelles

Document de référence pour le développement. Textes d'aide : `docs/aide/outils/generer_fiches.py` (pages `journal-accompagnement`, `beneficiaire-transferer`).

## Modèles (`beneficiaire/models_journal.py`)

- `EntretienSocial` : entretien. `synthese` (partagée, lisible du dossier complet), `synthese_privee` (lisible de son auteur, et du référent actuel en reprise).
- `NotePersonnelle` : note datée (`date_note`, automatique), `auteur`, `contenu`, `a_transmettre` (choix de l'auteur), `transmise_a_mds` et `transmise_le` (renseignés au transfert).

## Qui voit quoi

| Donnée | Auteur | Référent actuel de l'usager | Agents du dossier complet | Autres MDS |
|---|---|---|---|---|
| Entretien (synthèse partagée) | oui | oui | oui | non |
| Synthèse privée | oui (modifie) | lecture seule | non | non |
| Note personnelle | oui (modifie, supprime) | lecture seule | non | non |
| Note transmise (après transfert) | oui | — | — | MDS destinataire, lecture seule |

- `EntretienSocial.peut_lire_prive` et `NotePersonnelle.peut_lire` portent ces règles. Seul l'auteur modifie ou supprime (`NotePersonnelle.peut_gerer`).
- Le journal lui-même exige le dossier complet (`beneficiaire/views_journal.py`, `_usager`).

## Cycle de vie

- **Saisie** : `note_nouvelle`, réservée à l'équipe de la MDS de l'usager.
- **Transfert** (`beneficiaire/transfert.py`, `transferer`) : pour chaque personne transférée, les notes sont remises à zéro puis les notes cochées (`a_transmettre`) reçoivent `transmise_a_mds` et `transmise_le`. Le journal partagé ne suit pas le dossier.
- **Reprise** dans la même MDS : pas de transfert. Le référent actuel lit les notes et synthèses privées de l'ancien TS, en lecture seule, comme les feuilles jaunes d'un dossier papier.
- **Archivage** (`beneficiaire/archivage.py`, `archiver`) : les notes et les synthèses privées sont détruites avant l'archivage, avec une trace dans le journal d'audit.
- **Suppression du journal un mois après transfert** : écartée. Pas de suppression automatique.

## Tests

- `beneficiaire/tests_notes_personnelles.py` : saisie, visibilité, transfert, suppression, reprise, archivage. Les fixtures sont dans `FixturesNotes`.
- `beneficiaire/tests_journal.py` : journal, synthèse privée, sources du parcours.
