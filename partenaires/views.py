# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# partenaires/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import PartenaireForm
from .models import THEMATIQUES, Partenaire


@login_required
def liste(request):
    """Annuaire commun à toutes les MDS, avec recherche et filtre par thématique."""
    qs = Partenaire.objects.all()
    if request.GET.get('inactifs') != '1':
        qs = qs.filter(actif=True)
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(organisme__icontains=q) | Q(service__icontains=q) | Q(nom_contact__icontains=q)
                       | Q(prenom_contact__icontains=q) | Q(ville__icontains=q) | Q(fonction__icontains=q))
    if request.GET.get('thematique'):
        qs = qs.filter(thematique=request.GET['thematique'])
    partenaires = list(qs[:300])
    for p in partenaires:
        p.modifiable = p.peut_etre_modifie_par(request.user)
    return render(request, 'partenaires/liste.html', {
        'partenaires': partenaires, 'thematiques': THEMATIQUES, 'q': q,
        'thematique': request.GET.get('thematique', ''), 'inactifs': request.GET.get('inactifs') == '1',
    })


@login_required
def ajouter(request):
    form = PartenaireForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        p = form.save(commit=False)
        p.cree_par = request.user
        p.mds_origine = getattr(request.user, 'mds_principale', None)
        p.save()
        messages.success(request, f"Partenaire ajouté à l'annuaire : {p.organisme}.")
        return redirect('partenaires:liste')
    return render(request, 'partenaires/form.html', {'form': form, 'titre': "Ajouter un partenaire"})


@login_required
def modifier(request, pk):
    p = get_object_or_404(Partenaire, pk=pk)
    if not p.peut_etre_modifie_par(request.user):
        return HttpResponseForbidden("Seuls l'auteur de la fiche et les cadres peuvent la modifier.")
    form = PartenaireForm(request.POST or None, instance=p)
    if request.method == 'POST' and form.is_valid():
        p = form.save(commit=False)
        p.modifie_par = request.user
        p.save()
        messages.success(request, "Fiche partenaire mise à jour.")
        return redirect('partenaires:liste')
    return render(request, 'partenaires/form.html', {'form': form, 'titre': f"Modifier : {p.organisme}", 'partenaire': p})


@login_required
@require_POST
def basculer_actif(request, pk):
    """Désactiver (ou réactiver) plutôt que supprimer : les rendez-vous passés le citent encore."""
    p = get_object_or_404(Partenaire, pk=pk)
    if not p.peut_etre_modifie_par(request.user):
        return HttpResponseForbidden("Seuls l'auteur de la fiche et les cadres peuvent la modifier.")
    p.actif = not p.actif
    p.modifie_par = request.user
    p.save(update_fields=['actif', 'modifie_par', 'date_modification'])
    messages.success(request, f"{p.organisme} : {'réactivé' if p.actif else 'désactivé'}.")
    return redirect('partenaires:liste')
