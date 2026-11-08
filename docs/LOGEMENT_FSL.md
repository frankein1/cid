# Logement – FSL : accès au logement, énergie, eau

*Novembre 2026. Premier volet du module logement (suivront : FSL maintien, prévention des expulsions locatives).*

## Ce que fait CID

Depuis la fiche usager, encart **Logement – FSL**, boutons **FSL accès**, **FSL énergie**, **FSL eau** (agents de la MDS de l'usager).

1. **Préremplissage** avec ce que CID connaît déjà, à vérifier :
   - n° CAF, situation familiale ;
   - composition du foyer (réseau familial, personnes qui vivent au foyer) ;
   - ressources par personne, depuis le budget du foyer (salaires, France Travail, RSA, prime d'activité, prestations familiales…) ;
   - loyer et aide au logement du logement actuel ;
   - quotient familial CAF s'il a été relevé ;
   - coordonnées du travailleur social. Le **courriel proposé est celui de la MDS** : l'adresse nominative des agents reste interne.
2. **Saisie** du nouveau logement, de la proposition (garantie, caution, 1er loyer, compteurs, assurance, équipements), de l'avis motivé et des pièces (fournie / à fournir / sans objet).
3. **Alertes** selon les plafonds du règlement intérieur, paramétrés sur le gestionnaire. CID prévient, il ne bloque pas.
4. **Pièces manquantes** : l'agent demande l'avis du cadre. Le cadre rédige la note explicative jointe au dossier (« argumentaire de pièces manquantes ») et accepte l'envoi, ou renvoie la demande. Il est prévenu par un message CID.
5. **Envoi** (date) puis **réponse du FSL** : accordée (montants, garantie), ajournée (pièces demandées, la demande redevient modifiable puis se renvoie) ou refusée. Tout est daté dans l'historique.
6. **Dossier PDF** à imprimer et faire signer, dans l'ordre : demande, avis motivé, argumentaire du cadre, contrat de prêt, autorisation de prélèvement, contrat de garantie, convention d'accès, fiche d'identification du logement (bailleur privé), demande de versement direct de l'AL, liste des pièces. Chaque document ne figure que s'il concerne la demande.

## Énergie et eau

- Préremplissage :
  - adresse, loyer (budget), foyer, ressources ;
  - énergie : dette d'électricité (charge d'électricité non payée du budget) et dette de gaz (combustibles non payés) ;
  - charges exceptionnelles, à partir des dettes du budget.
- À saisir :
  - fournisseur ou distributeur, situation par rapport au logement ;
  - eau : date et montant de la facture ;
  - énergie : dettes, participation du ménage, plan du fournisseur ;
  - surendettement.
- **Instruction par un agent administratif** pour les factures de **moins de 500 €** (cadre réservé du formulaire) :
  - case « Instruite par un agent administratif » et commentaire ;
  - pas d'avis motivé du TS ;
  - au-delà de 500 €, CID refuse l'envoi sans avis d'un travailleur social.
- Dossier : formulaire, avis motivé (si TS), argumentaire de pièces manquantes énergie / eau (si besoin, case cochée dans la bonne colonne).

## Formulaires officiels : la pagination d'origine

Les formulaires des gestionnaires ne sont **jamais dans le dépôt**. Un administrateur les dépose, vierges, dans *Admin → Logement → Formulaires officiels* : gestionnaire, type de document, version. Le PDF est gardé en base, pas sur le disque du serveur.

CID écrit alors les données **sur le formulaire lui-même**, page par page. Chaque champ est placé par rapport à un libellé imprimé (« Loyer : », « Nom du travailleur social »…). Un logo différent (Métropole ou Département) ou une mise en page un peu décalée ne gênent donc pas. Ce que CID écrit apparaît en bleu.

- **Aperçu avec des données fictives**, dans la liste des formulaires : on voit où tombe chaque champ. Les champs non placés sont signalés.
- **Réglages** : si un champ tombe mal, on le corrige dans l'administration sans toucher au code, par exemple `{"ts_email": {"dx": 5, "dy": -2}}`, ou une position absolue `{"cle": {"page": 1, "x": 120, "y": 400}}`.
- Les placements livrés correspondent aux formulaires FSL accès, énergie et eau **version 03/2025**, aux avis motivés et argumentaires (accès ; énergie / eau) et au Cerfa 11362\*04. Si le gestionnaire change de version, on vérifie l'aperçu.
- **Sans formulaire déposé**, CID produit une **trame générique** avec les mêmes rubriques (demande, avis, pièces, note du cadre). Les contrats, la convention et les fiches propres au gestionnaire sont alors signalés « à joindre vierges ».

## Gestionnaires

*Admin → Logement → Gestionnaires du FSL* :
- nom et adresse ;
- **codes postaux couverts** ;
- un gestionnaire **par défaut** pour les autres communes ;
- **transmission** : par où passe le dossier. Par exemple, dans les Bouches-du-Rhône, le service du logement du Département trie et transmet à la Métropole ou au Département ;
- plafonds facultatifs.

Le gestionnaire est choisi d'après le code postal de l'usager. Il reste modifiable sur la demande.

## Démo

- Deux gestionnaires fictifs, sans formulaire officiel : la démo montre la trame CID.
- **FAM5-SAR** : demande en attente de l'avis du cadre (bail et fiche d'identification manquants).
- **FAM2-SOP** : demande d'accès accordée ; demande eau en préparation.
- **FAM5-SAR** : demande énergie instruite par un agent administratif (`aa1_mds1`), envoyée.

## Fichiers

- `logement/models.py` : GestionnaireFSL, FormulaireOfficiel, DemandeFSL.
- `logement/services/` :
  - `fsl.py` : rubriques, préremplissage, pièces, plafonds ;
  - `circuit.py` : circuit de la demande ;
  - `pdf_officiel.py` : écriture sur un PDF vierge par ancres ;
  - `placements_fsl.py` : placements du FSL accès ;
  - `fsl_pdf.py` : dossier et trame générique.
- Bibliothèques ajoutées : `pypdf` et `pdfplumber`.
