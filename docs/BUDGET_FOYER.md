# Budget du foyer

Sur la fiche usager (dossier complet), encart **Budget du foyer** → page `/beneficiaire/<code>/budget/`.

## Contenu
Mêmes rubriques que le budget de la demande d'AFASE (`AidFi/services/budget_afase.py`) :
- ressources mensuelles par rubrique, ventilées demandeur / conjoint / autres ;
- charges liées au logement et autres charges, chacune **payée** ou **non payée** ;
- dettes (créancier, montant) ;
- nombre de personnes au foyer (proposé d'après le réseau familial), observations.

**Reste à vivre** = (ressources − charges payées) / personnes au foyer / 30, par jour et par personne. Les charges non
payées et les dettes sont affichées à part.

## Historique
Un budget est daté (« établi le »). **Mettre à jour** crée un nouveau budget pré-rempli avec le précédent : l'ancien
reste dans l'historique. « Corriger ce budget » sert aux erreurs de saisie.

## Un budget par foyer
Le budget est enregistré sur la fiche d'un usager. Une personne qui vit au même foyer (lien familial « vit au foyer »)
et qui n'a pas de budget propre voit celui-ci, avec la mention « même foyer ».

## Lien avec l'AFASE
- Une **nouvelle demande d'AFASE** reprend le budget du foyer en cours (à vérifier et mettre à jour).
- Sans budget du foyer, la page propose de **repartir du budget de la dernière demande d'AFASE**.

## Droits
Lecture : dossier complet (agents de la MDS de l'usager). Saisie : agents de la MDS ayant la capacité `peut_creer`.
Supprimer une fiche supprime ses budgets ; l'anonymiseur vide les montants, dettes et observations.
