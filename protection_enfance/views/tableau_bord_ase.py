# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# protection_enfance/views/tableau_bord_ase.py

class TableauBordASEView:
    """Tableau de bord spécifique ASE"""
    
    def get_indicateurs_cles(self):
        return {
            'ip_en_cours': InformationPreoccupante.objects.filter(
                statut__in=['NOUVELLE', 'EN_COURS']
            ).count(),
            'placements_actifs': Placement.objects.filter(
                statut='EN_COURS'
            ).count(),
            'enfants_confies': Placement.objects.filter(
                statut='EN_COURS'
            ).values('enfant').distinct().count(),
            'mef_occupation': self.calcul_taux_occupation_mef(),
            'delai_moyen_traitement_ip': self.calcul_delai_moyen_ip(),
        }
