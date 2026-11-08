# Organisation des MDS : types, fonctions, signatures

*Décisions de Fred, 7 novembre 2026.*

## Deux types de MDS

| | MDS de territoire (MDST) | MDS de proximité (MDSp) |
|---|---|---|
| Encadrement | CODIR : directeur / directrice, adjoint(e) enfance, adjoint(e) prévention, médecin PMI, secrétaire général(e) | cadre de proximité (décide par délégation de signature, rend compte au directeur) ; adjoint(e) de proximité, qui fait aussi office de secrétaire générale |
| Rattachement | — | dépend d'une MDS de territoire (champ « MDS de territoire de rattachement ») |
| Pilotage des IP | l'adjoint(e) enfance (sinon le responsable de la MDS) | le cadre de proximité (sinon le responsable de la MDS) |

Le type et le rattachement se règlent sur la fiche de la MDS. Le responsable de la MDSp et/ou son adjoint participent au CODIR de la MDST : c'est une réunion, CID n'a rien à gérer pour cela.

## Qui voit quoi

- Les membres du **CODIR de la MDS de territoire** voient les dossiers des **MDS de proximité rattachées**. CID leur donne automatiquement un accès sur chaque MDSp (ligne « CODIR … » dans la liste des agents de la MDSp). Cet accès :
  - suit le profil d'origine : désactivé, daté ou retiré en même temps que lui, et recalculé si la MDSp change de rattachement ;
  - ne donne pas la gestion des comptes de la MDSp ;
  - ne se modifie pas depuis la MDSp, mais depuis la MDS de territoire.
- Le **médecin PMI** de la MDS de territoire couvre aussi la PMI des MDSp : par ce même accès, il peut être proposé dans un binôme IP de la MDSp.
- Les agents d'une MDSp ne voient pas les dossiers de la MDS de territoire, ni ceux des autres MDSp.
- Un agent qui a aussi un rattachement propre à la MDSp le garde : il prime sur l'accès hérité.
- Pas de bouton d'escalade vers le territoire : cela se règle par téléphone ; au besoin, le cadre de territoire rédige une note, annexée au dossier comme un document.

## Équipe IP

Le cadre coche **Équipe IP** sur le rattachement des professionnels qui évaluent les informations préoccupantes (*Gestion des agents* → modifier l'agent). Ils sont proposés **en premier** pour le binôme (mention « équipe IP »), puis les autres du moins chargé au plus chargé. Le cadre reste libre de son choix ; un membre de l'équipe qui suit la famille n'est pas proposé pour elle. Pour le médecin PMI de la MDS de territoire, la case se coche sur son rattachement à la MDS de territoire et vaut aussi dans les MDS de proximité.

Une note du cadre de territoire se dépose dans la GED en **Divers** : l'objet et la date suffisent à la retrouver.

## Fonction et intitulé sur les courriers

Sur le rattachement de l'agent à sa MDS (*Gestion des agents de la MDS* → ajouter ou modifier) :

- **Fonction** : directeur, adjoint enfance, adjoint prévention, médecin PMI, secrétaire général (CODIR), cadre de proximité, adjoint de proximité, ou « Autre ».
- **Intitulé de la fonction (sur les courriers)** : proposé d'après la fonction et la MDS (« Directeur de la MDS de territoire TEST 01 »), à corriger au besoin (féminin, nom de la ville). Pour « Autre », texte libre (référent RSA…).

L'intitulé est repris :

- sous la signature des notifications AFASE (variable `{signataire_fonction}` des modèles de courrier ; un modèle déjà personnalisé en administration doit l'ajouter lui-même) ;
- dans la case « Cadre » du formulaire de demande AFASE, la décision de la feuille de remise CAP, le visa du cadre sur le rapport IP et la saisine de l'autorité judiciaire.

Quand l'intitulé est vide, seul le nom s'affiche. Les courriers RSA restent signés au nom du pôle insertion (`{pole}`) : leurs cadres ne sont pas rattachés à une MDS.
