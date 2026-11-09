# Hébergement d'urgence

Module de l'application `logement` : `models/m_hebergement.py`, `services/hebergement.py`, `services/hebergement_pdf.py`,
`views/v_hebergement.py`, gabarits `templates/logement/hebergement_*.html`.

## Ce que fait CID

| Étape | Qui | Dans CID |
|---|---|---|
| Ouvrir le dossier | agent de la MDS de l'usager | fiche usager → encart « Logement » ; un seul dossier ouvert par ménage (`HU-AAAA-NNNN`) |
| Tracer les démarches | agent | 115, fiche SIAO, centre maternel, accueil mère-enfants, DAHO, DALO, solution personnelle : date, précision, réponse |
| Préparer la fiche | agent | demande d'hébergement d'urgence, ou orientation vers les services de l'État (DDETS) ; préremplie |
| Viser | cadre de la MDS | un clic : initiales et date sur le PDF ; ou renvoi à l'agent |
| Transmettre | agent | envoi par mail (module d'envoi commun, pièces de la GED), compteur de papier évité |
| Saisir la réponse | agent | accord (structure, entrée, fin prévue), ajournement, refus |
| Renouveler | agent, cadre | fiche de renouvellement préremplie ; le référent est prévenu 21 jours avant l'échéance |
| Clore | agent | rapport final, motif de clôture |

## Règles reprises de la procédure départementale (2024)

- Sans démarches de droit commun tracées (115, SIAO, centres maternels s'il y a un enfant de moins de 3 ans), la
  demande risque l'ajournement : CID le signale, sans bloquer.
- Fiche conseillée d'après le foyer : demande d'hébergement pour une mère isolée avec un enfant de moins de 3 ans
  (ou une femme enceinte de plus de trois mois, que CID ne connaît pas) ; orientation vers l'État pour les autres
  ménages. L'agent reste libre du choix.
- Prise en charge : durée de la structure si elle est réglée, sinon 3 mois ; renouvellement de 3 mois, puis par
  périodes de 2 mois.
- Toutes les fiches partent avec l'aval du cadre. Une fiche modifiée après le visa doit être visée de nouveau.

## Protection des données

- L'information préoccupante et la mesure éducative ne sont jamais préremplies (le module IP a ses propres droits).
- Le numéro de carte d'identité ou AGDREF, demandé par l'État, n'est gardé que le temps du dossier : effacé à la
  clôture.
- Une grossesse n'est pas enregistrée comme donnée structurée.
- Droits : ceux du dossier de l'usager (MDS de l'usager, accès complet). Statistiques sans donnée par agent.
- Durée de conservation : code `HEBERGEMENT_URGENCE` du fichier du DPO (voir `RGPD_DUREES.md`).
- L'anonymiseur de base (`anonymiser_base`) couvre désormais toute l'application `logement`.

## Paramétrage (administration, jamais dans le dépôt)

- **Structures d'hébergement d'urgence** : nom, ville, public, durée d'accueil et durée d'un renouvellement (jours).
- **Destinataires des fiches** : adresse générique du service qui reçoit les fiches.

## Fiches papier d'origine

Les rubriques suivent la fiche de liaison MDS → service d'appui (demande et renouvellement), le rapport de prise en
charge et la fiche d'orientation vers la DDETS. Les modèles du Département ne sont pas dans le dépôt : CID imprime
ses propres PDF, aux mêmes rubriques.
