# AidFi/utils.py
from django.db.models import Q
from core.models.user import User

def verif_droits_aidfi(user, action=None, demande=None):
    """Vérifie les droits AidFi via le système core (capacités Profil)"""
    if not user or not user.is_authenticated: 
        return False
    
    # Super admin + Admin complet = TOUT accès (core)
    if user.a_la_capacite('peut_administrer'): 
        return True
    
    # Actions simples (indépendantes d'un objet)
    if action == 'voir':
        return user.a_la_capacite('peut_voir')  # Alias core: instruire OU valider
    
    if action == 'creer':
        return user.a_la_capacite('peut_creer')
        
    if action == 'decider':
        return user.a_la_capacite('peut_decider')
    
    # Actions conditionnelles (statut + capacité)
    if action == 'modifier' and demande:
        # UNIQUEMENT brouillon pour AFASE
        if demande.statut != 'BROUILLON': 
            return False
        # Créateur OU Décideur (core)
        return demande.cree_par == user or user.a_la_capacite('peut_decider')
    
    if action == 'deposer' and demande:
        return (demande.statut == 'BROUILLON' and 
                demande.cree_par == user and 
                user.a_la_capacite('peut_creer'))
    
    return False

def get_statuts_autorises(user, demande):
    """Retourne les statuts autorisés selon profil core + statut actuel"""
    if not user.a_la_capacite('peut_voir'):
        return []
    
    s = demande.statut
    choices = []
    
    # TOUT LE MONDE peut déposer son brouillon (si créateur)
    if (s == 'BROUILLON' and demande.cree_par == user and 
        user.a_la_capacite('peut_creer')):
        choices.append(('DEPOSE', 'Déposer la demande'))
    
    # Décideurs/Cadres : Décision
    if (s == 'DEPOSE' and user.a_la_capacite('peut_decider')):
        choices.append(('DECIDE', 'Prendre décision'))
    
    return choices
