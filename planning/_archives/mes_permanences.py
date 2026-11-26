# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# planning/_archives/mes_permanences.py

"""Archive : page « Mes permanences » (agent) et export ICS des créneaux libres.
Non chargé par Django (dossier _archives). Pour réactiver : remettre ces fonctions dans planning/views.py,
restaurer les URL de planning/urls.py et le gabarit planning/_archives/templates/mes_permanences_semaine.html.
Code restauré depuis planning/views.py (origin/render, 38ae2fc), inchangé.
"""

from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render

from planning.models import CreneauRdv


@login_required
def exporter_mes_permanences_ics(request):
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
        event.add('summary', f"Permanence MDS - {c.lieu_affichage}")
        event.add('dtstart', datetime.combine(c.date, c.heure_debut))
        event.add('dtend', datetime.combine(c.date, c.heure_fin))
        event.add('uid', f"permanence-{c.id}@mds.local")
        cal.add_component(event)
    
    response = HttpResponse(cal.to_ical(), content_type='text/calendar')
    response['Content-Disposition'] = 'attachment; filename="mes_permanences.ics"'
    return response




# SECTION 7 : MES PERMANENCES (AGENT)
# =============================================================================

@login_required
def mes_permanences_semaine(request, date_str=None):
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


# =============================================================================
