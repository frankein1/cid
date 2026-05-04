# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# protection_enfance/processus/informations_preoccupantes/circuit_ip.py

class CircuitIP:
    """Circuit complet d'une Information Préoccupante"""
    
    ETAPES_IP = [
        {
            'code': 'RECEPTION',
            'nom': 'Réception du signalement',
            'delai_max': '24h',
            'actions_obligatoires': [
                'Accusé réception',
                'Saisie dans le logiciel',
                'Transmission CRIP'
            ],
            'documents': ['Fiche de signalement']
        },
        {
            'code': 'ANALYSE_CRIP',
            'nom': 'Analyse par la CRIP',
            'delai_max': '15 jours',
            'actions_obligatoires': [
                'Examen en réunion CRIP',
                'Décision orientation',
                'Désignation évaluateur'
            ],
            'documents': ['Compte-rendu CRIP']
        },
        {
            'code': 'EVALUATION',
            'nom': 'Évaluation sociale',
            'delai_max': '3 mois',
            'actions_obligatoires': [
                'Rendez-vous famille',
                'Audition enfant',
                'Enquête sociale',
                'Rapport d\'évaluation'
            ],
            'documents': [
                'Rapport d\'évaluation sociale',
                'Compte-rendu audition',
                'Synthèse partenaires'
            ]
        },
        {
            'code': 'DECISION',
            'nom': 'Décision de suite',
            'delai_max': '8 jours après évaluation',
            'actions_obligatoires': [
                'Réunion de concertation',
                'Proposition mesure',
                'Notification décision'
            ],
            'documents': [
                'Décision administrative',
                'Notification famille',
                'Projet pour l\'enfant'
            ]
        }
    ]
    
    def get_prochaine_etape(self, ip):
        """Retourne la prochaine étape avec ses obligations"""
        etapes = self.ETAPES_IP
        etape_actuelle = self._get_etape_actuelle(ip)
        
        if etape_actuelle < len(etapes) - 1:
            return etapes[etape_actuelle + 1]
        return None
    
    def verifier_completude_etape(self, ip, etape):
        """Vérifie si toutes les actions d'une étape sont réalisées"""
        actions_realisees = ip.historique_actions.filter(etape=etape['code'])
        return len(actions_realisees) >= len(etape['actions_obligatoires'])
