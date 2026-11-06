# ProConnect (prêt, désactivé)

ProConnect (DINUM) permet aux professionnels de se connecter avec leur identité professionnelle (OpenID Connect).
Dans CID, le code est **prêt mais désactivé** : le bouton « S'identifier avec ProConnect » n'apparaît sur la page de
connexion que lorsque la DSI a renseigné les variables ci-dessous. Sans elles, rien ne change.

## Pour la DSI
1. Démarches (au nom du CD13, avec les coordonnées du responsable de traitement et du DPO) :
   formulaire « demande de création de fournisseur de service » (identifiants d'**intégration** sous 2 jours ouvrés),
   puis **DataPass** avec la DINUM, puis identifiants de **production**. Documentation :
   https://partenaires.proconnect.gouv.fr/
2. Adresses à déclarer : connexion `https://<CID>/connexion/proconnect/retour/` ; déconnexion `https://<CID>/login/`.
3. Variables d'environnement :

| Variable | Valeur |
|---|---|
| `PROCONNECT_DOMAIN` | domaine ProConnect (intégration ou production), sans `https://` |
| `PROCONNECT_CLIENT_ID`, `PROCONNECT_CLIENT_SECRET` | fournis par l'équipe ProConnect |
| `PROCONNECT_ALGORITHME` | algorithme de signature choisi à l'inscription : `RS256` (défaut), `ES256` ou `HS256` |
| `PROCONNECT_IDP_HINT` | facultatif : identifiant du fournisseur d'identité du Département, pour y envoyer directement |

Données demandées : `openid given_name usual_name email uid siret idp_id`, niveau `eidas1`.

## Règles
- **Pas de création automatique de compte.** La personne doit avoir un compte CID **actif**, créé par un
  administrateur avec son **courriel professionnel**. À la première connexion, CID retrouve le compte par ce courriel
  (refus si aucun ou plusieurs comptes) et enregistre le lien ProConnect (identifiant + fournisseur d'identité +
  SIRET). Ensuite, le lien suffit, même si le courriel change.
- Sécurité : `state` et `nonce` aléatoires vérifiés ; jetons signés vérifiés avec les clés publiques de ProConnect
  (ou le secret en HS256), émetteur et destinataire contrôlés.
- Déconnexion de CID → déconnexion de ProConnect.
- Admin › Identités ProConnect : liste des liens ; supprimer une ligne coupe le lien.
- La connexion par identifiant et mot de passe reste disponible.

## Plus tard
Profil « partenaire extérieur » (porteurs d'actions, partenaires) limité aux prescriptions adressées à son
organisme, rattaché par le SIRET reçu : à décider avec la DSI et le DPO (voir l'étude du projet).
