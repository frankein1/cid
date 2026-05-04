# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# protection_enfance/views.py - VERSION COMPLÈTE

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone

from .models import InformationPreoccupante, HistoriqueAction


# =============================================================================
# VUES TABLEAU DE BORD
# =============================================================================

@login_required
def dashboard_ase(request):
    """Tableau de bord ASE avec statistiques"""
    user = request.user
    
    # Statistiques générales (selon permissions)
    if user.groups.filter(name__in=['DITAS_Direction', 'DGAS_Direction']).exists():
        total_ips = InformationPreoccupante.objects.count()
        mes_ips = InformationPreoccupante.objects.filter(
            Q(referent_1=user) | Q(referent_2=user)
        ).count()
    else:
        total_ips = InformationPreoccupante.objects.filter(
            Q(mds_principale=user.mds_principale) |
            Q(mds_partage=user.mds_principale) |
            Q(referent_1=user) |
            Q(referent_2=user)
        ).distinct().count()
        mes_ips = InformationPreoccupante.objects.filter(
            Q(referent_1=user) | Q(referent_2=user)
        ).count()
    
    # IPs récentes
    ips_recentes = InformationPreoccupante.objects.filter(
        Q(mds_principale=user.mds_principale) |
        Q(referent_1=user) |
        Q(referent_2=user)
    ).distinct().order_by('-date_creation')[:5]
    
    context = {
        'total_ips': total_ips,
        'mes_ips': mes_ips,
        'ips_recentes': ips_recentes,
    }
    return render(request, 'protection_enfance/dashboard/ase.html', context)


@login_required
def dashboard_crip(request):
    """Tableau de bord CRIP"""
    context = {}
    return render(request, 'protection_enfance/dashboard/crip.html', context)


# =============================================================================
# VUES INFORMATIONS PRÉOCCUPANTES
# =============================================================================

@login_required
@permission_required('protection_enfance.view_informationpreoccupante', raise_exception=True)
def ip_liste(request):
    """
    Liste des IP accessibles par l'utilisateur.
    
    Filtre automatique selon :
    - Direction : voit tout
    - MDS : voit les IP de sa MDS + celles où il est référent
    """
    user = request.user
    
    # Direction : voit tout
    if user.groups.filter(name__in=['DITAS_Direction', 'DGAS_Direction']).exists():
        ips = InformationPreoccupante.objects.all()
    
    # Autres : filtre sur MDS + référent
    else:
        ips = InformationPreoccupante.objects.filter(
            Q(mds_principale=user.mds_principale) |  # IP de sa MDS
            Q(mds_partage=user.mds_principale) |     # IP partagées avec sa MDS
            Q(referent_1=user) |                      # IP où il est référent 1
            Q(referent_2=user)                        # IP où il est référent 2
        ).distinct()
    
    # Recherche
    query = request.GET.get('q')
    if query:
        ips = ips.filter(
            Q(numero__icontains=query) |
            Q(enfant_nom__icontains=query)
        )
    
    # Filtre par statut
    statut = request.GET.get('statut')
    if statut:
        ips = ips.filter(statut=statut)
    
    # Filtre "Mes dossiers" (où je suis référent)
    mes_dossiers = request.GET.get('mes_dossiers') == 'oui'
    if mes_dossiers:
        ips = ips.filter(Q(referent_1=user) | Q(referent_2=user))
    
    # Tri
    ips = ips.select_related('mds_principale', 'referent_1', 'referent_2').order_by('-date_creation')
    
    # Pagination
    paginator = Paginator(ips, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'statut': statut,
        'mes_dossiers': mes_dossiers,
        'statuts_choices': InformationPreoccupante._meta.get_field('statut').choices,
    }
    return render(request, 'protection_enfance/informations_preoccupantes/liste.html', context)


@login_required
@permission_required('protection_enfance.add_informationpreoccupante', raise_exception=True)
def ip_creation(request):
    """
    Créer une nouvelle IP.
    
    Auto-assigne :
    - mds_principale = MDS de l'utilisateur
    - referent_1 = utilisateur créateur
    """
    if not request.user.mds_principale:
        messages.error(request, "Vous devez être rattaché à une MDS pour créer une IP.")
        return redirect('protection_enfance:ip_liste')
    
    if request.method == 'POST':
        try:
            # Création de l'IP
            ip = InformationPreoccupante.create_with_numero(
                auteur=request.user,
                mds_principale=request.user.mds_principale,
                referent_1=request.user,
                origine=request.POST.get('origine', 'AUTRE'),
                description=request.POST.get('description', ''),
                enfant_nom=request.POST.get('enfant_nom', ''),
                enfant_date_naissance=request.POST.get('enfant_date_naissance') or None,
            )
            
            # Historique
            HistoriqueAction.objects.create(
                information=ip,
                action="Création du dossier",
                user=request.user,
                commentaire="Dossier créé"
            )
            
            messages.success(request, f"Dossier IP {ip.numero} créé avec succès.")
            return redirect('protection_enfance:ip_detail', ip_id=ip.numero)
        
        except Exception as e:
            messages.error(request, f"Erreur lors de la création : {str(e)}")
    
    # Choix d'origine pour le formulaire
    origines = InformationPreoccupante.origine_CHOICES
    
    context = {
        'origines': origines,
    }
    return render(request, 'protection_enfance/informations_preoccupantes/creation.html', context)


@login_required
@permission_required('protection_enfance.view_informationpreoccupante', raise_exception=True)
def ip_detail(request, ip_id):
    """
    Détail d'une IP.
    
    Vérifie les permissions au niveau objet :
    - Peut-il voir ce dossier ?
    - Peut-il le modifier ?
    - Peut-il transmettre au Parquet ?
    """
    # ip_id peut être le numéro (D13-00000001) ou l'ID numérique
    try:
        ip = InformationPreoccupante.objects.select_related(
            'mds_principale', 'referent_1', 'referent_2', 'auteur'
        ).get(numero=ip_id)
    except InformationPreoccupante.DoesNotExist:
        try:
            ip = InformationPreoccupante.objects.select_related(
                'mds_principale', 'referent_1', 'referent_2', 'auteur'
            ).get(id=ip_id)
        except InformationPreoccupante.DoesNotExist:
            messages.error(request, f"Dossier IP '{ip_id}' introuvable.")
            return redirect('protection_enfance:ip_liste')
    
    # Vérification permission objet
    if not ip.peut_voir(request.user):
        raise PermissionDenied(
            "Vous n'avez pas accès à ce dossier. "
            "Il n'appartient pas à votre MDS et vous n'en êtes pas référent."
        )
    
    # Historique des actions
    historique = ip.historique_actions.select_related('user').all()[:20]
    
    # Déterminer les capacités de l'utilisateur sur ce dossier
    niveau_acces = ip.get_niveau_acces(request.user)
    
    context = {
        'ip': ip,
        'historique': historique,
        'niveau_acces': niveau_acces,
        'peut_modifier': ip.peut_modifier(request.user),
        'peut_transmettre': ip.peut_transmettre_parquet(request.user),
        'est_referent': ip.est_referent(request.user),
    }
    return render(request, 'protection_enfance/informations_preoccupantes/detail.html', context)


@login_required
@permission_required('protection_enfance.change_informationpreoccupante', raise_exception=True)
def ip_modifier(request, ip_id):
    """
    Modifier une IP.
    
    Vérifie que l'utilisateur peut modifier CE dossier spécifique.
    """
    ip = get_object_or_404(InformationPreoccupante, numero=ip_id)
    
    # Vérification permission objet
    if not ip.peut_modifier(request.user):
        messages.error(
            request, 
            "Vous ne pouvez pas modifier ce dossier. "
            "Vous devez être référent ou cadre de la MDS en charge."
        )
        return redirect('protection_enfance:ip_detail', ip_id=ip.numero)
    
    if request.method == 'POST':
        try:
            # Mise à jour des champs
            ip.description = request.POST.get('description', ip.description)
            ip.statut = request.POST.get('statut', ip.statut)
            ip.enfant_nom = request.POST.get('enfant_nom', ip.enfant_nom)
            ip.origine = request.POST.get('origine', ip.origine)
            
            date_naissance = request.POST.get('enfant_date_naissance')
            if date_naissance:
                ip.enfant_date_naissance = date_naissance
            
            ip.save()
            
            # Historique
            HistoriqueAction.objects.create(
                information=ip,
                action="Modification du dossier",
                user=request.user,
                commentaire=request.POST.get('commentaire_modif', 'Dossier modifié')
            )
            
            messages.success(request, f"Dossier {ip.numero} modifié avec succès.")
            return redirect('protection_enfance:ip_detail', ip_id=ip.numero)
        
        except Exception as e:
            messages.error(request, f"Erreur lors de la modification : {str(e)}")
    
    context = {
        'ip': ip,
        'origines': InformationPreoccupante.origine_CHOICES,
        'statuts': InformationPreoccupante._meta.get_field('statut').choices,
    }
    return render(request, 'protection_enfance/informations_preoccupantes/modifier.html', context)


@login_required
@permission_required('protection_enfance.transmettre_parquet', raise_exception=True)
def ip_transmettre_parquet(request, ip_id):
    """
    Transmettre une IP au Parquet.
    
    Réservé aux cadres et direction.
    """
    ip = get_object_or_404(InformationPreoccupante, numero=ip_id)
    
    # Vérification permission objet
    if not ip.peut_transmettre_parquet(request.user):
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de transmettre ce dossier au Parquet. "
            "Action réservée aux cadres et direction."
        )
        return redirect('protection_enfance:ip_detail', ip_id=ip.numero)
    
    if request.method == 'POST':
        ip.transmit_parquet = True
        ip.transmis_parquet_date = timezone.now()
        ip.statut = 'TRANSMIS_PARQUET'
        ip.save()
        
        # Historique
        HistoriqueAction.objects.create(
            information=ip,
            action="Transmission au Parquet",
            user=request.user,
            commentaire=request.POST.get('commentaire', 'Dossier transmis au Parquet')
        )
        
        messages.success(request, f"Dossier {ip.numero} transmis au Parquet.")
        return redirect('protection_enfance:ip_detail', ip_id=ip.numero)
    
    context = {
        'ip': ip,
    }
    return render(request, 'protection_enfance/informations_preoccupantes/transmettre_parquet.html', context)


@login_required
@permission_required('protection_enfance.change_informationpreoccupante', raise_exception=True)
def ip_assigner_referents(request, ip_id):
    """
    Modifier le binôme de référents d'une IP.
    
    Réservé aux cadres de la MDS en charge.
    """
    ip = get_object_or_404(InformationPreoccupante, numero=ip_id)
    
    # Seuls les cadres de la MDS principale peuvent changer les référents
    if not request.user.groups.filter(name__in=['MDS_Cadres', 'DITAS_Direction']).exists():
        messages.error(request, "Action réservée aux cadres.")
        return redirect('protection_enfance:ip_detail', ip_id=ip.numero)
    
    if request.user.groups.filter(name='MDS_Cadres').exists():
        if request.user.mds_principale != ip.mds_principale:
            messages.error(request, "Vous ne pouvez modifier que les dossiers de votre MDS.")
            return redirect('protection_enfance:ip_detail', ip_id=ip.numero)
    
    if request.method == 'POST':
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        referent_1_id = request.POST.get('referent_1')
        referent_2_id = request.POST.get('referent_2')
        
        try:
            if referent_1_id:
                ip.referent_1 = User.objects.get(id=referent_1_id)
            if referent_2_id:
                ip.referent_2 = User.objects.get(id=referent_2_id)
            
            ip.save()
            
            # Historique
            ref1 = ip.referent_1.get_full_name() if ip.referent_1 else 'Non assigné'
            ref2 = ip.referent_2.get_full_name() if ip.referent_2 else 'Non assigné'
            
            HistoriqueAction.objects.create(
                information=ip,
                action="Modification du binôme référent",
                user=request.user,
                commentaire=f"Nouveaux référents : {ref1} et {ref2}"
            )
            
            messages.success(request, "Binôme référent mis à jour.")
            return redirect('protection_enfance:ip_detail', ip_id=ip.numero)
        
        except Exception as e:
            messages.error(request, f"Erreur : {str(e)}")
    
    # Liste des agents de la MDS pour le formulaire
    from django.contrib.auth import get_user_model
    User = get_user_model()
    agents_mds = User.objects.filter(
        mds_principale=ip.mds_principale,
        is_active=True
    ).order_by('last_name', 'first_name')
    
    context = {
        'ip': ip,
        'agents_mds': agents_mds,
    }
    return render(request, 'protection_enfance/informations_preoccupantes/assigner_referents.html', context)


# =============================================================================
# VUES PLACEMENTS (Placeholders pour l'instant)
# =============================================================================

@login_required
def placements_liste(request):
    """Liste des placements"""
    context = {}
    return render(request, 'protection_enfance/placements/liste.html', context)


@login_required
def placement_detail(request, placement_id):
    """Détail d'un placement"""
    context = {
        'placement_id': placement_id,
    }
    return render(request, 'protection_enfance/placements/detail.html', context)
