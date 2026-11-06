# Ateliers collectifs

Menu **Planning › Ateliers collectifs** (`/planning/ateliers/`).

## Principe
- Un **atelier** est un thème (« Cuisine à petit prix », « Premiers pas numériques »…). Il est créé dans
  l'administration (Planning › Ateliers), soit pour une MDS, soit pour tout le Département (MDS vide).
- Une **séance** est une date de cet atelier dans une MDS : horaires, lieu, animateur, partenaire co-animateur
  (annuaire), action d'insertion liée (facultatif), nombre de places (vide = sans limite), condition d'âge
  (« à partir de » / « jusqu'à »), gratuit ou payant (tarif).

## Inscriptions
- **Usager suivi** : recherche parmi les usagers de la MDS de la séance. Si la condition d'âge n'est pas remplie
  (âge calculé au jour de la séance), CID prévient ; l'agent peut « inscrire quand même ».
- **Personne extérieure** ou **accompagnant** : prénom / nom, et seulement le nécessaire pour la prévenir
  (téléphone, courriel, commune).
- Séance complète → **liste d'attente**. Quand une personne inscrite est désinscrite, la première de la liste
  d'attente passe automatiquement inscrite (CID l'affiche : il reste à la prévenir).
- Une séance annulée n'accepte plus d'inscription ; elle peut être rétablie.

## Le jour J
- **Feuille d'émargement** PDF (inscrits + 3 lignes libres) et export **CSV** (séparateur « ; », lisible par Excel).
- Présences (présent / absent / excusé) et, si payant, paiement reçu.
- La fiche de l'usager affiche ses participations (bloc « Ateliers collectifs », visible dès qu'il y en a une).

## Droits
- Voir : agents ayant la capacité `peut_voir` et accès à la MDS de la séance.
- Créer / modifier une séance, inscrire, noter les présences : capacité `peut_creer` dans cette MDS.

## Données personnelles
- Les participants extérieurs sont des données personnelles : l'anonymiseur (`anonymiser_base`) les efface comme le
  reste ; supprimer une fiche usager supprime ses inscriptions.
