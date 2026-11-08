# Logement – demande de logement social, commission des publics prioritaires, papier économisé

*Novembre 2026. Décisions de Fred (8/11/2026).*

## Demande de logement social

Encart **Logement** de la fiche usager → **Demande de logement**. La MDS n'aide aux démarches que ponctuellement (Maison France Services), mais le suivi a besoin de :
- numéro unique (NUD) et date de création : CID calcule l'**ancienneté** et prévient 30 jours avant le **renouvellement annuel** ;
- DALO, mutation, Al'In : déposé ou non, date, état ;
- communes souhaitées (6), typologie, étage, logement PMR, précisions.

Il n'existe pas d'API ouverte aux départements pour le SNE ou MonDALO : la saisie est manuelle. Ces données sont reprises dans la saisine de la commission et, plus tard, dans le DSF.

## Commission des publics prioritaires (COPP / CTPP)

C'est un dispositif métropolitain, organisé par territoire (pour Martigues et Port-de-Bouc : la commission du Pays de Martigues). Elle se réunit environ tous les trois mois. **Paramétrable** : un autre département la renomme ou ne l'utilise pas.

- **Séances** : *Admin → Logement → Commissions des publics prioritaires*, avec date, date limite de dépôt, lieu, horaire et MDS concernées. La prochaine séance ouverte est proposée ; une alerte apparaît 7 jours avant la date limite.
- **Saisine** (encart Logement → *Saisine commission des publics prioritaires*). Elle est **préremplie** depuis :
  - le référent et la MDS ;
  - le NUD et son ancienneté ;
  - le demandeur et le conjoint (dont le n° de sécurité sociale de la fiche) ;
  - les enfants ;
  - le logement actuel : loyer, APL, taux d'effort, reste à vivre du budget ;
  - les ressources par personne et les dettes du budget ;
  - la demande de logement : DALO, mutation, Al'In, souhaits.
- **À saisir** : revenu fiscal de référence N-1 et N-2 (CID ne le relève pas), plafonds (PLAI, PLUS…), mesure d'accompagnement en cours (liste issue du guide PDALHPD 13 de 2024, ou saisie libre).
- **Motifs** : plusieurs au choix, avec « autre » à préciser. La liste reste ouverte pour les statistiques :
  - DALO sans décision ou refusé ;
  - expulsion ;
  - sans logement ;
  - sur-occupation ;
  - logement indigne ;
  - logement inadapté ;
  - handicap ou santé ;
  - violences intrafamiliales ;
  - logement trop cher ;
  - séparation.
- **Rapport social** rédigé par le travailleur social.
- **Justificatifs** : on coche ceux de la GED de l'usager ou on en ajoute (mise à jour, remplacement). Ils sont déposés dans la GED (identité, situation familiale ou professionnelle, ressources, avis d'imposition, logement, DALO, autre).
- **PDF** :
  - avec les fiches officielles déposées vierges (*Formulaires officiels → COPP page 1 et page 2*) : CID les remplit à leur place, puis ajoute une page « rapport social » ;
  - sinon, une trame CID avec les mêmes rubriques.
- **Envoi par mail** : le destinataire reste vide (l'adresse dépend du territoire). L'objet est « MDST (ou MDSP) - ville de la MDS - Fiche saisine rapport social et justificatifs pour COPP - NOM Prénom ». La fiche PDF et les pièces cochées sont jointes.
- Après la séance : on enregistre la **décision ou préconisation**.

## Envoi par mail, impression et papier économisé

**Tout dossier passe d'abord par un PDF.** En fin de dossier (FSL visé, saisine COPP prête), deux boutons :
- **Envoi par mail** : destinataire à saisir, objet prérempli, message, pièces de la GED à joindre.
  - Si la messagerie sortante de CID est réglée (variables `EMAIL_*` du serveur), CID envoie lui-même, avec en réponse l'adresse de la MDS.
  - Sinon (cas de la démo), CID prépare le PDF et l'objet ; l'agent envoie depuis sa messagerie puis confirme.
- **Imprimer pour envoi** : seulement si le destinataire l'exige (porteur interne, courrier). Le PDF s'ouvre pour l'impression.

Chaque envoi est compté : nature du dossier, MDS, mode, pages en équivalent A4 (un A3 compte pour deux), pièces jointes comprises.

Menu **Accompagnement → Papier économisé** affiche « nous avons économisé N pages par rapport aux anciens usages ». La page donne aussi les ramettes et les kilos, puis le détail par type de dossier et par MDS.
- **Jamais par agent** : le compteur n'enregistre pas qui envoie (l'historique du dossier, lui, le garde).
- **Pas de coût en euros** : c'est un choix.

## Visa et signature du cadre (FSL)

Toute demande FSL part avec le visa du cadre. En un clic, il appose ses initiales et la date sur le dossier (case du cachet, argumentaire de pièces manquantes). La **signature numérisée** n'est apposée qu'une fois déposée et **validée** : *Admin → MDS → Signatures numérisées*, image PNG ou JPG, case « usage validé ».

## Démo

- **FAM2-SOP** :
  - demande de logement (NUD de démo, DALO en cours, Al'In, à renouveler bientôt) ;
  - saisine COPP en préparation (DALO trop ancien, sur-occupation), pour la séance dans 25 jours ;
  - demande FSL accès envoyée par mail.
- **FAM3-CLA** : DALO refusé, saisine examinée à la séance passée, avec la décision de la commission.
- **FAM5-SAR** : demande énergie envoyée par mail.
- Quatre séances fictives (« Territoire de démonstration »).
