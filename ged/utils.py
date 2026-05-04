# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

"""
ged/utils.py - VERSION CONVERTIE CORE-DITAS 2026
Moteur de filtrage et de validation des droits GED
"""

from django.db.models import Q
from django.core.exceptions import PermissionDenied
from .models import DocumentGED
from mds.models import UserMDSProfile

def check_document_permission(user, document, action='view'):
    """
    Vérifie les permissions CORE-compatible sur un document.
    Centralise les appels aux méthodes de sécurité du modèle.
    """
    perms = {
        'view': document.peut_etre_vu_par,
        'edit': document.peut_etre_modifie_par,
        'delete': document.peut_etre_modifie_par,
        'validate': lambda u: u.a_la_capacite('peut_valider'),
    }

    check_func = perms.get(action)
    
    # Si l'action est validation et que la méthode n'existe pas, on check la capacité CORE
    if action == 'validate' and not check_func:
        if not user.a_la_capacite('peut_valider'):
            raise PermissionDenied("Vous n'avez pas la capacité de validation.")
        return True

    if check_func and not check_func(user):
        raise PermissionDenied(f"Action '{action}' non autorisée sur ce document.")
    
    return True

def get_documents_for_user(user):
    """
    Retourne le QuerySet des documents accessibles (CORE-compatible).
    Applique le double filtrage : Confidentialité (Profil) + Territoire (MDS).
    """
    # 1. ACCÈS TOTAL : Superuser ou Direction DITAS
    if user.is_superuser or user.profils.filter(nom="DITAS_Direction").exists():
        return DocumentGED.objects.all()

    # 2. IDENTIFICATION DU TERRITOIRE (MDS)
    user_mds_ids = UserMDSProfile.objects.filter(
        user=user, 
        actif=True
    ).values_list('mds_id', flat=True).distinct()

    # 3. FILTRE DE CONFIDENTIALITÉ (Selon capacités/profils)
    # ------------------------------------------------------
    profil_filter = Q()
    user_profils = list(user.profils.values_list('nom', flat=True))

    if "DGAS_Direction" in user_profils or "MDS_Cadres" in user_profils:
        # Accès large : Tout sauf 'TRES_CONFIDENTIEL' (réservé DITAS)
        profil_filter = Q(confidentialite__in=['PUBLIC', 'RESTREINT', 'CONFIDENTIEL'])
    
    elif "MDS_Agents_Sociaux" in user_profils:
        # Accès standard + dossiers où l'agent est désigné explicitement
        profil_filter = Q(confidentialite__in=['PUBLIC', 'RESTREINT']) | \
                        Q(confidentialite='CONFIDENTIEL', agents_autorises=user)
    
    elif "MDS_Administratifs" in user_profils:
        # Accès administratif strict
        profil_filter = Q(confidentialite__in=['PUBLIC', 'RESTREINT'])
    
    else:
        # Sécurité : Si aucun profil matché, on ne voit que ses propres uploads
        profil_filter = Q(uploaded_by=user)

    # 4. FILTRE DE TERRITORIALITÉ (Barrière MDS)
    # ------------------------------------------------------
    # On filtre les documents liés à des bénéficiaires appartenant aux MDS de l'utilisateur.
    # On utilise 'beneficiaire__mds_id' car dans ton système, l'objet lié est souvent le bénéficiaire.
    # Pour les GenericForeignKey, on filtre via le ContentType si nécessaire.
    
    qs = DocumentGED.objects.filter(profil_filter)

    # Si l'agent n'est pas "Direction globale", on applique la barrière MDS
    if not ("DITAS_Direction" in user_profils or "DGAS_Direction" in user_profils):
        # Filtrage territorial sur le bénéficiaire lié (via GenericRelation ou IDs)
        # On suppose ici que le DocumentGED est lié à un bénéficiaire (object_id)
        # On restreint aux documents dont l'object_id (bénéficiaire) appartient aux MDS autorisées.
        from django.contrib.contenttypes.models import ContentType
        from beneficiaire.models import Beneficiaire
        
        beneficiaire_type = ContentType.objects.get_for_model(Beneficiaire)
        
        # Filtre complexe : documents du territoire OU documents créés par l'utilisateur lui-même
        qs = qs.filter(
            Q(content_type=beneficiaire_type, object_id__in=Beneficiaire.objects.filter(mds_id__in=user_mds_ids).values('id')) |
            Q(uploaded_by=user)
        )

    return qs.distinct()
