# protection_enfance/workflows/ip_workflow.py

IP_WORKFLOW = {
    'states': [
        {'name': 'NOUVELLE', 'description': 'Nouvelle IP reçue'},
        {'name': 'ANALYSE_CRIP', 'description': 'Analyse par la CRIP'},
        {'name': 'EN_EVALUATION', 'description': 'Évaluation en cours'},
        {'name': 'TRANSMISSION_PARQUET', 'description': 'Transmission au parquet'},
        {'name': 'SUIVI_ASE', 'description': 'Suivi par l\'ASE'},
        {'name': 'CLASSEE', 'description': 'Classée sans suite'},
    ],
    'transitions': [
        {'from': 'NOUVELLE', 'to': 'ANALYSE_CRIP', 'name': 'Analyser'},
        {'from': 'ANALYSE_CRIP', 'to': 'EN_EVALUATION', 'name': 'Décider évaluation'},
        {'from': 'ANALYSE_CRIP', 'to': 'CLASSEE', 'name': 'Classer'},
        {'from': 'EN_EVALUATION', 'to': 'TRANSMISSION_PARQUET', 'name': 'Transmettre parquet'},
        {'from': 'EN_EVALUATION', 'to': 'SUIVI_ASE', 'name': 'Ouvrir suivi ASE'},
        {'from': 'EN_EVALUATION', 'to': 'CLASSEE', 'name': 'Terminer sans suite'},
    ]
}
