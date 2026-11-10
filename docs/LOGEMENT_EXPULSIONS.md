# Logement – prévention des expulsions locatives (1 : Service Logement et dossier)

*Novembre 2026. Décisions de Fred (8/11/2026). Première PR d'une série de trois.*

## Qui fait quoi

Aujourd'hui, le **Service Logement (SL)** du Département importe la liste des assignations dans le logiciel actuel, puis envoie à la MDS un PDF par mail (fiche de liaison CD 13 – CAF 13). La MDS va ensuite chercher le dossier dans le module « expulsions » pour le suivre. Dans CID, le SL garde sa partie : centralisation, statistiques, appui aux MDS, relations avec certains bailleurs, suivi avec la préfecture jusqu'au concours de la force publique.

Trois profils pour le SL, attribués dans *Comptes & droits* :

| Profil | Capacités | Peut |
|---|---|---|
| `SL_CADRE` – cadres et adjoint | `expulsion_sl_gestion`, `expulsion_sl_pilotage`, `expulsion_sl_stats` | tout : saisie, affectation, suivi, statistiques, suppression d'un dossier saisi par erreur |
| `SL_AGENT_ADMINISTRATIF` – agents administratifs | `expulsion_sl_gestion` | saisir et suivre les dossiers de tous les territoires, les affecter aux MDS |
| `SL_SECRETARIAT` – secrétariat | `expulsion_sl_stats` | lire les statistiques départementales (pour l'instant) |

## Annuaire des usagers : éviter les doubles saisies

**Tout agent de CID** (Service Logement, pôles insertion, services centraux…) peut chercher un usager dans l'**annuaire** (`/beneficiaire/annuaire/`, menu « Annuaire des usagers », ou *Bénéficiaires → Annuaire (toutes MDS)* pour les MDS). Il apprend ainsi si l'usager existe déjà et à quelle MDS il est rattaché.

- **Ce qui s'affiche :** l'identité de base, c'est-à-dire nom, prénom, nom de naissance, date et lieu de naissance, code usager CID et MDS de rattachement. Rien d'autre : ni adresse, ni dossier.
- **Comment chercher :**
  - par un identifiant exact, qui suffit seul : code usager CID, n° CAF ou téléphone (fixe ou portable, quelle que soit l'écriture : 06 12…, +33 6…) ;
  - ou par deux éléments parmi le nom (d'usage ou de naissance), le prénom, la date de naissance et l'adresse, même incomplète (« rue Montmirail » sans le numéro). Exemples : nom + prénom, prénom + date de naissance, nom + adresse.
- **Orthographes proches :** après les réponses exactes, CID propose les usagers dont le nom ou le prénom **se prononce pareil**. Par exemple, « Frederik » trouve Frédéric, Frederick et Frédérique. Ces réponses sont signalées « orthographe proche » : on vérifie avec la date de naissance.
  - Comment ça marche : une clé phonétique française est calculée à l'enregistrement de l'usager (`core/phonetique.py`, champs indexés). La recherche reste rapide, et aucune extension PostgreSQL n'est nécessaire.
  - Limite : seules les fautes « qui se prononcent pareil » sont rattrapées (k/c/qu, ph/f, lettres doublées, accents, finales muettes…). Une lettre oubliée ou inversée (« Fredreic ») ne l'est pas.

  On ne peut pas parcourir l'annuaire, et la recherche s'arrête à 20 réponses.
- **Journal :** chaque recherche est inscrite au journal d'activité. Le n° CAF et le téléphone n'y sont pas recopiés.
- **Accès à la fiche :** un agent qui a déjà accès à la fiche peut l'ouvrir depuis l'annuaire.

**Dans le dossier d'expulsion,** le SL saisit le **code usager CID**, ou CID retrouve l'usager par le **n° allocataire** s'il est unique.
- Le dossier est alors rattaché à l'usager et part à **sa MDS** : nom et prénom se remplissent seuls.
- Depuis le dossier, le SL peut aussi chercher l'usager (code, n° CAF, ou deux éléments parmi nom, prénom, date de naissance). CID propose d'office les correspondances sur le n° allocataire ou sur nom + prénom.
- **Le SL ouvre et affecte les dossiers** : par arrondissement à Marseille, par ville ailleurs. Une MDS n'ouvre pas de dossier et ne change pas l'affectation.
- **Secteur des MDS** : chaque MDS indique les villes, arrondissements ou codes postaux qu'elle couvre (fiche de la MDS → *Secteur*, par ex. « Port-de-Bouc, Saint-Mitre-les-Remparts », ou « 13001, 13002 » à Marseille ; « Marseille 3e » et les codes INSEE sont aussi reconnus). Pour un usager inconnu, CID **propose** la MDS du secteur d'après l'adresse de la fiche, dans le formulaire comme sur le dossier. Le SL confirme ou choisit une autre MDS : il garde le dernier mot.
- **Usager inconnu de CID** : la MDS reçoit les informations minimales de la fiche du SL et fait la **mise à disposition** prévue par la procédure. Si le ménage est ensuite suivi et créé dans CID, la MDS peut rattacher le dossier à cet usager de sa MDS ; l'affectation, elle, reste au SL.

Côté MDS :
- les agents qui ont `peut_voir` voient les dossiers de leur MDS ;
- avec `peut_modifier`, ils complètent la fiche, saisissent la décision, ajoutent des étapes, rattachent l'usager quand il a été créé dans leur MDS après la mise à disposition, et clôturent ;
- le cadre (`peut_valider`) désigne le référent ; un travailleur social (`peut_instruire`) peut se désigner lui-même ;
- une MDS n'ouvre pas de dossier : si elle repère une procédure, elle prévient le SL, qui ouvre le dossier (origine « Repéré par la MDS ») et l'affecte.

## Le dossier (`logement/models/m_expulsion.py`)

`DossierExpulsion` reprend la **fiche de liaison** rubrique par rubrique :
- dossier n° (`EXP-AAAA-NNNN`) et date ;
- locataire et colocataire, adresse ;
- propriétaire et type de bailleur ;
- date de signature du bail, loyer total, loyer, charges ;
- dette réclamée et sa date ;
- observations CAF (fiche CAF, service social CAF, non identifié, retour le, association, CCAS) et n° allocataire ;
- tribunal, date et heure de l'audience ;
- décision du tribunal, en cases à cocher : présence, provisions et montant, suspension de la clause résolutoire, accord de délai 12 / 24 mois / autre, résiliation, expulsion, délais de paiement, délais pour quitter les lieux, rejet.

La **fiche CAF** « Prévention de l'expulsion domiciliaire » est stockée en JSON (`caf`), avec ses rubriques : identification, situation familiale et professionnelle, ressources, prestations, logement, FSL, commentaire. On peut ainsi ajouter une rubrique sans migration.

`EtapeExpulsion` tient le **journal de la procédure** : signalement, commandement de payer, assignation, DSF transmis, audience, jugement, signification, plan d'apurement, commandement de quitter les lieux, demande de CFP, commission préfectorale, CFP accordé, expulsion, relogement, autre.

Chaque étape a une date, une échéance éventuelle et un commentaire.
- **Échéances proposées** quand le champ est laissé vide : commandement de payer → 6 semaines ; commandement de quitter les lieux → 2 mois. Elles restent modifiables.
- Une échéance s'affiche dans « À faire » 15 jours avant, jusqu'à ce qu'elle soit marquée traitée.
- **Trêve hivernale** (1er novembre – 31 mars) : un bandeau s'affiche dans la liste et sur les dossiers au stade du commandement de quitter les lieux ou du CFP.

**Alertes** (`alertes()`) :
- dossier à affecter ;
- référent à désigner ;
- audience dans les 30 jours ;
- audience passée sans décision saisie ;
- échéance proche.

## Notifications (messagerie de CID)

- Affectation ou réaffectation par le SL → le **responsable de la MDS** est prévenu. Ce message remplace le PDF envoyé par mail.
- Référent désigné → le **référent** est prévenu.
- Décision saisie ou dossier clos par la MDS → les **agents du SL** sont prévenus.

## PDF

**Fiche de liaison PDF** (`logement/services/expulsion_pdf.py`) : la page 1 reprend la fiche de liaison, la page 2 la fiche CAF.
- Les fiches de liaison et CAF sont des documents locaux (CD 13 / CAF 13). CID produit une trame avec les mêmes rubriques ; aucune fiche réelle n'est publiée.
- Les coordonnées du SL imprimées sur la fiche viennent du paramètre `SERVICE_LOGEMENT_COORDONNEES` (*Admin → Configuration*), jamais du code.

## Formulaires et courriers (règle retenue)

- **Formulaires nationaux** (Cerfa du diagnostic social et financier) : documents publics, livrés avec CID.
- **Courriers** (convocations, relances, actualisation) : modèles en administration, modifiables par territoire.
- **Fiches locales** (fiche de liaison, fiche CAF, questionnaire bailleur, bordereau de carence) : déposées en administration. Sinon CID produit une trame.

## Statistiques

*Expulsions → Statistiques* :
- dossiers en cours et clos ;
- dossiers à affecter, référent à désigner, audiences dans les 30 jours ;
- dette moyenne ;
- répartition par MDS, par étape (dernière étape saisie), par origine, par motif de clôture.

Le SL et son secrétariat voient tout le Département ; une MDS voit ses dossiers. **Aucun chiffre par agent.**

## Travail de la MDS : convocations, questionnaire bailleur, DSF, carence (2e PR)

**Délais du DSF (jours ouvrés, hors week-end et fériés)** — `services/jours_ouvres.py`, `DossierExpulsion.echeances_dsf()` :
- entretien proposé au locataire : 15 jours ouvrés après le signalement ;
- nouvel entretien si pas de réponse : 15 jours ouvrés avant l'audience ;
- CCAPEX locale, si elle suit le ménage : 10 jours ouvrés avant l'audience ;
- transmission du DSF ou du bordereau au juge et à la CCAPEX : 5 jours ouvrés avant l'audience.
Ces échéances apparaissent dans les alertes du dossier, tant que l'audience est à venir et que l'action n'est pas faite.
Points à trancher : la note locale de Marseille (dsf.marseille) parle de 15 jours avant l'audience pour la transmission.

Bloc **Diagnostic social et financier** du dossier (`logement/views/v_expulsion_mds.py`, `services/expulsion_mds.py`).

**Convocations** (`ConvocationExpulsion`)
- Une 1re convocation, puis une 2e et dernière. Chacune pose un rendez-vous (`planning.CreneauRdv`, réservé, hors permanence) dans l'agenda de l'agent qui reçoit.
- Venu, absent ou annulé : la convocation et le rendez-vous suivent.
- Courriers `EXP_CONVOCATION_DSF` et `EXP_CONVOCATION_DSF_2`, textes génériques modifiables dans *Admin → Modèles de courriers*. Ils sont signés par le responsable de la MDS. On n'y met jamais le mail d'un agent, seulement le téléphone de la MDS.

**Questionnaire au bailleur**
- On fixe une date de retour (CID propose 15 jours, au plus tard une semaine avant l'audience) et le mail du bailleur s'il est connu.
- Le courrier `EXP_QUESTIONNAIRE_BAILLEUR` et le questionnaire partent par « Envoi par mail » ou « Imprimer pour envoi ».
- Le questionnaire local se dépose en administration (code `EXP_QUEST_BAILLEUR`) ; sinon CID produit une trame aux mêmes rubriques, avec l'adresse de la MDS.
- « Retour reçu » note la date de réception.

**DSF** (`DiagnosticExpulsion`, type DSF)
- Le Cerfa 16227*01 (formulaire national) est **livré avec CID** (`logement/formulaires/`). Une version plus récente peut être déposée en administration (code `EXP_DSF`).
- Les données sont saisies dans CID sous les noms des champs du Cerfa (`services/dsf.py`), puis le Cerfa est rempli :
  - la notice (5 pages) est retirée ;
  - totaux, reste à vivre et taux d'effort sont calculés par CID ;
  - les dates et l'heure « en peigne » sont gérées ;
  - les cases cochées sont retrouvées même quand leurs noms sont mal encodés dans le PDF.
- **Prérempli** depuis :
  - le dossier : identité, adresse, dette, loyer et charges, bail, type de bailleur, audience ;
  - la fiche usager et sa composition familiale ;
  - le budget du foyer (mêmes rubriques que le Cerfa) ;
  - le FSL maintien et la demande de logement social ;
  - le rédacteur (mail de la MDS).

**Bordereau de carence** (`DiagnosticExpulsion`, type CARENCE)
- Il est proposé quand trois critères sont réunis (note MDS du 27/03/2023) : deux convocations DSF sans présence du
  locataire ; aucune observation du locataire (case « observations du locataire » de la fiche du dossier) ; bailleur
  sollicité (questionnaire envoyé) et sans information (pas de questionnaire retour). La CCAPEX n'est pas un critère :
  une absence de réponse du service public ne bloque pas la carence (`services/expulsion_mds.criteres_carence`).
- CID reprend les dates non honorées, le **n° EXPLOC** (nouveau champ du dossier) et le n° allocataire.
- Formulaire local en administration (code `EXP_CARENCE`), sinon trame CID.

**Visa et transmission**
- Visa du cadre en un clic, comme pour le FSL : « Visa initiales le jj/mm/aaaa » en bas du document, et signature numérisée si elle est validée.
- Une modification après le visa annule le visa.
- L'envoi est réservé aux documents visés. Les adresses du greffe et de la préfecture se règlent dans *Admin → Destinataires des diagnostics*, éventuellement par MDS.
- Le Service Logement est prévenu ; l'étape « DSF transmis » ou « Bordereau de carence transmis » s'ajoute au journal.
- Chaque envoi par mail compte dans le papier économisé.

## Commissions : CAPEX locale, commission préfectorale, CCAPEX (3e PR)

- **Séances** (`CommissionExpulsion`) :
  - champs : instance, nom, date, heure, lieu, date limite des actualisations, mail du secrétariat, MDS concernées ;
  - créées par le Service Logement ou par le cadre (`peut_valider`) d'une MDS concernée ;
  - le SL voit toutes les séances, une MDS celles qui la concernent ou celles qui n'ont pas de MDS précisée.
- **Ordre du jour** (`PassageCommission`) :
  - on inscrit un dossier en cours depuis la séance ou depuis le dossier ; le référent est prévenu ;
  - PDF en paysage : n° de dossier, ménage, commune, MDS, référent, étape, dette, état de l'actualisation, avis ;
  - jamais de données de santé ni de détail de l'évaluation ; chacun ne voit que les dossiers auxquels il a accès.
- **Actualisation** (rubriques de la fiche locale « Actualisation pour commission expulsion », trame CID) :
  - préremplie avec les rencontres (convocations honorées), l'accompagnant, le ménage et le bailleur, la composition familiale, les revenus du budget du foyer, le logement, la dette, l'historique des étapes, les FSL et plans d'apurement, et l'évaluation du dernier DSF à actualiser ;
  - visa du cadre en un clic, puis envoi par mail au secrétariat de la séance (ou impression) ;
  - une modification après le visa annule le visa.
- **Convocations avant commission** : modèles `EXP_CONVOCATION_COMMISSION` et `EXP_RELANCE_COMMISSION`, avec rendez-vous dans l'agenda. Elles ne comptent pas pour le bordereau de carence, qui ne regarde que les convocations au DSF.
- **Avis** : le Service Logement ou le cadre saisit l'avis et les préconisations.
  - Choix possibles : maintien et plan à respecter, délai, orientation, avis favorable ou défavorable au concours de la force publique, ajourné, autre.
  - L'étape « CAPEX locale » ou « Commission préfectorale » s'ajoute au dossier, et le référent (puis le SL) est prévenu.
  - La séance se marque « tenue » avec ses observations.
- **Passerelles** : quand l'usager est rattaché et que l'agent a accès à sa fiche, le dossier propose FSL maintien ou concordat, saisine COPP et demande de logement social, préremplis.
- **Statistiques** : diagnostics et bordereaux de carence transmis, avis des commissions.

Import de la liste des assignations : CID ne reçoit pas le fichier aujourd'hui (le SL l'importe dans le logiciel actuel). Un import pourra être ajouté quand le format sera connu (en-têtes seulement, jamais de données réelles).
