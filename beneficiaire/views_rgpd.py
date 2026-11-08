# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/views_rgpd.py
"""
Archivage RGPD des dossiers (beneficiaire/archivage.py).
- cadres de MDS (capacité rgpd_archiver) : archiver les dossiers inactifs de leur MDS, consulter et désarchiver ;
- administrateur : tout le département, et l'effacement définitif sur confirmation d'une liste.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from mds.models import MDS, UserMDSProfile
from . import archivage as rgpd
from .models import Beneficiaire, OperationRGPD

MOT_CONFIRMATION = "EFFACER"


def _tout(u):
    return u.is_superuser or u.a_la_capacite('peut_administrer')


def _peut_archiver(u):
    return _tout(u) or u.a_la_capacite('rgpd_archiver')


def _mds_ids(u):
    """None = tout le département."""
    if _tout(u):
        return None
    return set(UserMDSProfile.objects.filter(user=u, actif=True).values_list('mds_id', flat=True))


def _dans_perimetre(u, b):
    ids = _mds_ids(u)
    return ids is None or b.mds_id in ids


def _mds_filtre(request, ids):
    mds = request.GET.get('mds', '')
    if mds.isdigit() and (ids is None or int(mds) in ids):
        return {int(mds)}
    return ids


@login_required
def rgpd_archivage(request):
    u = request.user
    if not _peut_archiver(u):
        return HttpResponseForbidden("Réservé aux cadres de MDS et aux administrateurs.")
    ids = _mds_ids(u)
    filtre = _mds_filtre(request, ids)
    mds_liste = MDS.objects.order_by('nom') if ids is None else MDS.objects.filter(pk__in=ids).order_by('nom')
    return render(request, 'beneficiaire/rgpd_archivage.html', {
        'candidats': rgpd.candidats(filtre), 'archives': rgpd.archives(filtre).order_by('-date_archivage')[:200],
        'motifs': rgpd.MOTIFS, 'delai_archivage_mois': rgpd.delai_archivage_mois(), 'delai_mois': rgpd.delai_effacement_mois(),
        'mds_liste': mds_liste, 'mds_choisie': request.GET.get('mds', ''), 'tout': _tout(u),
        'nb_effacables': rgpd.effacables().count() if _tout(u) else 0,
    })


@login_required
@require_POST
def rgpd_archiver(request):
    u = request.user
    if not _peut_archiver(u):
        return HttpResponseForbidden("Réservé aux cadres de MDS et aux administrateurs.")
    motif = request.POST.get('motif', '')
    choisis = [i for i in request.POST.getlist('ids') if i.isdigit()]
    # Seuls les dossiers réellement proposés (inactifs, hors IP/enfance, dans le périmètre) sont archivés
    proposes = {b.pk: b for b, _ in rgpd.candidats(_mds_ids(u))}
    faits, refus = 0, []
    for i in choisis:
        b = proposes.get(int(i))
        if not b:
            refus.append(i)
            continue
        try:
            rgpd.archiver(b, u, motif, request.POST.get('commentaire', ''))
            faits += 1
        except rgpd.ErreurRGPD as e:
            messages.error(request, f"{b.code_interne} : {e}")
    if faits:
        messages.success(request, f"{faits} dossier(s) archivé(s) : ils n'apparaissent plus dans CID.")
    if refus:
        messages.warning(request, f"{len(refus)} dossier(s) non archivé(s) : ils ne sont plus proposés.")
    if not choisis:
        messages.info(request, "Aucun dossier sélectionné.")
    return redirect('beneficiaire:rgpd_archivage')


@login_required
def rgpd_dossier(request, code_interne):
    """Consultation en lecture seule d'un dossier archivé, et désarchivage."""
    u = request.user
    b = get_object_or_404(Beneficiaire.tous.select_related('mds', 'referent_mds', 'archive_par'),
                          code_interne=code_interne, statut='ARCHIVE')
    if not _peut_archiver(u) or not _dans_perimetre(u, b):
        return HttpResponseForbidden("Réservé aux cadres de la MDS du dossier et aux administrateurs.")
    if request.method == 'POST':
        try:
            rgpd.desarchiver(b, u, request.POST.get('motif', 'AUTRE'), request.POST.get('commentaire', ''))
        except rgpd.ErreurRGPD as e:
            messages.error(request, str(e))
            return redirect('beneficiaire:rgpd_dossier', code_interne=code_interne)
        messages.success(request, "Dossier désarchivé : il est de nouveau visible dans CID.")
        return redirect('beneficiaire:detail_beneficiaire', code_interne=code_interne)
    return render(request, 'beneficiaire/rgpd_dossier.html', {
        'b': b, 'motif': dict(rgpd.MOTIFS).get(b.motif_archivage, b.motif_archivage),
        'derniere_activite': rgpd.derniere_activite([b.pk]).get(b.pk),
        'contenu': rgpd.bilan(b), 'motifs_desarchivage': rgpd.MOTIFS_DESARCHIVAGE,
        'operations': b.operations_rgpd.select_related('par'),
    })


@login_required
def rgpd_effacement(request):
    """Effacement définitif : administrateur seulement, sur confirmation d'une liste."""
    u = request.user
    if not _tout(u):
        return HttpResponseForbidden("Réservé aux administrateurs.")
    dossiers = list(rgpd.effacables())
    if request.method == 'POST':
        if request.POST.get('confirmation', '').strip() != MOT_CONFIRMATION:
            messages.error(request, f"Tapez {MOT_CONFIRMATION} pour confirmer l'effacement définitif.")
            return redirect('beneficiaire:rgpd_effacement')
        choisis = {int(i) for i in request.POST.getlist('ids') if i.isdigit()}
        faits = 0
        for b in dossiers:
            if b.pk not in choisis:
                continue
            try:
                rgpd.effacer(b, u)
                faits += 1
            except rgpd.ErreurRGPD as e:
                messages.error(request, f"{b.code_interne} : {e}")
        if faits:
            messages.success(request, f"{faits} dossier(s) effacé(s) définitivement. Il n'en reste qu'une trace anonyme.")
        return redirect('beneficiaire:rgpd_effacement')
    return render(request, 'beneficiaire/rgpd_effacement.html', {
        'lignes': [(b, rgpd.bilan(b)) for b in dossiers], 'delai_mois': rgpd.delai_effacement_mois(),
        'mot': MOT_CONFIRMATION,
        'traces': OperationRGPD.objects.filter(action=OperationRGPD.EFFACEMENT).select_related('mds', 'par')[:50],
    })
