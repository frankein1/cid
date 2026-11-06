# Journal de l'accompagnement

Sur la fiche usager (dossier complet), encart **Journal de l'accompagnement** → `/beneficiaire/<code>/journal/`.
Menu Planning › **Mes suites à donner**.

## Un journal unique
Le journal présente, du plus récent au plus ancien :
- les **entretiens** saisis par les agents ;
- ce que CID sait déjà du parcours, sans ressaisie : rendez-vous, demandes d'aide financière, contrats et
  prescriptions RSA, ateliers collectifs, budgets du foyer. Chaque source garde ses droits (une aide que l'agent ne
  peut pas voir n'apparaît pas ; le RSA seulement pour ceux qui ont accès au module).

Les **informations préoccupantes et la protection de l'enfance n'y figurent pas** (rendez-vous IP / enfance compris) :
elles gardent leur cloisonnement.

Filtres : par nature (entretiens, rendez-vous…) et par type d'accompagnement.

## L'entretien
Date, heure, mode (accueil, RDV, VAD, téléphone, écrit, visio, extérieur), durée, objet, **types d'accompagnement**,
autres personnes du foyer présentes, co-intervenants, **synthèse**, **synthèse privée**, orientation vers un partenaire
de l'annuaire, **suite à donner** avec échéance.

- **Synthèse** : visible des agents qui ont accès au dossier complet.
- **Synthèse privée** : lisible par **son seul auteur** (reprise de Mon Suivi Social). Absente de l'administration.
  Elle reste une donnée du dossier : en cas de demande d'accès de l'usager (RGPD), elle fait partie de ce qui peut lui
  être communiqué — à valider avec le délégué à la protection des données.
- Seul l'auteur modifie son entretien.
- **Compte rendu d'un rendez-vous** : un RDV réalisé sans compte rendu affiche « Rédiger le compte rendu », qui
  pré-remplit la date, l'heure, le mode, la durée et les co-intervenants.

## Types d'accompagnement
Référentiel modifiable dans l'administration (Bénéficiaires › Types d'accompagnement). La case **« légal »** signale
un accompagnement prévu par un texte (RSA, suivi de mesure de protection de l'enfance, MASP…) : badge « légal » dans
le journal. Liste de départ générique, installée par la migration `beneficiaire/0011`.

## Suites à donner
« Mes suites à donner » liste les suites non faites des entretiens dont l'agent est auteur ou co-intervenant, échéance
dépassée en rouge ; bouton « Fait ».

## Données personnelles
Supprimer la fiche supprime ses entretiens ; l'anonymiseur remplace objets, synthèses, suites et précisions.
