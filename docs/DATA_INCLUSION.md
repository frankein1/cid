# data·inclusion : trouver un service d'insertion

Menu **Accompagnement › Trouver un service d'insertion** (`/connecteurs/inclusion/`), lien depuis le formulaire
d'entretien (« Trouver un service près de chez l'usager ») et depuis l'annuaire des partenaires.

## Ce que c'est
Le référentiel national de l'offre d'insertion (GIP Plateforme de l'inclusion) : structures et services (Dora,
France Travail, Soliguide, emplois de l'inclusion, Missions locales…), décrits selon le schéma data·inclusion v1
(thématiques, publics, frais, modes d'accueil). Données publiques, **Licence Ouverte 2.0**.

## Étape 1 (cette version) : fichiers ouverts, sans jeton
- CID télécharge les fichiers CSV de data.gouv.fr (structures, puis services), les lit **en flux** et ne garde que
  les départements de `DATA_INCLUSION_DEPARTEMENTS` (« 13 » par défaut ; plusieurs : « 13,84 »). Un service sans
  adresse est gardé si sa zone d'éligibilité couvre le département.
- **Mise à jour** : page « Mise à jour » (administrateurs) → « Mettre à jour maintenant » (quelques minutes, en
  arrière-plan) ; en production, planifier `python manage.py importer_data_inclusion` **chaque mardi** (fichiers
  republiés le lundi). Chaque mise à jour est tracée ; un service disparu des fichiers est retiré ; un fichier vide
  (incident) ne vide pas la base.
- **Rien n'est envoyé** à data·inclusion : la recherche se fait dans la copie locale, sans aucune donnée d'usager.

## Recherche
- Par **catégorie** (les 16 du schéma), **commune** / code postal, mots-clés, **gratuit**, **accueil sur place**.
- **Proximité** : les services sont classés du plus proche au plus éloigné de la commune choisie (point de
  référence calculé à partir des services de cette commune, sans géocodage extérieur).
- Depuis un entretien : la commune de l'usager et les **types d'accompagnement cochés** sont repris ; chaque type a
  ses catégories data·inclusion (admin › Types d'accompagnement › « Thématiques data·inclusion », correspondance
  installée par la migration `beneficiaire/0013`).
- **Ajouter à l'annuaire** : crée la fiche partenaire (structure, service, coordonnées publiques, horaires, lien),
  une seule fois (`reference_inclusion`). Elle peut alors être choisie comme orientation dans l'entretien et compte
  dans les statistiques.

## Étape 2 (production, plus tard)
API avec jeton (formulaire data·inclusion) : recherche en direct, coordonnées des référents. Voir l'étude
« ProConnect et data·inclusion » du projet.

## Démo
Sur Render, un administrateur clique « Mettre à jour maintenant » : les vraies données publiques des
Bouches-du-Rhône sont importées. La remise à zéro de la démo les conserve.
