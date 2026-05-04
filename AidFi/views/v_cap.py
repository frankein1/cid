# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# AidFi/views/v_cap.py
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib import messages
from ..models.m_generique import DemandeAide
from ..models.m_cap import CAPCheque
from ..forms.f_cap import CAPAttributionForm
try:
    from mds.models import UserMDSProfile
except ImportError:
    UserMDSProfile = None

# from AidFi.models.m_cap import DemandeCAP  # Assurez-vous que ce modèle existe


@login_required
def cap_attribution(request, demande_id):
    """Attribuer chèque CAP à une demande."""
    if not request.user.a_la_capacite("peut_gerer_finance"):
        return HttpResponseForbidden()
    
    demande = get_object_or_404(DemandeAide, pk=demande_id)
    
    # Vérifier si CAP existe déjà
    cap_existante = getattr(demande, 'cap_cheque', None)
    if cap_existante:
        messages.info(request, "Chèque CAP déjà attribué.")
        return redirect("AidFi:detail_demande", demande_id=demande.id)
    
    if request.method == "POST":
        form = CAPAttributionForm(request.POST)
        if form.is_valid():
            cap = form.save(commit=False)
            cap.demande = demande
            cap.cree_par = request.user
            cap.save()
            messages.success(request, "Chèque CAP attribué avec succès!")
            return redirect("AidFi:detail_demande", demande_id=demande.id)
    else:
        form = CAPAttributionForm()
    
    return render(request, "AidFi/cap_attribution.html", {
        "form": form, 
        "demande": demande
    })

@login_required
def cap_detail(request, demande_id):
    """
    Détail d'une attribution de chèque CAP.
    """
    demande = get_object_or_404(DemandeCAP, pk=demande_id)
    
    # Vérification des permissions
    if not request.user.a_la_capacite("peut_voir"):
        return HttpResponseForbidden("Accès refusé")
    
    return render(request, "AidFi/cap_detail.html", {
        "demande": demande,
        "beneficiaire": demande.beneficiaire,
    })
