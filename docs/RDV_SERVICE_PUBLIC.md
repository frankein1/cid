<!-- docs/RDV_SERVICE_PUBLIC.md -->
# Passerelle RDV Service Public

**État : présente, désactivée.** Elle sera prête à l'activation après deux choses : les identifiants OAuth délivrés par l'ANCT, et un test sur leur environnement de démonstration.

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

## Cible : agendas synchronisés (à construire)

L'objectif est qu'un rendez-vous existe une seule fois et apparaisse dans les deux agendas, quelle que soit la personne qui l'a pris.

| Qui prend le rendez-vous | Comment |
|---|---|
| L'agent d'accueil ou le référent | depuis CID (bouton de la fiche) |
| L'usager lui-même | en ligne sur RDV Service Public, **uniquement pour les motifs ouverts au public** (par exemple « Renouvellement RSA », « Aide financière ») |

Ce qui reste à construire :
- **Limiter la prise en ligne par l'usager.** Cela se règle dans RDV Service Public même : chaque motif y est déclaré réservable en ligne ou réservé aux agents. Tous les autres motifs restent fermés au public.
- **Faire revenir les rendez-vous RDV-SP dans l'agenda CID.** RDV-SP prévient CID à chaque création, modification ou annulation, par une notification signée (webhook). CID crée ou met à jour le rendez-vous correspondant (`planning.CreneauRdv`) avec l'agent, l'usager, la date, le lieu et le statut.
  - Les rendez-vous sans lien avec un usager connu sont mis en attente de rapprochement par l'accueil.
  - Le format exact des notifications et leur signature sont à confirmer avec l'ANCT.
- **Éviter les doubles réservations.** Les créneaux ouverts dans RDV-SP sont marqués comme tels dans CID ; un rendez-vous interne ne peut pas les occuper.
- **Statuts.** Venu et absent saisis dans CID sont renvoyés à RDV-SP (fonction déjà prête).

## Questions pour l'ANCT

- Délivrance des identifiants OAuth pour une collectivité (procédure, convention).
- Accès à l'environnement de démonstration.
- Webhooks : format et signature.
- Organisation du CD13 dans RDV-SP : une organisation par MDS ?
