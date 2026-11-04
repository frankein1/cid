<!-- docs/INSERTION.md -->
# Module RSA – Insertion

Menu **Accompagnement → RSA – Insertion**. Étape 1 : pôles insertion et référentiel des actions d'insertion. Étape 2 : le contrat, son circuit et la file active. Les prescriptions, comités de suivi technique, réorientations et statistiques viendront ensuite.

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

Fiche du bénéficiaire → **Contrat RSA** (agents de la MDS du bénéficiaire). Le nom du contrat s'affiche partout tel qu'il est réglé en administration.

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

## Remise à zéro (démonstration)

La remise à zéro totale conserve les paramètres du contrat, les types d'actions et les actions départementales (sans leurs liens vers les pôles, MDS et partenaires, recréés ensuite) ; les actions locales disparaissent avec leur MDS.
