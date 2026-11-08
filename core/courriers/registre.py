# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/courriers/registre.py
"""
Liste des courriers dont le texte se modifie en administration (Modèles de courriers).

Pour chaque courrier : ses variables (remplies par CID à partir du dossier), ses conditions ({si_…:…|…}),
des valeurs d'exemple pour l'aperçu, et son texte par défaut. Les textes par défaut sont ceux que CID
produisait avant les modèles : tant que personne ne les modifie, les courriers restent identiques.
Ce sont des textes génériques, écrits pour CID : le texte officiel d'une collectivité se saisit dans
l'administration de son propre serveur (ou s'importe en JSON), jamais dans le dépôt de code.

Ajouter un courrier : une entrée ici, puis, dans le service qui fabrique le PDF, appeler
core.courriers.modele_texte(code) et construire les valeurs (voir AidFi/services/afase_documents.py).
"""

# Variables communes
_DESTINATAIRE = {
    "civilite_appel": ("Madame ou Monsieur, selon la civilité du destinataire", "Madame"),
}
_FONDEMENT = {
    "fondement_juridique": ("Fondement juridique (Paramètres des aides financières)",
                            "Articles L.222-2 à L.222-4 du code de l'action sociale et des familles."),
    "voies_recours": ("Voies et délais de recours (Paramètres des aides financières)",
                      "Vous pouvez contester cette décision dans un délai de deux mois…"),
}
_AFASE = {
    "numero_dossier": ("Numéro du dossier d'aide", "1042"),
    "date_demande": ("Date de la demande (signature du demandeur)", "12/10/2026"),
    "date_recours": ("Date du recours, si la demande fait suite à un recours", "02/09/2026"),
    "date_decision": ("Date de la décision", "20/10/2026"),
    "enfants": ("Enfants concernés (ou « vos enfants »)", "Léa EXEMPLE, Tom EXEMPLE"),
    "signataire": ("Nom du cadre qui a décidé", "Cadre Exemple"),
    "signataire_fonction": ("Fonction du cadre qui a décidé (fiche de l'agent ; vide si non renseignée)",
                            "Directrice de la MDS de territoire Exemple"),
}
_AFASE_CONDITIONS = {"si_recours": "la demande fait suite à un recours"}

_SIGNATURE_AFASE = "Pour le Président du Conseil départemental\net par délégation,\n\n{signataire}\n{signataire_fonction}"
_FIN_AFASE = ("[petit]Décision prise en application des textes suivants : {fondement_juridique}[/petit]\n\n"
              "**Voies et délais de recours :** {voies_recours}\n\n"
              "Je vous prie d'agréer, {civilite_appel}, l'expression de mes salutations distinguées.")
_SUITE_AFASE = ("{si_recours:Suite à votre demande du {date_demande} et à votre recours du {date_recours}"
                "|Suite à votre demande du {date_demande}}")

_IP = {
    "numero_ip": ("Référence de l'IP", "D13-00000124"),
    "salutation": ("« Madame, », « Monsieur, » ou « Madame, Monsieur, »", "Madame, Monsieur,"),
    "salutation_courte": ("La même, sans la virgule (formule de fin)", "Madame, Monsieur"),
    "date_rdv": ("Date et heure de la convocation", "12/11/2026 à 10:00"),
    "lieu": ("MDS : nom et adresse", "MDS Exemple, 1 rue de l'Exemple, 13000 Exemple"),
}
_IP_ENFANTS = {
    "vos_enfants": ("« votre enfant Prénom NOM » ou « vos enfants … »", "vos enfants Léa EXEMPLE, Tom EXEMPLE"),
    "Vos_enfants": ("La même, avec une majuscule (début de phrase)", "Vos enfants Léa EXEMPLE, Tom EXEMPLE"),
}
_IP_ADULTES = {
    "enfants_ip": ("Enfants de l'IP, avec leur date de naissance", "Léa EXEMPLE (né(e) le 03/04/2016)"),
}
_IP_PRECEDENTE = {"date_precedente": ("Date de la convocation précédente", "05/11/2026 à 14:00")}
_C_PLUSIEURS = {"si_plusieurs_enfants": "plusieurs enfants sont convoqués"}
_C_REPORT = {"si_report_convenu": "la nouvelle date a été convenue avec la famille"}
_C_PRECEDENTE = {"si_date_precedente": "la date de la convocation précédente est connue"}

_EMPECHEMENT = ("En cas d'empêchement, merci de nous contacter au plus vite pour convenir d'une autre date.\n\n"
                "Nous vous prions d'agréer, {salutation_courte}, nos salutations distinguées.")
_OBLIGATOIRE = ("Nous vous rappelons que cette évaluation est obligatoire. À défaut de pouvoir la mener avec vous, "
                "le rapport sera établi avec les seuls éléments recueillis et transmis à l'inspecteur enfance "
                "famille du Département, qui pourra décider de saisir l'autorité judiciaire.")
_CONVOCATION_ENFANTS = ("Dans le cadre de l'information préoccupante, {vos_enfants} "
                        "{si_plusieurs_enfants:sont convoqués|est convoqué(e)} le **{date_rdv}**, à {lieu}.\n\n"
                        "{si_plusieurs_enfants:Les enfants sont reçus un par un par les professionnels ; merci de les "
                        "accompagner. Les adultes qui les accompagnent patientent en salle d'attente."
                        "|L'enfant est reçu seul par les professionnels ; merci de l'accompagner. "
                        "L'adulte qui l'accompagne patiente en salle d'attente.}")
_CONVOCATION_ADULTES = ("Dans le cadre de l'information préoccupante concernant {enfants_ip}, "
                        "vous êtes convoqué(e) le **{date_rdv}**, à {lieu}.")
_PRECEDENTE = "{si_date_precedente:à la convocation du {date_precedente}|à la précédente convocation}"
_REPORT = "{si_report_convenu:Comme convenu avec vous, nous vous adressons la nouvelle date de convocation.}"
_OBJET_IP = "convocation – information préoccupante réf. {numero_ip}"


_RSA = {
    "civilite_appel": ("Madame ou Monsieur, selon la civilité du bénéficiaire", "Madame"),
    "beneficiaire": ("Prénom et NOM du bénéficiaire", "Lucie EXEMPLE"),
    "date_naissance": ("Date de naissance du bénéficiaire", "03/04/1990"),
    "nom_contrat": ("Nom du contrat (Paramètres du contrat RSA)", "Contrat d'engagement"),
    "numero_contrat": ("Numéro du contrat dans CID", "C2026-00012"),
    "pole": ("Nom du pôle insertion", "Pôle insertion Exemple"),
    "referent": ("Nom du référent", "Agent Exemple"),
    "mds": ("MDS du référent", "MDS Exemple"),
}

_EXP = {
    "civilite_appel": ("Madame ou Monsieur, selon la civilité du locataire", "Madame"),
    "locataire": ("Prénom et NOM du locataire", "Lucie EXEMPLE"),
    "adresse_locataire": ("Adresse du logement", "1 rue de l'Exemple, 13000 Exemple"),
    "date_audience": ("Date de l'audience", "28/11/2026"),
    "tribunal": ("Tribunal (dossier d'expulsion)", "Tribunal judiciaire d'Exemple"),
    "mds": ("MDS : nom et adresse", "MDS Exemple, 1 rue de l'Exemple, 13000 Exemple"),
    "telephone_mds": ("Téléphone de la MDS", "04 00 00 00 00"),
    "signataire": ("Responsable de la MDS", "Cadre Exemple"),
    "signataire_fonction": ("Fonction du responsable (fiche de l'agent)", "Responsable de la MDS Exemple"),
}
_EXP_RDV = {
    "date_rdv": ("Date et heure du rendez-vous", "12/11/2026 à 10:00"),
    "lieu": ("Lieu du rendez-vous (la MDS par défaut)", "la MDS Exemple, 1 rue de l'Exemple, 13000 Exemple"),
    "agent": ("Travailleur social qui reçoit", "Agent Exemple"),
}
_EXP_C = {"si_tribunal": "le tribunal est indiqué au dossier", "si_audience": "la date d'audience est connue"}
_EXP_PIECES = ("Merci d'apporter les documents concernant votre situation familiale et financière, votre logement "
               "et vos dettes : ils seront joints au diagnostic.")
_EXP_EMPECHEMENT = ("En cas d'empêchement, contactez-nous au {telephone_mds} ou adressez-nous vos observations par "
                    "écrit : elles seront transmises au tribunal. Sans nouvelles de votre part, nous transmettrons les "
                    "informations les plus récentes dont nous disposons sur votre situation.")
_EXP_AUDIENCE = ("Lors de l'audience du {date_audience}, le juge peut prononcer la résiliation de votre bail : votre "
                 "présence est indispensable pour faire valoir vos arguments.")
_EXP_SIGNATURE = "{signataire}\n{signataire_fonction}"

COURRIERS = {
    # ------------------------------------------------------------------ AFASE
    "AFASE_ACCORD": {
        "rubrique": "AFASE", "libelle": "Notification d'une AFASE accordée",
        "variables": {**_DESTINATAIRE, **_AFASE, **_FONDEMENT,
                      "montant_mensuel": ("Montant mensuel accordé", "150,00 €"),
                      "duree_mois": ("Durée en mois", "3"),
                      "montant_total": ("Montant total (mensuel × durée)", "450,00 €"),
                      "objet_aide": ("Objet de l'aide (libellé de la décision)", "Soutien alimentaire"),
                      "organisme_paiement": ("Organisme payé, si versement à un tiers", "Épicerie solidaire (exemple)")},
        "conditions": {**_AFASE_CONDITIONS, "si_versement_organisme": "l'aide est versée à un organisme"},
        "objet": "votre demande d'allocation financière de l'aide sociale à l'enfance (dossier n° {numero_dossier})",
        "corps": ("{civilite_appel},\n\n"
                  + _SUITE_AFASE + ", j'ai le plaisir de vous informer qu'une allocation financière de "
                  "l'aide sociale à l'enfance vous est accordée pour {enfants} :\n\n"
                  "**{montant_mensuel} par mois pendant {duree_mois} mois** (versement mensuel), "
                  "soit {montant_total} au total, au titre de : **{objet_aide}**.\n\n"
                  "{si_versement_organisme:Elle sera versée à {organisme_paiement}, comme vous l'avez autorisé."
                  "|Elle sera versée sur votre compte bancaire.}\n\n" + _FIN_AFASE),
        "signature": _SIGNATURE_AFASE,
    },
    "AFASE_REFUS": {
        "rubrique": "AFASE", "libelle": "Notification d'une AFASE refusée",
        "variables": {**_DESTINATAIRE, **_AFASE, **_FONDEMENT,
                      "motif_refus": ("Texte du motif de refus (Motifs de refus AFASE), avec sa précision",
                                      "Votre demande relève d'un autre dispositif.")},
        "conditions": dict(_AFASE_CONDITIONS),
        "objet": "votre demande d'allocation financière de l'aide sociale à l'enfance (dossier n° {numero_dossier})",
        "corps": ("{civilite_appel},\n\n"
                  + _SUITE_AFASE + ", j'ai le regret de vous informer que je ne peux pas y donner "
                  "une suite favorable, pour le motif suivant :\n\n**{motif_refus}**\n\n" + _FIN_AFASE),
        "signature": _SIGNATURE_AFASE,
    },
    # ------------------------------------------------------------------ IP : convocations
    "IP_CONVOCATION_ADULTES": {
        "rubrique": "Informations préoccupantes", "libelle": "Convocation d'un adulte (audition des parents)",
        "variables": {**_IP, **_IP_ADULTES}, "conditions": dict(_C_REPORT),
        "objet": _OBJET_IP,
        "corps": "{salutation}\n\n" + _REPORT + "\n\n" + _CONVOCATION_ADULTES + "\n\n" + _EMPECHEMENT,
    },
    "IP_CONVOCATION_ENFANTS": {
        "rubrique": "Informations préoccupantes", "libelle": "Convocation des enfants (adressée à l'adulte qui les héberge)",
        "variables": {**_IP, **_IP_ENFANTS}, "conditions": {**_C_PLUSIEURS, **_C_REPORT},
        "objet": _OBJET_IP,
        "corps": "{salutation}\n\n" + _REPORT + "\n\n" + _CONVOCATION_ENFANTS + "\n\n" + _EMPECHEMENT,
    },
    "IP_LRAR_ADULTES": {
        "rubrique": "Informations préoccupantes", "libelle": "Relance en recommandé d'un adulte absent",
        "variables": {**_IP, **_IP_ADULTES, **_IP_PRECEDENTE}, "conditions": dict(_C_PRECEDENTE),
        "objet": _OBJET_IP,
        "corps": ("{salutation}\n\nVous ne vous êtes pas présenté(e) " + _PRECEDENTE + ".\n\n"
                  + _CONVOCATION_ADULTES + "\n\n" + _OBLIGATOIRE + "\n\n" + _EMPECHEMENT),
    },
    "IP_LRAR_ENFANTS": {
        "rubrique": "Informations préoccupantes", "libelle": "Relance en recommandé : enfants absents",
        "variables": {**_IP, **_IP_ENFANTS, **_IP_PRECEDENTE}, "conditions": {**_C_PLUSIEURS, **_C_PRECEDENTE},
        "objet": _OBJET_IP,
        "corps": ("{salutation}\n\n{Vos_enfants} {si_plusieurs_enfants:ne se sont pas présentés|ne s’est pas présenté(e)} "
                  + _PRECEDENTE + ".\n\n" + _CONVOCATION_ENFANTS + "\n\n" + _OBLIGATOIRE + "\n\n" + _EMPECHEMENT),
    },
    # ------------------------------------------------------------------ RSA – Insertion
    "RSA_CERTIFICAT_MEDECIN": {
        "rubrique": "RSA – Insertion", "libelle": "Contrat santé : demande de certificat au médecin traitant",
        "variables": {**_RSA,
                      "adresse_pli": ("Adresse du médecin du pôle, pour l'envoi sous pli cacheté",
                                      "Médecin du pôle insertion, 1 rue de l'Exemple, 13000 Exemple"),
                      "adresse_mssante": ("Adresse MSSanté du médecin du pôle", "medecin.pole@exemple.mssante.fr")},
        "conditions": {"si_mssante": "le pôle a une adresse MSSanté"},
        "objet": "certificat médical – {nom_contrat} de {beneficiaire}",
        "corps": ("Docteur,\n\n"
                  "Votre patient(e) {beneficiaire}, né(e) le {date_naissance}, bénéficiaire du RSA, prépare avec "
                  "son référent un {nom_contrat} orienté vers la santé.\n\n"
                  "Pour que ce contrat puisse être validé, le médecin du pôle insertion a besoin d'un certificat "
                  "médical de votre part, indiquant si l'état de santé de votre patient(e) justifie, pour la durée "
                  "du contrat, un parcours centré sur la santé plutôt que sur l'emploi.\n\n"
                  "Ce certificat est couvert par le secret médical. Il est adressé au seul médecin du pôle :\n\n"
                  "{si_mssante:**par messagerie sécurisée de santé (MSSanté) : {adresse_mssante}**, ou sous pli "
                  "cacheté portant la mention « Confidentiel – secret médical » à : {adresse_pli}"
                  "|**sous pli cacheté** portant la mention « Confidentiel – secret médical », à : {adresse_pli}}\n\n"
                  "Le référent et les services administratifs n'ont connaissance que de l'avis du médecin du pôle "
                  "(favorable ou défavorable), jamais du contenu du certificat.\n\n"
                  "Je vous remercie de votre collaboration et vous prie d'agréer, Docteur, l'expression de mes "
                  "salutations distinguées."),
        "signature": "{referent}\nRéférent, {mds}",
    },
    "RSA_INVITATION_RDV": {
        "rubrique": "RSA – Insertion", "libelle": "Invitation à prendre en ligne le rendez-vous de renouvellement du contrat",
        "variables": {**_RSA,
                      "date_fin": ("Fin du contrat en cours", "30/11/2026"),
                      "lien": ("Lien personnel de réservation (aussi en QR code)", "https://rdv-solidarites.fr/prendre_rdv?…"),
                      "delai_min": ("Délai minimum de réservation, en heures", "48"),
                      "delai_max": ("Délai maximum de réservation, en jours", "15")},
        "conditions": {},
        "objet": "renouvellement de votre {nom_contrat} : prenez rendez-vous en ligne",
        "corps": ("{civilite_appel},\n\n"
                  "Votre {nom_contrat} (n° {numero_contrat}) arrive à échéance le **{date_fin}**. Pour préparer son "
                  "renouvellement avec {referent}, vous pouvez choisir vous-même votre rendez-vous à la {mds}, "
                  "en ligne, à l'adresse suivante :\n\n"
                  "{lien}\n\n"
                  "ou en scannant le code ci-dessous avec votre téléphone. Le rendez-vous se réserve au moins "
                  "{delai_min} heures et au plus {delai_max} jours à l'avance.\n\n"
                  "Ce lien vous est personnel : ne le transmettez pas. Si vous ne pouvez pas réserver en ligne, "
                  "contactez l'accueil de la {mds}.\n\n"
                  "Je vous prie d'agréer, {civilite_appel}, l'expression de mes salutations distinguées."),
        "signature": "{referent}\nRéférent, {mds}",
    },
    "RSA_NOTIFICATION_DECISION": {
        "rubrique": "RSA – Insertion", "libelle": "Notification au bénéficiaire de la décision sur son contrat",
        "variables": {**_RSA,
                      "date_decision": ("Date de la commission", "20/10/2026"),
                      "date_debut": ("Début du contrat validé", "01/11/2026"),
                      "date_fin": ("Fin du contrat validé", "30/04/2027"),
                      "duree_mois": ("Durée validée en mois", "6"),
                      "actions_non_retenues": ("Actions non retenues et leur motif", "Atelier Exemple (places complètes)"),
                      "motif": ("Motif de l'ajournement ou de la non-validation", "Objectifs à préciser avec le référent"),
                      "date_renouvellement": ("Date à laquelle préparer le renouvellement (un mois avant la fin)",
                                              "31/03/2027"),
                      "signataire": ("Nom du cadre du pôle qui a décidé", "Cadre Exemple")},
        "conditions": {"si_valide": "le contrat est validé (avec ou sans réserve)",
                       "si_sauf_action": "le contrat est validé sauf une action",
                       "si_ajourne": "le contrat est ajourné",
                       "si_non_valide": "le contrat n'est pas validé",
                       "si_transport_accorde": "l'aide aux transports est accordée",
                       "si_transport_refuse": "l'aide aux transports est refusée"},
        "objet": "votre {nom_contrat} (n° {numero_contrat})",
        "corps": ("{civilite_appel},\n\n"
                  "Votre {nom_contrat}, préparé avec {referent} ({mds}), a été examiné par la commission du "
                  "{date_decision}.\n\n"
                  "{si_valide:Il est **validé pour {duree_mois} mois, du {date_debut} au {date_fin}**.}\n\n"
                  "{si_sauf_action:Une action n'a pas été retenue : {actions_non_retenues}. Votre référent "
                  "reprendra ce point avec vous d'ici la fin du contrat.}\n\n"
                  "{si_ajourne:Il est **ajourné** : {motif}. Votre référent reprendra le contrat avec vous.}\n\n"
                  "{si_non_valide:Il n'est **pas validé** : {motif}. Votre référent prendra contact avec vous.}\n\n"
                  "{si_transport_accorde:L'aide aux transports demandée vous est accordée pour la durée du contrat.}\n\n"
                  "{si_transport_refuse:L'aide aux transports demandée ne vous est pas accordée.}\n\n"
                  "{si_valide:Comme vous vous y êtes engagé(e), pensez à préparer le renouvellement de votre contrat "
                  "avec votre référent à partir du {date_renouvellement}.}\n\n"
                  "Je vous prie d'agréer, {civilite_appel}, l'expression de mes salutations distinguées."),
        "signature": "Pour le Président du Conseil départemental\net par délégation,\n\n{signataire}\n{pole}",
    },
    "RSA_NOTIFICATION_REORIENTATION": {
        "rubrique": "RSA – Insertion", "libelle": "Notification au bénéficiaire de la décision de réorientation",
        "variables": {
            "civilite_appel": ("Madame ou Monsieur, selon la civilité du bénéficiaire", "Madame"),
            "beneficiaire": ("Prénom et NOM du bénéficiaire", "Lucie EXEMPLE"),
            "date_commission": ("Date de la commission de réorientation", "15/01/2027"),
            "organisme": ("Nouveau référent RSA (organisme retenu)", "France Travail"),
            "coordonnees_organisme": ("Adresse et téléphone de l'organisme", "1 rue de l'Exemple – 13000 Exemple"),
            "date_effet": ("Date d'effet de la réorientation", "01/02/2027"),
            "motif": ("Motif de la décision", "Projet professionnel défini"),
            "referent": ("Nom du référent actuel", "Agent Exemple"),
            "mds": ("MDS du référent actuel", "MDS Exemple"),
            "pole": ("Nom du pôle insertion", "Pôle insertion Exemple"),
            "signataire": ("Agent du pôle qui a noté la décision", "Cadre Exemple"),
        },
        "conditions": {"si_acceptee": "la réorientation est acceptée", "si_refusee": "la réorientation est refusée"},
        "objet": "votre accompagnement au titre du RSA",
        "corps": ("{civilite_appel},\n\n"
                  "Votre situation a été examinée par la commission de réorientation du {date_commission}.\n\n"
                  "{si_acceptee:Vous êtes désormais accompagné(e) par **{organisme}**, à compter du {date_effet}. "
                  "Cet organisme devient votre référent pour le RSA et prendra contact avec vous.}\n\n"
                  "{si_acceptee:Coordonnées : {coordonnees_organisme}}\n\n"
                  "{si_refusee:Votre accompagnement se poursuit avec {referent} ({mds}). Motif : {motif}}\n\n"
                  "Je vous prie d'agréer, {civilite_appel}, l'expression de mes salutations distinguées."),
        "signature": "Pour le Président du Conseil départemental\net par délégation,\n\n{signataire}\n{pole}",
    },
    # ------------------------------------------------------------------ Logement – prévention des expulsions
    "EXP_CONVOCATION_DSF": {
        "rubrique": "Logement – prévention des expulsions",
        "libelle": "1re convocation pour le diagnostic social et financier (DSF)",
        "variables": {**_EXP, **_EXP_RDV}, "conditions": dict(_EXP_C),
        "objet": "diagnostic social et financier – audience du {date_audience}",
        "corps": ("{civilite_appel},\n\n"
                  "Vous êtes assigné(e) devant {si_tribunal:le {tribunal}|le tribunal} pour des impayés de loyer. "
                  "Dans le cadre de la prévention des expulsions locatives, un diagnostic social et financier (DSF) "
                  "est établi avant l'audience : il apporte au juge les éléments de votre situation pour l'aider "
                  "dans sa décision.\n\n"
                  "Cet entretien est aussi l'occasion de rechercher avec vous des solutions et les aides dont vous "
                  "pourriez bénéficier pour résorber votre dette de loyer. C'est pourquoi nous vous proposons un "
                  "rendez-vous le **{date_rdv}**, à {lieu}, avec {agent}.\n\n"
                  + _EXP_PIECES + "\n\n" + _EXP_EMPECHEMENT + "\n\n" + _EXP_AUDIENCE + "\n\n"
                  "Nous vous prions d'agréer, {civilite_appel}, l'expression de nos salutations distinguées."),
        "signature": _EXP_SIGNATURE,
    },
    "EXP_CONVOCATION_DSF_2": {
        "rubrique": "Logement – prévention des expulsions",
        "libelle": "2e et dernière convocation pour le diagnostic social et financier",
        "variables": {**_EXP, **_EXP_RDV,
                      "date_precedente": ("Date du rendez-vous proposé la première fois", "05/11/2026 à 14:00")},
        "conditions": dict(_EXP_C),
        "objet": "diagnostic social et financier – audience du {date_audience}",
        "corps": ("{civilite_appel},\n\n"
                  "Nous vous avions proposé un rendez-vous le {date_precedente} au sujet de votre assignation "
                  "devant le tribunal pour des impayés de loyer.\n\n"
                  "Le diagnostic social et financier doit être transmis au juge, que vous soyez présent(e) ou non à "
                  "l'entretien. Si vous ne vous présentez pas, nous serons tenus d'indiquer votre absence.\n\n"
                  "Nous vous proposons un deuxième et dernier rendez-vous le **{date_rdv}**, à {lieu}, avec {agent}."
                  "\n\n" + _EXP_PIECES + "\n\n" + _EXP_EMPECHEMENT + "\n\n" + _EXP_AUDIENCE + "\n\n"
                  "Nous vous prions d'agréer, {civilite_appel}, l'expression de nos salutations distinguées."),
        "signature": _EXP_SIGNATURE,
    },
    "EXP_QUESTIONNAIRE_BAILLEUR": {
        "rubrique": "Logement – prévention des expulsions",
        "libelle": "Courrier au bailleur accompagnant le questionnaire pour le DSF",
        "variables": {**_EXP, "date_retour": ("Date de retour souhaitée du questionnaire", "20/11/2026")},
        "conditions": dict(_EXP_C),
        "objet": "questionnaire bailleur – diagnostic social et financier",
        "corps": ("Madame, Monsieur,\n\n"
                  "Vous avez assigné votre locataire, {locataire}, résidant {adresse_locataire}, pour des impayés "
                  "de loyer{si_audience: ; l'audience est fixée au {date_audience}|}.\n\n"
                  "Le Département intervient à plusieurs étapes de la prévention des expulsions locatives : le "
                  "travailleur social établit un diagnostic social et financier destiné au juge, qui peut recueillir "
                  "vos observations.\n\n"
                  "Nous vous serions reconnaissants de bien vouloir nous retourner le questionnaire ci-joint, "
                  "complété, ainsi que le décompte locatif à jour, **avant le {date_retour}**, à l'adresse de la "
                  "{mds}.\n\n"
                  "Nous vous prions de recevoir, Madame, Monsieur, nos salutations distinguées."),
        "signature": _EXP_SIGNATURE,
    },
}
CHAMPS = ("objet", "corps", "signature")


def definition(code):
    return COURRIERS[code]


def exemple(code):
    """Valeurs et conditions d'exemple, pour l'aperçu en administration."""
    d = COURRIERS[code]
    return {n: ex for n, (_, ex) in d["variables"].items()}, {c: True for c in d.get("conditions", {})}
