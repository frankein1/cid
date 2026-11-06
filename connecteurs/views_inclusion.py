# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/views_inclusion.py
"""Trouver un service d'insertion (data·inclusion) ; l'ajouter à l'annuaire des partenaires ; mise à jour (admin)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from beneficiaire.models import Beneficiaire, TypeAccompagnement
from partenaires.models import Partenaire

from . import data_inclusion as di
from . import thematiques_inclusion as th
from .models import ImportInclusion, ServiceInclusion

THEMATIQUE_PARTENAIRE = {  # catégorie data·inclusion → thématique de l'annuaire CID
    "logement-hebergement": "LOGEMENT", "sante": "SANTE", "trouver-un-emploi": "EMPLOI",
    "preparer-sa-candidature": "EMPLOI", "choisir-un-metier": "EMPLOI", "se-former": "EMPLOI",
    "creer-une-entreprise": "EMPLOI", "remobilisation": "EMPLOI", "famille": "ENFANCE",
    "difficultes-financieres": "BUDGET", "difficultes-administratives-ou-juridiques": "ACCES_DROITS",
    "lecture-ecriture-calcul": "SCOLARITE",
}


def _admin(u):
    return u.is_superuser or u.a_la_capacite('peut_administrer')


@login_required
def recherche(request):
    u = request.user
    if not (u.is_superuser or u.a_la_capacite('peut_voir')):
        return HttpResponseForbidden("Réservé aux agents.")
    g = request.GET
    usager = None
    if g.get('usager'):
        usager = Beneficiaire.objects.filter(code_interne=g['usager']).first()
        if usager and usager.niveau_acces(u) is None:
            usager = None
    categories = [c for c in g.getlist('cat') if c in th.LIBELLE_CATEGORIE]
    if not categories and g.getlist('types'):         # depuis l'entretien : types d'accompagnement cochés
        for t in TypeAccompagnement.objects.filter(pk__in=[x for x in g.getlist('types') if x.isdigit()]):
            categories += [c for c in t.thematiques_inclusion or [] if c not in categories]
    commune = g.get('commune', '').strip() or (usager.ville if usager else '') or getattr(u.mds_principale, 'ville', '')
    code_postal = g.get('cp', '').strip() or (usager.code_postal if usager else '')
    services, total, centre = di.rechercher(categories, commune, code_postal, gratuit=g.get('gratuit') == '1',
                                            presentiel=g.get('presentiel') == '1', texte=g.get('q', '').strip())
    for s in services:
        s.libelles = list(dict.fromkeys(th.libelle(t) for t in (s.thematiques or [])))[:4]
        s.type_libelle = th.TYPES.get(s.type, s.type)
        s.publics_libelles = [th.PUBLICS.get(p, p) for p in (s.publics or [])][:4]
    deja = set(Partenaire.objects.exclude(reference_inclusion='').values_list('reference_inclusion', flat=True))
    return render(request, 'connecteurs/inclusion_recherche.html', {
        'services': services, 'total': total, 'centre': centre, 'categories': th.CATEGORIES, 'choisies': categories,
        'commune': commune, 'cp': code_postal, 'usager': usager, 'deja': deja, 'q': g.get('q', ''),
        'gratuit': g.get('gratuit') == '1', 'presentiel': g.get('presentiel') == '1',
        'dernier': ImportInclusion.objects.filter(fin__isnull=False, erreur='').first(),
        'vide': not ServiceInclusion.objects.exists(), 'admin': _admin(u),
        'peut_creer': u.is_superuser or u.a_la_capacite('peut_creer'),
    })


@login_required
@require_POST
def ajouter_annuaire(request, pk):
    u = request.user
    if not (u.is_superuser or u.a_la_capacite('peut_creer')):
        return HttpResponseForbidden("Réservé aux agents qui peuvent créer.")
    s = get_object_or_404(ServiceInclusion, pk=pk)
    p = Partenaire.objects.filter(reference_inclusion=s.di_id).first()
    if p:
        messages.info(request, f"Déjà dans l'annuaire : {p.organisme}.")
    else:
        theme = next((THEMATIQUE_PARTENAIRE[c] for c in s.categories if c in THEMATIQUE_PARTENAIRE), 'AUTRE')
        p = Partenaire.objects.create(
            organisme=(s.structure_nom or s.nom)[:150], service=(s.nom if s.structure_nom else "")[:150], thematique=theme,
            email=s.courriel if '@' in s.courriel else '', telephone=s.telephone[:20], adresse=s.adresse[:200],
            code_postal=s.code_postal, ville=s.commune,
            commentaire="\n".join(x for x in [s.horaires_accueil, s.lien_mobilisation or s.lien_source,
                                              f"Source : data·inclusion ({s.source}), mis à jour le "
                                              f"{s.date_maj:%d/%m/%Y}" if s.date_maj else f"Source : data·inclusion ({s.source})"] if x),
            reference_inclusion=s.di_id, cree_par=u, mds_origine=getattr(u, 'mds_principale', None))
        messages.success(request, f"Ajouté à l'annuaire des partenaires : {p.organisme}. Il peut être choisi comme orientation.")
    retour = request.POST.get('retour', '')
    if retour and url_has_allowed_host_and_scheme(retour, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(retour)
    return redirect('connecteurs:inclusion_recherche')


@login_required
def etat(request):
    if not _admin(request.user):
        return HttpResponseForbidden("Réservé aux administrateurs.")
    if request.method == 'POST':
        if di.lancer_en_arriere_plan(request.user):
            messages.success(request, "Mise à jour lancée : elle prend quelques minutes. Rechargez la page pour suivre.")
        else:
            messages.warning(request, "Une mise à jour est déjà en cours.")
        return redirect('connecteurs:inclusion_etat')
    return render(request, 'connecteurs/inclusion_etat.html', {
        'imports': ImportInclusion.objects.all()[:10], 'nb': ServiceInclusion.objects.count(),
        'departements': ", ".join(di.departements()),
    })
