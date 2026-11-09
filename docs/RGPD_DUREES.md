# Durées de conservation (RGPD)

*Novembre 2026. Décision de Fred (8/11/2026) : le DPO remplit un tableau procédure par procédure, l'administrateur l'importe ; toutes les durées en mois.*

## Le circuit

1. *Administration → Durées de conservation (RGPD)* → **Télécharger le modèle (CSV)**. Le fichier est aussi dans `docs/rgpd/`.
   - Une ligne par traitement de CID (23 traitements).
   - On y trouve les réglages en vigueur : `actuel_base_active (en mois)`, `actuel_archivage_intermediaire (en mois)`, `actuel_point_de_depart`.
2. Le **DPO** remplit, pour chaque ligne qui le concerne :
   - `duree_base_active (en mois)`, `point_de_depart`, `duree_archivage_intermediaire (en mois)` ;
   - `sort_final` : suppression, anonymisation ou versement aux archives départementales ;
   - `base_legale_ou_reference`, `commentaire_dpo`.

   La colonne `code` ne se modifie pas.
3. L'administrateur clique sur **Importer le CSV**.
   - Les durées doivent être des nombres entiers de mois.
   - Une seule erreur (code inconnu, « 2 ans », sort final inconnu…) bloque tout l'import, et les erreurs sont listées ligne par ligne.
   - Une ligne laissée vide garde le réglage de CID.
   - Les fichiers enregistrés en UTF-8 ou en Windows-1252, séparés par des points-virgules ou des virgules, sont acceptés.

Priorité d'une durée : la valeur importée, sinon l'ancienne clé de configuration (`RGPD_ARCHIVAGE_ANS` ×12, `RGPD_EFFACEMENT_MOIS`, `JOURNAL_DUREE_MOIS`), sinon la valeur par défaut de CID.

## Ce que CID applique lui-même

| Traitement | Effet |
|---|---|
| `USAGER_DOSSIER` | La base active est le délai sans activité avant que le dossier soit proposé à l'archivage (par défaut 36 mois). L'archivage intermédiaire est le délai avant l'effacement possible (par défaut 12 mois). |
| Traitements qui suivent le dossier usager | Ils sont archivés et effacés avec lui : journal d'accompagnement, budget, GED, rendez-vous, ateliers, AFASE, CAP, régie, IP, RSA, FSL, logement social, COPP. |
| `JOURNAL_ACTIVITE` | Le journal d'activité est purgé après base active + archivage (par défaut 12 mois). |
| `ANNUAIRE_RECHERCHES` | Les recherches dans l'annuaire des usagers peuvent être purgées plus tôt que le reste du journal, jamais plus tard. |
| `EXPULSION_DOSSIER` | Point de départ : la clôture du dossier. Selon le sort final : **suppression** ; **anonymisation** (identité, adresse, numéros, bailleur, fiche CAF, historique, commentaires et messages effacés ; MDS, commune, dette, étapes et décision gardées pour les statistiques) ; **versement aux archives** (rien n'est détruit, les dossiers sont signalés dans les statistiques du Service Logement). Rien ne se passe tant que la durée n'est pas fixée. |
| `EXPULSION_DSF` | Le diagnostic, le bordereau de carence et les convocations sont supprimés, s'ils doivent partir avant le dossier. |
| `HEBERGEMENT_URGENCE` | Point de départ : la clôture du dossier. **Suppression** : le dossier disparaît ; **anonymisation** : fiches, démarches, historique et messages effacés, il reste la MDS, les dates, la structure et le motif de clôture (statistiques) ; **versement aux archives** : CID ne détruit rien. Le numéro du titre d'identité ou de séjour est effacé dès la clôture, sans attendre. |

Les purges tournent une fois par jour, à la première connexion, comme celle du journal : le plan gratuit de Render n'a pas de tâche planifiée.

Les autres traitements (messagerie, comptes et signatures des agents, appels aux services de l'État) sont **documentés** mais pas encore purgés automatiquement. La colonne « Appliqué par CID » de l'administration le signale.

L'anonymisation d'une copie de base (`anonymiser_base`) et la remise à zéro conservent ces réglages.
