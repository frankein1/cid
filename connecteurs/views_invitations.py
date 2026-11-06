# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/views_invitations.py
"""Étape 2 RDV-Solidarités : liste mensuelle des invitations (référents), courriers, suspension sur la fiche."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from beneficiaire.models import Beneficiaire

from . import rdv_service_public as api
from . import rdvsp_invitations as inv_service
from .invitation_pdf import courrier_invitation_pdf
from .models import CampagneInvitations, InvitationRSA


@login_required
def invitations_rsa(request):
    u = request.user
    campagnes = CampagneInvitations.objects.all()[:3]
    if request.method == "POST":
        campagne = get_object_or_404(CampagneInvitations, pk=request.POST.get("campagne"), envoyee_le__isnull=True)
        cochees = {int(i) for i in request.POST.getlist("ids") if i.isdigit()}
        inv_service.valider(u, campagne, cochees)
        messages.success(request, "Liste validée : seules les personnes cochées seront invitées.")
        return redirect("connecteurs:invitations_rsa")
    lignes = []
    for c in campagnes:
        qs = c.invitations.select_related("beneficiaire", "contrat", "referent")
        if not u.is_superuser:
            qs = qs.filter(referent=u)
        lignes.append((c, list(qs)))
    return render(request, "connecteurs/invitations_rsa.html", {
        "lignes": lignes, "actif": api.est_actif(), "courriel_reel": inv_service.courriel_reel()})


@login_required
def invitation_courrier(request, pk):
    inv = get_object_or_404(InvitationRSA.objects.select_related("beneficiaire", "contrat"), pk=pk)
    if not (request.user.is_superuser or inv.referent_id == request.user.pk
            or inv.beneficiaire.niveau_acces(request.user) == "complet"):
        return HttpResponseForbidden("Réservé au référent et aux agents de la MDS.")
    return FileResponse(courrier_invitation_pdf(inv), as_attachment=False,
                        filename=f"invitation_rdv_{inv.beneficiaire.code_interne}.pdf",
                        content_type="application/pdf")


@login_required
@require_POST
def reservation_en_ligne(request, code_interne):
    b = get_object_or_404(Beneficiaire, code_interne=code_interne)
    if b.niveau_acces(request.user) != "complet":
        return HttpResponseForbidden("Réservé aux agents de la MDS de l'usager.")
    suspendue = request.POST.get("suspendue") == "1"
    inv_service.suspendre(b, request.user, suspendue, request.POST.get("commentaire", ""))
    messages.success(request, "Réservation en ligne suspendue : l'usager passe par l'accueil." if suspendue
                     else "Réservation en ligne de nouveau possible.")
    return redirect(reverse("beneficiaire:detail_beneficiaire", kwargs={"code_interne": code_interne}) + "#rdv-usager")
