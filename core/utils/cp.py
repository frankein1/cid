# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

"""
Utilitaire pour la gestion des codes postaux français
Fichier : core/utils/cp.py - VERSION AVEC API GOUVERNEMENTALE

Utilise l'API geo.api.gouv.fr (gratuite, sans clé API)
Fallback sur une base locale si l'API ne répond pas
"""

import requests
from functools import lru_cache
from typing import Optional, Dict, List


# Cache local minimal (fallback si API inaccessible)
CACHE_LOCAL = {
    # Bouches-du-Rhône - 
# Marseille (16 arrondissements)
    "13000": "Marseille",
    "13001": "Marseille 1er",
    "13002": "Marseille 2e",
    "13003": "Marseille 3e",
    "13004": "Marseille 4e",
    "13005": "Marseille 5e",
    "13006": "Marseille 6e",
    "13007": "Marseille 7e",
    "13008": "Marseille 8e",
    "13009": "Marseille 9e",
    "13010": "Marseille 10e",
    "13011": "Marseille 11e",
    "13012": "Marseille 12e",
    "13013": "Marseille 13e",
    "13014": "Marseille 14e",
    "13015": "Marseille 15e",
    "13016": "Marseille 16e",
    
    # Aix-en-Provence et environs
    "13080": "Aix-en-Provence",
    "13090": "Aix-en-Provence",
    "13100": "Aix-en-Provence",
    "13290": "Aix-en-Provence",
    "13540": "Aix-en-Provence",
    
    # Autres communes des Bouches-du-Rhône (par ordre alphabétique)
    "13410": "Lambesc",
    "13122": "Ventabren",
    "13116": "Vernègues",
    "13114": "Puyloubier",
    "13113": "Lamanon",
    "13119": "Saint-Savournin",
    "13115": "Saint-Paul-lès-Durance",
    "13117": "Martigues",
    "13118": "Entressen",
    "13120": "Gardanne",
    "13121": "Aurons",
    "13123": "Peypin",
    "13124": "Peypin",
    "13125": "Belcodène",
    "13126": "Vauvenargues",
    "13127": "Vitrolles",
    "13128": "Gréasque",
    "13129": "Simiane-Collongue",
    "13130": "Berre-l'Étang",
    "13131": "Saint-Antonin-sur-Bayon",
    "13132": "Éguilles",
    "13133": "Marseille",
    "13140": "Miramas",
    "13150": "Tarascon",
    "13160": "Châteaurenard",
    "13170": "Les Pennes-Mirabeau",
    "13180": "Gignac-la-Nerthe",
    "13190": "Allauch",
    "13200": "Arles",
    "13210": "Saint-Rémy-de-Provence",
    "13220": "Châteauneuf-les-Martigues",
    "13230": "Port-Saint-Louis-du-Rhône",
    "13240": "Septèmes-les-Vallons",
    "13250": "Saint-Chamas",
    "13260": "Cassis",
    "13270": "Fos-sur-Mer",
    "13280": "Arles",
    "13300": "Salon-de-Provence",
    "13310": "Saint-Martin-de-Crau",
    "13320": "Bouc-Bel-Air",
    "13330": "Pélissanne",
    "13340": "Rognac",
    "13350": "Charleval",
    "13360": "Roquevaire",
    "13370": "Mallemort",
    "13380": "Plan-de-Cuques",
    "13390": "Auriol",
    "13400": "Aubagne",
    "13420": "Gémenos",
    "13430": "Eyguières",
    "13440": "Cabannes",
    "13450": "Grans",
    "13460": "Saintes-Maries-de-la-Mer",
    "13470": "Carnoux-en-Provence",
    "13480": "Cabriès",
    "13490": "Jouques",
    "13500": "Martigues",
    "13510": "Éguilles",
    "13520": "Maussane-les-Alpilles",
    "13530": "Trets",
    "13550": "Noves",
    "13560": "Sénas",
    "13570": "Barbentane",
    "13580": "La Faire-les-Oliviers",
    "13590": "Meyreuil",
    "13600": "La Ciotat",
    "13610": "Le Puy-Sainte-Réparade",
    "13620": "Carry-le-Rouet",
    "13630": "Eyragues",
    "13640": "La Roque-d'Anthéron",
    "13650": "Meyrargues",
    "13660": "Orgon",
    "13670": "Verquières",
    "13680": "Lançon-Provence",
    "13690": "Graveson",
    "13700": "Marignane",
    "13710": "Fuveau",
    "13720": "La Bouilladisse",
    "13730": "Saint-Victoret",
    "13740": "Le Rove",
    "13750": "Plan-d'Orgon",
    "13760": "Saint-Cannat",
    "13770": "Venelles",
    "13780": "Cuges-les-Pins",
    "13790": "Rousset",
    "13800": "Istres",
    "13810": "Eygalières",
    "13820": "Ensuès-la-Redonne",
    "13830": "Roquefort-la-Bédoule",
    "13840": "Rognes",
    "13850": "Gréasque",
    "13860": "Peyrolles-en-Provence",
    "13870": "Rognonas",
    "13880": "Velaux",
    "13890": "Mouriès",
    "13900": "Arles",
    "13910": "Maillane",
    "13920": "Saint-Mitre-les-Remparts",
    "13930": "Aureille",
    "13940": "Molleges",
    "13950": "Cadolive",
    "13960": "Sausset-les-Pins",
    "13970": "Charleval",
    "13980": "Alleins",
    "13990": "Fontvieille", 
}


@lru_cache(maxsize=1000)
def get_ville_from_api(code_postal: str) -> Optional[str]:
    """
    Récupère la ville depuis l'API gouvernementale
    Résultat mis en cache automatiquement
    
    Args:
        code_postal: Code postal à rechercher
        
    Returns:
        Nom de la ville ou None si non trouvé
    """
    try:
        url = f"https://geo.api.gouv.fr/communes?codePostal={code_postal}&fields=nom,codesPostaux"
        response = requests.get(url, timeout=3)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                # Retourner le nom de la première commune
                return data[0]['nom']
    except Exception as e:
        # En cas d'erreur réseau, on passe au fallback
        print(f"Erreur API geo.gouv.fr: {e}")
    
    return None


def get_ville_from_cp(code_postal: str) -> str:
    """
    Récupère la ville correspondant à un code postal
    
    Stratégie:
    1. Vérifier le cache local (rapide)
    2. Interroger l'API gouvernementale (complet)
    3. Retourner vide si rien trouvé
    
    Args:
        code_postal: Code postal à rechercher (5 chiffres)
    
    Returns:
        Nom de la ville ou chaîne vide
    
    Exemple:
        >>> get_ville_from_cp("13000")
        'Marseille'
    """
    if not code_postal or not isinstance(code_postal, str):
        return ""
    
    # Nettoyer le code postal
    code_postal = code_postal.strip()
    
    # Vérifier format
    if len(code_postal) != 5 or not code_postal.isdigit():
        return ""
    
    # 1. Vérifier le cache local (instantané)
    if code_postal in CACHE_LOCAL:
        return CACHE_LOCAL[code_postal]
    
    # 2. Interroger l'API (avec cache LRU)
    ville = get_ville_from_api(code_postal)
    if ville:
        # Ajouter au cache local pour les prochaines fois
        CACHE_LOCAL[code_postal] = ville
        return ville
    
    # 3. Pas trouvé
    return ""


def valider_code_postal(code_postal: str) -> bool:
    """
    Valide qu'un code postal existe
    
    Args:
        code_postal: Code postal à valider
    
    Returns:
        True si le code postal existe
    """
    if not code_postal or not isinstance(code_postal, str):
        return False
    
    code_postal = code_postal.strip()
    
    if len(code_postal) != 5 or not code_postal.isdigit():
        return False
    
    # Essayer de récupérer la ville
    return bool(get_ville_from_cp(code_postal))


def get_departement(code_postal: str) -> str:
    """
    Extrait le numéro de département d'un code postal
    
    Args:
        code_postal: Code postal
    
    Returns:
        Numéro de département (2 premiers chiffres)
    """
    if not code_postal or len(code_postal) < 2:
        return ""
    
    return code_postal[:2]


def rechercher_communes_par_nom(nom: str, limit: int = 10) -> List[Dict[str, str]]:
    """
    Recherche des communes par nom via l'API
    
    Args:
        nom: Nom de la commune à rechercher
        limit: Nombre maximum de résultats
    
    Returns:
        Liste de dictionnaires {nom, code_postal}
    """
    if not nom or len(nom) < 2:
        return []
    
    try:
        url = f"https://geo.api.gouv.fr/communes?nom={nom}&fields=nom,codesPostaux&limit={limit}"
        response = requests.get(url, timeout=3)
        
        if response.status_code == 200:
            data = response.json()
            
            # Formater les résultats
            resultats = []
            for commune in data:
                nom_commune = commune.get('nom', '')
                codes_postaux = commune.get('codesPostaux', [])
                
                for cp in codes_postaux:
                    resultats.append({
                        'nom': nom_commune,
                        'code_postal': cp
                    })
            
            return resultats
    except Exception as e:
        print(f"Erreur recherche commune: {e}")
    
    return []


def vider_cache():
    """
    Vide le cache LRU de l'API
    Utile pour forcer le rafraîchissement des données
    """
    get_ville_from_api.cache_clear()


def get_statistiques_cache() -> Dict:
    """
    Retourne des statistiques sur le cache
    """
    info = get_ville_from_api.cache_info()
    return {
        'cache_hits': info.hits,
        'cache_misses': info.misses,
        'taille_cache': info.currsize,
        'taille_max_cache': info.maxsize,
        'cache_local_size': len(CACHE_LOCAL),
    }


# ============================================================================
# TESTS
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("TEST DE L'API GEO.GOUV.FR")
    print("=" * 60)
    
    # Tests
    tests = [
        "13000",  # Marseille
        "13100",  # Aix-en-Provence
        "13600",  # La Ciotat
        "13127",  # Vitrolles
        "75001",  # Paris 1er
        "69001",  # Lyon 1er
        "99999",  # N'existe pas
    ]
    
    for cp in tests:
        ville = get_ville_from_cp(cp)
        print(f"CP {cp} → {ville if ville else '❌ Non trouvé'}")
    
    print("\n" + "=" * 60)
    print("RECHERCHE PAR NOM")
    print("=" * 60)
    
    resultats = rechercher_communes_par_nom("Marseille", limit=5)
    for r in resultats:
        print(f"  {r['code_postal']} - {r['nom']}")
    
    print("\n" + "=" * 60)
    print("STATISTIQUES DU CACHE")
    print("=" * 60)
    
    stats = get_statistiques_cache()
    for key, value in stats.items():
        print(f"  {key}: {value}")
        
def get_villes_multiples(code_postal: str) -> List[str]:
    """
    Récupère TOUTES les villes correspondant à un code postal.
    Utile pour les CP qui couvrent plusieurs communes.
    """
    if not code_postal or not isinstance(code_postal, str):
        return []
    
    code_postal = code_postal.strip()
    
    try:
        url = f"https://geo.api.gouv.fr/communes?codePostal={code_postal}&fields=nom"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            # On extrait juste les noms des communes
            return [commune['nom'] for commune in data]
    except Exception as e:
        print(f"Erreur API villes multiples: {e}")
    
    # Fallback sur la fonction simple si l'API échoue
    ville_unique = get_ville_from_cp(code_postal)
    return [ville_unique] if ville_unique else []
