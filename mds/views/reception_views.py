# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

#/mds/views/reception_views.py
#(Planning de réception et Salles)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from ..models import MDS, MDSReception, DemiJourneeReception, HoraireMDS
from ..forms import MDSReceptionForm

User = get_user_model()

@login_required
def mes_demi_journees(request):
    agent = request.user
    mds = agent.mds_principale
    if not mds: 
        return redirect("accueil")
    
    demi_journees = DemiJourneeReception.objects.filter(agent=agent, mds=mds).order_by('jour_semaine', 'type_demi_journee')
    
    if not demi_journees.exists():
        for jour in range(5):
            for type_dj in ['MATIN', 'APRES_MIDI']:
                DemiJourneeReception.objects.get_or_create(
                    agent=agent, mds=mds, jour_semaine=jour, type_demi_journee=type_dj, defaults={'actif': False}
                )
        demi_journees = DemiJourneeReception.objects.filter(agent=agent, mds=mds)
    
    jours_semaine = dict(HoraireMDS.JOURS_SEMAINE)
    field_type = DemiJourneeReception._meta.get_field('type_demi_journee')
    types_demi_journee = dict(field_type.choices)
    
    grille = []
    for jour_num, jour_nom in jours_semaine.items():
        if jour_num >= 5: continue
        
        matin = demi_journees.filter(jour_semaine=jour_num, type_demi_journee='MATIN').first()
        aprem = demi_journees.filter(jour_semaine=jour_num, type_demi_journee='APRES_MIDI').first()
        
        grille.append({
            'jour_num': jour_num,
            'jour_nom': jour_nom,
            'matin': matin,
            'apresmidi': aprem,
            'type_lieu_matin': matin.type_lieu if matin else 'MDS',
            'lieu_externe_matin': matin.lieu_externe if matin else '',
            'type_lieu_aprem': aprem.type_lieu if aprem else 'MDS',
            'lieu_externe_aprem': aprem.lieu_externe if aprem else '',
        })
    
    return render(request, "mds/mes_demi_journees.html", {
        "grille": grille,
        "mds": mds,
        "jours_semaine": jours_semaine,
        "types_demi_journee": types_demi_journee
    })

@login_required
@require_POST
def toggle_demi_journee(request):
    agent_id = request.POST.get('agent_id')
    if agent_id and str(agent_id) != str(request.user.id):
        if not request.user.has_perm('mds.change_mds'):
            return JsonResponse({"error": "Interdit"}, status=403)
        try:
            agent = User.objects.get(id=agent_id)
        except User.DoesNotExist:
            return JsonResponse({"error": "Agent introuvable"}, status=404)
    else:
        agent = request.user
    
    mds = agent.mds_principale
    if not mds:
        return JsonResponse({"error": "MDS principale manquante"}, status=400)
    
    jour_semaine = request.POST.get('jour_semaine')
    type_demi_journee = request.POST.get('type_demi_journee')
    
    if not jour_semaine or not type_demi_journee:
        return JsonResponse({"error": "Paramètres manquants"}, status=400)
    
    dj, created = DemiJourneeReception.objects.get_or_create(
        agent=agent, mds=mds, jour_semaine=int(jour_semaine), 
        type_demi_journee=type_demi_journee, defaults={'actif': True}
    )
    
    if not created:
        dj.actif = not dj.actif
        dj.save()
    
    return JsonResponse({"success": True, "actif": dj.actif})

@login_required
@require_POST
def update_demi_journee_lieu(request):
    agent_id = request.POST.get('agent_id')
    if agent_id and str(agent_id) != str(request.user.id):
        if not request.user.has_perm('mds.change_mds'):
            return JsonResponse({"error": "Interdit"}, status=403)
        try:
            agent = User.objects.get(id=agent_id)
        except User.DoesNotExist:
            return JsonResponse({"error": "Agent introuvable"}, status=404)
    else:
        agent = request.user
    
    mds = agent.mds_principale
    if not mds:
        return JsonResponse({"error": "MDS principale manquante"}, status=400)
    
    jour_semaine = request.POST.get('jour_semaine')
    type_demi_journee = request.POST.get('type_demi_journee')
    champ = request.POST.get('champ')
    valeur = request.POST.get('valeur')
    
    if not all([jour_semaine, type_demi_journee, champ]):
        return JsonResponse({"error": "Paramètres manquants"}, status=400)
    
    dj, created = DemiJourneeReception.objects.get_or_create(
        agent=agent,
        mds=mds,
        jour_semaine=int(jour_semaine),
        type_demi_journee=type_demi_journee,
        defaults={'actif': True}
    )
    
    if champ == 'type_lieu':
        if valeur not in ['MDS', 'EXTERNE']:
            return JsonResponse({"error": "Valeur de type_lieu invalide"}, status=400)
        dj.type_lieu = valeur
        if valeur == 'MDS':
            dj.lieu_externe = ''
    elif champ == 'lieu_externe':
        if dj.type_lieu != 'EXTERNE':
            dj.type_lieu = 'EXTERNE'
        dj.lieu_externe = valeur
    else:
        return JsonResponse({"error": "Champ invalide"}, status=400)
    
    dj.save()
    
    return JsonResponse({
        "success": True,
        "type_lieu": dj.type_lieu,
        "lieu_externe": dj.lieu_externe,
    })
