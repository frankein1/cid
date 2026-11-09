# Orientation ASELL

Accompagnement socio-éducatif lié au logement : fiche d'orientation **généraliste** ou **renforcée**, volet **accès**
ou **maintien**. Code : `logement/models/m_asell.py`, `services/asell.py`, `views/v_asell.py`,
`templates/logement/asell_detail.html`.

## Parcours

1. Fiche de l'usager → encart « Logement » → ASELL (choisir le volet, puis généraliste ou renforcé). Depuis un dossier
   de prévention des expulsions : « Solutions pour le ménage » → *Orientation ASELL renforcé*.
2. La fiche est préremplie : identité, n° CAF, adresse, téléphone, composition familiale, ressources hors aide au
   logement, AL/APL, loyer et dettes (budget du foyer), FSL en cours, mesure ASELL déjà demandée.
   Pour l'ASELL renforcé lié à un dossier d'expulsion : bailleur, dette, dates de l'assignation, du commandement de
   quitter les lieux, du concours de la force publique, FSL déjà accordé.
3. L'agent choisit l'opérateur, complète, rédige l'évaluation.
4. PDF puis envoi par mail (module d'envoi commun) ou impression ; l'envoi est tracé, y compris dans le dossier
   d'expulsion.
5. Réponse de l'opérateur saisie par l'agent : mesure engagée, liste d'attente, orientation non retenue.

## Choix faits

- **Pas de visa du cadre** : le modèle de fiche ne porte que la signature du travailleur social. S'il faut un visa,
  il se branche comme pour l'hébergement d'urgence.
- **Opérateurs** : la liste annuelle du Département s'importe en administration (Logement → Opérateurs ASELL, CSV ou
  Excel, tout ou rien). Une ligne = un opérateur et une thématique (généraliste, renforcé…). Le sélecteur de la fiche
  propose d'abord les opérateurs du secteur de l'usager (commune, ou arrondissement de Marseille), puis les autres. Les
  lignes sans sigle (cellules fusionnées) reprennent l'opérateur du dessus : l'import le signale, à vérifier.
- **Destinataires** : toutes les adresses mail de la ligne opérateur sont proposées à l'envoi (une ou plusieurs).
  Les fichiers réels ne sont jamais versés au dépôt : seul le modèle CSV et les données fictives le sont.
- Les cases à cocher du PDF sont écrites `[X]` : même rendu sur tous les serveurs.
- Durée de conservation : code `ASELL`, suit le dossier de l'usager.
