# Relation Usager (RU)

Le SAS (Service d'Action Sociale) est le service départemental qui reçoit les demandes ; la logique du circuit reste la même dans tous les Départements. Le module `ru` reprend la note de procédure n° 39 du 19 mai 2022 et ses annexes, dont le modèle `RapportsocialàtransmettreauSAS.dotm` fourni dans cette demande. L'objectif est le transfert d'information dans CID et le PDF comme support prioritaire; l'impression reste possible, sans constituer le parcours normal.

## Parcours et notifications

1. Le SAS enregistre la demande, indique si elle relève d'une réponse directe ou d'une évaluation MDS, puis choisit la MDS et le travailleur social destinataire. Le bouton **Transmettre à la MDS choisie** fixe la date de notification, déclenche le délai et crée un message interne CID à destination de l'agent.
2. Le travailleur social renseigne la demande, l'évaluation synthétique, les démarches, la situation actualisée, le plan, les aides et les rendez-vous. Le bouton **Transmettre au cadre pour validation** fait passer le dossier dans la file du cadre et l'avertit par la messagerie CID.
3. Le cadre valide l'évaluation. CID conserve ses initiales, l'agent signataire et l'horodatage; l'action **Valider et transmettre au SAS** crée un message interne à destination des profils SAS RU habilités.
4. Le SAS complète le masque **Fiche retour SAS**, produit son PDF, puis confirme la transmission à l'usager et au service émetteur dans CID. Cette confirmation clôt le dossier dans l'application.

Les messages internes transportent la référence et un lien vers le dossier; ils ne recopient pas le récit social. Ils ne remplacent pas l'envoi externe. CID n'envoie pas automatiquement de courriel ou de courrier. La validation enregistrée est une signature de workflow (initiales, identité et heure), et non une signature électronique qualifiée. Le format nominatif `initiale + nom` d'AFASE est réutilisé par un helper commun; AFASE conserve son horodatage existant.

## Saisie, TERU et rendez-vous

La fiche numérique reprend les champs du modèle fourni : numéro de dossier et SAP, MDS, dates de transmission et de clôture, identité et adresse, transmission, motif et priorité, situation familiale, nombre d'enfants, revenu principal, âge, premier et second rendez-vous et absences, demande de l'usager, problématique/plan, AMASE ou SAA, montants, dates, motif de rejet, travailleur social et visa du cadre. Les informations de liaison et de contact sont aussi tracées dans CID pour soutenir le traitement.

Le TERU est téléchargeable en PDF depuis le dossier. Le travailleur social saisit les dates et heures de rendez-vous; CID peut générer un PDF de convocation pour le premier rendez-vous puis, après absence au premier, pour le second. La génération du fichier est journalisée, mais ne marque pas le courrier comme expédié : l'agent vérifie et transmet le PDF selon les pratiques du service.

Le masque de saisie **Fiche retour SAS** est une fiche de réponse générique opérationnelle, faute de modèle distinct fourni pour ce document. Elle distingue réponse directe, réponse après évaluation MDS, réorientation ou autre suite et propose une sortie PDF. Son contenu pourra être rapproché d'un formulaire officiel si une annexe dédiée est disponible.

## Délais et relances

Le délai de la note court depuis l'envoi effectif du SAS à la MDS : un mois calendaire pour une demande ordinaire, 15 jours calendaires pour une demande signalée/urgente. Pour une demande reçue directement par une MDS, la réception sert de point de départ. La date est affichée au dossier; week-ends et jours fériés ne sont pas retranchés, la note ne donnant pas de convention de jours ouvrés. Le SAS peut enregistrer des relances manuelles lorsque la demande est en retard; à la troisième, CID envoie un message interne au responsable MDS ou, à défaut, à un cadre habilité, et trace le résultat dans l'historique. Si aucun destinataire habilité n'est configuré, l'historique le signale explicitement. Aucun rappel automatique n'est déclenché.

## Habilitations, GED et activation

Les agents MDS doivent disposer de `peut_voir` et d'un rattachement actif au territoire concerné; la création MDS demande aussi `peut_creer`. La validation du cadre requiert `peut_valider` dans la MDS. La gestion transversale SAS est isolée dans la capacité `ru_gerer_sas` et le profil initialisable `RU_SAS`. Un administrateur attribue ce profil uniquement aux agents SAS habilités. Le superutilisateur conserve les droits d'administration.

Les pièces jointes sont limitées au PDF et versées dans la GED avec le type sensible `RU_PJ`; les contrôles d'accès s'appuient sur le droit de voir la demande. Après déploiement, exécuter `python manage.py migrate`, puis `python manage.py init_profils` pour créer/actualiser le profil `RU_SAS` et les capacités métier.
