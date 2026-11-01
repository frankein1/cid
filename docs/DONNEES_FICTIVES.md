<!-- docs/DONNEES_FICTIVES.md -->
# Données fictives de CID : comptes, familles et dossiers de test

Toutes les personnes, adresses, numéros et montants ci-dessous sont **inventés**. Les montants sont des exemples : ils ne reprennent pas la note de service.

## Créer ou recréer le jeu de données

| Commande | Effet |
|---|---|
| `python manage.py init2` | Comptes de base, MDS TEST 01, familles MONOP, RECOMP, CLASSIC, identités du bac à sable API Particulier, une IP. |
| `python manage.py init_demo` | Tout le reste (voir ci-dessous). Lance `init2` si besoin. Ne fait rien si le jeu existe déjà. |
| `python manage.py init_demo --reinitialiser` | Supprime les dossiers de démonstration (aides, IP, rendez-vous, messages liés) et les recrée avec des dates recalculées à partir d'aujourd'hui. Les comptes et les familles sont conservés. |
| Menu **Planning → Administration → Données de démonstration** (super-administrateur) | Même effet que `init_demo --reinitialiser`, depuis CID : pour Render gratuit, qui n'a pas d'accès au shell. |

Sur Render, `render_start.py` lance `init2` puis `init_demo` à chaque démarrage : le jeu est créé au premier démarrage, puis laissé tel quel.

**Les dates bougent avec le temps.** Elles sont calculées le jour de la création : une AFASE « à décider sous 10 jours » finit par dépasser son délai. Pour retrouver les situations décrites ici : sur Render, menu **Données de démonstration** (super-administrateur) ; en local, `python manage.py init_demo --reinitialiser`.

## Comptes de test

**Mot de passe :** celui de la variable d'environnement `DEMO_PASSWORD` si elle est définie au moment de la création du compte, sinon `testpass123`.
⚠️ Le dépôt est public : sur une instance accessible depuis Internet, définissez `DEMO_PASSWORD` sur Render, ou changez ces mots de passe.

| Identifiant | Nom affiché | Profil | MDS | Sert à tester |
|---|---|---|---|---|
| `asmith` | Agent Social 1 | Travailleur social | MDS TEST 01 | Créer et instruire les aides, répondre à un ajournement, évaluer une IP (binôme) |
| `bjones`, `cdubois` | Agent Social 2 et 3 | Travailleur social | MDS TEST 01 | Second membre de binôme IP, travail à plusieurs |
| `MarioB`, `LuigiB` | Agent Admin 1 et 2 | Administratif | MDS TEST 01 | Accueil, réservation de rendez-vous |
| `kchef` | Chef de service | Cadre, **directeur de la MDS TEST 01** | MDS TEST 01 | Décider les AFASE, CAP et régies, recours, binôme IP, visas, statistiques. Reçoit les messages du cadre. |
| `jcadre1` | Cadre MDS 1 | Cadre | MDS TEST 01 | Second cadre (peut aussi décider) |
| `pmi1` | Agent PMI 1 | PMI (protection infantile) | MDS TEST 01 | Binôme IP avec un TS |
| `crip1` | Agent CRIP 1 | CRIP | (départemental) | Saisir une IP et la transmettre à la MDS |
| `pief1` | Inspecteur Enfance famille 1 | Inspecteur enfance-famille | (départemental) | AFASE des familles avec mesure ASE, avis sur les rapports IP |
| `cadre2` | Cadre MDS 2 | Responsable de MDS | MDS TEST 02 | Cloisonnement entre MDS, famille séparée sur deux MDS |
| `ts2` | Agent Social MDS 2 | Travailleur social | MDS TEST 02 | Idem côté travailleur social |
| `uagaf1` | Agent UAGAF 1 | Contrôle des AFASE (UAGAF) | (départemental) | Contrôler un dossier, le renvoyer, enregistrer le paiement |
| `regie1` | Régisseur Central 1 | Régisseur central | (départemental) | Chèques service remis par la paierie, régies d'urgence |

Le **super-administrateur** n'est pas créé ici : `install` le crée avec le mot de passe de la variable `ADMIN_PASSWORD`.

## MDS

- **MDS TEST 01**, Port-de-Bouc : la MDS principale, avec ses salles (init2).
- **MDS TEST 02**, Martigues : une seconde MDS, pour tester ce qu'un agent voit ou ne voit pas d'une autre MDS.

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
| FAM8 | PEREZ Laura | Mère, Noé (hors foyer) et Mila | **Mesure ASE** (assistance éducative) : l'AFASE va à l'inspecteur ; IP en évaluation |
| FAM9 | GARNIER Céline | Mère, 2 enfants | Refus d'AFASE avec **recours en cours** |
| FAM10 | CHERIF Yasmine | Mère, 1 enfant | Refus **réformé** après recours : nouvelle AFASE |
| FAM11 | LEGRAND Thomas | Père veuf, fille de 16 ans | Refus **confirmé** après recours contentieux ; IP reçue par la CRIP |
| FAM12 | AUBERT Aurélie et David | Couple marié, 2 enfants | IP en synthèse ; chèques service à décider |

## AFASE : un dossier à chaque étape du circuit

« J » = jour de création du jeu. Connectez-vous avec le compte indiqué.

| Famille | État | Compte | Ce qu'on peut tester |
|---|---|---|---|
| VIDAL Nolan | Brouillon | `asmith` | Reprendre une saisie, compléter le formulaire jeune majeur |
| AMRANI Sarah | En instruction (budget saisi, évaluation à faire) | `asmith` | Finaliser l'instruction et déposer ; enfant à naître |
| CLASSIC Claire | Déposée (J-3) | `kchef` | Décider : aide à la décision, reste à vivre, motif, montant indicatif |
| RECOMP Sophie | Déposée, **plus que 10 jours** avant les 2 mois | `kchef` | Alerte de délai, rappel au cadre |
| BERNANRD Julien | Déposée, **réputée refusée** (2 mois dépassés) | `kchef` | Bandeau rouge, message au cadre et au TS ; décision expresse à prendre |
| ROUX Kevin | **Ajournée** il y a 5 jours | `asmith` | Compléter et redéposer ; alerte hors 13 |
| MONOP Jean | **Ajournée depuis 20 jours** | `kchef` | Les 15 jours sont dépassés : refus code 1 proposé par défaut |
| BENSALEM Nadia | Accordée (paiement à la famille) | `kchef` | Notification à l'usager, pièces exigées, transmission à l'UAGAF |
| CLASSIC Marc | Transmise au contrôle | `uagaf1` | Contrôler, renvoyer à la MDS ou enregistrer la demande de paiement |
| RECOMP Paul | Paiement demandé (versement à la **cantine**, tiers) | `uagaf1` | Enregistrer le paiement ; notification avec versement à un tiers |
| MONOP Jean | Clôturée, payée (il y a ~4 mois) | `kchef` | Historique des 12 mois, statistiques mensuelles |
| BENSALEM Karim (MDS 2) | Accordée puis **renvoyée par l'UAGAF** (RIB illisible) | `cadre2` | Correction après renvoi ; cloisonnement MDS 2 |
| LALANNE Francis | Refusée, **code 3 avec précision** (« le Fonds d'aide aux jeunes ») | `kchef` | Courrier de refus avec la précision |
| GARNIER Céline | Refusée, **recours gracieux en cours** | `kchef` | Enregistrer l'issue du recours |
| CHERIF Yasmine | Refusée, recours **réformé** → nouvelle AFASE déposée | `kchef` | Décider la nouvelle AFASE (sans délai de 2 mois), joindre la décision sur le recours, courrier « suite à votre recours » |
| LEGRAND Thomas | Refusée, recours **contentieux rejeté** | `kchef` | Pièce facultative sur l'AFASE refusée ; statistiques des recours |
| PEREZ Laura | Déposée, **mesure ASE** | `pief1` | La décision revient à l'inspecteur ; le cadre de MDS ne peut pas décider |

Les textes de refus des codes 1 à 3 sont remplis avec des **textes d'exemple**, seulement s'ils sont vides. Le référentiel complet s'importe depuis **Cadre → Référentiel AFASE** (fichier JSON tiré de la note de service, hors dépôt).

## Chèques service et régie d'urgence

| Famille | Aide | État | Compte |
|---|---|---|---|
| AUBERT Aurélie | Chèques service | Déposée | `kchef` (décider) |
| VIDAL Nolan | Chèques service (40 €) | Accordée, à remettre | `kchef` (remise depuis le coffre) |
| LEGRAND Thomas | Chèques service | Refusée | `kchef` (consultation) |
| AMRANI Sarah | Régie (espèces) | Déposée | `kchef` (décider) |
| GARNIER Céline | Régie (**paiement à un tiers** : pharmacie) | Accordée, transmise à la paierie | `regie1` (verser) |
| CHERIF Yasmine | Régie (espèces) | Versée, clôturée | `regie1`, statistiques |

**Coffre CAP de la MDS TEST 01** : régisseur **Agent Admin 1** (`MarioB`), 26 chèques fictifs au coffre (10 de 10 €, 10 de 20 €, 6 de 30 € : 480 €), numérotés `DEMO-10-0001`, `DEMO-20-0001`… Ils sont recréés à chaque réinitialisation.

## Informations préoccupantes (IP)

| Famille | Statut | Compte | Ce qu'on peut tester |
|---|---|---|---|
| LEGRAND Thomas | **Reçue par la CRIP** (appel au 119), pas encore transmise | `crip1` | Compléter la composition familiale et transmettre à la MDS |
| CLASSIC Marc | Transmise à la MDS (init2) | `kchef` | Désigner le binôme (proposition de CID) |
| PEREZ Laura | En évaluation : binôme Agent Social 1 + PMI, **convocation des parents dans 6 jours** | `asmith` ou `pmi1` | Courriers de convocation, présences, actions, rédaction du rapport |
| AUBERT Aurélie | **En synthèse** : rapport soumis | `kchef`, `asmith` | Visas du cadre et du binôme, transmission à l'inspecteur (`pief1`) |

## Planning

Le premier jour ouvré à partir de J : permanence d'**Agent Social 1** (`asmith`) à la MDS TEST 01, avec 3 rendez-vous réservés (GARNIER, AMRANI, VIDAL) et 2 créneaux libres. La convocation IP de la famille PEREZ (dans 6 jours) apparaît aussi dans l'agenda de la MDS.

## Parcours de test conseillés

1. **Circuit AFASE complet** : `asmith` finalise AMRANI → `kchef` accorde → `kchef` transmet à l'UAGAF → `uagaf1` demande le paiement puis l'enregistre.
2. **Délais** : `kchef` ouvre son tableau de bord (RECOMP Sophie à J-10, BERNANRD réputée refusée, MONOP ajournée échue), puis vérifie ses messages.
3. **Recours** : `kchef` enregistre l'issue du recours GARNIER (réformé) → décide la nouvelle AFASE → courrier de notification.
4. **Deux MDS** : `ts2` peut consulter la fiche d'un usager de la MDS TEST 01 (consultation de tous les usagers), mais pas ses dossiers d'aide ; `cadre2` ne décide que les dossiers de la MDS TEST 02 (BENSALEM Karim), et `kchef` ne voit pas ceux de la MDS TEST 02. La famille BENSALEM est répartie entre les deux MDS.
5. **IP** : `crip1` transmet LEGRAND → `kchef` désigne le binôme → `asmith` convoque → rapport → visas → `pief1` donne son avis.
6. **Statistiques** : `kchef`, page des aides financières (mois par mois, recours) et page des IP.
