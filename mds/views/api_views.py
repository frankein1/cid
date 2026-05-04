# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# /mds/views/api_views.py
# (Toutes tes fonctions JSON et utilitaires CP)

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from core.utils.cp import get_ville_from_cp, get_villes_multiples
from ..models import MDS, UserMDSProfile, MDSReception

@login_required
def ajax_get_ville_from_cp(request):
    code_postal = request.GET.get("cp", "").strip()
    if len(code_postal) == 5 and code_postal.isdigit():
        villes = get_villes_multiples(code_postal)
        return JsonResponse({"success": True, "villes": [v.upper() for v in villes]})
    return JsonResponse({"success": False}, status=400)

@login_required
def get_utilisateurs_mds_json(request, mds_id):
    mds = get_object_or_404(MDS, id=mds_id)
    if not request.user.a_acces_mds(mds): 
        return JsonResponse({"error": "Interdit"}, status=403)
    profiles = UserMDSProfile.objects.filter(mds=mds, actif=True).select_related("user")
    return JsonResponse({"utilisateurs": [{"id": p.user.id, "nom": p.user.get_full_name()} for p in profiles]})

@login_required
def get_salles_mds_json(request, mds_id):
    mds = get_object_or_404(MDS, id=mds_id)
    if not request.user.a_acces_mds(mds):
        return JsonResponse({"error": "Permission refusée"}, status=403)
    salles = MDSReception.objects.filter(mds=mds, actif=True)
    data = [{"id": s.id, "nom": s.nom, "capacite": s.capacite, "type": s.get_type_salle_display()} for s in salles]
    return JsonResponse({"salles": data})
