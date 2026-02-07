#core/utils/constants.py
# Profils prédéfinis
PROFILS_PREDEFINIS = [
    {
        'code': 'TRAVAILLEUR_SOCIAL',
        'nom': 'Travailleur social',
        'peut_creer_dossier': True,
        'peut_instruire_dossier': True,
    },
    {
        'code': 'CADRE_SOCIAL',
        'nom': 'Cadre social',
        'peut_creer_dossier': True,
        'peut_instruire_dossier': True,
        'peut_valider_dossier': True,
        'peut_administrer': True,        
    },
    {
        'code': 'AGENT_ADMINISTRATIF',
        'nom': 'Agent administratif',
        'peut_creer_dossier': True,
    },
    {
        'code': 'REGIE_AVANCE',
        'nom': 'Régie d\'avance',
        'peut_valider_dossier': True,
        'peut_decider_aide': True,
        'peut_acceder_finance': True,
        'acces_donnees_sensibles': True,
    },
    {
        'code': 'DIRECTEUR',
        'nom': 'Directeur',
        'peut_creer_dossier': True,
        'peut_instruire_dossier': True,
        'peut_valider_dossier': True,
        'peut_decider_aide': True,
        'peut_administrer': True,
        'acces_donnees_sensibles': True,
    },
]

# Configurations prédéfinies
CONFIGURATIONS_PREDEFINIES = [
    {
        'cle': 'SYSTEME_NOM',
        'valeur': 'SI DITAS',
        'type_valeur': 'STRING',
        'categorie': 'SYSTEME',
        'description': 'Nom du système',
        'modifiable': False,
    },
    {
        'cle': 'SESSION_TIMEOUT',
        'valeur': '3600',
        'type_valeur': 'INTEGER',
        'categorie': 'SECURITE',
        'description': 'Durée de session en secondes',
        'modifiable': True,
    },
]
