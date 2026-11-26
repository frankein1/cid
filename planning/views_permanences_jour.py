# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# planning/views_permanences_jour.py
"""Permanences du jour pour l'agent d'accueil : une page à l'écran, limitée à la MDS de l'agent, classée par horaire.
Les rendez-vous traités sont masqués (case « afficher les traités »). PDF et envoi par mail sur demande seulement."""
from datetime import date, datetime, timedelta
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from mds.models import UserMDSProfile
from planning.models import CreneauRdv

STATUTS_TRAITES = ['VENU_RECU', 'VENU_NON_RECU', 'ABSENT', 'VAD_ABSENT',
                   'ANNULE_USAGER', 'REPORT_USAGER', 'ANNULE_MDS', 'REPORT_MDS']
ISSUES_ACCUEIL = [('VENU_RECU', 'Venu et reçu'), ('VENU_NON_RECU', 'Venu non reçu'), ('ABSENT', 'Absent')]


def mds_de_l_agent(user):
    profil = UserMDSProfile.objects.filter(user=user, actif=True).first()
    return profil.mds if profil else None


def accueil_autorise(user):
    return user.is_authenticated and user.a_la_capacite('peut_creer')


def accueil_de_la_mds(user, rdv):
    """L'agent d'accueil de la MDS du rendez-vous peut en noter l'issue (et seulement celui-là)."""
    if not accueil_autorise(user):
        return False
    mds = mds_de_l_agent(user)
    return bool(mds) and (rdv.mds_id == mds.pk or (rdv.salle_id and rdv.salle.mds_id == mds.pk))


def _rendez_vous_du_jour(mds, jour, traites):
    qs = (CreneauRdv.objects.filter(date=jour, beneficiaire__isnull=False)
          .filter(Q(mds=mds) | Q(salle__mds=mds))
          .select_related('beneficiaire', 'salle', 'agent').order_by('heure_debut', 'pk'))
    return qs.filter(statut__in=STATUTS_TRAITES) if traites else qs.exclude(statut__in=STATUTS_TRAITES)


def _lignes(rdv_qs):
    lignes = []
    for c in rdv_qs:
        b = c.beneficiaire
        lignes.append({
            'pk': c.pk,
            'heure': c.heure_debut.strftime('%H:%M'),
            'code': b.code_interne or '',
            'nom': f"{b.nom.upper()} {b.prenom}",
            'naissance': b.date_naissance.strftime('%d/%m/%Y'),
            'adresse': b.adresse,
            'cp_ville': f"{b.code_postal} {b.ville}",
            'telephone': b.telephone_mobile or b.telephone_fixe or '',
            'motif': f"{c.get_nature_display()} – {c.get_domaine_display()}",
            'lieu': c.lieu_affichage,
            'agent': c.agent.get_full_name() if c.agent else '-',
            'statut': c.get_statut_display(),
            'statut_code': c.statut,
            'traite': c.statut in STATUTS_TRAITES,
        })
    return lignes


def _date_depuis(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return date.today()


@login_required
def permanences_du_jour(request, date_str=None):
    if not accueil_autorise(request.user):
        messages.error(request, "Accès réservé à l'accueil de la MDS.")
        return redirect('core:dashboard')
    jour = _date_depuis(date_str)
    mds = mds_de_l_agent(request.user)
    traites = request.GET.get('traites') == '1'
    lignes = _lignes(_rendez_vous_du_jour(mds, jour, traites)) if mds else []
    context = {
        'jour': jour,
        'jour_precedent': jour - timedelta(days=1),
        'jour_suivant': jour + timedelta(days=1),
        'mds': mds,
        'lignes': lignes,
        'traites': traites,
        'nb_a_traiter': len(_lignes(_rendez_vous_du_jour(mds, jour, False))) if mds else 0,
        'issues': ISSUES_ACCUEIL,
        'email_defaut': request.user.email,
    }
    return render(request, 'planning/permanences_du_jour.html', context)


def _pdf(jour, mds, lignes):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1 * cm, rightMargin=1 * cm,
                            topMargin=1.2 * cm, bottomMargin=1.2 * cm)
    styles = getSampleStyleSheet()
    cellule = styles['BodyText']
    cellule.fontSize = 8
    cellule.leading = 9.5
    titre = f"Permanences du {jour:%d/%m/%Y} – {mds.nom if mds else ''}"
    entete = ['Heure', 'N° CID', 'Nom et prénoms', 'Naissance', 'Adresse', 'Téléphone', 'Motif', 'Lieu', 'Agent', 'Statut']
    donnees = [entete]
    for l in lignes:
        donnees.append([
            Paragraph(l['heure'], cellule), Paragraph(l['code'], cellule), Paragraph(l['nom'], cellule),
            Paragraph(l['naissance'], cellule), Paragraph(f"{l['adresse']}<br/>{l['cp_ville']}", cellule),
            Paragraph(l['telephone'], cellule), Paragraph(l['motif'], cellule), Paragraph(l['lieu'], cellule),
            Paragraph(l['agent'], cellule), Paragraph(l['statut'] if l['traite'] else '', cellule),
        ])
    table = Table(donnees, repeatRows=1,
                  colWidths=[1.2 * cm, 1.9 * cm, 3.6 * cm, 2.1 * cm, 4.6 * cm, 2.6 * cm, 3.6 * cm, 2.9 * cm, 2.6 * cm, 2.7 * cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    doc.build([Paragraph(titre, styles['Title']), Spacer(1, 0.4 * cm), table])
    buf.seek(0)
    return buf.getvalue()


@login_required
def permanences_du_jour_pdf(request, date_str=None):
    if not accueil_autorise(request.user):
        return HttpResponseForbidden("Accès réservé à l'accueil de la MDS.")
    jour = _date_depuis(date_str)
    mds = mds_de_l_agent(request.user)
    lignes = _lignes(_rendez_vous_du_jour(mds, jour, request.GET.get('traites') == '1')) if mds else []
    return FileResponse(BytesIO(_pdf(jour, mds, lignes)), content_type='application/pdf',
                        filename=f"permanences_{jour:%Y-%m-%d}.pdf")


@login_required
@require_POST
def permanences_du_jour_mail(request, date_str=None):
    from logement.services import envoi
    if not accueil_autorise(request.user):
        return HttpResponseForbidden("Accès réservé à l'accueil de la MDS.")
    jour = _date_depuis(date_str)
    url = reverse('planning:permanences_du_jour_date', args=[jour.isoformat()])
    destinataire = (request.POST.get('email') or '').strip()
    try:
        validate_email(destinataire)
    except ValidationError:
        messages.error(request, "Adresse mail incorrecte.")
        return redirect(url)
    if not envoi.mail_configure():
        messages.error(request, "La messagerie de CID n'est pas réglée : utilisez le PDF téléchargé.")
        return redirect(url)
    mds = mds_de_l_agent(request.user)
    lignes = _lignes(_rendez_vous_du_jour(mds, jour, False)) if mds else []
    try:
        envoi.envoyer_mail([destinataire], f"Permanences du {jour:%d/%m/%Y}",
                           "Liste des permanences du jour. Ce document contient des données personnelles : "
                           "ne le transmettez à personne d'autre que les agents concernés.",
                           _pdf(jour, mds, lignes), f"permanences_{jour:%Y-%m-%d}.pdf", [])
    except Exception as e:                                                   # noqa: BLE001
        messages.error(request, f"L'envoi a échoué : {e}")
    else:
        messages.success(request, f"PDF envoyé à {destinataire}.")
    return redirect(url)
