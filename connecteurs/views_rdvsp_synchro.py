# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/views_rdvsp_synchro.py
"""
Synchronisation des agendas avec RDV-Solidarités (connecteurs/rdvsp_synchro.py) :
- réception des avis automatiques signés (webhooks), sans connexion mais avec vérification de signature ;
- actions d'administration : synchroniser maintenant, déclarer l'adresse de CID.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotFound, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import rdv_service_public as api
from . import rdvsp_synchro as sync


@csrf_exempt
@require_POST
def avis(request):
    """Avis automatique de RDV-Solidarités : refusé si la signature (HMAC SHA-256 du corps) ne correspond pas."""
    if not api.est_actif():
        return HttpResponseNotFound("Passerelle désactivée.")
    corps = request.body
    if not sync.signature_valide(corps, request.headers.get("X-Lapin-Signature", "")):
        return HttpResponseForbidden("Signature invalide.")
    a = sync.recevoir_avis(corps)
    # 200 même si le traitement a échoué : l'avis est conservé pour reprise, inutile que RDV-Solidarités le renvoie
    return JsonResponse({"recu": True, "traite": a.traite})


def _admin(u):
    return u.is_superuser


@login_required
@user_passes_test(_admin)
@require_POST
def synchroniser(request):
    try:
        b = sync.synchroniser()
    except (sync.SynchroErreur, api.RDVSPErreur) as e:
        messages.error(request, f"Synchronisation impossible : {e}")
        return redirect("connecteurs:rdvsp_etat")
    messages.success(request, f"Synchronisation faite : {b['publiees']} permanence(s) publiée(s), "
                              f"{b['prolongees']} prolongée(s), {b['neutralisees']} retirée(s), "
                              f"{b['blocages']} blocage(s) envoyé(s).")
    for e in b["erreurs"][:10]:
        messages.warning(request, e)
    return redirect("connecteurs:rdvsp_etat")


@login_required
@user_passes_test(_admin)
@require_POST
def declarer(request):
    url = request.build_absolute_uri(reverse("connecteurs:rdvsp_avis"))
    try:
        for mds, erreur in sync.declarer_avis(url):
            (messages.warning if erreur else messages.success)(
                request, f"{mds} : {erreur or 'adresse de CID déclarée'}")
    except (sync.SynchroErreur, api.RDVSPErreur) as e:
        messages.error(request, str(e))
    return redirect("connecteurs:rdvsp_etat")
