<!-- docs/SIMULATION_DROITS.md -->
# Simulation des droits (OpenFisca)

Accès : fiche usager → bloc **Situation CAF / MSA et France Travail** → **Simuler les droits**. Réservé aux agents de la MDS de l'usager.

## Ce que fait l'écran

- **Le foyer vient de la fiche.** L'usager, son conjoint et ses enfants sont repris des liens familiaux marqués « vit au foyer ». Rien n'est retapé.
- **L'agent saisit seulement :**
  - les ressources mensuelles moyennes de chaque adulte : salaire, chômage, retraite, pension alimentaire reçue ;
  - le logement : statut, loyer et zone.
- **CID estime pour le mois en cours :** RSA, prime d'activité, aide au logement, allocations familiales, complément familial et allocation de soutien familial.

C'est une **estimation indicative**. Elle ne vaut pas décision de la CAF ou de la MSA.

Le calcul ne prend pas en compte :
- l'AAH et le handicap ;
- la grossesse ;
- la garde alternée ;
- le patrimoine ;
- les aides propres au Département.

## Protection des données

Le calcul se fait **sur le serveur CID**, dans un processus séparé : aucune donnée n'est envoyée à un service extérieur. L'API publique d'OpenFisca n'est **pas** utilisée. Rien n'est enregistré : la simulation disparaît quand on quitte la page.

## Le moteur

[OpenFisca-France](https://pypi.org/project/openfisca-france/) est le moteur de calcul libre de l'État pour le système socio-fiscal.

- **Activité :** en novembre 2026, il sortait plusieurs versions par mois ; la dernière datait du 27 octobre 2026.
- **Installation séparée :** il n'est pas installé avec CID, car il impose des versions de paquets incompatibles avec CID (gunicorn < 23, alors que CID est en 26). Il vit dans un environnement à part, `.venv-openfisca`.
- **Exécution :** CID le lance pour chaque calcul (`connecteurs/openfisca_moteur.py`), et la mémoire est libérée ensuite.
- **Coût mesuré :** environ 210 Mo de mémoire et 3 à 5 secondes par calcul.

## Installer sur Render

Dans Render → **Settings → Build Command**, ajouter à la commande existante :

```
&& python -m venv .venv-openfisca && .venv-openfisca/bin/pip install -r requirements-openfisca.txt
```

Tant que ce n'est pas fait, le bouton **Simuler les droits** n'apparaît pas et CID fonctionne normalement.

Variable facultative : `OPENFISCA_PYTHON`, le chemin d'un autre interpréteur où OpenFisca est installé.

**Mémoire :** l'offre gratuite de Render donne 512 Mo. CID et un calcul en cours peuvent s'en approcher. Si le service redémarre pendant une simulation, c'est la cause : il faut alors passer sur une offre payante.

## Mettre à jour la législation

La législation change : mettre à jour la version dans `requirements-openfisca.txt` quelques fois par an, en prenant la dernière publiée sur pypi.org. Les tests `connecteurs/test_simulation.py` vérifient le calcul réel sur une famille fictive.
