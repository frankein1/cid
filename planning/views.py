# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

"""
planning/views.py
VERSION FINALE CORRIGÉE - 12/02/2026
Corrections appliquées :
- ✅ Accès planning pour agents sociaux (peut_creer)
- ✅ Vérification robuste des capacités (sans a_la_capacite)
- ✅ Bug UserMDSProfile.get() → .filter().first()
- ✅ Permission planning_generer pour les cadres
- ✅ Champ duree_minutes désactivé pour PERMANENCE
- ✅ Paramètre beneficiaire dans calendrier_rdv
"""

from datetime import date, timedelta, datetime, time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.http import JsonResponse, HttpResponse, FileResponse
from django.db.models import Q, Prefetch
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.template.loader import render_to_string
try:
    from mds.models import UserMDSProfile
except ImportError:
    UserMDSProfile = None

# Imports pour les exports PDF (ReportLab)
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from .models import CreneauRdv, JourBloque, PermanenceExterne
from .forms import RdvForm, GenererCreneauxForm, JourBloqueForm, PermanenceExterneForm 
from .utils import generer_creneaux_permanences, est_jour_ferie

User = get_user_model()

# =============================================================================
# CONSTANTES DE FONCTIONNEMENT
# =============================================================================
HEURE_DEBUT_MATIN = time(9, 0)
HEURE_FIN_MATIN = time(12, 0)
HEURE_DEBUT_APRES_MIDI = time(13, 30)
HEURE_FIN_APRES_MIDI = time(16, 30)


# =============================================================================
# VUES EXISTANTES (CALENDRIER PRINCIPAL)
# =============================================================================

@login_required
def calendrier_rdv(request, beneficiaire_id=None):
    """Vue principale du calendrier - Accès agents sociaux et cadres"""
    today = date.today()
    
    # ✅ VÉRIFICATION ROBUSTE - Utilisation du système de capacités
    from core.models import Capacite
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Récupérer l'utilisateur avec ses profils pré-chargés
    user = User.objects.prefetch_related('profils__capacites').get(pk=request.user.pk)
    
    # Collecter TOUTES les capacités de l'utilisateur via ses profils
    capacites_user = set()
    for profil in user.profils.all():
        for capacite in profil.capacites.all():
            capacites_user.add(capacite.code)
    
    # Vérifier l'accès
    if not (user.is_superuser or 
            'peut_creer' in capacites_user or 
            'peut_voir_stats' in capacites_user):
        messages.error(request, "Accès refusé au planning.")
        return redirect('core:dashboard')
    
    # ✅ Récupérer le bénéficiaire depuis l'URL si présent
    beneficiaire_id = request.GET.get('beneficiaire')
    beneficiaire = None
    if beneficiaire_id:
        from beneficiaire.models import Beneficiaire
        beneficiaire = get_object_or_404(Beneficiaire, pk=beneficiaire_id)    

    vue = request.GET.get('vue', 'mois')
    
    from mds.models import MDSReception, UserMDSProfile
    try:
        profile = UserMDSProfile.objects.filter(user=request.user, actif=True).first()
        salles = MDSReception.objects.filter(mds=profile.mds, actif=True) if profile else MDSReception.objects.filter(actif=True)
    except:
        salles = MDSReception.objects.filter(actif=True)

    context = {
        'today': today,
        'salles': salles,
        'vue': vue,
        'horaires_reception': {
            'debut_matin': HEURE_DEBUT_MATIN.strftime('%H:%M'),
            'fin_matin': HEURE_FIN_MATIN.strftime('%H:%M'),
            'debut_apres_midi': HEURE_DEBUT_APRES_MIDI.strftime('%H:%M'),
            'fin_apres_midi': HEURE_FIN_APRES_MIDI.strftime('%H:%M')
        },
        'beneficiaire': beneficiaire,
    }
    return render(request, 'planning/calendrier.html', context)


@login_required
def api_creneaux(request):
    """API pour FullCalendar - Logique de couleurs et de statuts"""
    start_raw = request.GET.get("start")
    end_raw = request.GET.get("end")
    
    start_date = parse_date(start_raw) or (parse_datetime(start_raw).date() if start_raw else None)
    end_date = parse_date(end_raw) or (parse_datetime(end_raw).date() if end_raw else None)

    events = []

    # 1. JOURS FÉRIÉS (FOND ROSE)
    if start_date and end_date:
        curr = start_date
        while curr <= end_date:
            if est_jour_ferie(curr):
                events.append({
                    'title': 'FÉRIÉ',
                    'start': f"{curr.isoformat()}",
                    'allDay': True,
                    'display': 'background',
                    'backgroundColor': '#FEE2E2',
                })
            curr += timedelta(days=1)

    # 2. JOURS BLOQUÉS MDS (ROUGE BORDEAUX)
    bloques = JourBloque.objects.filter(date__range=(start_date, end_date))
    for b in bloques:
        events.append({
            'id': f'bloque-{b.id}',
            'title': f"FERMÉ: {b.get_raison_display()}",
            'start': f"{b.date.isoformat()}T{b.heure_debut.isoformat()}",
            'end': f"{b.date.isoformat()}T{b.heure_fin.isoformat()}",
            'backgroundColor': '#991B1B', 
            'borderColor': '#7F1D1D',
            'textColor': '#FFFFFF',
            'extendedProps': {'type': 'blocage'}
        })

    # 3. CRÉNEAUX DE RDV
    creneaux = CreneauRdv.objects.filter(date__range=(start_date, end_date))
    
    from mds.models import UserMDSProfile
    profile = UserMDSProfile.objects.filter(user=request.user, actif=True).first()
    if profile and profile.mds and not request.user.is_superuser:
        creneaux = creneaux.filter(salle__mds=profile.mds)

    for c in creneaux:
        if not c.peut_etre_vu_par(request.user): 
            continue

        color_map = {
            'DISPONIBLE': '#10B981', # Vert
            'RESERVE': '#3B82F6',    # Bleu
            'VENU_RECU': '#6B7280',  # Gris
            'ANNULE_MDS': '#FCA5A5', # Rouge Pastel
        }
        color = color_map.get(c.statut, '#F59E0B')

        events.append({
            'id': c.id,
            'title': f"{c.agent.last_name if c.agent else 'MDS'} | {c.salle.nom}",
            'start': f"{c.date.isoformat()}T{c.heure_debut.isoformat()}",
            'end': f"{c.date.isoformat()}T{c.heure_fin.isoformat()}",
            'backgroundColor': color,
            'borderColor': color,
            'extendedProps': {
                'statut': c.statut,
                'agent': str(c.agent) if c.agent else "Non assigné",
                'salle': c.salle.nom,
                'peut_reserver': c.peut_etre_reserve_par(request.user),
            }
        })

    return JsonResponse(events, safe=False)

@login_required
def reserver_rdv(request, creneau_id, beneficiaire_id=None):
    creneau = get_object_or_404(CreneauRdv, pk=creneau_id)
    
    # Récupération du bénéficiaire (priorité : URL > GET > formulaire)
    if not beneficiaire_id:
        beneficiaire_id = request.GET.get('beneficiaire_id')
    
    beneficiaire = None
    if beneficiaire_id:
        beneficiaire = get_object_or_404(Beneficiaire, pk=beneficiaire_id)
        # Vérifier que l'agent a le droit sur ce bénéficiaire
        if not beneficiaire.peut_etre_vu_par(request.user):
            messages.error(request, "Accès non autorisé à ce bénéficiaire.")
            return redirect('planning:calendrier_rdv')
   
   
    # 2. Vérification de disponibilité
    if not creneau.is_disponible():
        messages.error(request, "Ce créneau n'est pas disponible.")
        return redirect('planning:calendrier_rdv')
    
    # 3. Initialisation du formulaire
    if request.method == 'POST':
        # En POST, on traite les données envoyées
        form = RdvForm(request.POST, instance=creneau, creneau=creneau, request=request)
    else:
        # En GET, on pré-remplit le bénéficiaire s'il est connu
        initial_data = {}
        if beneficiaire:
            initial_data['beneficiaire'] = beneficiaire
            
        form = RdvForm(instance=creneau, creneau=creneau, request=request, initial=initial_data)
    
    # 4. Logique spécifique aux permanences (champ durée désactivé)
    if creneau.type_rdv == 'PERMANENCE' and 'duree_minutes' in form.fields:
        form.fields['duree_minutes'].disabled = True
        form.fields['duree_minutes'].help_text = "Durée fixe de 30 minutes pour les permanences"
    
    # 5. Traitement de la validation
    if request.method == 'POST':
        if form.is_valid():
            rdv = form.save(commit=False)
            
            # On utilise le bénéficiaire du formulaire (ou celui de l'URL par sécurité)
            target_beneficiaire = rdv.beneficiaire or beneficiaire
            
            if not target_beneficiaire:
                messages.error(request, "Aucun bénéficiaire sélectionné.")
            else:
                rdv.reserver(request.user, target_beneficiaire, rdv.description)
                messages.success(request, f"Rendez-vous confirmé pour le {creneau.date}")
                
                # Redirection vers le tableau de bord du bénéficiaire (logique AidFi)
                return redirect('planning:calendrier_rdv')
        else:
            messages.error(request, "Erreur dans le formulaire. Veuillez vérifier les champs.")
    
    return render(request, 'planning/reserver.html', {
        'form': form, 
        'creneau': creneau,
        'beneficiaire': beneficiaire
    })


@login_required
def ajouter_jour_bloque(request):
    """Ajout d'une période de fermeture (Administrateurs/Cadres via capacités)"""
    if not (request.user.a_la_capacite('peut_administrer') or request.user.is_superuser):
        messages.error(request, "Permission insuffisante.")
        return redirect('planning:calendrier_rdv')

    if request.method == 'POST':
        form = JourBloqueForm(request.POST, request=request)
        if form.is_valid():
            jb = form.save(commit=False)
            jb.cree_par = request.user
            jb.save() 
            messages.success(request, "La période a été bloquée.")
            return redirect('planning:calendrier_rdv')
    else:
        form = JourBloqueForm(request=request)
    return render(request, 'planning/ajouter_jour_bloque.html', {'form': form})


@login_required
def generer_creneaux(request):
    """Génération en masse de créneaux selon les règles métier"""
    if not (request.user.is_superuser or request.user.a_la_capacite('planning_generer')):
        messages.error(request, "Seuls les gestionnaires peuvent générer des créneaux.")
        return redirect('planning:calendrier_rdv')

    if request.method == 'POST':
        form = GenererCreneauxForm(request.POST)
        if form.is_valid():
            try:
                from mds.models import UserMDSProfile
                profile = UserMDSProfile.objects.filter(user=request.user, actif=True).first()
                if not profile:
                    messages.error(request, "Vous n'êtes pas rattaché à une MDS active.")
                    return redirect('planning:calendrier_rdv')
                
                choix = form.cleaned_data['date_debut']
                date_debut = date.today()
                if choix == 'monday':
                    date_debut += timedelta(days=(7 - date.today().weekday()))
                elif choix == 'next_month':
                    date_debut = (date.today().replace(day=1) + timedelta(days=32)).replace(day=1)

                nb_semaines = form.cleaned_data['nombre_semaines']
                type_rdv = form.cleaned_data['type_rdv']
                date_fin = date_debut + timedelta(weeks=nb_semaines)
                
                # 1. Génération des créneaux MDS classiques
                creneaux = generer_creneaux_permanences(date_debut, nb_semaines, profile.mds, type_rdv)
                
                # 2. Génération des créneaux pour salles externes (si demandé)
                inclure_externes = form.cleaned_data.get('inclure_externes', True)
                if inclure_externes:
                    from .utils import generer_creneaux_depuis_permanences_externes
                    creneaux_externes = generer_creneaux_depuis_permanences_externes(
                        date_debut, date_fin, profile.mds
                    )
                    creneaux += creneaux_externes

                messages.success(request, f"Succès : {len(creneaux)} créneaux créés.")
                return redirect('planning:calendrier_rdv')
                
            except Exception as e:
                messages.error(request, f"Erreur de génération : {str(e)}")
                return redirect('planning:calendrier_rdv')
    else:
        form = GenererCreneauxForm()
    
    return render(request, 'planning/generer.html', {'form': form})


@login_required
def annuler_rdv(request, creneau_id):
    """Annulation d'un RDV spécifique"""
    creneau = get_object_or_404(CreneauRdv, pk=creneau_id)
    if creneau.peut_etre_modifie_par(request.user):
        creneau.annuler(request.user)
        messages.success(request, "Le créneau a été libéré.")
    else:
        messages.error(request, "Droit d'annulation refusé.")
    return redirect('planning:calendrier_rdv')


# =============================================================================
# VUES PLANNING ACCUEIL
# =============================================================================

@login_required
def planning_accueil_jour(request, date_str=None):
    """Vue journalière pour l'accueil (filtre territorial)"""
    if not (request.user.a_la_capacite('peut_creer') or request.user.is_superuser):
        messages.error(request, "Accès refusé.")
        return redirect('core:dashboard')
    
    if date_str:
        try:
            date_affichage = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            date_affichage = date.today()
    else:
        date_affichage = date.today()
    
    date_precedente = date_affichage - timedelta(days=1)
    date_suivante = date_affichage + timedelta(days=1)
    
    from mds.models import UserMDSProfile
    profile = UserMDSProfile.objects.filter(user=request.user, actif=True).first()
    mds_courante = profile.mds if profile else None
    
    creneaux_query = CreneauRdv.objects.filter(date=date_affichage).select_related(
        'agent', 'salle', 'beneficiaire'
    ).order_by('heure_debut')
    
    if mds_courante and not request.user.is_superuser:
        creneaux_query = creneaux_query.filter(salle__mds=mds_courante)
    
    creneaux = [c for c in creneaux_query if c.peut_etre_vu_par(request.user)]
    creneaux_matin = [c for c in creneaux if c.heure_debut < time(12, 30)]
    creneaux_apres_midi = [c for c in creneaux if c.heure_debut >= time(12, 30)]
    
    context = {
        'date_affichage': date_affichage,
        'date_precedente': date_precedente,
        'date_suivante': date_suivante,
        'creneaux_matin': creneaux_matin,
        'creneaux_apres_midi': creneaux_apres_midi,
        'total_creneaux': len(creneaux),
        'creneaux_reserves': len([c for c in creneaux if c.statut == 'RESERVE']),
        'est_ferie': est_jour_ferie(date_affichage),
        'mds_courante': mds_courante,
    }
    return render(request, 'planning/accueil_jour.html', context)


@login_required
def planning_accueil_semaine(request, date_str=None):
    """Vue hebdomadaire pour l'accueil"""
    if date_str:
        try:
            date_ref = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            date_ref = date.today()
    else:
        date_ref = date.today()
    
    debut_semaine = date_ref - timedelta(days=date_ref.weekday())
    fin_semaine = debut_semaine + timedelta(days=6)
    
    from mds.models import UserMDSProfile
    profile = UserMDSProfile.objects.filter(user=request.user, actif=True).first()
    
    creneaux_query = CreneauRdv.objects.filter(
        date__range=[debut_semaine, fin_semaine]
    ).select_related('agent', 'salle', 'beneficiaire').order_by('date', 'heure_debut')
    
    if profile and profile.mds and not request.user.is_superuser:
        creneaux_query = creneaux_query.filter(salle__mds=profile.mds)
    
    creneaux_par_jour = {}
    for i in range(7):
        jour = debut_semaine + timedelta(days=i)
        creneaux_par_jour[jour] = [c for c in creneaux_query if c.date == jour and c.peut_etre_vu_par(request.user)]
    
    context = {
        'debut_semaine': debut_semaine,
        'fin_semaine': fin_semaine,
        'creneaux_par_jour': creneaux_par_jour,
        'semaine_precedente': debut_semaine - timedelta(days=7),
        'semaine_suivante': debut_semaine + timedelta(days=7),
    }
    return render(request, 'planning/accueil_semaine.html', context)


# =============================================================================
# EXPORTS OUTLOOK ET PDF
# =============================================================================

@login_required
def export_planning_ical(request):
    """Export iCalendar (.ics)"""
    try:
        from icalendar import Calendar, Event as iCalEvent
    except ImportError:
        messages.error(request, "Bibliothèque icalendar manquante.")
        return redirect('planning:calendrier_rdv')
    
    agent_id = request.GET.get('agent')
    creneaux = CreneauRdv.objects.filter(date__gte=date.today()).select_related('agent', 'salle')
    
    if agent_id:
        creneaux = creneaux.filter(agent_id=agent_id)

    cal = Calendar()
    cal.add('prodid', '-//MDS Planning//FR')
    cal.add('version', '2.0')
    
    for c in creneaux:
        if c.peut_etre_vu_par(request.user):
            event = iCalEvent()
            event.add('summary', f"RDV - {c.salle.nom}")
            event.add('dtstart', datetime.combine(c.date, c.heure_debut))
            event.add('dtend', datetime.combine(c.date, c.heure_fin))
            event.add('uid', f"creneau-{c.id}@mds.local")
            cal.add_component(event)
    
    response = HttpResponse(cal.to_ical(), content_type='text/calendar')
    response['Content-Disposition'] = 'attachment; filename="planning.ics"'
    return response


@login_required
def imprimer_planning_jour_pdf(request, date_str):
    """Génération du PDF de planning quotidien"""
    try:
        date_affichage = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return redirect('planning:planning_accueil_jour')
    
    from mds.models import UserMDSProfile
    profile = UserMDSProfile.objects.filter(user=request.user, actif=True).first()
    
    creneaux = CreneauRdv.objects.filter(date=date_affichage).select_related('agent', 'salle', 'beneficiaire').order_by('heure_debut')
    if profile and not request.user.is_superuser:
        creneaux = creneaux.filter(salle__mds=profile.mds)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []
    
    styles = getSampleStyleSheet()
    titre = f"Planning MDS - {date_affichage.strftime('%d/%m/%Y')}"
    elements.append(Paragraph(titre, styles['Title']))
    
    data = [['Heure', 'Salle', 'Bénéficiaire', 'Agent', 'Statut']]
    for c in creneaux:
        if c.peut_etre_vu_par(request.user):
            data.append([
                f"{c.heure_debut.strftime('%H:%M')}",
                c.salle.nom,
                str(c.beneficiaire) if c.beneficiaire else "-",
                c.agent.get_full_name() if c.agent else "-",
                c.get_statut_display()
            ])
            
    table = Table(data, colWidths=[3*cm, 4*cm, 8*cm, 5*cm, 4*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    return FileResponse(buffer, content_type='application/pdf', filename=f"planning_{date_str}.pdf")


@login_required
def exporter_planning_agent_outlook(request, agent_id):
    """Redirection vers l'export standard avec filtre agent"""
    return redirect(f"{reverse('planning:export_ical')}?agent={agent_id}")

def preparer_sync_outlook_graph(request):
    """Placeholder futur"""
    messages.info(request, "Fonctionnalité prévue pour la phase 2.")
    return redirect('planning:calendrier_rdv')

@login_required
def mes_permanences_semaine(request, date_str=None):
    """Vue planning : les créneaux à venir de l'agent connecté"""
    if date_str:
        try:
            date_ref = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            date_ref = date.today()
    else:
        date_ref = date.today()
    
    debut_semaine = date_ref - timedelta(days=date_ref.weekday())
    fin_semaine = debut_semaine + timedelta(days=6)
    
    creneaux = CreneauRdv.objects.filter(
        agent=request.user,
        date__gte=date.today(),
        date__range=[debut_semaine, fin_semaine]
    ).select_related('salle', 'beneficiaire').order_by('date', 'heure_debut')
    
    # Structurer par jour
    creneaux_par_jour = {}
    for i in range(7):
        jour = debut_semaine + timedelta(days=i)
        creneaux_par_jour[jour] = [c for c in creneaux if c.date == jour]
    
    context = {
        'debut_semaine': debut_semaine,
        'fin_semaine': fin_semaine,
        'creneaux_par_jour': creneaux_par_jour,
        'semaine_precedente': debut_semaine - timedelta(days=7),
        'semaine_suivante': debut_semaine + timedelta(days=7),
    }
    return render(request, 'planning/mes_permanences_semaine.html', context)


@login_required
def exporter_mes_permanences_ics(request):
    """Export iCalendar des créneaux à venir de l'agent"""
    try:
        from icalendar import Calendar, Event as iCalEvent
    except ImportError:
        messages.error(request, "Bibliothèque icalendar manquante.")
        return redirect('planning:calendrier_rdv')
    
    creneaux = CreneauRdv.objects.filter(
        agent=request.user,
        date__gte=date.today(),
        statut='DISPONIBLE'
    ).select_related('salle')
    
    cal = Calendar()
    cal.add('prodid', '-//MDS Planning//FR')
    cal.add('version', '2.0')
    
    for c in creneaux:
        event = iCalEvent()
        event.add('summary', f"Permanence MDS - {c.salle.nom}")
        event.add('dtstart', datetime.combine(c.date, c.heure_debut))
        event.add('dtend', datetime.combine(c.date, c.heure_fin))
        event.add('uid', f"permanence-{c.id}@mds.local")
        cal.add_component(event)
    
    response = HttpResponse(cal.to_ical(), content_type='text/calendar')
    response['Content-Disposition'] = 'attachment; filename="mes_permanences.ics"'
    return response

@login_required
def api_recherche_beneficiaire(request):
    """API pour l'autocomplétion des bénéficiaires (Select2)"""
    from beneficiaire.models import Beneficiaire
    from django.db.models import Q
    
    q = request.GET.get('q', '')
    if len(q) < 3:
        return JsonResponse({'results': []})
    
    # Filtrer par MDS de l'utilisateur
    mds = request.user.mds_principale
    if not mds:
        return JsonResponse({'results': []})
    
    beneficiaires = Beneficiaire.objects.filter(
        Q(nom__icontains=q) | Q(prenom__icontains=q) | Q(code_interne__icontains=q),
        mds=mds,
        statut='ACTIF'
    )[:20]
    
    results = [
        {'id': b.id, 'text': f"{b.nom} {b.prenom} ({b.code_interne})"}
        for b in beneficiaires
    ]
    return JsonResponse({'results': results})


# rechercher rdv par 
@login_required
def creer_rdv_depuis_beneficiaire(request, beneficiaire_id):
    from beneficiaire.models import Beneficiaire
    from datetime import date, timedelta
    from django.urls import reverse
    from django.shortcuts import redirect, get_object_or_404
    from django.contrib import messages
    
    beneficiaire = get_object_or_404(Beneficiaire, id=beneficiaire_id)
    
    # Vérification des droits
    if not beneficiaire.peut_etre_vu_par(request.user):
        messages.error(request, "Accès non autorisé à ce bénéficiaire.")
        return redirect('beneficiaire:detail_beneficiaire', code_interne=beneficiaire.code_interne)
    
    # Déterminer l'agent référent
    agent = beneficiaire.referent_mds
    if not agent:
        # Pas de référent : on prend l'agent connecté
        agent = request.user
        # On met à jour le référent pour les prochains RDV
        beneficiaire.referent_mds = agent
        beneficiaire.save(update_fields=['referent_mds'])
    
    # Trouver le premier créneau disponible dans les 15 jours
    start_date = date.today() + timedelta(days=2)
    end_date = start_date + timedelta(days=15)
    
    creneau = CreneauRdv.objects.filter(
        date__gte=start_date,
        date__lte=end_date,
        agent=agent,
        statut='DISPONIBLE'
    ).order_by('date', 'heure_debut').first()
    
    if not creneau:
        messages.warning(
            request, 
            f"Aucun créneau disponible pour {agent.get_full_name()} dans les 15 jours. "
            "Vous pouvez choisir un autre créneau dans le calendrier."
        )
        return redirect(f"{reverse('planning:calendrier_rdv')}?agent={agent.id}")
    
    # Rediriger vers le formulaire de réservation avec bénéficiaire pré-rempli
    return redirect(f"{reverse('planning:reserver_rdv', args=[creneau.id])}?beneficiaire_id={beneficiaire.id}")


# =============================================================================
# GESTION DES PERMANENCES EXTERNES (CADRE) (Deepseek voulait que ce soit l'admin mais je ne suis pas d'accord)
# =============================================================================

@login_required
def gerer_permanences_externes(request):
    """Vue cadre : lister, créer, modifier, supprimer les permanences externes"""
    if not (request.user.is_superuser or request.user.a_la_capacite('planning_generer')):
        messages.error(request, "Accès réservé aux cadres gestionnaires.")
        return redirect('planning:calendrier_rdv')
    
    mds = request.user.mds_principale
    if not mds:
        messages.error(request, "Vous n'êtes pas rattaché à une MDS.")
        return redirect('planning:calendrier_rdv')
    
    permanences = PermanenceExterne.objects.filter(
        salle__mds=mds
    ).select_related('agent', 'salle').order_by('jour_semaine', 'heure_debut')
    
    if request.method == 'POST':
        form = PermanenceExterneForm(request.POST, user=request.user)
        if form.is_valid():
            perm = form.save(commit=False)
            perm.cree_par = request.user
            perm.save()
            messages.success(request, f"Permanence externe ajoutée : {perm.salle.nom} - {perm.get_jour_semaine_display()}")
            return redirect('planning:gerer_permanences_externes')
    else:
        form = PermanenceExterneForm(user=request.user)
    
    # Jours semaine pour l'affichage
    jours = dict(PermanenceExterne._meta.get_field('jour_semaine').choices)
    
    return render(request, 'planning/gerer_permanences_externes.html', {
        'permanences': permanences,
        'form': form,
        'mds': mds,
        'jours': jours,
    })


@login_required
def supprimer_permanence_externe(request, pk):
    """Supprimer une permanence externe"""
    if not (request.user.is_superuser or request.user.a_la_capacite('planning_generer')):
        messages.error(request, "Accès refusé.")
        return redirect('planning:calendrier_rdv')
    
    perm = get_object_or_404(PermanenceExterne, pk=pk)
    mds = request.user.mds_principale
    
    if perm.salle.mds != mds and not request.user.is_superuser:
        messages.error(request, "Cette permanence n'appartient pas à votre MDS.")
        return redirect('planning:gerer_permanences_externes')
    
    if request.method == 'POST':
        nom = perm.salle.nom
        perm.delete()
        messages.success(request, f"Permanence pour {nom} supprimée.")
        return redirect('planning:gerer_permanences_externes')
    
    return render(request, 'planning/supprimer_permanence_externe.html', {'perm': perm})
