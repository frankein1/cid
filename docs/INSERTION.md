<!-- docs/INSERTION.md -->
# Module RSA – Insertion

Menu **Accompagnement → RSA – Insertion**. Étape 1 : pôles insertion et référentiel des actions d'insertion. Les contrats, prescriptions, comités de suivi technique et la file active viendront ensuite.

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

## Remise à zéro (démonstration)

La remise à zéro totale conserve les types d'actions et les actions départementales (sans leurs liens vers les pôles, MDS et partenaires, recréés ensuite) ; les actions locales disparaissent avec leur MDS.
