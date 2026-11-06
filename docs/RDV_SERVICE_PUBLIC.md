<!-- docs/RDV_SERVICE_PUBLIC.md -->
# Passerelle RDV Service Public

**État : présente, désactivée. Synchronisation des agendas (étape 1) prête et vérifiée sur une vraie copie de RDV-Solidarités.** Elle sera prête à l'activation après deux choses : les identifiants OAuth délivrés par l'ANCT, et un test sur leur environnement de démonstration.

RDV Service Public est l'outil de prise de rendez-vous de l'ANCT. Le fonctionnement de la passerelle est repris de Mon Suivi Social v2 (ANCT, licence MIT).

## Ce qu'elle fait une fois activée

1. **Relier le compte de l'agent.** Chaque agent relie une fois son compte CID à son compte RDV Service Public, par OAuth2. CID garde son jeton et le renouvelle seul ; les jetons ne s'affichent jamais dans l'administration.
2. **Prendre un rendez-vous depuis la fiche usager.** Le bouton **📅 RDV Service Public** apparaît dans le bloc Rendez-vous, et seulement quand la passerelle est active.
   - Il crée ou met à jour l'usager côté RDV-SP, en n'envoyant que les données utiles : nom, prénom, date de naissance, adresse, téléphone, courriel.
   - Il ouvre ensuite directement l'écran où l'agent choisit le motif et le créneau.
   - L'identifiant usager RDV-SP est mémorisé pour les fois suivantes.
3. **Relire les rendez-vous et en changer le statut.** Fonctions prêtes dans `connecteurs/rdv_service_public.py`, pas encore affichées : lire les rendez-vous de l'usager, et passer un rendez-vous à venu, absent, excusé ou annulé.

Chaque appel est tracé dans **Journal des appels RDV Service Public** (qui, quand, quel usager, résultat).

## Activer

Variables d'environnement du serveur (Render) :

| Variable | Contenu |
|---|---|
| `RDVSP_ACTIF` | `1` pour activer (absent = désactivée) |
| `RDVSP_URL` | adresse de RDV Service Public, démonstration puis production, fournie par l'ANCT |
| `RDVSP_CLIENT_ID` | identifiant OAuth de CID, délivré par l'ANCT |
| `RDVSP_CLIENT_SECRET` | secret OAuth associé |
| `RDVSP_REDIRECT_URI` | facultatif ; par défaut `https://<serveur CID>/connecteurs/rdv-service-public/retour/` |

La page **Admin → Passerelle RDV Service Public** (`/connecteurs/rdv-service-public/`) montre trois choses :
- ce qui manque encore pour activer la passerelle ;
- l'adresse de retour à déclarer à l'ANCT ;
- les derniers appels.

## Synchronisation des agendas (étape 1, faite)
CID est l'agenda maître. RDV-Solidarités n'est que la vitrine de la réservation en ligne. Le code est dans `connecteurs/rdvsp_synchro.py`.

**Ce que fait la synchronisation :**
- **Publication :**
  - Chaque **demi-journée de réception** en MDS (MDS → Demi-journées de réception), dans une MDS ouverte en ligne, devient une **permanence hebdomadaire** dans RDV-Solidarités.
  - Elle est publiée pour 8 semaines (réglable) et prolongée quand il en reste moins de 3.
  - Une demi-journée retirée ou modifiée dans CID est **neutralisée** par une absence répétée, puisque l'API ne permet ni de modifier ni de supprimer une permanence. La nouvelle version est republiée.
- **Blocages :** chacun de ces cas envoie une absence de l'agent à RDV-Solidarités, retirée quand le motif disparaît :
  - un créneau pris dans CID ;
  - un **jour bloqué** (fermeture, férié, indisponibilité) ;
  - le **plafond** de RDV en ligne atteint dans une demi-journée (2 par défaut). Les RDV placés par un agent ne comptent pas dans ce plafond.
- **Retour des RDV :** chaque RDV pris, modifié ou annulé arrive par un **avis signé** (`/connecteurs/rdv-service-public/avis/`). Il occupe le créneau CID correspondant, rattaché à l'usager s'il est connu, sinon marqué « à rapprocher ».
  - Une annulation garde son **heure**, ce qui permettra de repérer les annulations tardives à l'étape 2.
  - Le créneau redevient libre dans CID.
- **Statuts :** « venu » ou « absent » saisi dans CID est renvoyé à RDV-Solidarités.

**Quand la synchronisation se fait :**
- les changements d'agenda (créneaux, jours bloqués, statuts) partent **aussitôt** ;
- la publication et la prolongation se font **une fois par jour** : à la première connexion sur Render, ou par `python manage.py synchro_rdvsp` à planifier chaque nuit en production ;
- et à la demande : Admin → Passerelle RDV Service Public → **Synchroniser maintenant**.

**Réglages :**
- dans Admin → Passerelle RDV Service Public :
  - le **compte de synchronisation** : un administrateur CID, relié une fois à RDV-Solidarités, et administrateur de l'espace départemental côté RDV-Solidarités ;
  - l'identifiant du service social ;
  - pour chaque MDS : son **organisation** RDV-Solidarités et la case « en ligne » ;
  - le **motif** « Renouvellement RSA » (30 min, de 48 h à 15 jours à l'avance, 2 en ligne au maximum par demi-journée, sur invitation seulement) ;
- dans les variables d'environnement :
  - `RDVSP_SECRET_AVIS` : secret partagé pour signer les avis ;
  - `RDVSP_PREFIXE` : préfixe des références CID, différent pour chaque serveur CID qui partage les mêmes identifiants (défaut `cid`).
- Puis cliquer sur **Déclarer l'adresse de CID** une fois : RDV-Solidarités saura où envoyer ses avis. Côté ANCT, l'adresse doit aussi être autorisée.

**Permanences en lieu externe** (CCAS, mairie, école…) :
- Elles sont publiées quand leur nom, tel que l'agent le saisit dans ses demi-journées, correspond à un **lieu externe déclaré avec son adresse**, dans Admin → Lieux externes publiés. La comparaison ignore les majuscules.
- La page d'état liste les lieux saisis par les agents mais pas encore déclarés : ils ne sont pas publiés, pour ne jamais montrer de fausse adresse à l'usager.

## Invitations et suspension (étape 2, faite)
Le code est dans `connecteurs/rdvsp_invitations.py`.

**La liste mensuelle :**
- **Préparation :** chaque mois, le **1er lundi** par défaut (réglable : jour, délai, heure), CID prépare pour chaque référent la liste de ses bénéficiaires dont le **contrat arrive à échéance**, avec les mêmes règles que la vue « À renouveler ».
  - Seules les MDS ouvertes en ligne sont concernées.
  - Les usagers **suspendus** en sont exclus.
- **Référents :** chacun est prévenu par la **messagerie de CID**. Sur RSA – Insertion → **Invitations à réserver en ligne**, il **décoche** ceux à ne pas inviter, puis valide.
- **Sans validation :** la liste part **telle quelle le lendemain à 18 h** (réglable).

**L'envoi :**
- CID crée l'usager dans RDV-Solidarités s'il n'y est pas encore, puis obtient son **lien personnel**. Le motif « Renouvellement RSA » n'est réservable que sur invitation.
- **Avec adresse courriel :** CID envoie un **courriel**, avec en pièce jointe le **courrier PDF** et son **QR code**. Le texte du courrier se modifie dans Modèles de courriers → `RSA_INVITATION_RDV`.
- **Sans adresse courriel :** le courrier est **à imprimer** depuis la liste.
- **Serveur de courriel :** sans serveur configuré par la DSI, rien n'est réellement expédié. Les variables à renseigner sont `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` et `DEFAULT_FROM_EMAIL`. Les SMS de rappel ne sont pas faits (accréditations).

**La suspension :** une case **« Réservation en ligne suspendue »** dans le bloc Rendez-vous de la fiche usager, cochée par l'agent.
- Elle affiche à côté les **annulations à moins de 48 h** et les **absences** des RDV pris en ligne. CID ne bloque jamais rien de lui-même.
- Une personne suspendue entre la préparation et l'envoi n'est pas invitée.

**Quand ça se fait :** à la connexion d'un agent, en arrière-plan, et par `python manage.py synchro_rdvsp` en production.

**Vérification :** sur le banc d'essai, le lien envoyé est **accepté par RDV-Solidarités**, qui connecte l'usagère et ouvre la recherche de créneaux. Un faux lien est refusé.

**Vérification :** `.github/workflows/essai-rdv-solidarites.yml` lance une vraie copie de RDV-Solidarités (à partir de github.com/frankein1/MRS) sur GitHub, avec des données fictives, et fait le parcours complet :
1. publication ;
2. blocage d'un créneau CID ;
3. RDV pris en ligne reçu dans CID ;
4. plafond ;
5. annulation ;
6. statut « venu » ;
7. retrait d'une permanence.

## Questions pour l'ANCT

- Délivrance des identifiants OAuth pour une collectivité (procédure, convention).
- Accès à l'environnement de démonstration.
- Webhooks : format et signature.
- Organisation du CD13 dans RDV-SP : une organisation par MDS ?
