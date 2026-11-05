<!-- docs/JOURNAL_ACTIVITE.md -->
# Journal d'activité

Traçabilité des accès aux dossiers (RGPD), inspirée de Mon Suivi Social. Code : `core/journal.py` ; données : `core.AuditLog` (modèle existant, complété : usager concerné, nom de l'agent, libellé de l'objet).

## Ce qui est noté

| Action | Comment |
|---|---|
| Connexion, échec de connexion | `core/authentication/backends.py` (existant) |
| Déconnexion | signal `user_logged_out` |
| **Consultation** d'un dossier | middleware `JournalConsultationMiddleware`, vues listées dans `VUES_CONSULTEES` (fiche usager et sa modification, parcours RSA, contrat, prescription, réorientation, document de la GED) ; dédoublonnée : une même page rouverte par le même agent dans les 10 minutes n'est notée qu'une fois |
| **Création, modification, suppression** | signaux sur `MODELES_JOURNALISES` (usager, lien familial, transfert, document GED, IP, demande et décision AFASE, rendez-vous, contrat, prescription, réorientation, compte) ; une modification garde l'**avant / après** des champs modifiés |
| **Export, téléchargement** | middleware : réponse PDF, CSV ou pièce jointe, paramètre `export` ; téléchargement d'un document de la GED |

- Seules les actions d'un **agent connecté** sont notées : les scripts (installation, démo, remise à zéro) ne remplissent pas le journal.
- Les valeurs des **champs sensibles** (`CHAMPS_MASQUES` : n° de sécurité sociale, mots de passe, n° fiscal…) ne sont jamais recopiées : le journal indique seulement qu'ils ont changé.
- Une erreur d'écriture du journal n'empêche jamais l'action (elle est notée dans les logs du serveur).

## Qui le consulte

- **Super-administrateur** : tout (menu Admin → Journal d'activité).
- **Cadres de MDS** (capacité `voir_journal_activite`, ajoutée aux profils cadres) : ce qui touche aux dossiers des usagers de leurs MDS (menu Cadre → Journal d'activité, et bouton **Journal du dossier** sur la fiche usager).
- Filtres : usager (code), agent, action, période (30 derniers jours par défaut) ; export CSV (« ; », UTF-8).

## Conservation

12 mois, puis effacement automatique : une fois par jour, à la première connexion (Render gratuit n'a pas de tâche planifiée). Durée réglable par la clé de configuration `JOURNAL_DUREE_MOIS` (administration → Configuration) ; `python manage.py purger_journal` purge à la demande.
