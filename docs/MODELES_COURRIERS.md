<!-- docs/MODELES_COURRIERS.md -->
# Modèles de courriers

Les textes des courriers produits par CID se modifient sans toucher au code : **Administration (/admin/) → Core → Modèles de courriers** (super-administrateur).

## Courriers concernés

| Courrier | Code |
|---|---|
| Notification d'une AFASE accordée | `AFASE_ACCORD` |
| Notification d'une AFASE refusée | `AFASE_REFUS` |
| Convocation d'un adulte (audition des parents) | `IP_CONVOCATION_ADULTES` |
| Convocation des enfants (à l'adulte qui les héberge) | `IP_CONVOCATION_ENFANTS` |
| Relance en recommandé d'un adulte absent | `IP_LRAR_ADULTES` |
| Relance en recommandé : enfants absents | `IP_LRAR_ENFANTS` |

Tant qu'un modèle n'est pas modifié, CID imprime son **texte d'origine** : un texte générique, écrit pour CID, identique aux courriers d'avant les modèles. L'en-tête (MDS, destinataire, lieu et date), le numéro de recommandé et les signatures des professionnels restent ajoutés par CID.

## Écrire un modèle

| On écrit | On obtient |
|---|---|
| `{montant_mensuel}` | la valeur tirée du dossier ; la liste des variables de chaque courrier est affichée sur sa fiche, avec un exemple |
| `{si_recours:texte si oui\|texte si non}` | un texte qui dépend du dossier ; « \|texte si non » est facultatif ; les deux textes peuvent contenir des variables, pas d'autre condition |
| `**texte**` | du gras |
| `[petit]texte[/petit]` | des petits caractères |
| une ligne vide | un nouveau paragraphe |

Un paragraphe disparaît s'il est vide ou si toutes ses variables sont vides (par exemple « Voies de recours : {voies_recours} » quand ce texte n'est pas renseigné dans les paramètres des aides).

À l'enregistrement, CID refuse un modèle qui contient une variable ou une condition inconnue. Le bouton **Aperçu PDF** montre le courrier enregistré avec des données d'exemple (jamais celles d'un usager).

## Revenir en arrière, reprendre des modèles

- Action **Remettre le texte d'origine** (cocher le ou les modèles dans la liste).
- Action **Exporter (fichier JSON)**, puis bouton **Importer (JSON)** sur un autre serveur : c'est ainsi que les textes officiels d'une collectivité passent d'un serveur à l'autre, **sans passer par le dépôt de code**. Un modèle qui contient une variable inconnue de la version de CID qui l'importe est ignoré, les autres sont importés.
- La remise à zéro totale de la démonstration conserve les modèles de courriers.

## Textes officiels

Le dépôt de code est public : les textes et modèles internes d'une collectivité ne doivent jamais y être ajoutés. Ils se saisissent (ou s'importent) dans l'administration du serveur de la collectivité.

## Pour les développeurs

- Registre des courriers, variables, conditions, exemples et textes d'origine : `core/courriers/registre.py`.
- Rendu : `core/courriers/rendu.py` ; tests : `python manage.py test core.tests.test_courriers`.
- Dans le service qui produit le PDF : `m = modele_texte(code)`, puis `rendu.ligne(m["objet"], valeurs, conditions)`, `rendu.paragraphes(m["corps"], …)`, `rendu.bloc(m["signature"], …)` (exemples : `AidFi/services/afase_documents.py`, `protection_enfance/services/ip_pdf.py`).
- Un nouveau courrier : une entrée dans le registre, puis son service PDF. Son texte d'origine doit être générique (écrit à partir des textes publics : code de l'action sociale et des familles, code des relations entre le public et l'administration…).
