# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/pieces.py
"""Pièces à fournir par type de demande, d'après les argumentaires de pièces manquantes FSL (MDS).

Le cadre coche chaque pièce jointe au formulaire. Une pièce absente se justifie (200 caractères au plus) :
l'envoi reste possible, la justification est tracée."""

COMMUN = [
    ('ETAT_CIVIL', "Justificatifs d'état civil de toutes les personnes du foyer (livret de famille, passeport, CNI, "
                   "titre de séjour pour les étrangers)"),
    ('RESSOURCES_FOYER', "Justificatifs de ressources de toutes les personnes du foyer, du mois précédant la demande"),
    ('RESSOURCES_MAJEURS', "Justificatifs de ressources ou de non-ressources des enfants majeurs (attestation sur "
                           "l'honneur non recevable)"),
    ('RIB', "Relevé d'identité bancaire, postal ou Caisse d'Épargne"),
]

ACCES = COMMUN + [
    ('PRET', "Contrat de prêt signé par le ou les demandeurs"),
    ('PRELEVEMENT', "Autorisation de prélèvement sur compte"),
    ('MISE_EN_JEU', "Contrat de mise en jeu de la garantie (si demandée)"),
    ('BAIL', "Bail daté et signé par les parties (IML : contrat de location)"),
    ('ETAT_LIEUX', "État des lieux signé par le locataire et le bailleur"),
    ('ASSURANCE', "Attestation d'assurance du nouveau logement, avec quittance ou échéancier"),
    ('IDENT_LOGEMENT', "Fiche d'identification du logement, datée et signée par le bailleur"),
    ('CONVENTION_ACCES', "Convention d'accès au logement signée par le ménage et le bailleur"),
    ('VERSEMENT_DIRECT', "Demande de versement direct de l'APL, signée par le bailleur et le locataire"),
]

FLUIDES = COMMUN + [
    ('FACTURE', "Dernière facture impayée (moins de 3 mois, ou moins d'un an en régularisation), relevé de "
                "consommation recto verso"),
    ('QUITTANCE', "Quittance de loyer ou avis d'échéance"),
]

MAINTIEN = COMMUN + [
    ('RELEVE_LOCATAIRE', "Relevé de compte locataire depuis l'origine de la dette (appels de loyer et de charges, "
                         "paiements, solde cumulatif)"),
    ('IDENT_LOGEMENT', "Fiche d'identification du logement, datée et signée par le bailleur privé"),
    ('RIB_BAILLEUR', "Relevé d'identité bancaire du bailleur privé"),
    ('PRET', "Contrat de prêt signé par le ou les demandeurs"),
    ('PRELEVEMENT', "Autorisation de prélèvement sur compte"),
    ('ASSURANCE', "Attestation d'assurance du logement"),
    ('VERSEMENT_DIRECT', "Demande de versement direct de l'allocation logement, signée par le bailleur et le locataire"),
    ('ENGAGEMENTS', "Engagements du locataire et du bailleur, datés et signés"),
    ('CCAPEX', "Justificatif de saisine de la CCAPEX"),
]

PAR_TYPE = {'ACCES': ACCES, 'MAINTIEN': MAINTIEN, 'EAU': FLUIDES, 'ENERGIE': FLUIDES}


def liste_fsl(type_aide):
    """[(code, libellé)] des pièces à cocher pour ce type de demande FSL ; [] si inconnu."""
    return list(PAR_TYPE.get(type_aide, []))


def manquantes(type_aide, cochees):
    """Libellés des pièces non cochées."""
    return [libelle for code, libelle in liste_fsl(type_aide) if code not in set(cochees)]
