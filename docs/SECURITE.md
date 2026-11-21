<!-- docs/SECURITE.md -->
# Sécurité, rôles et conformité RGPD

Ce document fait le point sur les mesures **présentes dans le code**, et sur ce qui reste à la charge de l'organisation qui déploie CID. Il ne remplace ni une analyse de risques, ni une analyse d'impact (AIPD), ni le travail du délégué à la protection des données (DPO).

## Périmètre de la démonstration

Le dépôt et l'instance de démonstration ne contiennent **que des données fictives** (`DONNEES_FICTIVES.md`). Les paramètres par défaut de `cid/settings.py` (`SECRET_KEY` de développement, `DEBUG=True`) ne servent qu'à l'essai local : un déploiement réel les remplace par ses propres valeurs (voir `SECURITY.md`).

## Authentification

- Connexion par identifiant et mot de passe, ou par **ProConnect** (`PROCONNECT.md`).
- Mots de passe : hachage Django ; un poivre optionnel (`PASSWORD_PEPPER`) peut être ajouté côté serveur ; une politique de mot de passe est appliquée par un middleware (`core/mot_de_passe.py`).

## Rôles et droits

Les droits reposent sur trois niveaux :

1. **Profil** (`core.Profil`) : ensemble de capacités attribué à un agent. Les profils de base sont créés par `python manage.py init_profils`.
2. **Capacité** (`core.Capacite`) : un droit précis, par exemple `peut_voir`, `peut_lister`, `peut_decider`, `peut_administrer`, ou des capacités par module (`av_piloter`, `av_evaluer` pour les adultes vulnérables).
3. **Rattachement à une MDS** (`mds.UserMDSProfile`) : un agent ne voit que les dossiers des MDS auxquelles il est rattaché. Les règles de rattachement, dont l'accès accordé au CODIR de la MDS de territoire, sont décrites dans `ORGANISATION_MDS.md`.

Les modules à accès restreint (protection de l'enfance, adultes vulnérables, RU) ajoutent leurs propres capacités ; un droit de voir la MDS ne suffit pas à voir ces dossiers.

## Traçabilité

- **Journal d'activité** (`JOURNAL_ACTIVITE.md`) : consultations des dossiers, créations, modifications (avec avant / après des champs modifiés) et suppressions sont enregistrées dans `core.AuditLog`, avec l'agent et l'usager concerné.
- Durée de conservation du journal : 12 mois par défaut, réglable (`JOURNAL_DUREE_MOIS`), puis effacement automatique.
- Les modèles héritent de `AuditedMixin` (date de création et de modification, auteur).

## Chiffrement

- Les **documents de la GED** sont chiffrés en AES-256-GCM, avec une clé par fichier (`CHIFFREMENT_GED.md`). La clé maîtresse est confiée à la DSI (variable d'environnement ou gestionnaire de clés). Sans elle, les fichiers ne sont pas lisibles.
- Le transport passe par HTTPS en production (à la charge de l'hébergeur).

## Stockage des documents

Ordre de choix, dans `ged/storage.py` :

1. **pCloud** (WebDAV), dès que `PCLOUD_USER` et `PCLOUD_PASSWORD` sont définis. C'est le mode de production. Une erreur de pCloud remonte à l'utilisateur : il n'y a aucun repli.
2. **Stockage temporaire** (`/tmp/ged_docs`) sur Render si pCloud n'est pas configuré. **Ces fichiers disparaissent au redémarrage ou au redéploiement de l'instance.**
3. **SeaweedFS** dans les autres cas. En cas d'échec, le code bascule **en silence** sur le stockage temporaire (avertissement dans les journaux seulement).

SeaweedFS n'est donc pas utilisé en production : il reste une option pour un hébergement propre. Les tests remplacent le stockage par un dossier temporaire (`ged/tests_securite.py`).

Une vérification est à faire avant toute mise en service : pCloud doit être configuré sur l'instance, sinon les documents seraient écrits dans le stockage temporaire.

## Conservation et RGPD

- Durées de conservation par type de donnée : `RGPD_DUREES.md`.
- Archivage des dossiers inactifs : `RGPD_ARCHIVAGE.md` (proposition, masquage en lecture seule, effacement seulement sur décision d'un administrateur).
- Anonymisation pour copies de travail : `ANONYMISATION.md`.
- Dossier RGPD complémentaire : répertoire `docs/rgpd/`.

## À la charge de l'organisation qui déploie

- Désigner les responsables de traitement et un DPO ; tenir le registre des traitements.
- Réaliser une **AIPD** pour les modules sensibles (protection de l'enfance, adultes vulnérables, RU, RSA).
- Contrats de sous-traitance avec l'hébergeur ; choix de l'hébergement (données de santé et d'action sociale).
- Revue régulière des comptes et des rattachements, et des capacités accordées.
- Sauvegardes et tests de restauration de la base et de la GED.
- Mises à jour de sécurité des dépendances (`requirements.txt`).

## Ce qui n'est pas couvert ici

- Aucun audit de sécurité externe n'a été réalisé à ce jour.
- La couverture de tests et la conformité des modèles aux référentiels métier restent à mesurer et à documenter.
- Les licences des dépendances sont à vérifier avant tout déploiement hors du Département (le projet est sous AGPL v3, voir `LICENCE.md`).
