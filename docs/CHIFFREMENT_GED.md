<!-- docs/CHIFFREMENT_GED.md -->
# Chiffrement des documents de la GED

Code : `ged/chiffrement.py`. La conception est reprise de Mon Suivi Social v2 (ANCT, licence MIT).

## Principe (« chiffrement d'enveloppe »)
- **Une clé par fichier :** chaque fichier est chiffré en **AES-256-GCM** avec **sa propre clé**, tirée au hasard.
- **Une clé maîtresse :** elle chiffre cette clé de fichier et ne sort jamais du gestionnaire de clés. Seule la clé de fichier *chiffrée* est rangée, dans l'en-tête du fichier.
- **Le stockage** (pCloud, SeaweedFS…) ne voit que des fichiers illisibles, et la base de données ne contient aucune clé.
- **L'en-tête est authentifié :** un fichier ou un en-tête modifié est refusé à l'ouverture.
- **Pour les agents, rien ne change :** CID déchiffre au téléchargement. Empreinte et taille restent celles du fichier en clair.
- **Anciens fichiers :** ceux déposés avant l'activation restent lisibles en clair, jusqu'à leur chiffrement par la commande ci-dessous.

## Activer
1. **Générer une clé maîtresse :** `python manage.py cle_ged` affiche 32 octets en base64.
2. **La recopier** dans la variable d'environnement **`GED_CLE_MAITRESSE`** du serveur (sur Render : Environment).
3. **La SAUVEGARDER hors de CID**, dans le coffre-fort de la DSI par exemple : **sans elle, les fichiers chiffrés sont définitivement perdus.**
4. **Chiffrer les fichiers existants :** Admin → Chiffrement de la GED → **Chiffrer les fichiers existants** (par lots de 50, à recliquer jusqu'à « 0 restant »), ou `python manage.py chiffrer_ged` sur le serveur. `--essai` compte sans rien modifier.

La page **Admin → Chiffrement de la GED** indique si le chiffrement est actif.

Sans clé configurée, CID fonctionne comme avant, avec des fichiers en clair. Une alerte est alors écrite dans les journaux du serveur.

Si le chiffrement échoue (gestionnaire de clés injoignable, par exemple), le fichier **n'est pas déposé** : il n'y a jamais de repli en clair.

## Changer de clé (rotation)
1. Générer une nouvelle clé et la mettre dans `GED_CLE_MAITRESSE`, avec un nouvel identifiant `GED_CLE_ID` (par exemple `k2`).
2. Garder l'ancienne dans `GED_CLES_ANCIENNES="k1:<ancienne clé>"`.

Les nouveaux fichiers utilisent la nouvelle clé ; les anciens restent lisibles avec l'ancienne.

## En production : un gestionnaire de clés
`GED_KMS=openbao` utilise le moteur « transit » d'**OpenBao** ou de **Vault**, comme Mon Suivi Social : la clé maîtresse reste dans le gestionnaire, et CID ne la voit jamais.

| Variable | Rôle |
|---|---|
| `OPENBAO_ADDR` | adresse du gestionnaire |
| `OPENBAO_TOKEN` | jeton d'accès |
| `OPENBAO_CLE` | nom de la clé transit (défaut `cid-ged`) |
| `OPENBAO_MOUNT` | point de montage (défaut `transit`) |

Ce branchement est testé avec des réponses simulées. Il faudra le valider sur le gestionnaire de la DSI.

## Format d'un fichier chiffré
`CIDGED1\0` (8 octets) | longueur de l'en-tête (4 octets) | en-tête JSON (version, algorithme, gestionnaire, identifiant de clé, clé de fichier chiffrée) | nonce (12 octets) | contenu chiffré + étiquette d'authentification (16 octets).
