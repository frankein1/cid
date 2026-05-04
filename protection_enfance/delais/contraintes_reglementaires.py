# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# protection_enfance/delais/contraintes_reglementaires.py

class DelaisReglementaires:
    """Gestion des délais légaux ASE"""
    
    DELAIS_IP = {
        'accus_reception': 24,  # Heures
        'transmission_crip': 24,  # Heures
        'traitement_crip': 15,  # Jours
        'evaluation_sociale': 3,  # Mois
        'transmission_parquet_urgence': 24,  # Heures
        'transmission_parquet_courant': 15,  # Jours
    }
    
    DELAIS_PLACEMENT = {
        'rendez_vous_famille': 8,  # Jours
        'rapport_presentation': 15,  # Jours
        'reunion_concertation': 21,  # Jours
        'decision_placement': 30,  # Jours
        'notification_decision': 8,  # Jours
    }
    
    DELAIS_RAPPORTS = {
        'rapport_annuel_placement': 365,  # Jours
        'bilan_sante_6_mois': 180,  # Jours
        'bilan_scolaire_annuel': 365,  # Jours
        'projet_pour_enfant': 90,  # Jours après placement
    }

class GestionnaireDelais:
    """Surveillance et alertes des délais"""
    
    def verifier_delais_ip(self, information_preoccupante):
        delais = DelaisReglementaires.DELAIS_IP
        aujourdhui = timezone.now().date()
        
        alertes = []
        
        # Délai de traitement CRIP
        if information_preoccupante.date_reception:
            delai_crip = information_preoccupante.date_reception + timedelta(days=delais['traitement_crip'])
            if aujourdhui > delai_crip:
                alertes.append(f"Délai CRIP dépassé depuis {(aujourdhui - delai_crip).days} jours")
        
        return alertes
