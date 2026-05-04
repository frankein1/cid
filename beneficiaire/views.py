# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

"""
beneficiaire/views.py
Vues pour l'application bénéficiaire - VERSION CORE INTÉGRALE
FICHIER 100% CORRIGÉ - a_la_capacite() partout
"""

from datetime import datetime
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import PermissionDenied

from messagerie.models import Message

from .forms import (
    BeneficiaireForm,
    DecesBeneficiaireForm,
    SortieBeneficiaireForm,
    LienFamilialForm,
)
from .models import Beneficiaire, DocumentBeneficiaireLink, LienFamilial
from ged.models import DocumentGED, DocumentType
from ged.storage import SeaweedFSStorage
try:
    from mds.models import UserMDSProfile
except ImportError:
    UserMDSProfile = None

User = get_user_model()

# =============================================================================
# Vues AJAX
# =============================================================================

@login_required
def load_referents(request):
    """✅ CORRIGÉ : Filtre via UserMDSProfile"""
    mds_id = request.GET.get("mds_id")
    if not mds_id:
        return JsonResponse({"referents": []})

    from mds.models import UserMDSProfile
    user_ids = UserMDSProfile.objects.filter(
        mds_id=mds_id, 
        actif=True
    ).values_list('user_id', flat=True)

    users = User.objects.filter(id__in=user_ids, is_active=True).order_by('last_name')
    
    referents_list = [
        {
            "id": u.id,
            "nom_complet": f"{u.get_full_name()} ({u.username})" if u.get_full_name() else u.username
        }
        for u in users
    ]
    return JsonResponse({"referents": referents_list})

# =============================================================================
# Helpers de sécurité CORE
# =============================================================================

def user_peut_creer(user):
    """Helper pour capacité 'peut_creer'"""
    return user.is_superuser or user.a_la_capacite('peut_creer')

def user_peut_valider(user):
    """Helper pour capacité 'peut_valider'"""
    return user.is_superuser or user.a_la_capacite('peut_valider')

def user_peut_agir_sur_beneficiaire(user, beneficiaire):
    """✅ CORRIGÉ CORE : Vérification complète MDS + capacité"""
    if user.is_superuser:
        return True
    if not beneficiaire.mds:
        return False
    
    # Doit avoir la capacité ET être rattaché à la bonne MDS
    return (user.a_la_capacite('peut_creer') and 
            UserMDSProfile.objects.filter(
                user=user, mds=beneficiaire.mds, actif=True
            ).exists())

# =============================================================================
# Vues de gestion des bénéficiaires
# =============================================================================

@login_required
def liste_beneficiaires(request):
    """Recherche multicritère de bénéficiaires."""
    nom = request.GET.get('nom', '').strip()
    prenom = request.GET.get('prenom', '').strip()
    identifiant = request.GET.get('identifiant', '').strip()
    ville_cp = request.GET.get('ville_cp', '').strip()
    date_naiss = request.GET.get('date_naiss', '')

    beneficiaires = None
    
    if nom or prenom or identifiant or ville_cp or date_naiss:
        filters = Q()
        if nom:
            filters &= Q(nom__icontains=nom)
        if prenom:
            filters &= Q(prenom__icontains=prenom)
        if identifiant:
            filters &= (
                Q(nir__icontains=identifiant) | 
                Q(numero_caf__icontains=identifiant) |
                Q(numero_france_travail__icontains=identifiant) | 
                Q(numero_fiscal__icontains=identifiant) |
                Q(code_interne__icontains=identifiant) |
                Q(telephone_mobile__icontains=identifiant)
            )
        if ville_cp:
            filters &= (Q(ville__icontains=ville_cp) | Q(code_postal__icontains=ville_cp))
        if date_naiss:
            filters &= Q(date_naissance=date_naiss)

        beneficiaires = Beneficiaire.objects.filter(filters)
    
    # Filtrer selon les droits MDS seulement si on a des résultats
    if beneficiaires is not None and not request.user.is_superuser:
        from mds.models import UserMDSProfile
        mds_ids = UserMDSProfile.objects.filter(
            user=request.user, actif=True
        ).values_list('mds_id', flat=True)
        beneficiaires = beneficiaires.filter(mds_id__in=mds_ids)
    
    # Trier et optimiser les requêtes
    if beneficiaires is not None:
        beneficiaires = beneficiaires.select_related('mds', 'referent_mds').order_by('nom', 'prenom')

    return render(request, 'beneficiaire/liste_beneficiaires.html', {
        'beneficiaires': beneficiaires,
        'nom': nom, 'prenom': prenom, 'identifiant': identifiant,
        'ville_cp': ville_cp, 'date_naiss': date_naiss,
    })

@login_required
def ajouter_beneficiaire(request):
    """✅ CORRIGÉ : Vérification capacité + MDS"""
    if not user_peut_creer(request.user):
        messages.error(request, "Capacité 'peut_creer' requise.")
        return redirect('core:dashboard')

    if request.method == "POST":
        form = BeneficiaireForm(request.POST)
        if form.is_valid():
            benef = form.save(commit=False)
            benef.cree_par = request.user
            
            # ✅ Rattachement automatique à la MDS de l'utilisateur
            from mds.models import UserMDSProfile
            profile = UserMDSProfile.objects.filter(
                user=request.user, actif=True
            ).first()
            if profile and profile.mds:
                benef.mds = profile.mds
                
            benef.save()
            messages.success(request, f"Bénéficiaire {benef.prenom} {benef.nom} ajouté.")
            return redirect("beneficiaire:detail_beneficiaire", code_interne=benef.code_interne)
    else:
        form = BeneficiaireForm()
    return render(request, "beneficiaire/ajouter_beneficiaire.html", {"form": form})

@login_required
def modifier_beneficiaire(request, code_interne):
    """✅ CORRIGÉ : Vérification peut_agir_sur_beneficiaire"""
    beneficiaire = get_object_or_404(Beneficiaire, code_interne=code_interne)
    
    if not user_peut_agir_sur_beneficiaire(request.user, beneficiaire):
        messages.warning(request, "Modification impossible : hors secteur MDS.")
        return redirect("beneficiaire:detail_beneficiaire", code_interne=beneficiaire.code_interne)

    if request.method == "POST":
        form = BeneficiaireForm(request.POST, instance=beneficiaire)
        if form.is_valid():
            form.save()
            messages.success(request, f"Mise à jour de {beneficiaire.nom} effectuée.")
            return redirect("beneficiaire:detail_beneficiaire", code_interne=beneficiaire.code_interne)
    else:
        form = BeneficiaireForm(instance=beneficiaire)

    # VOICI LA CORRECTION : Ajouter "action" dans le dictionnaire
    return render(request, "beneficiaire/modifier_beneficiaire.html", {
        "form": form, 
        "beneficiaire": beneficiaire,
        "action": "Modifier le bénéficiaire"  # ← AJOUTE CETTE LIGNE
    })

@login_required
def detail_beneficiaire(request, code_interne):
    """Détail de la fiche, liens et documents - OPTIMISÉ avec select_related"""
    beneficiaire = get_object_or_404(
        Beneficiaire.objects.select_related('mds', 'referent_mds'),
        code_interne=code_interne
    )
    
    if not beneficiaire.peut_etre_vu_par(request.user):
        messages.error(request, "Accès refusé à ce bénéficiaire.")
        return redirect('beneficiaire:liste')
    
    # Optimisation des requêtes pour les liens familiaux
    liens = LienFamilial.objects.filter(
        Q(personne_a=beneficiaire) | Q(personne_b=beneficiaire)
    ).select_related(
        'personne_a__mds', 
        'personne_b__mds',
        'personne_a__referent_mds',
        'personne_b__referent_mds'
    )
    
    if request.GET.get("inclure_sortis", "non") != "oui":
        liens = liens.exclude(
            Q(personne_a__statut__in=["SORTI", "DECEDE"]) | 
            Q(personne_b__statut__in=["SORTI", "DECEDE"])
        )

    context = {
        "beneficiaire": beneficiaire,
        "liens_familiaux": liens,
        "documents": DocumentBeneficiaireLink.objects.filter(
            beneficiaire=beneficiaire
        ).select_related('document_ged').order_by("-date_creation"),
        "inclure_sortis": request.GET.get("inclure_sortis", "non") == "oui",
        "peut_modifier": user_peut_agir_sur_beneficiaire(request.user, beneficiaire),
        "messages": Message.objects.filter(
            beneficiaire=beneficiaire
        ).select_related('expediteur', 'destinataire')[:10]
    }
    return render(request, "beneficiaire/detail_beneficiaire.html", context)
   
@login_required
def ajouter_ayant_droit(request, code_interne):
    """Ajouter un membre à la famille (crée une fiche + un lien)."""
    referent = get_object_or_404(Beneficiaire, code_interne=code_interne)

    if not user_peut_agir_sur_beneficiaire(request.user, referent):
        messages.error(request, "Action interdite hors secteur.")
        return redirect("beneficiaire:detail_beneficiaire", code_interne=code_interne)

    if request.method == "POST":
        form = BeneficiaireForm(request.POST, est_ayant_droit=True)
        lien_form = LienFamilialForm(request.POST)
        
        if form.is_valid() and lien_form.is_valid():
            nouveau_membre = form.save(commit=False)
            nouveau_membre.cree_par = request.user
            nouveau_membre.mds = referent.mds  # Même MDS que le référent
            nouveau_membre.save()
            
            lien = lien_form.save(commit=False)
            lien.personne_a = nouveau_membre
            lien.personne_b = referent
            lien.save()
            
            messages.success(request, f"{nouveau_membre.prenom} ajouté au réseau.")
            return redirect("beneficiaire:detail_beneficiaire", code_interne=code_interne)
    else:
        form = BeneficiaireForm(est_ayant_droit=True, initial={
            "nom": referent.nom, "mds": referent.mds,
            "adresse": referent.adresse, "code_postal": referent.code_postal, "ville": referent.ville
        })
        lien_form = LienFamilialForm()

    return render(request, "beneficiaire/ajouter_ayant_droit.html", {
        "form": form, "lien_form": lien_form, "beneficiaire_principal": referent
    })

@login_required
def sortir_beneficiaire(request, code_interne):
    beneficiaire = get_object_or_404(Beneficiaire, code_interne=code_interne)
    if not user_peut_agir_sur_beneficiaire(request.user, beneficiaire):
        raise PermissionDenied

    if request.method == "POST":
        form = SortieBeneficiaireForm(request.POST, instance=beneficiaire)
        if form.is_valid():
            form.save()
            messages.success(request, "Sortie enregistrée.")
            return redirect("beneficiaire:detail_beneficiaire", code_interne=code_interne)
    else:
        form = SortieBeneficiaireForm(instance=beneficiaire)
    return render(request, "beneficiaire/sortir_beneficiaire.html", {"form": form, "beneficiaire": beneficiaire})

@login_required
def declarer_deces(request, code_interne):
    beneficiaire = get_object_or_404(Beneficiaire, code_interne=code_interne)
    if not user_peut_agir_sur_beneficiaire(request.user, beneficiaire):
        raise PermissionDenied

    if request.method == "POST":
        form = DecesBeneficiaireForm(request.POST, instance=beneficiaire)
        if form.is_valid():
            form.save()
            messages.success(request, "Décès enregistré.")
            return redirect("beneficiaire:detail_beneficiaire", code_interne=code_interne)
    else:
        form = DecesBeneficiaireForm(instance=beneficiaire)
    return render(request, "beneficiaire/declarer_deces.html", {"form": form, "beneficiaire": beneficiaire})
    
    
@login_required
def annuler_deces(request, code_interne):
    beneficiaire = get_object_or_404(Beneficiaire, code_interne=code_interne)
    # Logique pour annuler un décès
    return render(request, "beneficiaire/annuler_deces.html", {"beneficiaire": beneficiaire})

@login_required
def supprimer_beneficiaire(request, code_interne):
    """✅ CORRIGÉ : peut_valider requis"""
    benef = get_object_or_404(Beneficiaire, code_interne=code_interne)
    if not user_peut_valider(request.user) or not user_peut_agir_sur_beneficiaire(request.user, benef):
        messages.error(request, "Droits insuffisants (Cadre requis).")
        return redirect("beneficiaire:detail_beneficiaire", code_interne=code_interne)
    
    if request.method == "POST":
        benef.delete()
        messages.success(request, "Fiche supprimée.")
        return redirect("beneficiaire:liste")
    return render(request, "beneficiaire/confirmer_suppression.html", {"beneficiaire": benef})

@login_required
def ajouter_document(request, code_interne):
    """Gestion des documents GED"""
    benef = get_object_or_404(Beneficiaire, code_interne=code_interne)
    
    if not user_peut_agir_sur_beneficiaire(request.user, benef):
        messages.error(request, "Ajout interdit hors secteur.")
        return redirect("beneficiaire:detail_beneficiaire", code_interne=code_interne)

    from ged.forms import DocumentGEDForm

    if request.method == "POST":
        form = DocumentGEDForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            try:
                doc_ged = form.save(commit=False)
                doc_ged.content_type = ContentType.objects.get_for_model(Beneficiaire)
                doc_ged.object_id = benef.id
                doc_ged.uploaded_by = request.user
                doc_ged.save()
                
                DocumentBeneficiaireLink.objects.create(
                    beneficiaire=benef,
                    document_ged=doc_ged,
                    type_document=doc_ged.type_document.code,
                    cree_par=request.user
                )
                
                messages.success(request, "Document ajouté et chiffré avec succès.")
                return redirect("beneficiaire:detail_beneficiaire", code_interne=code_interne)
            except Exception as e:
                messages.error(request, f"Erreur technique : {e}")
    else:
        form = DocumentGEDForm(user=request.user)

    return render(request, "beneficiaire/ajouter_document.html", {
        "beneficiaire": benef,
        "form": form,
    })
