<!-- SECURITY.md -->
# Politique de sécurité

## Données

**Le dépôt ne contient que des données fictives** (voir `docs/DONNEES_FICTIVES.md`). Aucun dossier réel d'usager, aucun identifiant réel ne doit être publié, ni dans le code, ni dans les tickets, ni dans les captures d'écran. Si une donnée réelle est trouvée dans le dépôt, le signaler immédiatement (voir ci-dessous).

## Signaler une vulnérabilité

Ne pas ouvrir de ticket public pour une faille. Écrire au mainteneur du projet par message privé (GitHub : `frankein1`, ou adresse indiquée sur le dépôt). Préciser :

- la page ou le module concerné ;
- les étapes pour reproduire ;
- l'impact estimé (accès à des données, contournement d'un contrôle d'accès, etc.).

Un accusé de réception est envoyé dans un délai raisonnable ; la correction est publiée avant toute divulgation publique.

## Configuration de déploiement

Les valeurs par défaut de `cid/settings.py` (`SECRET_KEY`, `DEBUG=True`, `ALLOWED_HOSTS`) sont **réservées au développement et à la démonstration locale**. Tout déploiement réel doit définir au minimum :

- `SECRET_KEY` : valeur aléatoire propre à l'instance ;
- `DEBUG=False` ;
- `ALLOWED_HOSTS` : le nom de domaine de l'instance ;
- la clé maîtresse de la GED (voir `docs/CHIFFREMENT_GED.md`).

## Périmètre

Les audits de sécurité et de conformité RGPD relèvent de chaque organisation qui déploie CID. Le détail des mesures en place (chiffrement, rôles, traçabilité, durées de conservation) est dans `docs/SECURITE.md`.
