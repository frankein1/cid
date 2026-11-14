# Prise de message usager

Document de référence pour le développement. Les textes d'aide sont dans `docs/aide/outils/generer_fiches.py`.

## Règles

- **Qui prend un message** : tout agent connecté, depuis l'annuaire (`beneficiaire:annuaire`), via le bouton « Prendre un message » (`messagerie:nouveau_message_beneficiaire` avec `?prise=1`). Aucun sélecteur d'usager dans la rédaction, aucune liste de tous les usagers.
- **Ce que voit un agent hors MDS** : nom, prénom, date de naissance, ville de résidence, code usager, MDS de rattachement. Il ne peut pas ouvrir la fiche ni transférer le dossier.
- **Visibilité d'un message concernant un usager** (`messagerie/views.py`, `_participe`) : expéditeur, destinataire, copie, ou agent actif rattaché à la MDS de l'usager.
- **Réponse** : seul le destinataire renseigne `issue`, `reponse_texte` et `reponse_le` (action `reponse_usager`). `reponse_le` est fixée une seule fois.
- **Mode de contact** (`mode_contact`, facultatif, liste unique) et **motifs** (`motifs_contact`, plusieurs cases) ne sont enregistrés que pour un message concernant un usager. Les valeurs hors liste sont ignorées.
- **Type de réponse** (`issue`) : courrier, répondeur, injoignable, entretien en présentiel, entretien téléphonique, courriel.

## Listes validées (14/11)

- Modes : courrier, accueil physique, téléphone, courriel.
- Motifs : logement, insertion, aide financière, adulte vulnérable, budget / CESF, réaffectation, autre.

## Demande de réaffectation (motif « Réaffectation »)

- L'agent d'une MDS qui reçoit un usager suivi ailleurs prend un message avec le motif Réaffectation. La MDS demandeuse est mémorisée (`mds_demandeuse`).
- Le message est adressé à un agent de la MDS d'origine ; seul le **cadre** de cette MDS (`peut_gerer_utilisateurs`) décide (`messagerie:decider_reaffectation`).
- **Accepter** : transfert de l'usager et des membres de son foyer cochés (`beneficiaire/transfert.py`, `transferer`), puis réponse à la MDS demandeuse. La demande est close.
- **Refuser** : motif obligatoire, transmis dans la réponse à la MDS demandeuse. La demande est close, l'usager ne bouge pas.
- Une seule décision par demande.
- Non implémenté (à définir) : la feuille de transfert signée par le cadre, jointe au dossier ; l'expurgation des notes personnelles du travailleur social avant envoi.
- Issues : courrier, répondeur, injoignable, entretien en présentiel, entretien téléphonique, courriel.

## Non implémenté

- Bouton de transfert central vers le module adapté depuis les résultats de recherche.
- Avertissement à l'envoi d'une pièce jointe non indexée à la GED.
- Suppression automatique 15 jours après clôture d'un message (avec journalisation).
- Circuits MDS de tri et fusion de doublons (après décision sur l'import SAP).

## Tests

- `messagerie/tests_prise_message.py` : prise de message, visibilité, réponse du destinataire.
- `beneficiaire/tests_annuaire_creation.py` : annuaire et création.
