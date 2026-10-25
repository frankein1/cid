# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/views/accompagnement.py
"""
Menu « Accompagnement » : un point d'entrée par domaine d'intervention.
Aides financières : opérationnel. RSA (CER), IP, Enfance, Logement : pages d'attente,
alimentées au fur et à mesure des ateliers.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render

MODULES = {
    'rsa': {
        'titre': "RSA – Contrat d'engagement (CER)", 'icone': 'fa-file-signature', 'couleur': 'blue',
        'prevu': [
            "Contrat de 3, 6, 12 ou 18 mois, signé par l'AS référente",
            "Types : social, santé (dont RQTH), garde de jeunes enfants, emploi (France Travail), relais de 3 mois",
            "Objectifs, actions et échéances ; bilan en fin de contrat",
            "Suivi des manquements : 1er et 2e rendez-vous, suspension, délai d'un mois, résiliation",
            "PDF du contrat pour la passerelle et rangement dans la rubrique RSA de la GED",
        ],
    },
    'ip': {
        'titre': "Informations préoccupantes (IP)", 'icone': 'fa-triangle-exclamation', 'couleur': 'red',
        'prevu': [
            "Réception et enregistrement de l'IP, délais à suivre",
            "Évaluation, synthèse IP (déjà possible en réunion dans le planning, domaine IP)",
            "Décision et transmission à la CRIP",
        ],
    },
    'enfance': {
        'titre': "Enfance – famille", 'icone': 'fa-children', 'couleur': 'purple',
        'prevu': [
            "Suivi des mesures et des interventions auprès des familles",
            "Rendez-vous et VAD du domaine Enfance (déjà possibles dans le planning)",
        ],
    },
    'logement': {
        'titre': "Logement", 'icone': 'fa-house', 'couleur': 'emerald',
        'prevu': [
            "DALO, FSL accès, FSL maintien",
            "COPP (commission d'orientation des publics prioritaires)",
            "Prévention des expulsions",
        ],
    },
}


@login_required
def module_a_venir(request, module):
    infos = MODULES.get(module)
    if not infos:
        raise Http404
    return render(request, 'core/module_a_venir.html', {'module': infos})


@login_required
def aides_financieres(request):
    """Demandes d'aides de la MDS (AFASE, CAP, régie), avec statut et décision."""
    from AidFi.models.m_generique import DemandeAide, STATUT_DEMANDE
    from AidFi.views.v_generique import DECISIONS, _decision

    from mds.models import UserMDSProfile
    mds = getattr(request.user, 'mds_principale', None) or getattr(
        UserMDSProfile.objects.filter(user=request.user, actif=True).select_related('mds').first(), 'mds', None)
    if not (request.user.a_la_capacite('peut_voir') and mds):
        messages.error(request, "Accès réservé aux agents d'une MDS.")
        return redirect('core:dashboard')

    est_cadre = request.user.a_la_capacite('peut_valider')
    qs = (DemandeAide.objects.filter(beneficiaire__mds=mds)
          .select_related('type_aide', 'beneficiaire', 'cree_par').order_by('-date_creation'))
    mes = request.GET.get('mes', '0' if est_cadre else '1') == '1'
    if mes:
        qs = qs.filter(cree_par=request.user)
    if request.GET.get('type'):
        qs = qs.filter(type_aide__code=request.GET['type'])
    if request.GET.get('statut'):
        qs = qs.filter(statut=request.GET['statut'])

    routes = {'AFASE': 'AidFi:afase_detail', 'CAP': 'AidFi:cap_detail', 'REGIE': 'AidFi:regie_detail'}
    lignes = []
    for d in qs[:200]:
        code = d.type_aide.code if d.type_aide_id else ''
        afase = None
        if code == 'AFASE':
            from AidFi.models.m_afase import DemandeAFASE
            afase = DemandeAFASE.objects.filter(pk=d.pk).first()
        decision, montant = _decision(d, afase)
        lignes.append({'demande': d, 'route': routes.get(code), 'code': code,
                       'decision': DECISIONS.get(decision), 'montant_accorde': montant})
    return render(request, 'core/aides_financieres.html', {
        'lignes': lignes, 'mes': mes, 'type': request.GET.get('type', ''),
        'statut': request.GET.get('statut', ''), 'statuts': STATUT_DEMANDE,
    })
