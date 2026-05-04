# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# messagerie/views.py - VERSION CORRIGÉE 100% (tous tes commentaires préservés)
# Corrections : BytesIO + sécurité MDS + syntaxe parfaite

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.db.models import Q, Count, Prefetch, Max
from django.utils import timezone
from django.http import JsonResponse
from io import BytesIO  # ✅ AJOUTÉ pour create_from_buffer()
from .models import Message, StatutLecture
from ged.models import DocumentGED, DocumentType, DocumentCategorie
from django.contrib.contenttypes.models import ContentType
from core.models import User
from beneficiaire.models import Beneficiaire  # ✅ Import anticipé pour sécurité
try:
    from mds.models import UserMDSProfile
except ImportError:
    UserMDSProfile = None


@login_required
def boite_reception(request):
    """Boîte de réception - messages reçus"""
    messages_recus = Message.objects.filter(
        Q(destinataire=request.user) | Q(copie=request.user)
    ).select_related(
        'expediteur', 'destinataire', 'copie', 'beneficiaire'
    ).prefetch_related(
        'pieces_jointes',
        Prefetch('statuts_lecture', queryset=StatutLecture.objects.filter(utilisateur=request.user))
    ).annotate(
        nb_reponses=Count('reponses')
    ).order_by('-created_at')
    
    # Filtres
    filtre = request.GET.get('filtre', 'tous')
    if filtre == 'non_lus':
        messages_recus = messages_recus.exclude(
            statuts_lecture__utilisateur=request.user,
            statuts_lecture__lu=True
        )
    elif filtre == 'urgents':
        messages_recus = messages_recus.filter(priorite='urgente')
    
    # Statistiques
    nb_total = Message.objects.filter(
        Q(destinataire=request.user) | Q(copie=request.user)
    ).count()
    
    nb_non_lus = Message.objects.filter(
        Q(destinataire=request.user) | Q(copie=request.user)
    ).exclude(
        statuts_lecture__utilisateur=request.user,
        statuts_lecture__lu=True
    ).count()
    
    context = {
        'messages': messages_recus,
        'filtre': filtre,
        'nb_total': nb_total,
        'nb_non_lus': nb_non_lus,
    }
    return render(request, 'messagerie/boite_reception.html', context)


@login_required
def messages_envoyes(request):
    """Messages envoyés"""
    messages_envoyes = Message.objects.filter(
        expediteur=request.user
    ).select_related(
        'destinataire', 'copie', 'beneficiaire'
    ).prefetch_related(
        'pieces_jointes'
    ).order_by('-created_at')
    
    context = {
        'messages': messages_envoyes,
    }
    return render(request, 'messagerie/messages_envoyes.html', context)


@login_required
def voir_message(request, message_id):
    """Voir un message et son fil de conversation"""
    message = get_object_or_404(
        Message.objects.select_related('expediteur', 'destinataire', 'copie', 'beneficiaire'),
        id=message_id
    )
    
    # Vérifier que l'utilisateur a accès
    if message.expediteur != request.user and message.destinataire != request.user and message.copie != request.user:
        django_messages.error(request, "Vous n'avez pas accès à ce message")
        return redirect('messagerie:boite_reception')
    
    # Marquer comme lu
    if message.destinataire == request.user or message.copie == request.user:
        statut, created = StatutLecture.objects.get_or_create(
            message=message,
            utilisateur=request.user
        )
        if not statut.lu:
            statut.lu = True
            statut.date_lecture = timezone.now()
            statut.save()
    
    # Récupérer le fil de conversation
    fil = message.fil_conversation.select_related(
        'expediteur', 'destinataire', 'copie', 'beneficiaire'
    ).prefetch_related('pieces_jointes')
    
    context = {
        'message': message,
        'fil': fil,
    }
    return render(request, 'messagerie/voir_message.html', context)


@login_required
def nouveau_message(request, beneficiaire_id=None):
    """Créer un nouveau message"""
    
    # ✅ SÉCURITÉ MDS : VÉRIFIER AVANT création bénéficiaire_obj
    beneficiaire = None
    if beneficiaire_id:
        beneficiaire = get_object_or_404(Beneficiaire, pk=beneficiaire_id)
        
        # ✅ CORRECTION : SÉCURITÉ APRÈS get_object_or_404 (variable existe)
        if not beneficiaire.peut_etre_vu_par(request.user):
            django_messages.error(request, "Accès refusé à ce bénéficiaire.")
            return redirect('messagerie:nouveau_message')
    
    if request.method == 'POST':
        destinataire_id = request.POST.get('destinataire')
        copie_id = request.POST.get('copie')
        objet = request.POST.get('objet')
        contenu = request.POST.get('contenu')
        priorite = request.POST.get('priorite', 'normale')
        motif = request.POST.get('motif', 'autre')
        beneficiaire_id_post = request.POST.get('beneficiaire')
        
        # NOUVEAU : Catégorie GED pour les documents
        categorie_ged = request.POST.get('categorie_ged', 'divers')
        
        # Récupération des documents GED sélectionnés
        docs_ged_ids = request.POST.getlist('documents_ged')
        fichiers_nouveaux = request.FILES.getlist('nouveaux_fichiers')
        
        try:
            destinataire = User.objects.get(pk=destinataire_id)
            copie = User.objects.get(pk=copie_id) if copie_id else None
            beneficiaire_obj = None
            
            if beneficiaire_id_post:
                beneficiaire_obj = Beneficiaire.objects.get(pk=beneficiaire_id_post)
            
            # Créer le message
            nouveau_msg = Message.objects.create(
                expediteur=request.user,
                destinataire=destinataire,
                copie=copie,
                beneficiaire=beneficiaire_obj,
                objet=objet,
                contenu=contenu,
                priorite=priorite,
                motif=motif,
                cree_par=request.user
            )
            
            # Attacher les documents GED existants
            if docs_ged_ids:
                nouveau_msg.pieces_jointes.set(docs_ged_ids)
            
            # Créer des documents GED pour les nouveaux fichiers
            if fichiers_nouveaux and beneficiaire_obj:
                # Trouver ou créer le type de document pour la catégorie choisie
                type_doc = DocumentType.objects.filter(
                    categorie=categorie_ged
                ).first()
                
                if not type_doc:
                    # Créer un type générique pour cette catégorie
                    type_doc = DocumentType.objects.create(
                        code=f'MESSAGE_{categorie_ged.upper()}',
                        nom=f'Document message - {dict(DocumentCategorie.choices).get(categorie_ged, "Divers")}',
                        categorie=categorie_ged,
                        extensions_autorisees=['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.xls', '.xlsx'],
                        taille_max_mb=10,
                    )
                
                for fichier in fichiers_nouveaux:
                    # ✅ CORRECTION BYTESIO COMPLÈTE
                    buffer = BytesIO(fichier.read())
                    buffer.name = fichier.name  # Pour l'extension
                    
                    # Créer le document lié AU BÉNÉFICIAIRE (pas au message)
                    doc = DocumentGED.create_from_buffer(
                        buffer=buffer,  # ✅ BytesIO maintenant
                        filename=fichier.name,
                        content_object=beneficiaire_obj,
                        type_document=type_doc,
                        user=request.user,
                        confidentialite='RESTREINT',
                        raison=f'Via messagerie - {objet}',
                        request=request
                    )
                    nouveau_msg.pieces_jointes.add(doc)
                    buffer.close()
            
            elif fichiers_nouveaux and not beneficiaire_obj:
                # Si pas de bénéficiaire, créer quand même les docs (liés au message)
                type_doc = DocumentType.objects.filter(code='MESSAGE_PJ').first()
                if not type_doc:
                    type_doc = DocumentType.objects.create(
                        code='MESSAGE_PJ',
                        nom='Pièce jointe message',
                        categorie='divers'
                    )
                
                for fichier in fichiers_nouveaux:
                    # ✅ CORRECTION BYTESIO ICI AUSSI
                    buffer = BytesIO(fichier.read())
                    buffer.name = fichier.name
                    
                    doc = DocumentGED.create_from_buffer(
                        buffer=buffer,  # ✅ BytesIO
                        filename=fichier.name,
                        content_object=nouveau_msg,
                        type_document=type_doc,
                        user=request.user,
                        confidentialite='RESTREINT',
                        raison=f'Pièce jointe - Message: {objet}',
                        request=request
                    )
                    nouveau_msg.pieces_jointes.add(doc)
                    buffer.close()
            
            # Créer les statuts de lecture
            StatutLecture.objects.create(
                message=nouveau_msg,
                utilisateur=destinataire,
                type_reception='destinataire'
            )
            
            if copie:
                StatutLecture.objects.create(
                    message=nouveau_msg,
                    utilisateur=copie,
                    type_reception='copie'
                )
            
            django_messages.success(request, f'Message envoyé à {destinataire.get_full_name()}')
            return redirect('messagerie:boite_reception')
            
        except User.DoesNotExist:
            django_messages.error(request, 'Destinataire invalide')
        except Exception as e:
            django_messages.error(request, f'Erreur lors de l\'envoi: {str(e)}')
    
    # GET - Afficher le formulaire
    utilisateurs = User.objects.filter(is_active=True).exclude(
        pk=request.user.pk
    ).order_by('last_name', 'first_name')
    
    # Documents GED de l'utilisateur
    mes_documents = DocumentGED.objects.filter(
        uploaded_by=request.user
    ).order_by('-date_creation')[:20]
    
    # Liste des bénéficiaires
    if beneficiaire_id:
        # Si on vient d'une fiche bénéficiaire : UNIQUEMENT ce bénéficiaire
        beneficiaires = Beneficiaire.objects.filter(pk=beneficiaire_id)
    else:
        # Si on est dans la messagerie : SEULEMENT les bénéficiaires actifs
        # Limité aux 100 derniers pour ne pas surcharger
        beneficiaires = Beneficiaire.objects.filter(
            est_decede=False,
            date_sortie__isnull=True
        ).order_by('-date_modification')[:100]
    
    # Catégories GED disponibles
    categories_ged = DocumentCategorie.choices
    
    context = {
        'utilisateurs': utilisateurs,
        'mes_documents': mes_documents,
        'beneficiaires': beneficiaires,
        'beneficiaire': beneficiaire,
        'categories_ged': categories_ged,
    }
    return render(request, 'messagerie/nouveau_message.html', context)


@login_required
def repondre_message(request, message_id):
    """Répondre à un message"""
    message_original = get_object_or_404(Message, id=message_id)
    
    if request.method == 'POST':
        contenu = request.POST.get('contenu')
        docs_ged_ids = request.POST.getlist('documents_ged')
        fichiers_nouveaux = request.FILES.getlist('nouveaux_fichiers')
        categorie_ged = request.POST.get('categorie_ged', 'divers')
        
        # Déterminer le destinataire
        destinataire = message_original.expediteur if message_original.expediteur != request.user else message_original.destinataire
        
        # Créer la réponse
        reponse = Message.objects.create(
            expediteur=request.user,
            destinataire=destinataire,
            copie=message_original.copie,
            beneficiaire=message_original.beneficiaire,
            objet=f"Re: {message_original.objet}",
            contenu=contenu,
            reponse_a=message_original,
            priorite=message_original.priorite,
            motif=message_original.motif,
            cree_par=request.user
        )
        
        # Documents
        if docs_ged_ids:
            reponse.pieces_jointes.set(docs_ged_ids)
        
        if fichiers_nouveaux:
            if message_original.beneficiaire:
                type_doc = DocumentType.objects.filter(categorie=categorie_ged).first()
                if not type_doc:
                    type_doc = DocumentType.objects.create(
                        code=f'MESSAGE_{categorie_ged.upper()}',
                        nom=f'Document message - {dict(DocumentCategorie.choices).get(categorie_ged, "Divers")}',
                        categorie=categorie_ged,
                        extensions_autorisees=['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png'],
                        taille_max_mb=10,
                    )
                
                # ✅ CORRECTION BYTESIO COMPLÈTE DANS repondre_message()
                for fichier in fichiers_nouveaux:
                    buffer = BytesIO(fichier.read())
                    buffer.name = fichier.name
                    
                    doc = DocumentGED.create_from_buffer(
                        buffer=buffer,  # ✅ BytesIO maintenant
                        filename=fichier.name,
                        content_object=message_original.beneficiaire,
                        type_document=type_doc,
                        user=request.user,
                        confidentialite='RESTREINT',
                        raison=f'Via messagerie - Réponse: {message_original.objet}',
                        request=request
                    )
                    reponse.pieces_jointes.add(doc)
                    buffer.close()
            else:
                type_doc = DocumentType.objects.filter(code='MESSAGE_PJ').first()
                if not type_doc:
                    type_doc = DocumentType.objects.create(
                        code='MESSAGE_PJ',
                        nom='Pièce jointe message',
                        categorie='divers'
                    )
                
                for fichier in fichiers_nouveaux:
                    buffer = BytesIO(fichier.read())
                    buffer.name = fichier.name
                    
                    doc = DocumentGED.create_from_buffer(
                        buffer=buffer,  # ✅ BytesIO
                        filename=fichier.name,
                        content_object=reponse,
                        type_document=type_doc,
                        user=request.user,
                        confidentialite='RESTREINT',
                        raison=f'Pièce jointe - Réponse',
                        request=request
                    )
                    reponse.pieces_jointes.add(doc)
                    buffer.close()
        
        # Statuts de lecture
        StatutLecture.objects.create(
            message=reponse,
            utilisateur=destinataire,
            type_reception='destinataire'
        )
        
        if message_original.copie:
            StatutLecture.objects.create(
                message=reponse,
                utilisateur=message_original.copie,
                type_reception='copie'
            )
        
        django_messages.success(request, 'Réponse envoyée')
        return redirect('messagerie:voir_message', message_id=message_original.id)
    
    mes_documents = DocumentGED.objects.filter(
        uploaded_by=request.user
    ).order_by('-date_creation')[:20]
    
    categories_ged = DocumentCategorie.choices
    
    context = {
        'message_original': message_original,
        'mes_documents': mes_documents,
        'categories_ged': categories_ged,
    }
    return render(request, 'messagerie/repondre_message.html', context)


@login_required
def nb_messages_non_lus(request):
    """API JSON pour le badge de notification"""
    nb = Message.objects.filter(
        Q(destinataire=request.user) | Q(copie=request.user)
    ).exclude(
        statuts_lecture__utilisateur=request.user,
        statuts_lecture__lu=True
    ).count()
    
    return JsonResponse({'nb_non_lus': nb})


@login_required
def rechercher_beneficiaire(request):
    """Recherche AJAX de bénéficiaires"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    beneficiaires = Beneficiaire.objects.filter(
        Q(nom__icontains=query) | 
        Q(prenom__icontains=query) |
        Q(numero_caf__icontains=query) |
        Q(nir__icontains=query),
        est_decede=False,
        date_sortie__isnull=True
    ).order_by('nom', 'prenom')[:20]
    
    results = [
        {
            'id': b.id,
            'text': f"{b.nom} {b.prenom} - {b.numero_caf or 'Sans n°'}",
            'nom': b.nom,
            'prenom': b.prenom,
            'numero_caf': b.numero_caf or ''
        }
        for b in beneficiaires
    ]
    
    return JsonResponse({'results': results})
