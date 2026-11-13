# Adultes vulnérables (`adultevul`)

Module de l'information préoccupante concernant un adulte vulnérable (note MDS n°19 du 10 janvier 2011, toujours en vigueur). Il remplace le suivi qui se faisait dans SAP. Le module est séparé de l'information préoccupante enfance (`protection_enfance`) mais reprend sa logique : journal, visas, capacités, génération PDF.

## Circuit

1. **Recueil** (annexe 1) : enregistré par un agent ayant accès à la MDS compétente (lieu d'habitation ou d'hébergement).
2. **Qualification** par le cadre : qualifiée (la cellule doit être constituée) ou non qualifiée (clôture possible).
3. **Cellule d'évaluation** (annexe 2) : composition, référents, modalités, investigations, plan d'action, propositions. Délai du rapport : 8 jours (urgence) ou 2 mois.
4. **Soumission au visa** : refusée tant que le rapport est incomplet ; le message indique ce qui manque. Une fois soumise, l'évaluation est figée.
5. **Visa** de l'adjoint Cohésion sociale ou du responsable de MDS de proximité. Le cadre peut renvoyer le rapport pour compléments.
6. **Décision** administrative du directeur de MDS, puis **clôture**.

Les propositions sont : classement sans suite, signalement police, accompagnement non contractualisé, MASP (niveau I ou II), psychiatrie, ARS, protection juridique.

## Annexes PDF

| Annexe | Contenu | Proposition liée |
|---|---|---|
| 1 | Grille de recueil | toujours |
| 2 | Cellule : plan d'action et propositions | toujours (une fois la cellule constituée) |
| 3 et 3 bis | Rapport police et courrier au procureur | police |
| 4 | Classement sans suite | classement |
| 5 | Accompagnement social non contractualisé | accompagnement |
| 6 | Demande de MASP | MASP |
| 7 et 7 bis | Rapport et courrier au médecin chef de psychiatrie | psychiatrie |
| 8 et 8 bis | Rapport et courrier au médecin inspecteur de l'ARS | ARS |
| 9 et 9 bis | Protection juridique : rapport et courrier au procureur | protection juridique |

Une annexe n'est proposée que si la cellule retient la proposition correspondante. Les signatures se font à la main après impression.

**Fiches de renseignements des parquets** (Aix 9.1, Marseille 9.2, Tarascon) : saisies dans CID (page « Fiche » du dossier, masque de saisie par rubriques), puis téléchargées en PDF **remplissable** (formulaire AcroForm, prérempli avec l'identité et les données saisies). Règle : on n'imprime qu'en cas de nécessité absolue. Les rubriques reproduites sont des reconstructions à faire valider.

## Protection juridique

Le rapport ne peut être soumis que si le parquet compétent et la mesure demandée sont renseignés, ainsi que les propositions et le référent. Les pièces du parquet (acte de naissance, fiche de renseignements, certificat médical ou motif de son absence) **ne bloquent pas** la soumission : un message rappelle aux agents d'y penser, sur la fiche et après soumission.

## MASP

Quand le MASP est proposé et que la situation est visée, le suivi se saisit dans CID : niveau I (sans perception des prestations) ou II (avec perception), dates de demande, de début, d'échéance et de réévaluation, référent.

## Capacités et profils

- `av_piloter` : qualifier, constituer la cellule, viser, renvoyer, clôturer. Profil **AV_PILOTE**.
- `av_evaluer` : référent d'une cellule, rédiger et soumettre le rapport. Profil **AV_EVALUATEUR** (avec `peut_voir`).
- `peut_decider` : décision administrative du directeur (profil directeur existant).
- `peut_voir` : accès au module et au recueil.

## Données de démonstration

`init_demo` crée trois situations fictives (voir `docs/DONNEES_FICTIVES.md`).
