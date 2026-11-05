<!-- docs/RGPD_ARCHIVAGE.md -->
# Archivage RGPD des dossiers usagers

Menus : **Cadre → Archivage RGPD** (cadres de MDS, capacité `rgpd_archiver`) et **Admin → Archivage RGPD** (tout le département, plus l'effacement définitif). Code : `beneficiaire/archivage.py`.

## 1. Proposition
Un dossier est proposé à l'archivage quand il n'a **aucune activité depuis 3 ans**.
- Ce qui compte comme activité : la fiche, les rendez-vous (y compris à venir), les aides, le RSA, les documents de la GED, les messages, les liens familiaux, les transferts…
- Qui le voit : les cadres de la MDS du dossier.
- Exception : les dossiers liés à une **information préoccupante** (comme famille, adulte ou enfant) ou à des **rendez-vous IP ou enfance** ne sont **jamais proposés**.

Le cadre coche les dossiers, choisit un motif (fin d'accompagnement, sans nouvelles, déménagement, réorientation, décès, autre) et archive. Seuls les dossiers réellement proposés peuvent être archivés.

## 2. Archivage
Le dossier archivé est **masqué partout dans CID** : liste, recherche, fiche, agenda, réseau familial des proches, messagerie… Il est aussi **en lecture seule**.

Techniquement, `Beneficiaire.objects` exclut les dossiers archivés, et `Beneficiaire.tous` les inclut ; seule la page d'archivage s'en sert.

Le cadre de la MDS (ou l'administrateur) peut :
- consulter le dossier archivé (identité, dates, motif, contenu) ;
- le **désarchiver**, par exemple au retour de l'usager. Le dossier retrouve alors son statut d'avant.

## 3. Effacement définitif
**Seul un administrateur** peut effacer, et seulement des dossiers **archivés depuis au moins 12 mois**.
- **Avant de confirmer :** pour chaque dossier, CID affiche ce qui sera effacé (aides, contrats, documents de la GED…).
- **Confirmation :** l'administrateur coche les dossiers et tape `EFFACER`.

L'effacement supprime :
- le dossier et tout ce qui en dépend, y compris les documents de la GED et leurs fichiers ;
- les aides financières rattachées. À vérifier avant de confirmer : les durées de conservation propres aux pièces comptables.

L'effacement ne supprime pas tout :
- **Rendez-vous passés :** ils restent dans l'agenda de la MDS, sans l'usager.
- **Dossiers bloqués :** un dossier cité par celui d'une autre personne (par exemple comme auteur d'une demande d'aide) ne peut pas être effacé. CID l'indique.

Il ne reste qu'une **trace anonyme** : MDS, dates, motif, nombre d'éléments effacés, auteur de l'effacement. Toutes les opérations (archivage, désarchivage, effacement) sont consultables dans Administration → Opérations RGPD.

## Réglages
Ils se font dans Administration → Configuration :

| Clé | Défaut | Rôle |
|---|---|---|
| `RGPD_ARCHIVAGE_ANS` | 3 | années sans activité avant proposition |
| `RGPD_EFFACEMENT_MOIS` | 12 | mois d'archivage avant effacement possible |
