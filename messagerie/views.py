# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

# messagerie/views.py - VERSION CORRIGÉE 100% (tous tes commentaires préservés)
# Corrections : BytesIO + sécurité MDS + syntaxe parfaite

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages as django_messages
from django.db.models import Q, Count, Prefetch, Max
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from io import BytesIO  # ✅ AJOUTÉ pour create_from_buffer()
from .models import ISSUE_CHOICES, MODE_CONTACT_CHOICES, MOTIFS_CONTACT, Message, StatutLecture
from ged.models import DocumentGED, DocumentType, DocumentCategorie
from django.contrib.contenttypes.models import ContentType
from core.models import User
from beneficiaire.models import Beneficiaire  # ✅ Import anticipé pour sécurité
try:
    from mds.models import UserMDSProfile
except ImportError:
    UserMDSProfile = None



DELAI_RAPPEL_JOURS_OUVRES = 3


def jours_ouvres_apres(jour, nb):
    """Le jour situé nb jours ouvrés (lundi-vendredi) après `jour`. Les jours fériés ne sont pas pris en compte."""
    from datetime import timedelta
    restants = nb
    while restants:
        jour += timedelta(days=1)
        if jour.weekday() < 5:
            restants -= 1
    return jour


def _date_saisie(valeur):
    from django.utils.dateparse import parse_date
    try:
        return parse_date((valeur or '').strip()) or None
    except ValueError:
        return None



def _choix(valeur, choix):
    """Renvoie la valeur si elle figure dans la liste de choix, sinon une chaîne vide."""
    valeurs = dict(choix)
    return valeur if valeur in valeurs else ''


def _choix_multiples(valeurs, choix):
    """Les valeurs reconnues, sans doublon, dans l'ordre de la liste de choix."""
    retenues = set(valeurs) & set(dict(choix))
    return [code for code, _ in choix if code in retenues]


def _mds_principale(user):
    """MDS de rattachement principale (ou première active) d'un agent."""
    from mds.models import UserMDSProfile
    ump = UserMDSProfile.objects.filter(user=user, actif=True).select_related('mds').order_by('-principale').first()
    return ump.mds if ump else None


def _est_cadre(user, mds):
    """Cadre de cette MDS : profil de gestion local (peut_gerer_utilisateurs)."""
    from mds.models import UserMDSProfile
    return bool(mds) and UserMDSProfile.objects.filter(
        user=user, mds=mds, actif=True, peut_gerer_utilisateurs=True).exists()


def _reaffectation_en_attente(message):
    return ('REAFFECTATION' in (message.motifs_contact or []) and message.beneficiaire is not None
            and message.mds_demandeuse_id is not None and message.mds_demandeuse_id != message.beneficiaire.mds_id
            and not message.decision_reaffectation)


def _participe(message, user):
    """Expéditeur, destinataire, personne en copie ; et, pour un message lié à un usager, les agents de la MDS de cet usager."""
    if user in (message.expediteur, message.destinataire, message.copie):
        return True
    if message.beneficiaire_id and message.beneficiaire.mds_id:
        from mds.models import UserMDSProfile
        return UserMDSProfile.objects.filter(user=user, actif=True, mds_id=message.beneficiaire.mds_id).exists()
    return False


def _documents_autorises(ids, user):
    """Pièces jointes choisies parmi la GED : seulement les documents que l'expéditeur a le droit de voir."""
    return [d for d in DocumentGED.objects.filter(pk__in=[i for i in ids if str(i).isdigit()])
            if d.peut_etre_vu_par(user)]


MAX_FICHIERS = 10


def _categorie(valeur):
    return valeur if valeur in DocumentCategorie.values else 'divers'


def _type_piece_jointe(categorie_ged, avec_usager):
    """Type GED des fichiers déposés depuis la messagerie (créé au besoin, extensions sans point)."""
    from ged.models import get_default_extensions
    if avec_usager:
        categorie_ged = _categorie(categorie_ged)
        type_doc = DocumentType.objects.filter(categorie=categorie_ged).first()
        if not type_doc:
            type_doc = DocumentType.objects.create(
                code=f'MESSAGE_{categorie_ged.upper()}',
                nom=f'Document message - {dict(DocumentCategorie.choices).get(categorie_ged, "Divers")}',
                categorie=categorie_ged,
                extensions_autorisees=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'xls', 'xlsx', 'odt', 'ods'],
                taille_max_mb=10)
        return type_doc
    return DocumentType.objects.filter(code='MESSAGE_PJ').first() or DocumentType.objects.create(
        code='MESSAGE_PJ', nom='Pièce jointe message', categorie='divers', extensions_autorisees=get_default_extensions(),
        taille_max_mb=10)


def _erreurs_fichiers(fichiers, type_doc):
    """Mêmes règles que le dépôt dans la GED (taille, extensions), vérifiées AVANT de créer le message."""
    from ged.validation import erreurs_fichier
    if len(fichiers) > MAX_FICHIERS:
        return [f"{MAX_FICHIERS} fichiers au plus par message."]
    return [e for f in fichiers for e in erreurs_fichier(f, type_doc)]


def _deposer(fichiers, message, type_doc, user, raison, request):
    """Dépose les fichiers (déjà vérifiés) dans la GED : sur l'usager du message s'il y en a un, sinon sur le message."""
    for fichier in fichiers:
        buffer = BytesIO(fichier.read())
        buffer.name = fichier.name
        doc = DocumentGED.create_from_buffer(
            buffer=buffer, filename=fichier.name, content_object=message.beneficiaire or message,
            type_document=type_doc, user=user, confidentialite='RESTREINT', raison=raison, request=request)
        message.pieces_jointes.add(doc)
        buffer.close()


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
        'liste_messages': messages_recus,
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
        'liste_messages': messages_envoyes,
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
    if not _participe(message, request.user):
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
        'motifs_contact_choices': MOTIFS_CONTACT,
        'issue_choices': ISSUE_CHOICES,
        'reaffectation_en_attente': _reaffectation_en_attente(message),
        'peut_decider_reaffectation': _reaffectation_en_attente(message) and _est_cadre(request.user, message.beneficiaire.mds),
    }
    return render(request, 'messagerie/voir_message.html', context)


@login_required
def nouveau_message(request, beneficiaire_id=None):
    """Créer un nouveau message"""
    
    # ✅ SÉCURITÉ MDS : VÉRIFIER AVANT création bénéficiaire_obj
    # Un usager ne se désigne que depuis l'annuaire : tout agent connecté peut lui laisser un message
    beneficiaire = get_object_or_404(Beneficiaire, pk=beneficiaire_id) if beneficiaire_id else None
    
    if request.method == 'POST':
        destinataire_id = request.POST.get('destinataire')
        copie_id = request.POST.get('copie')
        objet = request.POST.get('objet')
        contenu = request.POST.get('contenu')
        priorite = request.POST.get('priorite', 'normale')
        motif = request.POST.get('motif', 'autre')
        # Depuis une fiche ou l'annuaire, l'usager vient de l'URL : il est retenu si le champ n'est pas renseigné
        beneficiaire_id_post = request.POST.get('beneficiaire') or beneficiaire_id
        
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
            
            type_pj = _type_piece_jointe(categorie_ged, bool(beneficiaire_obj)) if fichiers_nouveaux else None
            erreurs = _erreurs_fichiers(fichiers_nouveaux, type_pj) if fichiers_nouveaux else []
            if erreurs:
                for e in erreurs:
                    django_messages.error(request, e)
                django_messages.warning(request, "Message non envoyé : retirez ou remplacez les fichiers refusés.")
                return redirect(request.get_full_path())

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
                date_rappel=_date_saisie(request.POST.get('date_rappel')) if beneficiaire_obj else None,
                mode_contact=_choix(request.POST.get('mode_contact'), MODE_CONTACT_CHOICES) if beneficiaire_obj else '',
                motifs_contact=_choix_multiples(request.POST.getlist('motifs_contact'), MOTIFS_CONTACT) if beneficiaire_obj else [],
                cree_par=request.user
            )
            
            # Demande de réaffectation : mémoriser la MDS qui la formule
            if beneficiaire_obj and 'REAFFECTATION' in nouveau_msg.motifs_contact:
                nouveau_msg.mds_demandeuse = _mds_principale(request.user)
                nouveau_msg.save(update_fields=['mds_demandeuse'])

            # Attacher les documents GED existants
            if docs_ged_ids:
                nouveau_msg.pieces_jointes.set(_documents_autorises(docs_ged_ids, request.user))
            
            # Nouveaux fichiers : dans la GED (déjà vérifiés ci-dessus)
            if fichiers_nouveaux:
                _deposer(fichiers_nouveaux, nouveau_msg, type_pj, request.user,
                         f'Via messagerie - {objet}' if beneficiaire_obj else f'Pièce jointe - Message: {objet}', request)

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
    
    
    # Catégories GED disponibles
    categories_ged = DocumentCategorie.choices
    
    prise_message = bool(beneficiaire) and request.GET.get('prise') == '1'
    context = {
        'utilisateurs': utilisateurs,
        'mes_documents': mes_documents,
        'beneficiaire': beneficiaire,
        'mode_contact_choices': MODE_CONTACT_CHOICES,
        'motifs_contact_choices': MOTIFS_CONTACT,
        'categories_ged': categories_ged,
        'prise_message': prise_message,
        'rappel_defaut': jours_ouvres_apres(timezone.localdate(), DELAI_RAPPEL_JOURS_OUVRES),
    }
    return render(request, 'messagerie/nouveau_message.html', context)


@login_required
def repondre_message(request, message_id):
    """Répondre à un message"""
    message_original = get_object_or_404(Message, id=message_id)
    if not _participe(message_original, request.user):
        django_messages.error(request, "Vous n'avez pas accès à ce message")
        return redirect('messagerie:boite_reception')

    if request.method == 'POST':
        contenu = request.POST.get('contenu')
        docs_ged_ids = request.POST.getlist('documents_ged')
        fichiers_nouveaux = request.FILES.getlist('nouveaux_fichiers')
        categorie_ged = request.POST.get('categorie_ged', 'divers')
        
        # Déterminer le destinataire
        destinataire = message_original.expediteur if message_original.expediteur != request.user else message_original.destinataire
        
        type_pj = (_type_piece_jointe(categorie_ged, bool(message_original.beneficiaire))
                   if fichiers_nouveaux else None)
        erreurs = _erreurs_fichiers(fichiers_nouveaux, type_pj) if fichiers_nouveaux else []
        if erreurs:
            for e in erreurs:
                django_messages.error(request, e)
            django_messages.warning(request, "Réponse non envoyée : retirez ou remplacez les fichiers refusés.")
            return redirect(request.get_full_path())

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
            reponse.pieces_jointes.set(_documents_autorises(docs_ged_ids, request.user))

        # Nouveaux fichiers : dans la GED (déjà vérifiés ci-dessus)
        if fichiers_nouveaux:
            _deposer(fichiers_nouveaux, reponse, type_pj, request.user,
                     f'Via messagerie - Réponse: {message_original.objet}' if message_original.beneficiaire
                     else 'Pièce jointe - Réponse', request)

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
@require_POST
def decider_reaffectation(request, message_id):
    """Décision du cadre de la MDS de l'usager sur une demande de réaffectation : transfert ou refus motivé."""
    from beneficiaire.transfert import membres_famille, transferer
    message = get_object_or_404(Message, id=message_id, beneficiaire__isnull=False)
    usager = message.beneficiaire
    if not _reaffectation_en_attente(message):
        django_messages.error(request, "Cette demande n'est pas en attente de décision.")
        return redirect('messagerie:voir_message', message_id=message.id)
    if not _est_cadre(request.user, usager.mds):
        django_messages.error(request, "Seul le cadre de la MDS de l'usager peut répondre à une demande de réaffectation.")
        return redirect('messagerie:voir_message', message_id=message.id)

    decision = request.POST.get('decision')
    motif_refus = (request.POST.get('motif_refus') or '').strip()
    if decision not in ('accepter', 'refuser'):
        django_messages.error(request, "Choisissez une décision.")
        return redirect('messagerie:voir_message', message_id=message.id)
    if decision == 'refuser' and not motif_refus:
        django_messages.error(request, "Indiquez le motif du refus : il est transmis à la MDS demandeuse.")
        return redirect('messagerie:voir_message', message_id=message.id)

    mds_demandeuse = message.mds_demandeuse
    maintenant = timezone.now()
    with transaction.atomic():
        if decision == 'accepter':
            a_transferer = [m['personne'] for m in membres_famille(usager) if m['coche']]
            transferer(usager, a_transferer, mds_demandeuse, request.user, request=request)
            resultat = 'ACCEPTEE'
            texte = (f"Votre demande de réaffectation est acceptée : {usager.prenom} {usager.nom.upper()} "
                     f"a été transféré vers la MDS {mds_demandeuse.nom} le {timezone.localtime(maintenant).strftime('%d/%m/%Y à %H:%M')}.")
        else:
            resultat = 'REFUSEE'
            texte = (f"Votre demande de réaffectation pour {usager.prenom} {usager.nom.upper()} est refusée.\n\n"
                     f"Motif : {motif_refus}")

        message.decision_reaffectation = resultat
        message.decision_reaffectation_par = request.user
        message.decision_reaffectation_le = maintenant
        message.motif_refus = motif_refus if resultat == 'REFUSEE' else ''
        if message.reponse_le is None:
            message.reponse_le = maintenant
        message.save(update_fields=['decision_reaffectation', 'decision_reaffectation_par',
                                    'decision_reaffectation_le', 'motif_refus', 'reponse_le', 'updated_at'])

        reponse = Message.objects.create(
            expediteur=request.user,
            destinataire=message.expediteur,
            beneficiaire=usager,
            objet=f"Réponse à la demande de réaffectation : {usager.prenom} {usager.nom.upper()}",
            contenu=texte,
            priorite='importante',
            motif='changement_situation',
            reponse_a=message,
            cree_par=request.user,
        )
        StatutLecture.objects.create(message=reponse, utilisateur=message.expediteur, type_reception='destinataire')

    django_messages.success(request, "Décision enregistrée. La demande est close et la MDS demandeuse est prévenue.")
    return redirect('messagerie:voir_message', message_id=message.id)


@login_required
@require_POST
def reponse_usager(request, message_id):
    """Réponse du destinataire d'une prise de message : issue, texte, « Réponse effectuée » (date et heure)."""
    message = get_object_or_404(Message, id=message_id, beneficiaire__isnull=False)
    if message.destinataire != request.user:
        django_messages.error(request, "Seul le destinataire peut renseigner la réponse.")
        return redirect('messagerie:voir_message', message_id=message.id)

    message.issue = _choix(request.POST.get('issue'), ISSUE_CHOICES)
    message.reponse_texte = (request.POST.get('reponse_texte') or '').strip()
    if request.POST.get('reponse_effectuee') == 'oui' and message.reponse_le is None:
        message.reponse_le = timezone.now()
    message.save(update_fields=['issue', 'reponse_texte', 'reponse_le', 'updated_at'])
    django_messages.success(request, "Réponse enregistrée.")
    return redirect('messagerie:voir_message', message_id=message.id)

