# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/indigne.py
"""Fiche de signalement au PDLHI (note n°37, fiche P 5010501X / DECENC) : rubriques saisies dans CID.

Réponses « oui / non / je ne sais pas » conservées comme trois états distincts (ond) ; « bon / mauvais /
je ne sais pas » pour les menuiseries et installations (bmn) ; texte libre sinon (texte)."""

OND = [('oui', "Oui"), ('non', "Non"), ('nsp', "Je ne sais pas")]
BMN = [('bon', "Bon"), ('mauvais', "Mauvais"), ('nsp', "Je ne sais pas")]
STATUT_OCCUPANT = [('locataire', "Locataire"), ('sous_locataire', "Sous-locataire"),
                   ('sans_titre', "Occupant sans titre"), ('proprietaire', "Propriétaire"),
                   ('heberge', "Hébergé à titre gracieux"), ('autre', "Autre")]

SECTIONS = [
    ("occupant", "1. Occupant et logement", [
        ('statut_occupant', "Statut de l'occupant", 'choix', STATUT_OCCUPANT),
        ('adultes', "Adultes du foyer (nombre)", 'texte', None),
        ('enfants', "Enfants : nombre et années de naissance", 'texte', None),
        ('caf_allocataire', "Allocataire CAF / MSA", 'ond', [('oui', "Oui"), ('non', "Non")]),
        ('numero_allocataire', "N° allocataire", 'texte', None),
        ('hlm', "Logement HLM", 'ond', [('oui', "Oui"), ('non', "Non")]),
        ('typologie', "Typologie", 'texte', None),
        ('surface', "Surface (m²)", 'texte', None),
        ('localisation', "Localisation (adresse, étage)", 'texte', None),
        ('bail_date', "Bail : date", 'texte', None),
        ('bail_duree', "Bail : durée", 'texte', None),
        ('loyer', "Loyer (€)", 'texte', None),
        ('charges', "Charges (€)", 'texte', None),
        ('date_entree', "Date d'entrée dans les lieux", 'texte', None),
    ]),
    ("batiment", "2. Bâtiment et parties communes", [
        ('eclairage_communs', "Éclairage des parties communes", 'ond', OND),
        ('stockage_gaz', "Stockage de bouteilles de gaz", 'ond', OND),
        ('elements_instables', "Éléments instables", 'ond', OND),
        ('elements_degrades', "Éléments dégradés", 'ond', OND),
        ('fil_apparent', "Fil électrique apparent", 'ond', OND),
    ]),
    ("habitabilite", "3. Habitabilité", [
        ('piece_enterree', "Pièce enterrée ou semi-enterrée", 'ond', OND),
        ('fenetres_exterieur', "Pièces principales avec fenêtre sur l'extérieur", 'ond', OND),
        ('allumage_jour', "Allumage électrique nécessaire en journée", 'ond', OND),
        ('piece_9m2', "Pièce principale d'au moins 9 m² et 2,20 m de hauteur", 'ond', OND),
        ('toilettes', "Toilettes", 'ond', OND),
        ('salle_eau', "Salle d'eau", 'ond', OND),
        ('cuisine', "Cuisine", 'ond', OND),
        ('revetements', "Revêtements", 'ond', OND),
        ('peintures_ecaillees', "Peintures écaillées", 'ond', OND),
    ]),
    ("menuiseries", "4. Menuiseries", [
        ('menuiseries_fonctionnement', "Fonctionnement", 'bmn', BMN),
        ('menuiseries_vetuste', "Vétusté", 'bmn', BMN),
        ('menuiseries_etancheite', "Étanchéité", 'bmn', BMN),
    ]),
    ("equipements", "5. Équipements", [
        ('eau_potable', "Eau potable", 'choix', [('reseau', "Réseau public"), ('puits', "Puits ou forage"),
                                                  ('autre', "Autre")]),
        ('humidite', "Humidité", 'ond', OND),
        ('ventilation', "Ventilation par pièce", 'ond', OND),
        ('installation_electrique', "Installation électrique", 'bmn', BMN),
        ('chauffage', "Chauffage", 'ond', OND),
        ('eau_chaude', "Eau chaude", 'ond', OND),
        ('eaux_usees', "Remontées d'eaux usées", 'ond', OND),
        ('remarque_equipements', "Autre remarque", 'texte', None),
    ]),
    ("proprietaire", "6. Propriétaire ou gestionnaire", [
        ('proprietaire_nom', "Nom", 'texte', None),
        ('proprietaire_adresse', "Adresse", 'texte', None),
        ('proprietaire_tel', "Téléphone", 'texte', None),
    ]),
    ("divers", "7. Divers", [
        ('rongeurs', "Rongeurs", 'ond', OND),
        ('insectes', "Insectes", 'ond', OND),
        ('punaises', "Punaises de lit", 'ond', OND),
        ('commentaires', "Commentaires", 'texte', None),
    ]),
    ("demarches", "8. Démarches engagées", [
        ('info_proprietaire', "Information du propriétaire", 'ond', OND),
        ('demarche_relogement', "Démarche de relogement", 'ond', OND),
        ('acceptation_enquete', "Acceptation d'une enquête de salubrité", 'ond', OND),
    ]),
]

ORIGINES = [('VAD', "Visite à domicile du TS"), ('LOCATAIRE', "Signalement du locataire"),
            ('BAILLEUR', "Signalement du bailleur"), ('COMMUNE', "Signalement de la commune"),
            ('AUTRE', "Autre")]


def champs_valides():
    """Dictionnaire {clé: (kind, choix)} de toutes les rubriques saisies."""
    return {key: (kind, choix) for _, _, champs in SECTIONS for key, _, kind, choix in champs}


def valeur_propre(key, valeur, champs=None):
    """Valeur acceptée pour une rubrique (choix contrôlé ou texte tronqué)."""
    champs = champs or champs_valides()
    kind, choix = champs[key]
    valeur = (valeur or '').strip()
    if kind == 'texte':
        return valeur[:300]
    return valeur if valeur in dict(choix) else ''
