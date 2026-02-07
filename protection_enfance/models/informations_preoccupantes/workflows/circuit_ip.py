# protection_enfance/informations_preoccupantes/workflows/circuit_ip.py

class CircuitIPCD13:
    """Circuit officiel des IP dans les Bouches-du-Rhône"""
    
    ETAPES = [
        {
            'code': 'RECEPTION_CRIP',
            'nom': 'Réception par la CRIP',
            'delai_reglementaire': '24 heures',
            'actions_obligatoires': [
                'Enregistrement du signalement',
                'Attribution numéro unique',
                'Envoi accusé réception',
            ]
        },
        {
            'code': 'ANALYSE_INITIALE',
            'nom': 'Analyse initiale CRIP',
            'delai_reglementaire': '15 jours',
            'actions_obligatoires': [
                'Évaluation niveau urgence',
                'Recherche antécédents',
                'Décision orientation',
            ]
        },
        {
            'code': 'EVALUATION_PLURIDISCIPLINAIRE',
            'nom': 'Évaluation pluridisciplinaire',
            'delai_reglementaire': '3 mois',
            'actions_obligatoires': [
                'Rencontre avec la famille',
                'Audition du mineur',
                'Évaluation globale',
                'Rapport d\'évaluation',
            ]
        },
        {
            'code': 'DECISION_MESURE',
            'nom': 'Décision de mesure',
            'delai_reglementaire': '1 mois après évaluation',
            'actions_obligatoires': [
                'Réunion de concertation',
                'Élaboration projet pour l\'enfant',
                'Décision mesure protection',
            ]
        }
    ]
    
    def get_prochaines_actions(self, ip):
        """Retourne les actions à réaliser selon l'étape"""
        etape_actuelle = self._get_etape_actuelle(ip)
        return self.ETAPES[etape_actuelle]['actions_obligatoires']
