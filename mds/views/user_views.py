# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

"""
mds/views/user_views.py
Gestion RH MDS - VERSION 100% CORE
Remplacement mds_principale → logique UserMDSProfile
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import get_user_model
from ..models import MDS, UserMDSProfile
from ..forms import UserMDSProfileForm, UserMDSProfileUpdateForm

User = get_user_model()

@login_required
def gestion_utilisateurs_mds(request, mds_id):
    """Tableau de bord agents MDS"""
    mds = get_object_or_404(MDS, id=mds_id)
    
    if not mds.peut_etre_modifiee_par(request.user):
        messages.error(request, "Cadre local requis.")
        return redirect("mds:detail_mds", mds_id=mds.id)
    
    profiles = UserMDSProfile.objects.filter(
        mds=mds,
        actif=True
    ).select_related("user").order_by("-principale", "user__last_name")
    
    return render(request, "mds/gestion_utilisateurs_mds.html", {
        "mds": mds, 
        "profiles": profiles
    })

@login_required
def ajouter_utilisateur_mds(request, mds_id):
    """Ajout agent (existant ou nouveau)"""
    mds = get_object_or_404(MDS, id=mds_id)
    
    if not mds.peut_etre_modifiee_par(request.user):
        messages.error(request, "Cadre local requis.")
        return redirect("mds:gestion_utilisateurs_mds", mds_id=mds.id)
    
    if request.method == "POST":
        form = UserMDSProfileForm(request.POST, mds=mds, request=request)
        if form.is_valid():
            try:
                with transaction.atomic():
                    mode = form.cleaned_data.get('mode')
                    
                    # 1. Création/identification User
                    if mode == 'nouveau':
                        user = User.objects.create_user(
                            username=form.cleaned_data['nouveau_matricule'],
                            matricule=form.cleaned_data['nouveau_matricule'],
                            email=form.cleaned_data['nouveau_email'],
                            password=form.cleaned_data['nouveau_mdp1'],
                            first_name=form.cleaned_data['nouveau_prenom'],
                            last_name=form.cleaned_data['nouveau_nom']
                        )
                    else:
                        user = form.cleaned_data.get('user_existant')

                    # 2. Vérifier s'il existe déjà un profil (actif ou inactif) pour cet user+MDS
                    existing_profile = UserMDSProfile.objects.filter(
                        user=user,
                        mds=mds
                    ).first()
                    
                    if existing_profile:
                        # ✅ Réactiver le profil existant
                        profile = existing_profile
                    else:
                        # ✅ CORRECTION : Créer explicitement un nouveau profil
                        profile = UserMDSProfile(user=user, mds=mds)
                    
                    # 3. ✅ Mettre à jour TOUS les champs (y compris actif)
                    profile.actif = True  # Forcé en premier
                    profile.date_debut = form.cleaned_data.get('date_debut')
                    profile.date_fin = form.cleaned_data.get('date_fin')
                    profile.principale = form.cleaned_data.get('principale', False)
                    profile.role_specifique = form.cleaned_data.get('role_specifique', '')
                    profile.bureau = form.cleaned_data.get('bureau', '')
                    profile.telephone_interne = form.cleaned_data.get('telephone_interne', '')
                    profile.peut_gerer_utilisateurs = form.cleaned_data.get('peut_gerer_utilisateurs', False)
                    
                    profile.save()
                    
                    # 4. Profil métier CORE
                    profil_core = form.cleaned_data.get('profil_core')
                    if profil_core:
                        user.profils.add(profil_core)
                    
                    # 5. Gestion principale
                    if profile.principale:
                        UserMDSProfile.objects.filter(
                            user=user, principale=True
                        ).exclude(pk=profile.pk).update(principale=False)
                
                messages.success(request, f"{user.get_full_name()} rattaché à {mds.code_mds}.")
                return redirect("mds:gestion_utilisateurs_mds", mds_id=mds.id)
                
            except Exception as e:
                messages.error(request, f"Erreur: {str(e)}")
    else:
        form = UserMDSProfileForm(mds=mds, request=request)
        
    return render(request, "mds/ajouter_utilisateur_mds.html", {
        "form": form, 
        "mds": mds
    })
    
    
@login_required
def modifier_profil_utilisateur(request, mds_id, user_id):
    """Modification profil agent"""
    mds = get_object_or_404(MDS, id=mds_id)
    profile = get_object_or_404(UserMDSProfile, mds=mds, user_id=user_id)
    
    if not mds.peut_etre_modifiee_par(request.user):
        messages.error(request, "Cadre local requis.")
        return redirect("mds:gestion_utilisateurs_mds", mds_id=mds.id)
    
    if request.method == "POST":
        form = UserMDSProfileUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            try:
                with transaction.atomic():
                    profile = form.save()
                    
                    # Profil métier CORE
                    profil_core = form.cleaned_data.get('profil_core')
                    if profil_core:
                        profile.user.profils.clear()
                        profile.user.profils.add(profil_core)
                    
                    # ✅ CORRIGÉ : Gestion principale via UserMDSProfile uniquement
                    if profile.principale:
                        UserMDSProfile.objects.filter(
                            user=profile.user, principale=True
                        ).exclude(pk=profile.pk).update(principale=False)

                messages.success(request, f"Profil {profile.user.get_full_name()} mis à jour.")
                return redirect("mds:gestion_utilisateurs_mds", mds_id=mds.id)
            except Exception as e:
                messages.error(request, f"Erreur: {str(e)}")
    else:
        initial_profil = profile.user.profils.first()
        form = UserMDSProfileUpdateForm(
            instance=profile, 
            initial={'profil_core': initial_profil}
        )
        
    return render(request, "mds/modifier_profil_utilisateur.html", {
        "form": form, 
        "mds": mds, 
        "profile": profile
    })

@login_required
def supprimer_utilisateur_mds(request, mds_id, user_id):
    """Détachement agent"""
    mds = get_object_or_404(MDS, id=mds_id)
    profile = get_object_or_404(UserMDSProfile, mds=mds, user_id=user_id)
    
    if not mds.peut_etre_modifiee_par(request.user):
        messages.error(request, "Cadre local requis.")
        return redirect("mds:gestion_utilisateurs_mds", mds_id=mds.id)
    
    if request.method == "POST":
        with transaction.atomic():
            # ✅ CORRIGÉ : Pas de mds_principale sur User
            if profile.principale:
                UserMDSProfile.objects.filter(
                    user=profile.user, principale=True
                ).exclude(pk=profile.pk).update(principale=False)
            profile.actif = False  # Désactivation au lieu de suppression
            profile.save()
        messages.success(request, f"{profile.user.get_full_name()} détaché.")
        return redirect("mds:gestion_utilisateurs_mds", mds_id=mds.id)
        
    return render(request, "mds/supprimer_utilisateur_mds.html", {
        "mds": mds, 
        "profile": profile
    })
