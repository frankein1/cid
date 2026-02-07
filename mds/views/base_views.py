#/mds/views/base_views.py
# (Le socle : Liste, Détails et Statistiques)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from ..models import MDS, UserMDSProfile, MDSReception
from ..forms import MDSForm

@login_required
def liste_mds(request):
    user = request.user
    mds_qs = MDS.objects.all() if (user.is_superuser or user.has_perm("mds.view_mds")) else \
             MDS.objects.filter(id__in=user.profils_mds.filter(actif=True).values_list("mds_id", flat=True))
    
    query = request.GET.get("q", "")
    if query:
        mds_qs = mds_qs.filter(Q(code_mds__icontains=query) | Q(nom__icontains=query) | Q(ville__icontains=query))

    paginator = Paginator(mds_qs.order_by("code_mds"), 20)
    return render(request, "mds/liste_mds.html", {"mds_list": paginator.get_page(request.GET.get("page")), "query": query})

@login_required
def detail_mds(request, mds_id):
    mds = get_object_or_404(MDS, id=mds_id)
    
    if not request.user.a_acces_mds(mds):
        messages.error(request, "Accès refusé.")
        return redirect("mds:liste_mds")

    # 1. On récupère les profils actifs
    profiles_actifs = UserMDSProfile.objects.filter(mds=mds, actif=True).select_related("user")
    salles_actives = MDSReception.objects.filter(mds=mds, actif=True)

    # 2. Calcul des statistiques pour les petits badges du haut
    capacite_actuelle = profiles_actifs.count()
    total_capacite_salles = sum(s.capacite for s in salles_actives)
    
    # Calcul du % d'occupation sécurisé
    pourcentage = 0
    if mds.nb_agents_max and mds.nb_agents_max > 0:
        pourcentage = int((capacite_actuelle / mds.nb_agents_max) * 100)

    # 3. Calcul du dictionnaire stats_profils (POUR LE GRAPHIQUE)
    # C'est cette boucle qui va faire apparaître Franck par métier
    stats_profils = {}
    for p in profiles_actifs:
        # On va chercher le premier profil métier rattaché à l'User Django
        profil_metier = p.user.profils.first()
        nom_metier = profil_metier.nom if profil_metier else "Non défini"
        stats_profils[nom_metier] = stats_profils.get(nom_metier, 0) + 1

    # 4. Statut d'ouverture (temporel)
    from django.utils import timezone
    import datetime
    
    # On récupère l'heure actuelle du serveur
    maintenant = timezone.localtime().time()
    est_ouverte = False
    
    # On vérifie si la MDS est active ET si on est dans les clous horaires
    if mds.active:
        # On récupère les horaires de la MDS (ou 08h-18h par défaut si vides)
        debut = getattr(mds, 'horaire_ouverture', datetime.time(8, 0))
        fin = getattr(mds, 'horaire_fermeture', datetime.time(18, 0))
        
        if debut <= maintenant <= fin:
            est_ouverte = True

    return render(request, "mds/detail_mds.html", {
        "mds": mds,
        "profiles": profiles_actifs,
        "salles": salles_actives,
        "capacite_actuelle": capacite_actuelle,           # Requis par template
        "total_capacite_salles": total_capacite_salles,   # Requis par template
        "pourcentage_occupation": pourcentage,            # Requis par template
        "stats_profils": stats_profils,                   # Requis par template
        "est_ouverte": est_ouverte,                       # Requis par template
    })


@login_required
def statistiques_mds(request, mds_id):
    mds = get_object_or_404(MDS, id=mds_id)
    
    # Sécurité d'accès
    # On vérifie si la méthode 'a_la_capacite' existe sur l'utilisateur pour éviter un plantage
    peut_admin = False
    if hasattr(request.user, 'a_la_capacite'):
        peut_admin = request.user.a_la_capacite('peut_administrer')

    if not request.user.is_superuser and mds.responsable != request.user and not peut_admin:
        messages.error(request, "Accès refusé.")
        return redirect("mds:detail_mds", mds_id=mds.id)
    
    # Calcul des stats de manière sécurisée
    stats_list = []
    # On utilise les noms EXACTS définis dans core/models/profil.py
    capacites_a_tester = [
        ("Créateurs", "peut_creer"),     # au lieu de peut_creer_dossier
        ("Validateurs", "peut_valider"), # au lieu de peut_valider_dossier
    ]
    for label, cap in capacites_a_tester:
        try:
            # On tente l'appel, si le champ n'existe pas dans le modèle Profil, 
            # le modèle MDS lèvera une FieldError qu'on attrape ici.
            count = mds.get_utilisateurs_par_capacite(cap).count()
            stats_list.append({"nom": label, "count": count})
        except Exception:
            # Si le champ n'existe pas, on affiche 0 ou on ignore
            stats_list.append({"nom": label, "count": 0})

    return render(request, "mds/statistiques_mds.html", {
        "mds": mds,
        "total_utilisateurs": UserMDSProfile.objects.filter(mds=mds, actif=True).count(),
        "stats_capacites": stats_list,
        "capacite_actuelle": getattr(mds, 'get_capacite_actuelle', lambda: 0)(),
        "pourcentage_occupation": getattr(mds, 'get_pourcentage_occupation', lambda: 0)(),
    })


@login_required
@permission_required('mds.add_mds', raise_exception=True)
def creer_mds(request):
    if request.method == 'POST':
        form = MDSForm(request.POST)
        if form.is_valid():
            mds = form.save(commit=False)
            mds.cree_par = request.user
            mds.save()
            messages.success(request, f"MDS {mds.code_mds} créée avec succès.")
            return redirect("mds:detail_mds", mds_id=mds.id)
    else:
        form = MDSForm()
    return render(request, "mds/creation_mds.html", {"form": form, "title": "Créer une nouvelle MDS"})

@login_required
def modifier_mds(request, mds_id):
    mds = get_object_or_404(MDS, id=mds_id)
    if not mds.peut_etre_modifiee_par(request.user):
        messages.error(request, "Accès refusé.")
        return redirect("mds:detail_mds", mds_id=mds.id)
    
    if request.method == 'POST':
        form = MDSForm(request.POST, instance=mds)
        if form.is_valid():
            form.save()
            messages.success(request, f"La MDS {mds.code_mds} a été modifiée avec succès.")
            return redirect("mds:detail_mds", mds_id=mds.id)
    else:
        form = MDSForm(instance=mds)
    return render(request, "mds/creation_mds.html", {"form": form, "mds": mds, "title": f"Modifier la MDS {mds.code_mds}"})
