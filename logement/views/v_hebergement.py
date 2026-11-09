# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/views/v_hebergement.py
"""Hébergement d'urgence : dossiers de la MDS, démarches préalables, fiches (demande, renouvellement, rapport final,
orientation vers l'État), visa du cadre, réponse, prise en charge et échéances, statistiques."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from beneficiaire.models import Beneficiaire
from beneficiaire.views import user_peut_agir_sur_beneficiaire

from ..models import (DemarcheHebergement as M, DossierHebergement as D, FicheHebergement as F,
                      StructureHebergement)
from ..services import hebergement as H

REFUS = "Réservé aux agents de la MDS de l'usager."


def _dossier(request, pk):
    d = get_object_or_404(D.objects.select_related('beneficiaire', 'mds', 'referent', 'structure'), pk=pk)
    return d, H.peut_voir(request.user, d)


def _fiche(request, pk):
    f = get_object_or_404(F.objects.select_related('dossier__beneficiaire', 'dossier__mds', 'dossier__referent',
                                                   'dossier__structure', 'cadre', 'redacteur'), pk=pk)
    return f, H.peut_voir(request.user, f.dossier)


# ------------------------------------------------------------------------------------------------- liste, stats
@login_required
def hebergement_liste(request):
    if not H.peut_voir_module(request.user):
        return HttpResponseForbidden(REFUS)
    qs = H.dossiers_visibles(request.user)
    filtre = request.GET.get('statut') or 'ouverts'
    if filtre == 'clos':
        qs = qs.filter(statut=D.CLOS)
    elif filtre in (D.RECHERCHE, D.HEBERGE):
        qs = qs.filter(statut=filtre)
    else:
        qs = qs.exclude(statut=D.CLOS)
    j = timezone.localdate()
    dossiers = list(qs.order_by('date_fin_prevue', '-date_ouverture')[:300])
    for d in dossiers:
        d.a_viser = d.fiches.filter(statut=F.A_VISER).count()
        d.en_attente = d.fiches.filter(statut=F.ENVOYEE, reponse='').count()
    return render(request, 'logement/hebergement_liste.html', {
        'dossiers': dossiers, 'filtre': filtre, 'alerte': H.ALERTE_JOURS,
        'echeances': sum(1 for d in dossiers if d.jours_restants is not None and d.jours_restants <= H.ALERTE_JOURS),
        'peut_stats': H.peut_voir_stats(request.user), 'aujourd_hui': j})


@login_required
def hebergement_stats(request):
    if not H.peut_voir_stats(request.user):
        return HttpResponseForbidden("Réservé aux cadres et à la direction.")
    annee = request.GET.get('annee')
    annee = int(annee) if annee and annee.isdigit() else None
    annees = sorted({x.year for x in D.objects.dates('date_ouverture', 'year')}, reverse=True)
    return render(request, 'logement/hebergement_stats.html', {
        's': H.statistiques(request.user, annee), 'annee': annee, 'annees': annees})


# ------------------------------------------------------------------------------------------------- dossier
@login_required
@require_POST
def hebergement_nouveau(request, code_interne):
    b = get_object_or_404(Beneficiaire.tous.select_related('mds'), code_interne=code_interne)
    if b.niveau_acces(request.user) != 'complet' or not user_peut_agir_sur_beneficiaire(request.user, b) or not b.mds_id:
        return HttpResponseForbidden(REFUS)
    d, cree = H.ouvrir(b, request.user)
    if cree:
        messages.success(request, "Dossier ouvert. Tracez d'abord les démarches déjà faites (115, SIAO…), puis "
                                  "préparez la fiche.")
    return redirect('logement:hebergement_detail', pk=d.pk)


@login_required
def hebergement_detail(request, pk):
    d, voir = _dossier(request, pk)
    if not voir:
        return HttpResponseForbidden(REFUS)
    ecrire = H.peut_ecrire(request.user, d)
    conseil = H.fiche_conseillee(d.beneficiaire) if d.beneficiaire else (None, "")
    fiches = list(d.fiches.select_related('cadre'))
    return render(request, 'logement/hebergement_detail.html', {
        'd': d, 'b': d.beneficiaire, 'peut_ecrire': ecrire, 'fiches': fiches, 'demarches': d.demarches.all(),
        'types_demarche': M.TYPES, 'motifs': D.MOTIFS_CLOTURE, 'conseil': conseil[0], 'conseil_raison': conseil[1],
        'controles': H.controles(d, F.SAS) if d.statut == D.RECHERCHE else [],
        'structures': StructureHebergement.objects.filter(actif=True),
        'peut_rouvrir': d.statut == D.CLOS and d.beneficiaire is not None
        and user_peut_agir_sur_beneficiaire(request.user, d.beneficiaire),
        'alerte': H.ALERTE_JOURS, 'aujourd_hui': timezone.localdate()})


@login_required
@require_POST
def hebergement_action(request, pk):
    d, voir = _dossier(request, pk)
    if not voir:
        return HttpResponseForbidden(REFUS)
    p, user, action = request.POST, request.user, request.POST.get('action')
    retour = redirect('logement:hebergement_detail', pk=d.pk)
    if action == 'rouvrir' and d.statut == D.CLOS and d.beneficiaire and user_peut_agir_sur_beneficiaire(user, d.beneficiaire):
        H.rouvrir(d, user)
        messages.success(request, "Dossier rouvert.")
        return retour
    if not H.peut_ecrire(user, d):
        return HttpResponseForbidden(REFUS)
    if action == 'demarche':
        type_ = p.get('type_demarche')
        if type_ not in dict(M.TYPES):
            messages.error(request, "Choisissez la démarche.")
        else:
            M.objects.create(dossier=d, type_demarche=type_, date=parse_date(p.get('date') or '') or timezone.localdate(),
                             precision=(p.get('precision') or '').strip()[:150],
                             reponse=(p.get('reponse') or '').strip()[:255], saisi_par=user)
            messages.success(request, "Démarche tracée.")
    elif action == 'demarche_reponse':
        m = get_object_or_404(M, pk=p.get('demarche'), dossier=d)
        m.reponse = (p.get('reponse') or '').strip()[:255]
        m.save()
        messages.success(request, "Réponse enregistrée.")
    elif action == 'demarche_supprimer':
        M.objects.filter(pk=p.get('demarche'), dossier=d).delete()
        messages.success(request, "Démarche retirée.")
    elif action == 'fiche':
        type_ = p.get('type_fiche')
        if type_ not in dict(F.TYPES) or (type_ in (F.RENOUVELLEMENT, F.FINAL) and d.statut != D.HEBERGE):
            messages.error(request, "Cette fiche ne correspond pas à l'état du dossier.")
        else:
            f = d.fiches.filter(type_fiche=type_, statut__in=(F.BROUILLON, F.A_VISER, F.VISEE)).first()
            if f is None:
                f = H.creer_fiche(d, type_, user)
                messages.success(request, "Fiche préremplie : vérifiez chaque rubrique, complétez, puis demandez le visa.")
            return redirect('logement:fiche_hebergement', pk=f.pk)
    elif action == 'prise_en_charge':
        structure = StructureHebergement.objects.filter(pk=p.get('structure') or 0).first()
        entree = parse_date(p.get('date_entree') or '')
        if not entree:
            messages.error(request, "Indiquez la date d'entrée dans la structure.")
        else:
            d.structure, d.structure_libre = structure, ("" if structure else (p.get('structure_libre') or '').strip()[:150])
            d.date_entree = entree
            d.date_fin_prevue = parse_date(p.get('date_fin_prevue') or '') or H.fin_apres(entree, H.duree_initiale(structure))
            d.statut = D.HEBERGE
            d.tracer(user, "Prise en charge mise à jour", f"{d.nom_structure}, du {entree:%d/%m/%Y} au {d.date_fin_prevue:%d/%m/%Y}")
            d.save()
            messages.success(request, "Prise en charge enregistrée.")
    elif action == 'referent':
        from ..services.expulsion import referents_possibles
        r = referents_possibles(d).filter(pk=p.get('referent') or 0).first()
        if r:
            d.referent = r
            d.tracer(user, "Référent social désigné", r.get_full_name() or r.username)
            d.save()
            messages.success(request, "Référent enregistré.")
    elif action == 'cloturer':
        if p.get('motif') not in dict(D.MOTIFS_CLOTURE):
            messages.error(request, "Choisissez le motif de clôture.")
        else:
            H.cloturer(d, user, p.get('motif'), parse_date(p.get('date_sortie') or ''))
            messages.success(request, "Dossier clos.")
    else:
        return HttpResponseForbidden(REFUS)
    return retour


# ------------------------------------------------------------------------------------------------- fiches
@login_required
def fiche_hebergement(request, pk):
    f, voir = _fiche(request, pk)
    if not voir:
        return HttpResponseForbidden(REFUS)
    d = f.dossier
    ecrire = H.peut_ecrire(request.user, d) and f.modifiable
    if request.method == 'POST':
        if not ecrire:
            return HttpResponseForbidden(REFUS)
        f.donnees = H.lire_formulaire(request.POST, f.type_fiche)
        if f.statut in (F.A_VISER, F.VISEE):
            f.statut, f.cadre, f.date_validation_cadre = F.BROUILLON, None, None
            messages.warning(request, "La fiche a changé après la demande de visa : redemandez le visa du cadre.")
        f.tracer(request.user, "Fiche modifiée")
        f.save()
        messages.success(request, "Fiche enregistrée.")
        return redirect('logement:fiche_hebergement', pk=f.pk)
    sections, personnes, revenus = H.pour_gabarit(f)
    debut = d.date_fin_prevue if f.type_fiche == F.RENOUVELLEMENT else None
    return render(request, 'logement/hebergement_fiche.html', {
        'f': f, 'd': d, 'b': d.beneficiaire, 'sections': sections, 'personnes': personnes, 'revenus': revenus,
        'qualites': H.QUALITES, 'peut_ecrire': ecrire, 'peut_viser': H.peut_viser(request.user, d),
        'peut_repondre': H.peut_ecrire(request.user, d), 'controles': H.controles(d, f.type_fiche),
        'demarches': d.demarches.all(), 'reponses': F.REPONSES,
        'structures': StructureHebergement.objects.filter(actif=True),
        'fin_proposee': H.fin_apres(debut, H.duree_renouvellement(d)) if debut else None})


@login_required
def fiche_hebergement_pdf(request, pk):
    f, voir = _fiche(request, pk)
    if not voir:
        return HttpResponseForbidden(REFUS)
    from ..services.hebergement_pdf import fiche_pdf
    r = HttpResponse(fiche_pdf(f), content_type='application/pdf')
    r['Content-Disposition'] = f'inline; filename="hebergement_{f.dossier.numero}_{f.type_fiche.lower()}.pdf"'
    return r


@login_required
@require_POST
def fiche_hebergement_action(request, pk):
    f, voir = _fiche(request, pk)
    if not voir:
        return HttpResponseForbidden(REFUS)
    p, user, action, d = request.POST, request.user, request.POST.get('action'), f.dossier
    ecrire = H.peut_ecrire(user, d)
    if action == 'demander_visa' and ecrire and f.statut == F.BROUILLON:
        cadre = H.demander_visa(f, user)
        messages.success(request, f"Visa demandé{' à ' + cadre.get_full_name() if cadre else ''}.")
    elif action == 'viser' and H.peut_viser(user, d) and f.statut in (F.BROUILLON, F.A_VISER):
        H.viser(f, user)
        messages.success(request, "Visée : vos initiales et la date figurent sur la fiche.")
    elif action == 'renvoyer' and H.peut_viser(user, d) and f.statut == F.A_VISER:
        H.renvoyer(f, user, (p.get('motif') or '').strip())
        messages.success(request, "Fiche renvoyée à l'agent.")
    elif action == 'reponse' and ecrire and f.statut == F.ENVOYEE:
        if p.get('reponse') not in dict(F.REPONSES):
            messages.error(request, "Choisissez la réponse reçue.")
        else:
            H.enregistrer_reponse(
                f, user, p.get('reponse'), parse_date(p.get('date_reponse') or ''), (p.get('detail') or '').strip(),
                structure=StructureHebergement.objects.filter(pk=p.get('structure') or 0).first(),
                structure_libre=(p.get('structure_libre') or '').strip(),
                date_entree=parse_date(p.get('date_entree') or ''), date_fin=parse_date(p.get('date_fin') or ''))
            messages.success(request, "Réponse enregistrée.")
            return redirect('logement:hebergement_detail', pk=d.pk)
    elif action == 'supprimer' and ecrire and f.statut == F.BROUILLON:
        d.tracer(user, "Fiche supprimée (brouillon)", f.get_type_fiche_display())
        d.save()
        f.delete()
        messages.success(request, "Brouillon supprimé.")
        return redirect('logement:hebergement_detail', pk=d.pk)
    else:
        return HttpResponseForbidden(REFUS)
    return redirect('logement:fiche_hebergement', pk=f.pk)


__all__ = ['hebergement_liste', 'hebergement_stats', 'hebergement_nouveau', 'hebergement_detail', 'hebergement_action',
           'fiche_hebergement', 'fiche_hebergement_pdf', 'fiche_hebergement_action']
