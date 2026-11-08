<!-- docs/DONNEES_FICTIVES.md -->
# Données fictives de CID : comptes, familles et dossiers de test

Toutes les personnes, adresses, numéros et montants ci-dessous sont **inventés**. Les montants sont des exemples : ils ne reprennent pas la note de service.

## Créer ou recréer le jeu de données

| Commande | Effet |
|---|---|
| `python manage.py init2` | Comptes de base, MDS TEST 01, familles MONOP, RECOMP, CLASSIC, identités du bac à sable API Particulier, une IP. |
| `python manage.py init_demo` | Tout le reste (voir ci-dessous). Lance `init2` si besoin. Ne fait rien si le jeu existe déjà. |
| `python manage.py init_demo --reinitialiser` | Supprime les dossiers de démonstration (aides, IP, rendez-vous, messages liés, **documents de la GED des usagers fictifs**, fichiers compris) et les recrée avec des dates recalculées à partir d'aujourd'hui. Les comptes et les familles sont conservés. |
| Menu **Admin → Démonstration → Données de démonstration** (super-administrateur) | Même effet que `init_demo --reinitialiser`, depuis CID : pour Render gratuit, qui n'a pas d'accès au shell. |
| Menu **Admin → Démonstration → Remise à zéro totale** (super-administrateur, **démonstration seulement**) | Vide **toute** la base (comptes, MDS, usagers, dossiers, fichiers de la GED) puis relance `install`, `init2` et `init_demo`. Conserve les super-administrateurs et le paramétrage saisi en administration (référentiel AFASE, motifs de refus, types de danger, configuration). Inactive tant que la variable d'environnement `CID_REMISE_A_ZERO_TOTALE=1` n'est pas définie. **À supprimer avant la mise en service** (`core/remise_a_zero.py`, vue `remise_a_zero_totale`, gabarit, URL et liens du menu). |

Sur Render, `render_start.py` lance `init2` puis `init_demo` à chaque démarrage : le jeu est créé au premier démarrage, puis laissé tel quel.

**Les dates bougent avec le temps.** Elles sont calculées le jour de la création : une AFASE « à décider sous 10 jours » finit par dépasser son délai. Pour retrouver les situations décrites ici : sur Render, menu **Données de démonstration** (super-administrateur) ; en local, `python manage.py init_demo --reinitialiser`.

## Comptes de test

**Mot de passe de tous les comptes de démonstration : `demo123&`** (ou celui de la variable d'environnement `DEMO_PASSWORD`, si elle est définie). Il est remis à chaque création ou réinitialisation du jeu de démonstration ; le super-administrateur n'est jamais concerné.
⚠️ Le dépôt est public : sur une instance accessible depuis Internet, définissez `DEMO_PASSWORD` sur Render, ou changez ces mots de passe.

| Identifiant | Nom affiché | Profil | MDS | Sert à tester |
|---|---|---|---|---|
| `as1_mds1` | Agent Social 1 | Travailleur social | MDS TEST 01 | Créer et instruire les aides, répondre à un ajournement, évaluer une IP (binôme) |
| `as2_mds1`, `as3_mds1` | Agent Social 2 et 3 | Travailleur social | MDS TEST 01 | Second membre de binôme IP, travail à plusieurs |
| `aa1_mds1`, `aa2_mds1` | Agent Admin 1 et 2 | Administratif | MDS TEST 01 | Accueil, réservation de rendez-vous |
| `chef_mds1` | Responsable MDS 1 | Cadre ; fonction **Directeur** (CODIR) de la MDS de territoire TEST 01 | MDS TEST 01, et MDS TEST 02 par le CODIR | Décider les AFASE, CAP et régies, recours, binôme IP, visas, statistiques. Reçoit les messages du cadre. |
| `cadre_mds1` | Cadre MDS 1 | Cadre ; fonction **Adjoint prévention** (CODIR) | MDS TEST 01, et MDS TEST 02 par le CODIR | Second cadre (peut aussi décider) |
| `pmi_mds1` | Agent PMI 1 | PMI (protection infantile) | MDS TEST 01 | Binôme IP avec un TS |
| `crip_c1` | Agent CRIP 1 | CRIP | (départemental) | Saisir une IP et la transmettre à la MDS |
| `ief_p1` | Inspecteur Enfance famille 1 | Inspecteur enfance-famille | (départemental) | AFASE des familles avec mesure ASE, avis sur les rapports IP |
| `chef_mds2` | Cadre MDS 2 | Responsable de MDS ; fonction **Cadre de proximité** | MDS TEST 02 | Pilote les IP de la MDS de proximité ; famille séparée sur deux MDS |
| `as1_mds2` | Agent Social MDS 2 | Travailleur social | MDS TEST 02 | Idem côté travailleur social |
| `uagaf_u1` | Agent UAGAF 1 | Contrôle des AFASE (UAGAF) | (départemental) | Contrôler un dossier, le renvoyer, enregistrer le paiement |
| `regie_r1` | Régisseur Central 1 | Régisseur central | (départemental) | Chèques service remis par la paierie, régies d'urgence |
| `admin_pi1` | Agent Pôle insertion | Pôle insertion – administratif | Pôle insertion de démonstration (MDS TEST 01 et 02) | Réception des contrats ; référentiel des actions : saisie, import et export CSV |
| `cadre_pi1` | Cadre Pôle insertion | Pôle insertion – cadre | Pôle insertion de démonstration | Référentiel des actions ; commission de validation des contrats (plus tard : réorientations) |
| `medecin_pi1` | Médecin Pôle insertion | Pôle insertion – médecin | Pôle insertion de démonstration | Contrats santé : certificat reçu, avis favorable ou défavorable |

Le **super-administrateur** n'est pas créé ici : `install` le crée avec le mot de passe de la variable `ADMIN_PASSWORD`.

## MDS

- **MDS TEST 01**, Port-de-Bouc : **MDS de territoire**, avec ses salles (init2).
- **MDS TEST 02**, Martigues : **MDS de proximité rattachée à MDS TEST 01**. Ses agents ne voient pas les dossiers de MDS TEST 01 ; le CODIR de MDS TEST 01 (`chef_mds1`, `cadre_mds1`) voit les siens.

Logement – FSL (voir `docs/LOGEMENT_FSL.md`) : deux gestionnaires fictifs, sans formulaire officiel (trame CID). FAM5-SAR : demande d'accès en attente de l'avis du cadre (pièces manquantes), demande énergie instruite par `aa1_mds1` et envoyée ; FAM2-SOP : demande d'accès accordée, demande eau en préparation ; FAM3-CLA : concordat en préparation. Demande de logement et commission des publics prioritaires (voir `docs/LOGEMENT_COPP.md`) : FAM2-SOP (saisine en préparation), FAM3-CLA (saisine examinée) ; quatre séances fictives.

Organisation (voir `docs/ORGANISATION_MDS.md`) : la fonction de chaque agent est choisie dans *Gestion des agents de la MDS* ; son intitulé (« Directeur de la MDS de territoire TEST 01 ») est proposé, corrigeable, et repris sous la signature des courriers et PDF. Équipe IP de MDS TEST 01 : `as2_mds1` et `pmi_mds1`.

## Familles

| Code | Famille | Composition | Particularité utile aux tests |
|---|---|---|---|
| FAM1 | MONOP Jean | Père seul, 2 enfants | Famille monoparentale (init2) |
| FAM2 | RECOMP Paul et Sophie | Famille recomposée, 4 enfants, nouvelle compagne | Enfants qui ne vivent pas tous au foyer (init2) |
| FAM3 | CLASSIC Marc et Claire | Couple marié, 3 enfants | Famille « simple » ; une IP transmise à la MDS (init2) |
| API-… | MARTIN, BERNANRD, LALANNE, DUPONT | Identités du bac à sable API Particulier | Seules identités qui répondent au connecteur API Particulier (init2) |
| FAM4 | VIDAL Nolan | Jeune majeur de 19 ans, seul | AFASE « jeune majeur » ; foyer d'une personne |
| FAM5 | AMRANI Sarah | Femme enceinte | AFASE avec **enfant à naître** |
| FAM6 | ROUX Kevin et Romain | Père et fils, à **Avignon (84)** | Alerte « demandeur hors Bouches-du-Rhône » |
| FAM7 | BENSALEM Nadia / Karim | Parents séparés : Nadia et Ilyes à Port-de-Bouc (MDS 1), Karim et Anissa à Martigues (MDS 2) | Famille sur **deux MDS** ; enfants qui ne vivent pas chez les deux parents |
| FAM8 | PEREZ Laura | Mère, Noé (hors foyer) et Mila | **Mesure ASE** (assistance éducative) : l'AFASE va à l'inspecteur ; IP en évaluation, binôme **confirmé par le cadre** alors qu'Agent Social 1 suit la famille (sous-effectif) |
| FAM9 | GARNIER Céline | Mère, 2 enfants | Refus d'AFASE avec **recours en cours** |
| FAM10 | CHERIF Yasmine | Mère, 1 enfant | Refus **réformé** après recours : nouvelle AFASE |
| FAM11 | LEGRAND Thomas | Père veuf, fille de 16 ans | Refus **confirmé** après recours contentieux ; IP reçue par la CRIP ; référent Agent Social 1, **non proposé** pour le binôme |
| FAM12 | AUBERT Aurélie et David | Couple marié, 2 enfants | IP en synthèse (binôme Agent Social 2 + PMI : la référente Agent Social 3 et Agent Social 1 ne sont pas proposés) ; chèques service à décider |

## AFASE : un dossier à chaque étape du circuit

« J » = jour de création du jeu. Connectez-vous avec le compte indiqué.

| Famille | État | Compte | Ce qu'on peut tester |
|---|---|---|---|
| VIDAL Nolan | Brouillon | `as1_mds1` | Reprendre une saisie, compléter le formulaire jeune majeur |
| AMRANI Sarah | En instruction (budget saisi, évaluation à faire) | `as1_mds1` | Finaliser l'instruction et déposer ; enfant à naître |
| CLASSIC Claire | Déposée (J-3) | `chef_mds1` | Décider : aide à la décision, reste à vivre, motif, montant indicatif |
| RECOMP Sophie | Déposée, **plus que 10 jours** avant les 2 mois | `chef_mds1` | Alerte de délai, rappel au cadre |
| BERNANRD Julien | Déposée, **réputée refusée** (2 mois dépassés) | `chef_mds1` | Bandeau rouge, message au cadre et au TS ; décision expresse à prendre |
| ROUX Kevin | **Ajournée** il y a 5 jours | `as1_mds1` | Compléter et redéposer ; alerte hors 13 |
| MONOP Jean | **Ajournée depuis 20 jours** | `chef_mds1` | Les 15 jours sont dépassés : refus code 1 proposé par défaut |
| BENSALEM Nadia | Accordée (paiement à la famille) | `chef_mds1` | Notification à l'usager, pièces exigées, transmission à l'UAGAF |
| CLASSIC Marc | Transmise au contrôle | `uagaf_u1` | Contrôler, renvoyer à la MDS ou enregistrer la demande de paiement |
| RECOMP Paul | Paiement demandé (versement à la **cantine**, tiers) | `uagaf_u1` | Enregistrer le paiement ; notification avec versement à un tiers |
| MONOP Jean | Clôturée, payée (il y a ~4 mois) | `chef_mds1` | Historique des 12 mois, statistiques mensuelles |
| BENSALEM Karim (MDS 2) | Accordée puis **renvoyée par l'UAGAF** (RIB illisible) | `chef_mds2` | Correction après renvoi ; cloisonnement MDS 2 |
| LALANNE Francis | Refusée, **code 3 avec précision** (« le Fonds d'aide aux jeunes ») | `chef_mds1` | Courrier de refus avec la précision |
| GARNIER Céline | Refusée, **recours gracieux en cours** | `chef_mds1` | Enregistrer l'issue du recours |
| CHERIF Yasmine | Refusée, recours **réformé** → nouvelle AFASE déposée | `chef_mds1` | Décider la nouvelle AFASE (sans délai de 2 mois), joindre la décision sur le recours, courrier « suite à votre recours » |
| LEGRAND Thomas | Refusée, recours **contentieux rejeté** | `chef_mds1` | Pièce facultative sur l'AFASE refusée ; statistiques des recours |
| PEREZ Laura | Déposée, **mesure ASE** | `ief_p1` | La décision revient à l'inspecteur ; le cadre de MDS ne peut pas décider |

Les textes de refus des codes 1 à 3 sont remplis avec des **textes d'exemple**, seulement s'ils sont vides. Le référentiel complet s'importe depuis **Cadre → Référentiel AFASE** (fichier JSON tiré de la note de service, hors dépôt).

## Chèques service et régie d'urgence

| Famille | Aide | État | Compte |
|---|---|---|---|
| AUBERT Aurélie | Chèques service | Déposée | `chef_mds1` (décider) |
| VIDAL Nolan | Chèques service (40 €) | Accordée, à remettre | `chef_mds1` (remise depuis le coffre) |
| LEGRAND Thomas | Chèques service | Refusée | `chef_mds1` (consultation) |
| AMRANI Sarah | Régie (espèces) | Déposée | `chef_mds1` (décider) |
| GARNIER Céline | Régie (**paiement à un tiers** : pharmacie) | Accordée, transmise à la paierie | `regie_r1` (verser) |
| CHERIF Yasmine | Régie (espèces) | Versée, clôturée | `regie_r1`, statistiques |

**Coffre CAP de la MDS TEST 01** : régisseur **Agent Admin 1** (`aa1_mds1`), 26 chèques fictifs au coffre (10 de 10 €, 10 de 20 €, 6 de 30 € : 480 €), numérotés `DEMO-10-0001`, `DEMO-20-0001`… Ils sont recréés à chaque réinitialisation.

## Informations préoccupantes (IP)

| Famille | Statut | Compte | Ce qu'on peut tester |
|---|---|---|---|
| LEGRAND Thomas | **Reçue par la CRIP** (appel au 119), pas encore transmise | `crip_c1` | Compléter la composition familiale et transmettre à la MDS |
| CLASSIC Marc | Transmise à la MDS (init2) | `chef_mds1` | Désigner le binôme (proposition de CID) |
| PEREZ Laura | En évaluation : binôme Agent Social 1 + PMI, **convocation des parents dans 6 jours** | `as1_mds1` ou `pmi_mds1` | Courriers de convocation, présences, actions, rédaction du rapport |
| AUBERT Aurélie | **En synthèse** : rapport soumis | `chef_mds1`, `as1_mds1` | Visas du cadre et du binôme, transmission à l'inspecteur (`ief_p1`) |

## RSA – Insertion

Menu **Accompagnement → RSA – Insertion**. Un **pôle insertion de démonstration** (`PI-DEMO`) couvre MDS TEST 01 et 02 ; ses trois agents (`admin_pi1`, `cadre_pi1`, `medecin_pi1`) n'ont accès qu'à ce module.

Cinq actions fictives : trois départementales (accompagnement global, plateforme mobilité limitée au pôle de démonstration, parcours santé) et deux locales de MDS TEST 01 (atelier insertion des femmes, atelier bricolage et logement). Les 16 types d'actions sont créés par `python manage.py init_insertion` (lancé par `install`).

Contrats fictifs, tous préparés par **Agent Social 1** (`as1_mds1`), à chaque étape du circuit :

| Bénéficiaire | Contrat | À tester avec |
|---|---|---|
| PEREZ Laura | En préparation (emploi), incomplet | `as1_mds1` : compléter, signer, transmettre |
| GARNIER Céline | **Santé**, transmis au pôle, certificat sous pli | `admin_pi1` réceptionne ; `medecin_pi1` donne l'avis ; `cadre_pi1` décide |
| BENSALEM Nadia | Reçu au pôle, en attente de commission (deux actions) | `cadre_pi1` : validé, validé sauf action, ajourné ou non validé |
| AUBERT Aurélie | **Ajourné** (logement) | `as1_mds1` : le reprendre et le transmettre de nouveau |
| LEGRAND Thomas | Validé sauf action, en vigueur (3 mois) | Fiche du contrat, notification |
| AMRANI Sarah | Validé, **à renouveler** (fin dans environ 20 jours), aide aux transports accordée | `as1_mds1` : préparer le prolongement |
| ROUX Kevin | Validé, **échu** depuis une dizaine de jours, sans suite | File active, onglet « Échus » |
| CHERIF Yasmine | Aucun contrat | `as1_mds1` : premier contrat (ouverture) |

Questions propres aux actions fictives : plateforme mobilité (permis de conduire, obligatoire ; besoins de mobilité, plusieurs choix), parcours santé (grille d'aide à la décision santé, obligatoire et **à accès restreint** ; l'action **passe par le pôle**), atelier insertion des femmes (garde d'enfants, obligatoire ; nombre d'enfants).

Prescriptions fictives (prescriptrice : `as1_mds1`) :

| Bénéficiaire | Prescription | À tester avec |
|---|---|---|
| PEREZ Laura | Plateforme mobilité, **en préparation** (sans consentement) | `as1_mds1` : compléter, adresser ; la ligne s'ajoute au contrat en préparation |
| GARNIER Céline | Parcours santé, **à valider par le pôle** | `admin_pi1` ou `cadre_pi1` : valider ou refuser ; `admin_pi1` ne voit pas la réponse restreinte, `medecin_pi1` la voit |
| AUBERT Aurélie | Parcours santé, **refusée** par le pôle | `as1_mds1` : onglet « À traiter » |
| BENSALEM Nadia | Atelier, **adressée au porteur**, en attente d'intégration | `admin_pi1` ou `as1_mds1` : noter le premier rendez-vous et l'intégration |
| LEGRAND Thomas | Atelier, **intégrée** (en cours) | `as1_mds1` : noter la sortie ; voir la ligne du contrat |
| AMRANI Sarah | Accompagnement global, **intégrée** | Ligne du contrat tenue à jour |
| ROUX Kevin | Plateforme mobilité, **terminée** (permis obtenu) | Onglet « Sorties » |
| CHERIF Yasmine | Aucune | `as1_mds1` : première prescription |

Réorientation (organismes : France Travail, CAF, « Association d'accompagnement Exemple (fictif) ») :

| Bénéficiaire | Demande | À tester avec |
|---|---|---|
| BENSALEM Karim (MDS 2) | **Acceptée** vers France Travail par la commission passée (il y a 70 jours), effective : sort de la file active | `as1_mds2` : bandeau sur son parcours RSA |
| GARNIER Céline | **Refusée** par la commission passée | Relevé de décisions de la commission passée |
| LEGRAND Thomas | **Ajournée** une fois, inscrite à la prochaine commission (dans 21 jours) | `admin_pi1`, `cadre_pi1` : décider, clôturer |
| AMRANI Sarah | Inscrite à la prochaine commission (France Travail) | idem |
| BENSALEM Nadia | Inscrite à la prochaine commission (CAF, naissance à venir) | idem |
| AUBERT Aurélie | **En préparation** (association), motif à écrire | `as1_mds1` : compléter, inscrire |

À tester : `chef_mds1` crée une action locale (pas d'action départementale) ; `as1_mds1` consulte seulement ; `admin_pi1` télécharge le fichier modèle CSV, importe, voit l'aperçu (créations, mises à jour, erreurs) avant d'enregistrer, et exporte. La remise à zéro totale conserve les paramètres du contrat, les types, les actions départementales et leurs questions, les organismes de réorientation.

## Points d'attention

Cases à cocher de la fiche usager (rubrique « Points d'attention » de la modification), affichées en bandeau en haut de la fiche pour tous les agents : **personne vulnérable** (GARNIER Céline), **rupture familiale** (VIDAL Nolan), **VFF** – violences faites aux femmes (AUBERT Aurélie).

## PMI

Mila PEREZ (4 ans) et Adam CHERIF (3 ans) ont un **n° de dossier PMI** fictif (`PMI-DEMO-0001`, `PMI-DEMO-0002`) : il renvoie au logiciel de la PMI, où reste le suivi médical. Il s'affiche sur la fiche et se cherche avec le champ « identifiant » de la liste des bénéficiaires.

## Planning

Le premier jour ouvré à partir de J : permanence d'**Agent Social 1** (`as1_mds1`) à la MDS TEST 01, avec 3 rendez-vous réservés (GARNIER, AMRANI, VIDAL) et 2 créneaux libres. Une semaine plus tard, même permanence avec 5 créneaux libres : de quoi tester « Prendre rendez-vous » depuis une fiche usager (CID propose les créneaux de J+2 à J+17). La convocation IP de la famille PEREZ (dans 6 jours) apparaît aussi dans l'agenda de la MDS.

## Archivage RGPD

Trois dossiers fictifs de la MDS TEST 01, sans aucune activité depuis longtemps :
- FERRAND Hugo et OUALI Yasmine sont **proposés à l'archivage** (Cadre → Archivage RGPD) ;
- MARCHETTI Odile est **archivée depuis 14 mois** : masquée dans CID, elle apparaît dans « Dossiers archivés » et, pour l'administrateur, dans **Effacement définitif**.

## Jeu « présentation » (statistiques)

30 familles fictives de plus (codes `PRES01-A` à `PRES30-…`), créées par `core/demo_presentation.py` à chaque
réinitialisation, toujours identiques (tirage au sort à graine fixe) :
- 20 familles à la MDS TEST 01 (Port-de-Bouc, Fos-sur-Mer, Saint-Mitre-les-Remparts), 10 à la MDS TEST 02 (Martigues,
  Lavéra, Saint-Victoret) ; familles monoparentales, couples avec ou sans enfants, personnes seules, personnes âgées ;
- environ 150 entretiens depuis le 1er janvier (quelques-uns l'année précédente), par les agents des deux MDS, avec types
  d'accompagnement (dont RSA, quelques MASP, suivis de mesure et violences intrafamiliales), orientations vers des
  partenaires fictifs et suites à donner (certaines en retard) ;
- une trentaine de budgets du foyer (impayés d'énergie ou de loyer, dettes) ;
- une quinzaine de séances d'ateliers passées, avec présences, liste d'attente et quelques personnes extérieures.

But : montrer les **statistiques de l'accompagnement** avec des effectifs au-dessus du secret statistique.

## Parcours de test conseillés

1. **Circuit AFASE complet** : `as1_mds1` finalise AMRANI → `chef_mds1` accorde → `chef_mds1` transmet à l'UAGAF → `uagaf_u1` demande le paiement puis l'enregistre.
2. **Délais** : `chef_mds1` ouvre son tableau de bord (RECOMP Sophie à J-10, BERNANRD réputée refusée, MONOP ajournée échue), puis vérifie ses messages.
3. **Recours** : `chef_mds1` enregistre l'issue du recours GARNIER (réformé) → décide la nouvelle AFASE → courrier de notification.
4. **Deux MDS** : `as1_mds2` peut consulter la fiche d'un usager de la MDS TEST 01 (consultation de tous les usagers), mais pas ses dossiers d'aide ; `chef_mds2` ne décide que les dossiers de la MDS TEST 02 (BENSALEM Karim), et `chef_mds1` ne voit pas ceux de la MDS TEST 02. La famille BENSALEM est répartie entre les deux MDS.
5. **IP** : `crip_c1` transmet LEGRAND → `chef_mds1` désigne le binôme → `as1_mds1` convoque → rapport → visas → `ief_p1` donne son avis.
6. **Statistiques** : `chef_mds1`, page des aides financières (mois par mois, recours) et page des IP.
7. **Archivage RGPD** : `chef_mds1` archive FERRAND Hugo (Cadre → Archivage RGPD) → la fiche disparaît de la liste et de la recherche → il la consulte dans « Dossiers archivés » et la désarchive ; l'administrateur efface MARCHETTI Odile (Admin → Archivage RGPD → Effacement définitif, en tapant EFFACER).
8. **Présentation des statistiques** : `chef_mds1`, Accompagnement → Statistiques de l'accompagnement → « Rapport annuel 2026 » (détail par agent) ; un administrateur voit la comparaison des deux MDS.
9. **IP et professionnel qui suit la famille** : `chef_mds1`, IP de FAM11 (Thomas LEGRAND) → bloc « Binôme » : Agent Social 1, référent de la famille, n'est pas proposé ; « Désigner quand même… » pour passer outre. IP de FAM8 : binôme confirmé par le cadre, motif affiché.

Chaque famille de démonstration a une AS référente (référent MDS), répartie entre les agents de sa MDS.
