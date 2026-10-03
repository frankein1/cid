# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
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
    Retourne le QuerySet des documents accessibles (CORE).
    Traduit en requête la règle de DocumentGED.peut_etre_vu_par :
    Territoire (MDS) + Confidentialité (capacités).
    """
    from django.contrib.contenttypes.models import ContentType
    from beneficiaire.models import Beneficiaire

    # 1. ACCÈS TOTAL : administrateur (inclut le superuser)
    if user.a_la_capacite('peut_administrer'):
        return DocumentGED.objects.all()

    # Sans capacité de consultation : aucun document (comme le modèle)
    if not user.a_la_capacite('peut_voir'):
        return DocumentGED.objects.none()

    # 2. FILTRE DE CONFIDENTIALITÉ (capacités CORE)
    # ------------------------------------------------------
    if user.a_la_capacite('peut_valider'):
        # Cadres : tous les niveaux, y compris TRES_CONFIDENTIEL
        profil_filter = Q()
    else:
        # Agents : accès standard + documents où ils sont nommément autorisés
        profil_filter = Q(confidentialite__in=['PUBLIC', 'RESTREINT']) | \
                        Q(confidentialite='CONFIDENTIEL', agents_autorises=user)

    # 3. FILTRE DE TERRITORIALITÉ (Barrière MDS)
    # ------------------------------------------------------
    user_mds_ids = UserMDSProfile.objects.filter(
        user=user,
        actif=True
    ).values_list('mds_id', flat=True)

    beneficiaire_type = ContentType.objects.get_for_model(Beneficiaire)
    territoire_filter = Q(
        content_type=beneficiaire_type,
        object_id__in=Beneficiaire.objects.filter(mds_id__in=user_mds_ids).values('id')
    )

    # Documents du territoire visibles selon la confidentialité
    qs = DocumentGED.objects.filter(territoire_filter & profil_filter)

    return qs.distinct()
