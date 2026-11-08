# Logement – prévention des expulsions locatives (1 : Service Logement et dossier)

*Novembre 2026. Décisions de Fred (8/11/2026). Première PR d'une série de trois.*

## Qui fait quoi

Aujourd'hui, le **Service Logement (SL)** du Département importe la liste des assignations dans le logiciel actuel, puis envoie à la MDS un PDF par mail (fiche de liaison CD 13 – CAF 13). La MDS va ensuite chercher le dossier dans le module « expulsions » pour le suivre. Dans CID, le SL garde sa partie : centralisation, statistiques, appui aux MDS, relations avec certains bailleurs, suivi avec la préfecture jusqu'au concours de la force publique.

Trois profils pour le SL, attribués dans *Comptes & droits* :

| Profil | Capacités | Peut |
|---|---|---|
| `SL_CADRE` – cadres et adjoint | `expulsion_sl_gestion`, `expulsion_sl_pilotage`, `expulsion_sl_stats` | tout : saisie, affectation, suivi, statistiques, suppression d'un dossier saisi par erreur |
| `SL_AGENT_ADMINISTRATIF` – agents administratifs | `expulsion_sl_gestion` | saisir et suivre les dossiers de tous les territoires, les affecter aux MDS |
| `SL_SECRETARIAT` – secrétariat | `expulsion_sl_stats` | lire les statistiques départementales (pour l'instant) |

Le SL n'a **pas** accès aux dossiers des usagers (pas de `peut_voir`) : c'est la MDS qui rattache le dossier d'expulsion à l'usager.

Côté MDS :
- les agents qui ont `peut_voir` voient les dossiers de leur MDS ;
- avec `peut_modifier`, ils complètent la fiche, saisissent la décision, ajoutent des étapes, rattachent l'usager et clôturent ;
- le cadre (`peut_valider`) désigne le référent ; un travailleur social (`peut_instruire`) peut se désigner lui-même ;
- une MDS peut aussi ouvrir un dossier qu'elle a repéré (origine « Repéré par la MDS »).

## Le dossier (`logement/models/m_expulsion.py`)

`DossierExpulsion` reprend la **fiche de liaison** rubrique par rubrique :
- dossier n° (`EXP-AAAA-NNNN`) et date ;
- locataire et colocataire, adresse ;
- propriétaire et type de bailleur ;
- date de signature du bail, loyer total, loyer, charges ;
- dette réclamée et sa date ;
- observations CAF (fiche CAF, service social CAF, non identifié, retour le, association, CCAS) et n° allocataire ;
- tribunal, date et heure de l'audience ;
- décision du tribunal, en cases à cocher : présence, provisions et montant, suspension de la clause résolutoire, accord de délai 12 / 24 mois / autre, résiliation, expulsion, délais de paiement, délais pour quitter les lieux, rejet.

La **fiche CAF** « Prévention de l'expulsion domiciliaire » est stockée en JSON (`caf`), avec ses rubriques : identification, situation familiale et professionnelle, ressources, prestations, logement, FSL, commentaire. On peut ainsi ajouter une rubrique sans migration.

`EtapeExpulsion` tient le **journal de la procédure** : signalement, commandement de payer, assignation, DSF transmis, audience, jugement, signification, plan d'apurement, commandement de quitter les lieux, demande de CFP, commission préfectorale, CFP accordé, expulsion, relogement, autre.

Chaque étape a une date, une échéance éventuelle et un commentaire.
- **Échéances proposées** quand le champ est laissé vide : commandement de payer → 6 semaines ; commandement de quitter les lieux → 2 mois. Elles restent modifiables.
- Une échéance s'affiche dans « À faire » 15 jours avant, jusqu'à ce qu'elle soit marquée traitée.
- **Trêve hivernale** (1er novembre – 31 mars) : un bandeau s'affiche dans la liste et sur les dossiers au stade du commandement de quitter les lieux ou du CFP.

**Alertes** (`alertes()`) :
- dossier à affecter ;
- référent à désigner ;
- audience dans les 30 jours ;
- audience passée sans décision saisie ;
- échéance proche.

## Notifications (messagerie de CID)

- Affectation ou réaffectation par le SL → le **responsable de la MDS** est prévenu. Ce message remplace le PDF envoyé par mail.
- Référent désigné → le **référent** est prévenu.
- Décision saisie ou dossier clos par la MDS → les **agents du SL** sont prévenus.

## PDF

**Fiche de liaison PDF** (`logement/services/expulsion_pdf.py`) : la page 1 reprend la fiche de liaison, la page 2 la fiche CAF.
- Les fiches de liaison et CAF sont des documents locaux (CD 13 / CAF 13). CID produit une trame avec les mêmes rubriques ; aucune fiche réelle n'est publiée.
- Les coordonnées du SL imprimées sur la fiche viennent du paramètre `SERVICE_LOGEMENT_COORDONNEES` (*Admin → Configuration*), jamais du code.

## Formulaires et courriers (règle retenue)

- **Formulaires nationaux** (Cerfa du diagnostic social et financier) : documents publics, livrés avec CID.
- **Courriers** (convocations, relances, actualisation) : modèles en administration, modifiables par territoire.
- **Fiches locales** (fiche de liaison, fiche CAF, questionnaire bailleur, bordereau de carence) : déposées en administration. Sinon CID produit une trame.

## Statistiques

*Expulsions → Statistiques* :
- dossiers en cours et clos ;
- dossiers à affecter, référent à désigner, audiences dans les 30 jours ;
- dette moyenne ;
- répartition par MDS, par étape (dernière étape saisie), par origine, par motif de clôture.

Le SL et son secrétariat voient tout le Département ; une MDS voit ses dossiers. **Aucun chiffre par agent.**

## Suite

- **PR B** :
  - convocations avec suivi « venu / pas venu » ;
  - DSF prérempli (Cerfa) et questionnaire bailleur, ou bordereau de carence ;
  - visa du cadre en un clic ;
  - envoi par mail au greffe du tribunal (adresse paramétrable) et à la préfecture (boîte de la responsable). Fini le circuit imprimer, signer, scanner.
- **PR C** :
  - CAPEX locale (Martigues / Port-de-Bouc) et commission préfectorale : séances, ordre du jour, avis ;
  - statistiques complétées ;
  - passerelles vers FSL maintien, COPP et logement social.

Import de la liste des assignations : CID ne reçoit pas le fichier aujourd'hui (le SL l'importe dans le logiciel actuel). Un import pourra être ajouté quand le format sera connu (en-têtes seulement, jamais de données réelles).
