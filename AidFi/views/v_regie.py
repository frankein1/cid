# AidFi/views/v_regie.py

from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib import messages
from ..models.m_generique import DemandeAide
from ..forms.f_regie import RegieUrgenceForm
try:
    from mds.models import UserMDSProfile
except ImportError:
    UserMDSProfile = None
#### from AidFi.models.m_regie import DemandeRegie  # Assurez-vous que ce modèle existe


@login_required
def regie_urgence_create(request, demande_id):
    if not request.user.a_la_capacite("peut_gerer_finance"):
        return HttpResponseForbidden()
    
    demande = get_object_or_404(DemandeAide, pk=demande_id)
    if request.method == "POST":
        form = RegieUrgenceForm(request.POST)
        if form.is_valid():
            regie = form.save(commit=False)
            regie.demande = demande
            regie.cree_par = request.user
            regie.save()
            messages.success(request, "Régie créée")
            return redirect("AidFi:detail_demande", demande_id=demande.id)
    else:
        form = RegieUrgenceForm()
    return render(request, "AidFi/regie_urgence_form.html", {"form": form, "demande": demande})
    
@login_required
def regie_detail(request, demande_id):
    """
    Détail d'une demande de régie d'urgence.
    """
    demande = get_object_or_404(DemandeRegie, pk=demande_id)
    
    # Vérification des permissions
    if not request.user.a_la_capacite("peut_voir"):
        return HttpResponseForbidden("Accès refusé")
    
    return render(request, "AidFi/regie_detail.html", {
        "demande": demande,
        "beneficiaire": demande.beneficiaire,
    })




