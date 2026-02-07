"""
# AidFi/views/v_generique.py
Logique de présentation GÉNÉRIQUE (Dashboard)
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from beneficiaire.models import Beneficiaire
from AidFi.models.m_generique import DemandeAide
try:
    from mds.models import UserMDSProfile
except ImportError:
    UserMDSProfile = None

@login_required
def dashboard_aidfi_beneficiaire(request, beneficiaire_id):
    """
    Vue centrale affichant l'historique complet des aides (AFASE, CAP, etc.)
    pour un bénéficiaire donné.
    """
    beneficiaire = get_object_or_404(Beneficiaire, id=beneficiaire_id)
    
    # Vérification des permissions
    if not request.user.a_la_capacite("peut_voir"):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Accès refusé")
    
    # On récupère TOUTES les aides via le modèle parent DemandeAide
    toutes_les_demandes = DemandeAide.objects.filter(
        beneficiaire=beneficiaire
    ).select_related('type_aide').order_by("-date_creation")
    
    # Récupération des permissions pour l'affichage conditionnel
    can_create = request.user.a_la_capacite("peut_creer")
    can_manage_finance = request.user.a_la_capacite("peut_gerer_finance")

    return render(request, "AidFi/dashboard_beneficiaire.html", {
        "beneficiaire": beneficiaire,
        "toutes_les_demandes": toutes_les_demandes,
        "can_create": can_create,
        "can_manage_finance": can_manage_finance,
    })
