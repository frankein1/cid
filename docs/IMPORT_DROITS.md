# Droits CAF / MSA et France Travail sur la fiche usager

Encart **« Situation CAF / MSA et France Travail »** de la fiche (agents de la MDS de l'usager).

## 1. Par l'API Particulier (automatique, sur clic)
| Source | Ce qui est gardé |
|---|---|
| RSA, prime d'activité, ASF, AAH, C2S | droit ouvert oui / non, depuis quand (majoration, participation) |
| **AEEH** | droit ouvert ; perçoit l'AEEH (allocataire) ou ouvre droit (l'enfant) ; depuis quand |
| Quotient familial CAF / MSA | valeur, mois, nombre d'enfants rattachés |
| France Travail (statut) | inscrit(e), depuis, catégorie, fin |
| **Paiements France Travail** | **les 6 derniers mois, mois par mois** (total, allocations, aides, autres) et la moyenne mensuelle |

- Les API de la CAF ne donnent **pas de montant** : seulement l'existence du droit.
- Les paiements France Travail ne sont demandés **qu'après le statut** (la documentation impose de vérifier que
  l'identifiant est bien celui de la personne).
- Démo : **bac à sable** (données fictives). Production : habilitation API Particulier du CD13 (DataPass),
  variables `API_PARTICULIER_URL`, `API_PARTICULIER_TOKEN`, `API_PARTICULIER_RECIPIENT`.

## 2. Écarts CAF / fiche (tracés)
Au quotient familial, CID compare **sans rien enregistrer de la réponse** :
- enfants rattachés à la CAF / MSA (date de naissance) et enfants du foyer dans CID ;
- commune et voie de l'adresse.

Un écart crée une trace : nature, détail sans nom (ex. « 1 enfant… année de naissance : 2019 »), signalé le / par.
L'agent corrige la fiche puis clique **Réglé** (commentaire facultatif) : réglé le / par. Pas de doublon tant qu'un
écart de même nature est ouvert. Les écarts réglés restent comptés sur la fiche.

## 3. Accès partenaire CAF (consultation par l'agent)
- Bouton **« Accès partenaire CAF »** : ouvre le site de la CAF dans un nouvel onglet (habilitation personnelle de
  l'agent). CID n'y lit rien. Adresse : variable `CAF_PARTENAIRE_URL` ou paramètre `CAF_PARTENAIRE_URL` de
  l'administration (par défaut https://partenaires.caf.fr/).
- **« Actualiser les aides »** (facultatif) : fenêtre avec les prestations (RSA, prime d'activité, aide au logement,
  allocations familiales, complément familial, ASF, PAJE, PreParE, AAH, AEEH, autre) ; l'agent coche celles qu'il a
  vérifiées et saisit le montant mensuel. Chaque relevé est daté et signé ; le dernier de chaque prestation s'affiche.
- **Budget du foyer** : « Reprendre dans un nouveau budget du foyer » pré-remplit les lignes correspondantes avec les
  montants relevés et la ligne chômage avec la moyenne France Travail ; l'agent vérifie avant d'enregistrer.

## 4. Réseau familial
Sous l'encart, chaque personne du réseau familial qui a une fiche (conjoint, grands-parents tiers digne de confiance,
personne qui a la garde…) a un bouton **« Actualiser ses droits »**, avec le résumé de ses droits ouverts. On revient
sur la fiche de départ.

## 5. À prévoir en production : flux RSA de la CNAF
La convention de gestion du RSA prévoit des fichiers CAF → Département (XML, quotidiens ou mensuels : instruction,
gestion et suivi des bénéficiaires, suivi financier), déposés sur le serveur national de la CNAF. Ils alimentent très
probablement SRS en droits et montants RSA. CID pourrait les lire pour les **montants RSA réels**, mois par mois.
À faire avec la DSI, qui les reçoit déjà : obtenir le format (fourni par la CNAF), le circuit de dépôt et l'accord du
DPO ; CID les rattacherait par numéro CAF / identité. Rien n'est codé tant que le format n'est pas connu.

## Données personnelles
Seules les données utiles sont gardées ; chaque appel est tracé (journal des appels) ; supprimer la fiche supprime
situations, écarts et relevés ; jamais utilisées dans les statistiques.
