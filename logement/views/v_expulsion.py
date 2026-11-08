# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/views/v_expulsion.py
"""Prévention des expulsions : liste, saisie par le Service Logement, suivi par la MDS, journal, statistiques."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from mds.models import MDS

from ..forms import DossierExpulsionForm, EtapeExpulsionForm
from ..models import DossierExpulsion as D, EtapeExpulsion
from ..models.m_expulsion import treve_hivernale
from ..services import expulsion as X

REFUS = "Réservé au Service Logement et aux agents de la MDS chargée du dossier."


def _dossier(request, pk):
    d = get_object_or_404(D.objects.select_related('mds', 'referent', 'beneficiaire'), pk=pk)
    return d, X.peut_voir(request.user, d)


def _mds_possibles(user):
    if X.est_sl(user) or X.est_admin(user):
        return MDS.objects.filter(active=True).order_by('nom')
    return X.mds_de(user).order_by('nom')


# ---------------------------------------------------------------------------------------------------------------
@login_required
def expulsion_liste(request):
    user = request.user
    if not X.peut_voir_module(user):
        if X.peut_voir_stats(user):
            return redirect('logement:expulsion_stats')
        return HttpResponseForbidden(REFUS)
    qs = X.dossiers_visibles(user)
    g = request.GET
    statut = g.get('statut', D.EN_COURS)
    if statut in dict(D.STATUTS):
        qs = qs.filter(statut=statut)
    if g.get('mds') == 'aucune':
        qs = qs.filter(mds__isnull=True)
    elif (g.get('mds') or '').isdigit():
        qs = qs.filter(mds_id=g['mds'])
    if g.get('vue') == 'mes':
        qs = qs.filter(referent=user)
    elif g.get('vue') == 'audiences':
        j = timezone.localdate()
        qs = qs.filter(date_audience__gte=j).order_by('date_audience')
    q = (g.get('q') or '').strip()
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(prenom__icontains=q) | Q(numero__icontains=q)
                       | Q(numero_allocataire__icontains=q) | Q(ville__icontains=q))
    page = Paginator(qs, 25).get_page(g.get('page'))
    return render(request, 'logement/expulsion_liste.html', {
        'page': page, 'statut': statut, 'statuts': D.STATUTS, 'q': q, 'vue': g.get('vue', ''),
        'mds_filtre': g.get('mds', ''), 'mds_liste': _mds_possibles(user), 'est_sl': X.est_sl(user),
        'peut_creer': X.peut_creer(user), 'peut_stats': X.peut_voir_stats(user), 'treve': treve_hivernale()})


@login_required
def expulsion_nouveau(request):
    user = request.user
    if not X.peut_creer(user):
        return HttpResponseForbidden(REFUS)
    form = DossierExpulsionForm(request.POST or None, mds_possibles=_mds_possibles(user), initial={'origine': D.SL_CAF})
    if request.method == 'POST' and form.is_valid():
        d = form.save(commit=False)
        mds = d.mds
        d.mds = None
        d.cree_par = user
        d.tracer(user, "Dossier ouvert", d.get_origine_display())
        if form.usager:
            X.rattacher(d, form.usager, user, affecter_mds=False)
        d.save()
        if mds:
            X.affecter(d, mds, user)
        messages.success(request, f"Dossier {d.numero} enregistré." + (" La MDS est prévenue dans CID." if mds else ""))
        return redirect('logement:expulsion_detail', pk=d.pk)
    return render(request, 'logement/expulsion_form.html', {'form': form, 'd': None})


@login_required
def expulsion_modifier(request, pk):
    d, voir = _dossier(request, pk)
    if not voir or not X.peut_ecrire(request.user, d):
        return HttpResponseForbidden(REFUS)
    sl = X.est_sl(request.user) or X.est_admin(request.user)
    mds_avant = d.mds
    decision_avant = (dict(d.decision or {}), d.date_decision)
    form = DossierExpulsionForm(request.POST or None, instance=d,
                                mds_possibles=_mds_possibles(request.user) if sl else MDS.objects.filter(pk=d.mds_id))
    if request.method == 'POST' and form.is_valid():
        d = form.save(commit=False)
        nouvelle_mds = d.mds
        d.mds = mds_avant
        if form.usager and form.usager != d.beneficiaire:
            if sl or form.usager.mds_id == d.mds_id:
                X.rattacher(d, form.usager, request.user, affecter_mds=False)
                if sl and form.usager.mds and 'mds' not in form.changed_data:
                    nouvelle_mds = form.usager.mds      # le dossier suit la MDS de l'usager
            else:
                messages.warning(request, "Cet usager relève d'une autre MDS : le Service Logement doit réaffecter le dossier.")
        d.tracer(request.user, "Dossier modifié", ", ".join(str(form.fields[c].label) for c in form.changed_data
                                                             if c in form.fields)[:300])
        d.save()
        if sl and nouvelle_mds and nouvelle_mds != mds_avant:
            X.affecter(d, nouvelle_mds, request.user)
        if (d.decision, d.date_decision) != decision_avant and d.date_decision and not sl:
            X.prevenir_sl(d, request.user, f"Prévention des expulsions : décision saisie – {d.nom_complet}",
                          f"La MDS a saisi la décision du tribunal du {d.date_decision:%d/%m/%Y} pour le dossier "
                          f"{d.numero} : {', '.join(d.libelles_decision()) or 'à préciser'}.")
        messages.success(request, "Dossier enregistré.")
        return redirect('logement:expulsion_detail', pk=d.pk)
    return render(request, 'logement/expulsion_form.html', {'form': form, 'd': d})


@login_required
def expulsion_detail(request, pk):
    d, voir = _dossier(request, pk)
    if not voir:
        return HttpResponseForbidden(REFUS)
    user = request.user
    peut_rattacher = X.peut_ecrire(user, d) and d.statut == D.EN_COURS
    from beneficiaire.views_annuaire import criteres, rechercher
    c = criteres(request.GET)
    usagers, message_recherche = [], ""
    if peut_rattacher and not d.beneficiaire_id:
        if any(c.values()):
            usagers, message_recherche = rechercher(**c)
        else:   # proposition automatique : n° allocataire, puis nom et prénom
            usagers = (rechercher(caf=d.numero_allocataire)[0] if d.numero_allocataire else []) \
                or (rechercher(nom=d.nom, prenom=d.prenom)[0] if d.prenom else []) \
                or (rechercher(nom=d.nom, adresse=d.adresse)[0] if d.adresse else [])
    return render(request, 'logement/expulsion_detail.html', {
        'd': d, 'etapes': d.etapes.select_related('saisi_par'), 'alertes': d.alertes(),
        'peut_ecrire': X.peut_ecrire(user, d), 'peut_affecter': X.peut_affecter(user),
        'peut_designer': X.peut_designer_referent(user, d), 'peut_prendre': X.peut_prendre(user, d),
        'peut_supprimer': X.peut_supprimer(user), 'peut_rattacher': peut_rattacher,
        'mds_liste': _mds_possibles(user) if X.peut_affecter(user) else [],
        'mds_secteur': MDS.pour_adresse(d.code_postal, d.ville) if X.peut_affecter(user) and not d.mds_id else [],
        'referents': X.referents_possibles(d), 'etape_form': EtapeExpulsionForm(initial={'date': timezone.localdate()}),
        'usagers': [{'b': b, 'possible': X.peut_rattacher(user, d, b)} for b in usagers], 'c': c,
        'message_recherche': message_recherche, 'acces_fiche': bool(d.beneficiaire and d.beneficiaire.niveau_acces(user)), 'motifs_cloture': D.MOTIFS_CLOTURE, 'caf': d.caf_par_rubrique(),
        'decision': d.libelles_decision(),
        'treve': treve_hivernale() and d.etapes.filter(type_etape__in=('COMMANDEMENT_QUITTER', 'DEMANDE_CFP',
                                                                       'COMMISSION_PREFECTORALE', 'CFP_ACCORDE')).exists()})


@login_required
@require_POST
def expulsion_action(request, pk):
    d, voir = _dossier(request, pk)
    user = request.user
    if not voir:
        return HttpResponseForbidden(REFUS)
    action = request.POST.get('action')
    retour = redirect('logement:expulsion_detail', pk=d.pk)

    if action == 'affecter':
        if not X.peut_affecter(user):
            return HttpResponseForbidden(REFUS)
        mds = MDS.objects.filter(pk=request.POST.get('mds')).first()
        if mds:
            X.affecter(d, mds, user)
            messages.success(request, f"Dossier confié à {mds} : son responsable est prévenu dans CID.")
        return retour

    if action in ('referent', 'prendre'):
        if action == 'prendre' and X.peut_prendre(user, d):
            X.designer_referent(d, user, user)
        elif action == 'referent' and X.peut_designer_referent(user, d):
            r = X.referents_possibles(d).filter(pk=request.POST.get('referent')).first()
            if not r:
                messages.error(request, "Choisissez un agent de la MDS.")
                return retour
            X.designer_referent(d, r, user)
        else:
            return HttpResponseForbidden(REFUS)
        messages.success(request, "Référent social enregistré.")
        return retour

    if not X.peut_ecrire(user, d):
        return HttpResponseForbidden(REFUS)

    if action == 'rattacher':
        from beneficiaire.models import Beneficiaire
        b = Beneficiaire.objects.select_related('mds').filter(pk=request.POST.get('beneficiaire')).first()
        if b and X.peut_rattacher(user, d, b):
            X.rattacher(d, b, user)
            d.save()
            messages.success(request, "Usager rattaché." + (f" Dossier confié à {d.mds} : son responsable est prévenu."
                                                            if X.est_sl(user) and d.mds else ""))
        else:
            messages.error(request, "Rattachement impossible : l'usager relève d'une autre MDS "
                                    "(le Service Logement réaffecte le dossier).")
    elif action == 'detacher':
        d.tracer(user, "Usager détaché", str(d.beneficiaire or ""))
        d.beneficiaire = None
        d.save()
    elif action == 'etape':
        form = EtapeExpulsionForm(request.POST)
        if form.is_valid():
            e = form.save(commit=False)
            e.dossier, e.saisi_par = d, user
            e.save()
            d.tracer(user, "Étape ajoutée", str(e))
            d.save()
            messages.success(request, f"Étape « {e.get_type_etape_display()} » ajoutée"
                             + (f", échéance le {e.echeance:%d/%m/%Y}." if e.echeance else "."))
        else:
            messages.error(request, "Étape incomplète : type et date obligatoires.")
    elif action in ('etape_faite', 'etape_supprimer'):
        e = get_object_or_404(EtapeExpulsion, pk=request.POST.get('etape'), dossier=d)
        if action == 'etape_faite':
            e.faite = True
            e.save(update_fields=['faite'])
        else:
            d.tracer(user, "Étape supprimée", str(e))
            e.delete()
            d.save()
    elif action == 'cloturer':
        motif = request.POST.get('motif_cloture')
        if motif not in dict(D.MOTIFS_CLOTURE):
            messages.error(request, "Indiquez le motif de clôture.")
            return retour
        d.statut, d.motif_cloture, d.date_cloture = D.CLOS, motif, timezone.localdate()
        d.tracer(user, "Dossier clos", d.get_motif_cloture_display())
        d.save()
        if not X.est_sl(user):
            X.prevenir_sl(d, user, f"Prévention des expulsions : dossier clos – {d.nom_complet}",
                          f"La MDS a clos le dossier {d.numero} : {d.get_motif_cloture_display().lower()}.")
        messages.success(request, "Dossier clos.")
    elif action == 'rouvrir':
        d.statut, d.motif_cloture, d.date_cloture = D.EN_COURS, '', None
        d.tracer(user, "Dossier rouvert")
        d.save()
    elif action == 'supprimer':
        if not X.peut_supprimer(user):
            return HttpResponseForbidden(REFUS)
        numero = d.numero
        d.delete()
        messages.success(request, f"Dossier {numero} supprimé.")
        return redirect('logement:expulsion_liste')
    return retour


@login_required
def expulsion_secteur(request):
    """MDS dont le secteur couvre l'adresse (arrondissement à Marseille, ville ailleurs) : une proposition au SL."""
    if not X.peut_affecter(request.user):
        return HttpResponseForbidden(REFUS)
    from django.http import JsonResponse
    return JsonResponse({'mds': [{'pk': m.pk, 'nom': m.nom} for m in
                                 MDS.pour_adresse(request.GET.get('cp', ''), request.GET.get('ville', ''))]})


@login_required
def expulsion_pdf(request, pk):
    d, voir = _dossier(request, pk)
    if not voir:
        return HttpResponseForbidden(REFUS)
    from ..services.expulsion_pdf import fiche
    r = HttpResponse(fiche(d), content_type='application/pdf')
    r['Content-Disposition'] = f'inline; filename="prevention_expulsion_{d.numero}.pdf"'
    return r


@login_required
def expulsion_stats(request):
    if not X.peut_voir_stats(request.user):
        return HttpResponseForbidden("Réservé aux personnes habilitées à consulter les statistiques.")
    annee = request.GET.get('annee')
    annee = int(annee) if (annee or '').isdigit() else None
    annees = sorted({x.year for x in D.objects.dates('date_reception', 'year')}, reverse=True)
    return render(request, 'logement/expulsion_stats.html', {
        's': X.statistiques(request.user, annee), 'annee': annee, 'annees': annees,
        'peut_liste': X.peut_voir_module(request.user)})


def dossiers_usager(beneficiaire, user):
    """Pour l'encart « Logement » de la fiche usager."""
    return X.dossiers_visibles(user).filter(beneficiaire=beneficiaire)


__all__ = ['expulsion_liste', 'expulsion_nouveau', 'expulsion_modifier', 'expulsion_detail', 'expulsion_action',
           'expulsion_pdf', 'expulsion_stats', 'expulsion_secteur']
