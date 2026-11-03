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
}
_AFASE_CONDITIONS = {"si_recours": "la demande fait suite à un recours"}

_SIGNATURE_AFASE = "Pour le Président du Conseil départemental\net par délégation,\n\n{signataire}"
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
}
CHAMPS = ("objet", "corps", "signature")


def definition(code):
    return COURRIERS[code]


def exemple(code):
    """Valeurs et conditions d'exemple, pour l'aperçu en administration."""
    d = COURRIERS[code]
    return {n: ex for n, (_, ex) in d["variables"].items()}, {c: True for c in d.get("conditions", {})}
