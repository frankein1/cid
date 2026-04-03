from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render

from AidFi.models.m_afase import DemandeAFASE


@login_required
def dashboard_cadre(request):
    """
    Dashboard cadre :
    liste de toutes les AFASE à décider
    """

    if not request.user.a_la_capacite("peut_decider"):
        return HttpResponseForbidden("Accès refusé")

    demandes = (
        DemandeAFASE.objects
        .filter(statut="EVALUATION")
        .select_related("beneficiaire")
        .order_by("created_at")
    )

    return render(
        request,
        "AidFi/dashboard_cadre.html",
        {
            "demandes": demandes,
        },
    )
