# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from beneficiaire.models import Beneficiaire
from . import api_particulier
from .models import SOURCES


@login_required
@require_POST
def actualiser_situation(request, code_interne):
    """
    Rapatrie la situation CAF/MSA et France Travail de l'usager.
    Réservé aux agents de la MDS où l'usager est inscrit (accès complet à la fiche).
    """
    beneficiaire = get_object_or_404(Beneficiaire, code_interne=code_interne)
    if beneficiaire.niveau_acces(request.user) != 'complet':
        return HttpResponseForbidden("Réservé aux agents de la MDS de l'usager.")

    source = request.POST.get('source')
    sources = [source] if source in dict(SOURCES) else None
    resultats = api_particulier.actualiser(beneficiaire, request.user, sources)

    ok = sum(1 for s in resultats if s.statut_appel == 'OK')
    if ok == len(resultats):
        messages.success(request, "Situation mise à jour.")
    elif ok:
        messages.info(request, f"Situation mise à jour pour {ok} source(s) sur {len(resultats)} : voir le détail.")
    else:
        messages.error(request, "Aucune information reçue : voir le détail dans le tableau.")
    retour = request.POST.get('retour', '')
    origine = Beneficiaire.objects.filter(code_interne=retour).first() if retour else None
    if origine and origine.niveau_acces(request.user) == 'complet':
        code_interne = origine.code_interne          # actualisé depuis le réseau familial : on revient sur la fiche d'origine
    return redirect(reverse('beneficiaire:detail_beneficiaire', kwargs={'code_interne': code_interne})
                    + '#situation-externe')


# -----------------------------------------------------------------------------
# Passerelle RDV Service Public (désactivée tant que RDVSP_ACTIF n'est pas à 1)
# -----------------------------------------------------------------------------
import secrets  # noqa: E402

from django.contrib.auth.decorators import user_passes_test  # noqa: E402
from django.shortcuts import render  # noqa: E402

from . import rdv_service_public as rdvsp  # noqa: E402
from .models import AppelRDVSP, CompteRDVSP, LienUsagerRDVSP  # noqa: E402
from .models import (AbsenceRDVSP, AvisRDVSP, MdsRDVSP, MotifRDVSP, ParametresRDVSP, PlageRDVSP,  # noqa: E402
                     RdvRDVSP)
from . import rdvsp_synchro  # noqa: E402


def _fiche(code_interne):
    return reverse('beneficiaire:detail_beneficiaire', kwargs={'code_interne': code_interne}) + '#rdv-usager'


def _retour_oauth(request):
    return request.build_absolute_uri(reverse('connecteurs:rdvsp_retour'))


@login_required
def rdvsp_connexion(request):
    """Envoie l'agent sur RDV Service Public pour qu'il autorise CID (une seule fois)."""
    suite = request.GET.get('suite', '')
    if not rdvsp.est_actif():
        messages.info(request, "La passerelle RDV Service Public n'est pas activée.")
        return redirect(_fiche(suite) if suite else 'accueil')
    etat = secrets.token_urlsafe(24)
    request.session['rdvsp_etat'] = etat
    request.session['rdvsp_suite'] = suite
    return redirect(rdvsp.url_autorisation(_retour_oauth(request), etat))


@login_required
def rdvsp_retour(request):
    """Retour d'autorisation : on vérifie l'état anti-rejeu, puis on enregistre le jeton de l'agent."""
    etat = request.session.pop('rdvsp_etat', None)
    suite = request.session.pop('rdvsp_suite', '')
    destination = _fiche(suite) if suite else 'accueil'
    if not rdvsp.est_actif():
        messages.info(request, "La passerelle RDV Service Public n'est pas activée.")
        return redirect(destination)
    code = request.GET.get('code')
    if not etat or request.GET.get('state') != etat or not code:
        messages.error(request, "Connexion à RDV Service Public interrompue : recommencez.")
        return redirect(destination)
    try:
        rdvsp.finaliser_connexion(request.user, code, _retour_oauth(request))
    except rdvsp.RDVSPErreur as e:
        messages.error(request, str(e))
        return redirect(destination)
    messages.success(request, "Votre compte RDV Service Public est relié à CID.")
    return redirect(destination)


@login_required
@require_POST
def rdvsp_planifier(request, code_interne):
    """Depuis la fiche usager : ouvre la prise de rendez-vous RDV-SP, usager déjà renseigné."""
    beneficiaire = get_object_or_404(Beneficiaire, code_interne=code_interne)
    if beneficiaire.niveau_acces(request.user) != 'complet':
        return HttpResponseForbidden("Réservé aux agents de la MDS de l'usager.")
    if not rdvsp.est_actif():
        messages.info(request, "La passerelle RDV Service Public n'est pas activée.")
        return redirect(_fiche(code_interne))
    if not rdvsp.compte_relie(request.user):
        return redirect(reverse('connecteurs:rdvsp_connexion') + f'?suite={code_interne}')
    fiche = request.build_absolute_uri(_fiche(code_interne))
    try:
        url = rdvsp.preparer_rdv(request.user, beneficiaire, fiche, fiche)
    except rdvsp.ConnexionRequise:
        CompteRDVSP.objects.filter(utilisateur=request.user).delete()
        return redirect(reverse('connecteurs:rdvsp_connexion') + f'?suite={code_interne}')
    except rdvsp.RDVSPErreur as e:
        messages.error(request, str(e))
        return redirect(_fiche(code_interne))
    return redirect(url)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def rdvsp_etat(request):
    """Page d'administration : état de la passerelle et ce qui manque pour l'activer."""
    conf = rdvsp.configuration()
    return render(request, 'connecteurs/rdvsp_etat.html', {
        'actif': rdvsp.est_actif(), 'manques': rdvsp.manques(conf), 'url': conf['url'],
        'redirect_uri': conf['redirect_uri'] or _retour_oauth(request),
        'nb_comptes': CompteRDVSP.objects.count(), 'nb_liens': LienUsagerRDVSP.objects.count(),
        'appels': AppelRDVSP.objects.select_related('utilisateur', 'beneficiaire')[:20],
        # Synchronisation des agendas (étape 1)
        'parametres': ParametresRDVSP.get(), 'synchro_prete': rdvsp_synchro.prete(),
        'secret_avis': bool(rdvsp_synchro.secret_avis()),
        'mds_sp': MdsRDVSP.objects.select_related('mds').order_by('mds__nom'),
        'motifs_sp': MotifRDVSP.objects.all(),
        'nb_plages': PlageRDVSP.objects.filter(neutralisee=False).count(),
        'nb_blocages': AbsenceRDVSP.objects.count(),
        'rdvs_sp': RdvRDVSP.objects.select_related('agent', 'beneficiaire')[:15],
        'avis_erreur': AvisRDVSP.objects.exclude(erreur='')[:10],
        'lieux_non_declares': rdvsp_synchro.lieux_externes_non_declares(),
    })
