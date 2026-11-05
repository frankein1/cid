<!-- docs/INSERTION.md -->
# Module RSA – Insertion

Menu **Accompagnement → RSA – Insertion**. Étape 1 : pôles insertion et référentiel des actions d'insertion. Étape 2 : le contrat, son circuit et la file active. Étape 3 : les prescriptions. Étape 4 : la commission de réorientation. Étape 5 : la file active et les statistiques. Les comités de suivi technique et le suivi des heures d'activité restent à préciser.

## Pôles insertion

Administration (/admin/) → **Pôles insertion** : code, nom, coordonnées, **MDS rattachées**, **agents du pôle**, adresse MSSanté du médecin du pôle (messagerie sécurisée de santé, pour les certificats médicaux des contrats santé ; vide = pli cacheté).

Profils des agents (module RSA uniquement : ni dossiers sociaux, ni IP, ni aides financières) :

| Profil | Capacités |
|---|---|
| Pôle insertion – administratif | `rsa_pole_admin`, `rsa_referentiel` |
| Pôle insertion – cadre | `rsa_pole_cadre`, `rsa_referentiel`, `peut_voir_stats` |
| Pôle insertion – médecin | `rsa_pole_medecin` |

Les cadres de MDS ont `rsa_actions_locales` : ils créent les actions locales de leur MDS.

## Référentiel des actions

- **Actions départementales** : gérées par les pôles insertion et l'administration (`rsa_referentiel`) ; tout le département ou certains pôles.
- **Actions locales** : créées par une MDS, pour son territoire.
- Chaque action est rattachée à un **type commun** (Administration → Types d'actions d'insertion ; créés par `python manage.py init_insertion`), pour des statistiques comparables entre MDS.
- Rien n'est supprimé : une action qui s'arrête passe « inactive ».

Qui voit quoi : les actions départementales sont visibles de tous les agents du module ; les actions locales, des agents de la MDS et des pôles insertion qui la couvrent.

## Import et export CSV

Bouton **Importer (CSV)** : télécharger le **fichier modèle**, le remplir dans un tableur, l'enregistrer en CSV (séparateur point-virgule), le déposer. CID affiche les créations, mises à jour et erreurs **avant** d'enregistrer ; les lignes en erreur sont ignorées.

| Colonne | Contenu |
|---|---|
| `code` | obligatoire, propre à CID (ex. ACCGLO) ; clé de l'action (avec la MDS pour une action locale) |
| `libelle` | obligatoire |
| `type` | code (ou libellé) d'un type d'action |
| `niveau` | DEPARTEMENTAL ou LOCAL |
| `mds` | code de la MDS (actions locales) |
| `poles` | codes des pôles séparés par des virgules ; vide = tout le département |
| `territoire`, `porteur`, `public_vise`, `duree`, `rythme_comite`, `description` | texte libre |
| `destinataires`, `pieces_a_joindre` | valeurs séparées par des virgules |
| `comite_suivi`, `aussi_logement`, `actif` | oui / non (`actif` vide = oui) |

Une ligne dont le code existe déjà met l'action à jour : l'export (bouton **Exporter**) se modifie et se réimporte. Chaque ligne est contrôlée avec les droits de la personne qui importe.

La liste réelle des actions d'un département ne se met pas dans le dépôt de code : elle s'importe sur son serveur.

## Le contrat (étape 2)

Fiche du bénéficiaire → **Parcours RSA** (contrats et prescriptions) (agents de la MDS du bénéficiaire). Le nom du contrat s'affiche partout tel qu'il est réglé en administration.

**Rédaction (référent)** : type **ouverture**, **prolongement** ou **rétablissement** (après une suspension ; une radiation impose une nouvelle demande CAF, donc une ouverture), nature (social, emploi, santé, logement), rubriques de l'imprimé départemental (conjoint, diagnostic, incidence financière, parole du bénéficiaire, objectifs et étapes du référent, actions, aide aux transports, engagements, signature). Le conjoint, les enfants et l'identifiant France Travail viennent de la fiche ; un prolongement reprend le diagnostic et les actions en cours du dernier contrat validé.

**Circuit** :

```
En préparation ──(référent : transmettre)──▶ Transmis au pôle ──(administratif : réceptionner)──▶ Reçu
     ▲                                                                                        │
     └──── Ajourné ◀──(cadre : commission)── Validé · Validé sauf action · Non validé ◀───────┘
```

- La transmission est refusée s'il manque la signature, l'accord du bénéficiaire, les objectifs, une action, ou (contrat santé) le mode de transmission du certificat.
- **Validé** : début et durée (1 à 12 mois, réglable) ; CID calcule la fin. **Validé sauf action** : l'action non retenue et son motif ; durée imposée de 3 mois (réglable). **Ajourné** / **non validé** : motif obligatoire ; l'ajourné revient modifiable chez le référent.
- Aide aux transports demandée (urbain, interurbain) : accordée ou refusée, motif (dérogation, durée maximale déjà accordée, conditions non remplies).
- Chaque étape est tracée (historique du contrat) et prévient la personne suivante par la messagerie. Les messages aux agents du pôle ne sont pas liés à la fiche du bénéficiaire (ils n'ont pas accès au dossier social).

**Contrat santé** (moins de 60 ans, réglable) : le médecin traitant adresse un certificat au **seul médecin du pôle**, sous pli cacheté ou par MSSanté (adresse du pôle). CID imprime la demande de certificat à remettre au bénéficiaire, puis n'enregistre que la date de réception, l'avis **favorable / défavorable** et une motivation **sans détail médical**. La commission ne peut valider qu'après l'avis.

**File active** (RSA – Insertion → Contrats et file active) : onglets *À traiter* (selon le rôle : réceptionner, avis, décider, reprendre un ajourné), *En vigueur*, *À renouveler* (fin dans les 30 jours, réglable, sans contrat suivant), *Échus sans renouvellement*, *Validés sauf action*, *En préparation*. Les agents d'un pôle voient les contrats des MDS de leur pôle ; les agents d'une MDS, ceux de leur MDS.

**Documents** : contrat imprimé (PDF, à signer ; la décision y figure une fois prise), demande de certificat au médecin traitant, notification de la décision au bénéficiaire. Les deux courriers sont des **modèles de courriers** (`RSA_CERTIFICAT_MEDECIN`, `RSA_NOTIFICATION_DECISION`) : leurs textes par défaut sont génériques ; le texte officiel se saisit (ou s'importe) en administration, jamais dans le dépôt.

**Paramètres du contrat RSA** (Admin → RSA – Insertion → Paramètres du contrat) : nom du contrat, durée proposée par défaut, durée maximale, durée d'un « validé sauf action », délai d'alerte de renouvellement, heures d'activité hebdomadaires minimales, âge limite du certificat médical.

| Rôle | Peut |
|---|---|
| Agent de la MDS (`peut_creer`) | rédiger, transmettre, annuler, renouveler ; imprimer contrat, demande de certificat, notification |
| Pôle – administratif (`rsa_pole_admin`) | réceptionner |
| Pôle – médecin (`rsa_pole_medecin`) | donner l'avis sur les contrats santé |
| Pôle – cadre (`rsa_pole_cadre`) | décider en commission |

## Les prescriptions (étape 3)

Parcours RSA du bénéficiaire → **Nouvelle prescription** : choix d'une action (départementales du pôle, locales de la MDS), puis la fiche de liaison.

- **Tronc commun prérempli** (dossier et contrat en cours) : situation RSA (socle, majoré), QPV, RQTH, France Travail, qualification, inactivité ; **freins** (liste commune : mobilité, garde d'enfants, langue, logement, famille, santé, finances, démarches administratives, isolement, projet professionnel, recherche d'emploi) ; diagnostic, avis motivé, objectifs ; orientation demandée par la personne ou proposée par le travailleur social ; pièces fournies ; **consentement** à la transmission (obligatoire).
- **Questions propres à l'action** : définies sur la fiche de l'action (« Modifier les questions ») par ceux qui gèrent l'action. Types : texte, oui / non, un choix, plusieurs choix, date, nombre ; obligatoire ou non ; **accès restreint** (réponse visible des agents de la MDS du bénéficiaire, du cadre et du médecin du pôle, jamais de l'administratif ; aucun détail médical).
- **Circuit** :

```
En préparation ──(prescripteur : adresser)──▶ [À valider par le pôle ──▶ Refusée]
                                             ──▶ Adressée au porteur ──▶ Intégrée ──▶ Terminée · Arrêtée · Réorientée
                                                                     ├─▶ Non intégrée
                                                                     └─▶ Réorientée
```

  Le passage par le pôle dépend de l'action (case « Prescription validée par le pôle insertion », colonne CSV `validation_pole`) ; l'administratif ou le cadre du pôle valide ou refuse (motif). Le **retour du porteur** (premier rendez-vous, diagnostic finalisé, intégration, sortie, réorientation vers l'ASI, un autre dispositif ou France Travail) est noté par le prescripteur ou par l'administratif du pôle. Messages automatiques au prescripteur ou au pôle ; historique.
- **Tableau des actions du contrat** : la prescription est rattachée au contrat en préparation ou en vigueur ; une fois adressée au porteur, la ligne de l'action s'y ajoute (ou reprend la ligne existante de la même action), et son entrée, sa sortie et son motif suivent le retour du porteur. Dans la rédaction du contrat, ces lignes ne se saisissent pas.
- **Fiche de liaison (PDF)** à signer et à adresser au porteur, avec un cadre « retour du porteur » à compléter.
- Le pôle ne voit ni les contrats ni les prescriptions **en préparation** (consentement pas encore recueilli).
- Liste RSA – Insertion → **Prescriptions** : à traiter (pôle : à valider ; prescripteur : refusées), en attente du porteur, en cours, sorties, en préparation.

| Rôle | Peut |
|---|---|
| Agent de la MDS (`peut_creer`) | prescrire, adresser, annuler, noter le retour du porteur, imprimer |
| Pôle – administratif (`rsa_pole_admin`) | valider ou refuser, noter le retour du porteur |
| Pôle – cadre (`rsa_pole_cadre`) | valider ou refuser ; voit les réponses à accès restreint |
| Pôle – médecin (`rsa_pole_medecin`) | consulter ; voit les réponses à accès restreint |

## La commission de réorientation (étape 4)

Tous les trimestres, la commission du pôle (un membre de chaque MDS, administratifs et cadres du pôle) réoriente des bénéficiaires vers **France Travail** (remise sur le marché de l'emploi), la **CAF** (par exemple à la première naissance) ou une **association** : l'organisme retenu devient leur référent RSA.

- **Demande** (référent, sans validation du cadre de MDS) : Parcours RSA → *Demander une réorientation* : situation, freins (repris de la dernière prescription), **motif** et **orientation proposée** (obligatoires), organisme proposé, précision, avis de la personne. *Inscrire en commission* : la demande rejoint la prochaine commission programmée du pôle, ou attend la suivante.
- **Commission** (RSA – Insertion → Réorientation, administratifs et cadres du pôle) : programmation (date, heure, lieu) — les demandes en attente sont inscrites d'office ; ordre du jour par MDS (PDF) ; participants (agents du pôle et des MDS du pôle, autres participants) ; décision par dossier : **acceptée** (organisme retenu, date d'effet), **refusée** ou **ajournée** (motif) ; retrait d'un dossier (commission suivante) ; **clôture** : les référents sont prévenus, les ajournées passent à la commission suivante ; relevé de décisions (PDF, une ligne par dossier examiné, `ExamenReorientation`).
- **Effet** : à la date d'effet d'une réorientation acceptée, la personne sort de la file active RSA de la MDS (plus d'alerte « à renouveler », « échu » ou « validé sauf action ») ; bandeau sur son parcours RSA ; l'historique reste consultable.
- **Notification au bénéficiaire** : modèle de courrier `RSA_NOTIFICATION_REORIENTATION` (texte générique, modifiable en administration).
- **Organismes de réorientation** (RSA – Insertion → Réorientation → Organismes, ou menu Admin) : France Travail et la CAF créés par `init_insertion` ; les associations s'ajoutent dans CID (pôles, `rsa_referentiel`).
- Le pôle ne voit pas les demandes en préparation ; le médecin du pôle ne voit pas les réorientations.

**Comités de suivi technique (CST)** : non développés, faute d'information sur leur fonctionnement (à préciser avec le pôle insertion).

## File active et statistiques (étape 5)

Aucune saisie supplémentaire : tout vient des contrats, des prescriptions et des réorientations (`insertion/services/statistiques.py`).

- **Périmètre** : super-administrateur → tout le département ; agent d'un pôle → les MDS du pôle ; cadre de MDS (`rsa_actions_locales`) → ses MDS ; référent → sa file active (contrats dont il est le référent, prescriptions et réorientations qu'il a faites).
- **File active** (RSA – Insertion → File active) : personnes qui ont un contrat (hors annulé) ou une prescription adressée, sauf celles réorientées depuis la date d'effet (filtre « Personnes réorientées » pour les voir). Une ligne par personne : contrat en vigueur (sinon le dernier), échéance, actions en cours, alertes (sans contrat en vigueur, à renouveler, échu, validé sauf action, en cours de validation, ajourné, réorientation inscrite). Filtres : recherche, MDS, référent, commune, nature, alerte.
- **Statistiques** (période, MDS) : file active, **taux de contractualisation** (contrat en vigueur / file active), alertes, comparaison par MDS, contrats établis par type, nature des contrats en vigueur, décisions de la commission, aide aux transports, contrats santé (avis), délais moyens (transmission → réception → décision), prescriptions par action et **taux d'intégration** (intégrées / (intégrées + non intégrées)), freins, sorties d'action, réorientations (décisions, vers qui, ajournements).
- **Export CSV** : séparateur « ; », UTF-8 avec BOM (LibreOffice, Excel, autres outils). File active : une ligne par personne, filtres compris. Statistiques : une liste « section ; libellé ; nombre ; part ».
- **Non fait** : suivi des heures d'activité (à voir avec le nouveau DAPE), statistiques par commune ou par âge.

## Remise à zéro (démonstration)

La remise à zéro totale conserve les paramètres du contrat, les types d'actions, les actions départementales et leurs questions, les organismes de réorientation (sans leurs liens vers les pôles, MDS et partenaires, recréés ensuite) ; les actions locales disparaissent avec leur MDS.
