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
    return redirect(reverse('beneficiaire:detail_beneficiaire', kwargs={'code_interne': code_interne})
                    + '#situation-externe')
