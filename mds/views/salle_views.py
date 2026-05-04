# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# mds/views/salle_views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import MDS, MDSReception
from ..forms import MDSReceptionForm

@login_required
def gestion_salles_mds(request, mds_id):
    mds = get_object_or_404(MDS, id=mds_id)
    
    # Correction : Utilisation du nouveau système de capacités unifié
    if not (request.user.is_superuser or 
            mds.responsable == request.user or 
            request.user.a_la_capacite('peut_administrer')):
        messages.error(request, "Permission insuffisante pour gérer les salles.")
        return redirect("mds:detail_mds", mds_id=mds.id)
    
    salles = MDSReception.objects.filter(mds=mds).order_by('nom')
    
    # OPTIMISATION pour éviter l'erreur 'split' dans le template :
    # Si tes salles ont des jours stockés en chaîne (ex: "Lundi,Mardi"), 
    # on les transforme en liste ici même.
    for salle in salles:
        if hasattr(salle, 'jours_ouverture') and isinstance(salle.jours_ouverture, str):
            salle.jours_list = [j.strip() for j in salle.jours_ouverture.split(',') if j]

    return render(request, "mds/gestion_salles_mds.html", {
        "mds": mds, 
        "salles": salles
    })

@login_required
def creer_salle_mds(request, mds_id):
    mds = get_object_or_404(MDS, id=mds_id)
    
    if not (request.user.is_superuser or mds.responsable == request.user or request.user.a_la_capacite('peut_administrer')):
        messages.error(request, "Permission insuffisante.")
        return redirect("mds:gestion_salles_mds", mds_id=mds.id)
    
    if request.method == 'POST':
        form = MDSReceptionForm(request.POST)
        if form.is_valid():
            salle = form.save(commit=False)
            salle.mds = mds
            salle.save()
            messages.success(request, f"Salle {salle.nom} créée avec succès.")
            return redirect("mds:gestion_salles_mds", mds_id=mds.id)
    else:
        form = MDSReceptionForm()
    return render(request, "mds/creer_salle_mds.html", {"form": form, "mds": mds})

@login_required
def modifier_salle_mds(request, mds_id, salle_id):
    mds = get_object_or_404(MDS, id=mds_id)
    salle = get_object_or_404(MDSReception, id=salle_id, mds=mds)
    
    if not (request.user.is_superuser or mds.responsable == request.user or request.user.a_la_capacite('peut_administrer')):
        messages.error(request, "Permission insuffisante.")
        return redirect("mds:gestion_salles_mds", mds_id=mds.id)
    
    if request.method == 'POST':
        form = MDSReceptionForm(request.POST, instance=salle)
        if form.is_valid():
            form.save()
            messages.success(request, f"Salle {salle.nom} modifiée.")
            return redirect("mds:gestion_salles_mds", mds_id=mds.id)
    else:
        form = MDSReceptionForm(instance=salle)
    return render(request, "mds/creer_salle_mds.html", {"form": form, "mds": mds, "salle": salle})

@login_required
def supprimer_salle_mds(request, mds_id, salle_id):
    mds = get_object_or_404(MDS, id=mds_id)
    salle = get_object_or_404(MDSReception, id=salle_id, mds=mds)
    
    if not (request.user.is_superuser or mds.responsable == request.user or request.user.a_la_capacite('peut_administrer')):
        messages.error(request, "Permission insuffisante.")
        return redirect("mds:gestion_salles_mds", mds_id=mds.id)
    
    if request.method == 'POST':
        nom = salle.nom
        salle.delete()
        messages.success(request, f"Salle {nom} supprimée.")
        return redirect("mds:gestion_salles_mds", mds_id=mds.id)
    return render(request, "mds/supprimer_salle_mds.html", {"mds": mds, "salle": salle})
