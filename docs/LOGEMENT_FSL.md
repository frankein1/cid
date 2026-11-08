# Logement – FSL : accès, maintien, énergie, eau

*Novembre 2026. Premier volet du module logement (suivra : prévention des expulsions locatives).*

## Ce que fait CID

Depuis la fiche usager, encart **Logement – FSL**, boutons **FSL accès**, **FSL maintien**, **FSL énergie**, **FSL eau** (agents de la MDS de l'usager).

1. **Préremplissage** avec ce que CID connaît déjà, à vérifier :
   - n° CAF, situation familiale ;
   - composition du foyer (réseau familial, personnes qui vivent au foyer) ;
   - ressources par personne, depuis le budget du foyer (salaires, France Travail, RSA, prime d'activité, prestations familiales…) ;
   - loyer et aide au logement du logement actuel ;
   - quotient familial CAF s'il a été relevé ;
   - coordonnées du travailleur social. Le **courriel proposé est celui de la MDS** : l'adresse nominative des agents reste interne.
2. **Saisie** du nouveau logement, de la proposition (garantie, caution, 1er loyer, compteurs, assurance, équipements), de l'avis motivé et des pièces (fournie / à fournir / sans objet).
3. **Alertes** selon les plafonds du règlement intérieur, paramétrés sur le gestionnaire. CID prévient, il ne bloque pas.
4. **Visa du cadre (toute demande)** : l'agent demande le visa et le cadre reçoit un message CID. En un clic, le cadre appose sur le dossier ses initiales et la date, plus sa signature numérisée si elle a été déposée et validée (*Admin → MDS → Signatures numérisées*). S'il manque des pièces, il rédige en plus la note explicative jointe au dossier (« argumentaire de pièces manquantes »). Il peut aussi renvoyer la demande.
5. **Envoi**, une fois la demande visée :
   - **Envoi par mail** : destinataire à saisir, objet prérempli « MDST/MDSP – ville – … – NOM Prénom », PDF et pièces de la GED joints ;
   - **Imprimer pour envoi**, seulement si le destinataire l'exige.

   Chaque envoi alimente le compteur de papier économisé (voir `docs/LOGEMENT_COPP.md`).
6. **Réponse du FSL** : accordée (montants, garantie), ajournée (pièces demandées : la demande redevient modifiable puis se renvoie) ou refusée. Tout est daté dans l'historique.
7. **Dossier PDF**, dans l'ordre : demande, avis motivé, argumentaire du cadre, contrat de prêt, autorisation de prélèvement, contrat de garantie, convention d'accès, fiche d'identification du logement (bailleur privé), demande de versement direct de l'AL, liste des pièces. Chaque document ne figure que s'il concerne la demande.

## Maintien et concordat

- **Une seule demande**, avec le choix entre :
  - **FSL maintien** : reprise du paiement du résiduel de loyer depuis 3 mois consécutifs ;
  - **FSL concordat** : 6 mois consécutifs, avec une remise de dette du bailleur.
- **La partie « logement » est à compléter par le bailleur.** CID la préremplit avec le loyer et l'AL du budget du foyer, et propose comme dette locative le loyer non payé.
- **À saisir :**
  - bailleur (social ou privé), typologie, surface, charges, garage, RLS ;
  - saisine de la commission de surendettement et de la CCAPEX ;
  - mois de reprise du paiement ;
  - concordat : remise du bailleur (oui / non, montant).
- **Alerte concordat :** CID prévient si la remise est absente ou inférieure au tiers de la dette, comme le prévoit la convention.
- **Pièces propres :**
  - relevé de compte locataire depuis l'origine de la dette ;
  - engagements du locataire et du bailleur ;
  - convention de résorption (concordat) ;
  - justificatif de saisine de la CCAPEX ;
  - état de la procédure de surendettement.
- **Dossier**, dans cet ordre :
  - demande maintien / concordat (la case du titre est cochée) ;
  - avis motivé ;
  - argumentaire maintien / concordat ;
  - contrat de prêt et prélèvement (si prêt) ;
  - engagements du locataire et du bailleur ;
  - convention de concordat ;
  - fiche d'identification du logement (bailleur privé) ;
  - versement direct de l'AL ;
  - liste des pièces.

  Le contrat de prêt, l'autorisation de prélèvement, l'avis motivé et la fiche d'identification sont les mêmes imprimés que pour l'accès : on ne les dépose qu'une fois.

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
- Les placements livrés correspondent aux formulaires FSL accès, maintien / concordat, énergie et eau **version 03/2025**, à leurs avis motivés, argumentaires, engagements, convention de concordat et listes de pièces, et au Cerfa 11362\*04. Si le gestionnaire change de version, on vérifie l'aperçu.
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
- **FAM3-CLA** : demande de concordat (bailleur privé, remise d'un tiers, CCAPEX saisie) en préparation.

## Fichiers

- `logement/models.py` : GestionnaireFSL, FormulaireOfficiel, DemandeFSL.
- `logement/services/` :
  - `fsl.py` : rubriques, préremplissage, pièces, plafonds ;
  - `circuit.py` : circuit de la demande ;
  - `pdf_officiel.py` : écriture sur un PDF vierge par ancres ;
  - `placements_fsl.py` : placements du FSL accès ;
  - `fsl_pdf.py` : dossier et trame générique.
- Bibliothèques ajoutées : `pypdf` et `pdfplumber`.
