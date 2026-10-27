# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/views/v_ip.py
"""IP : liste, saisie par la CRIP, fiche, transmission à la MDS, binôme, pièces."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from protection_enfance.forms.f_evaluation import ActionForm, AuditionForm, SaisineForm
from protection_enfance.forms.f_ip import (AdulteFormSet, BinomeForm, EnfantFamilleFormSet, EnfantFormSet,
                                          IPForm)
from protection_enfance.models import InformationPreoccupante
from protection_enfance.models.m_evaluation import PRESENCES, RESULTATS
from protection_enfance.models.m_ip import CAP_CRIP, CAP_EVALUER, CAP_PIEF, CAP_PILOTER, STATUTS
from protection_enfance.services import ip_circuit as circuit
from protection_enfance.services import ip_convocations as convocations
from protection_enfance.services import ip_famille as famille
from protection_enfance.services.ip_circuit import CircuitError


def acces_module(user):
    return user.is_superuser or any(user.a_la_capacite(c) for c in (CAP_CRIP, CAP_PIEF, CAP_PILOTER, CAP_EVALUER))


def get_ip(request, ip_id):
    """IP par numéro (D13-00000001) ou identifiant ; 403 si l'agent n'y a pas accès."""
    qs = InformationPreoccupante.objects.select_related('mds', 'famille', 'binome_1', 'binome_2', 'recue_par')
    ip = qs.filter(numero=ip_id).first() or (qs.filter(pk=ip_id).first() if str(ip_id).isdigit() else None)
    if ip is None:
        from django.http import Http404
        raise Http404("IP introuvable")
    return ip


def _refus():
    return HttpResponseForbidden("Accès réservé aux personnes en charge de cette IP.")


@login_required
def ip_liste(request):
    user = request.user
    if not acces_module(user):
        return HttpResponseForbidden("Module réservé à la CRIP, aux inspecteurs, aux cadres et aux évaluateurs.")
    qs = InformationPreoccupante.visibles_par(user)
    circuit.envoyer_rappels(qs)
    qs = qs.select_related('mds', 'famille', 'binome_1', 'binome_2').prefetch_related('enfants')

    statut = request.GET.get('statut', '')
    if statut == 'ouvertes':
        qs = qs.exclude(statut__in=('TRANSMISE_PIEF', 'CLOTUREE'))
    elif statut:
        qs = qs.filter(statut=statut)
    if request.GET.get('mes') == 'oui':
        qs = qs.filter(Q(binome_1=user) | Q(binome_2=user))
    q = (request.GET.get('q') or '').strip()
    if q:
        qs = qs.filter(Q(numero__icontains=q) | Q(famille__nom__icontains=q) | Q(famille_libelle__icontains=q)
                       | Q(enfants__nom__icontains=q)).distinct()
    page = Paginator(qs.order_by('date_echeance', 'id') if statut in ('', 'ouvertes') else qs, 25)
    return render(request, 'protection_enfance/ip_liste.html', {
        'page_obj': page.get_page(request.GET.get('page')), 'statuts': STATUTS, 'statut': statut, 'q': q,
        'mes': request.GET.get('mes') == 'oui', 'est_crip': user.a_la_capacite(CAP_CRIP),
        'est_pief': user.a_la_capacite(CAP_PIEF), 'query': request.GET.urlencode(),
    })


@login_required
def ip_saisie(request, ip_id=None):
    """Création (ou correction avant évaluation) d'une IP par la CRIP."""
    user = request.user
    ip = get_ip(request, ip_id) if ip_id else None
    if ip is None and not user.a_la_capacite(CAP_CRIP):
        return HttpResponseForbidden("Seule la CRIP enregistre les informations préoccupantes.")
    if ip is not None and not ip.peut_modifier_crip(user):
        return HttpResponseForbidden("Cette IP n'est plus modifiable par la CRIP.")
    form = IPForm(request.POST or None, instance=ip,
                  initial=None if ip else {'date_reception_crip': timezone.localdate()})
    formset = EnfantFormSet(request.POST or None, instance=ip or InformationPreoccupante(), prefix='enfants')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            nouvelle = ip is None
            ip = form.save(commit=False)
            if nouvelle:
                ip.recue_par = ip.cree_par = user
            ip.save()
            form.save_m2m()
            formset.instance = ip
            formset.save()
            famille.completer_depuis_dossier(ip)
            circuit.journal(ip, user, "IP enregistrée par la CRIP" if nouvelle else "IP modifiée par la CRIP")
            for c in famille.synchroniser_territoires(ip, user):
                messages.info(request, c)
        messages.success(request, f"IP {ip.numero} enregistrée. Vérifiez la composition familiale (adultes, « vit chez »).")
        return redirect('protection_enfance:ip_famille', ip_id=ip.numero)
    return render(request, 'protection_enfance/ip_form.html', {'form': form, 'formset': formset, 'ip': ip})


@login_required
def ip_detail(request, ip_id):
    ip = get_ip(request, ip_id)
    user = request.user
    if not ip.peut_voir(user):
        return _refus()
    rapport = getattr(ip, 'rapport', None)
    professionnels = _professionnels(ip)
    actions = list(ip.actions.select_related('enfant', 'auteur', 'creneau', 'destinataire')
                   .prefetch_related('participants', 'convoques__adulte', 'convoques__enfant', 'enfants_concernes'))
    for a in actions:
        a.relances = convocations.a_relancer(a) if a.est_audition and a.convoques.all() else []
    codes = [c for c, _ in STATUTS]
    rang = codes.index(ip.statut)
    etapes = [(c, l, 'fait' if i < rang or ip.statut == 'CLOTUREE' else 'actuel' if i == rang else 'avenir')
              for i, (c, l) in enumerate(STATUTS)]
    ctx = {
        'ip': ip, 'rapport': rapport, 'etapes': etapes, 'resultats': RESULTATS,
        'enfants': ip.enfants.select_related('beneficiaire', 'heberge_par').prefetch_related('dangers_constates'),
        'actions': actions,
        'adultes': ip.adultes.select_related('mds', 'beneficiaire'),
        'peut_composer': peut_composer(ip, user),
        'presences': PRESENCES,
        'audition_form': AuditionForm(ip=ip, professionnels=professionnels, prefix='aud',
                                      initial={'participants': [u.pk for u in ip.binome] or [user.pk]}),
        'saisines': ip.saisines.select_related('propose_par', 'cadre', 'inspecteur'),
        'historique': ip.historique_actions.select_related('user')[:40],
        'pieces': _pieces(ip),
        'voit_declarant': ip.voit_declarant(user),
        'peut_piloter': ip.peut_piloter(user), 'est_binome': ip.est_binome(user),
        'peut_evaluer': ip.peut_evaluer(user), 'peut_modifier_crip': ip.peut_modifier_crip(user),
        'est_crip': user.a_la_capacite(CAP_CRIP), 'est_pief': user.a_la_capacite(CAP_PIEF),
        'action_form': ActionForm(ip=ip, professionnels=professionnels,
                                  initial={'date': timezone.localtime().replace(second=0, microsecond=0),
                                           'participants': [u.pk for u in ip.binome] or [user.pk]}),
        'saisine_form': SaisineForm(),
        'peut_proposer_saisine': ip.statut in ('TRANSMISE_MDS', 'EN_EVALUATION', 'SYNTHESE')
                                 and (ip.est_binome(user) or ip.peut_piloter(user)),
    }
    if ctx['peut_piloter'] and ip.statut in ('TRANSMISE_MDS', 'EN_EVALUATION'):
        prop = circuit.proposer_binome(ip)
        candidats = [u for u, _ in prop['ts']] + [u for u, _ in prop['pmi']]
        init = {'referent_1': (ip.binome_1 or (prop['proposition'][0] if prop['proposition'] else None)),
                'referent_2': (ip.binome_2 or (prop['proposition'][1] if len(prop['proposition']) > 1 else None))}
        ctx.update(proposition=prop, binome_form=BinomeForm(candidats=candidats, initial=init))
    return render(request, 'protection_enfance/ip_detail.html', ctx)


def _professionnels(ip):
    """Professionnels de la MDS (et MDS associées) pouvant participer aux démarches et réunions."""
    from core.models import User
    mds = [m for m in [ip.mds] + list(ip.mds_partage.all()) if m]
    return list(User.objects.filter(is_active=True, profils_mds__mds__in=mds, profils_mds__actif=True)
                .distinct().order_by('last_name', 'first_name'))


def _pieces(ip):
    from django.contrib.contenttypes.models import ContentType
    from ged.models import DocumentGED
    return DocumentGED.objects.filter(content_type=ContentType.objects.get_for_model(ip), object_id=ip.pk)\
        .select_related('uploaded_by').order_by('-id')


@login_required
@require_POST
def ip_transmettre(request, ip_id):
    ip = get_ip(request, ip_id)
    if not request.user.a_la_capacite(CAP_CRIP):
        return _refus()
    try:
        circuit.transmettre_mds(ip, request.user)
        messages.success(request, f"IP transmise à {ip.mds} : le cadre est prévenu.")
    except CircuitError as e:
        messages.error(request, str(e))
    return redirect('protection_enfance:ip_detail', ip_id=ip.numero)


@login_required
@require_POST
def ip_binome(request, ip_id):
    ip = get_ip(request, ip_id)
    if not ip.peut_piloter(request.user):
        return _refus()
    prop = circuit.proposer_binome(ip)
    form = BinomeForm(request.POST, candidats=[u for u, _ in prop['ts']] + [u for u, _ in prop['pmi']])
    if not form.is_valid():
        messages.error(request, "Choisissez deux professionnels de la MDS.")
    else:
        try:
            circuit.designer_binome(ip, form.cleaned_data['referent_1'], form.cleaned_data['referent_2'],
                                    request.user)
            messages.success(request, "Binôme validé : les deux professionnels sont prévenus.")
        except CircuitError as e:
            messages.error(request, str(e))
    return redirect('protection_enfance:ip_detail', ip_id=ip.numero)


@login_required
@require_POST
def ip_piece(request, ip_id):
    """Pièce jointe à l'IP (AR de la LRAR, écrit d'un partenaire, document signé…) : GED, accès restreint."""
    ip = get_ip(request, ip_id)
    user = request.user
    if not (ip.est_binome(user) or ip.peut_piloter(user) or user.a_la_capacite(CAP_CRIP)
            or user.a_la_capacite(CAP_PIEF)):
        return _refus()
    fichier = request.FILES.get('fichier')
    titre = (request.POST.get('titre') or '').strip()[:200]
    if not fichier or not titre:
        messages.error(request, "Indiquez un titre et choisissez un fichier.")
    elif fichier.size > 10 * 1024 * 1024:
        messages.error(request, "Fichier trop volumineux (10 Mo maximum).")
    else:
        from ged.models import DocumentGED, DocumentType
        type_doc, _ = DocumentType.objects.get_or_create(
            code="IP_PIECE", defaults={"nom": "Pièce d'information préoccupante", "categorie": "divers",
                                       "extensions_autorisees": ["pdf", "jpg", "jpeg", "png"],
                                       "taille_max_mb": 10, "est_sensible": True, "actif": True})
        try:
            with transaction.atomic():
                doc = DocumentGED.objects.create(content_object=ip, type_document=type_doc, titre=titre,
                                                 confidentialite="TRES_CONFIDENTIEL", uploaded_by=user)
                doc.add_new_version(buffer=fichier, filename=fichier.name, user=user,
                                    raison=f"IP {ip.numero}", request=request)
            circuit.journal(ip, user, f"Pièce ajoutée : {titre}")
            messages.success(request, "Pièce ajoutée.")
        except Exception:
            messages.error(request, "La pièce n'a pas pu être enregistrée. Réessayez plus tard.")
    return redirect('protection_enfance:ip_detail', ip_id=ip.numero)


def peut_composer(ip, user):
    """Composition familiale : la CRIP avant l'évaluation, puis le cadre et le binôme jusqu'au rapport."""
    return ip.peut_modifier_crip(user) or (
        ip.statut in ('TRANSMISE_MDS', 'EN_EVALUATION') and (ip.est_binome(user) or ip.peut_piloter(user)))


@login_required
def ip_famille(request, ip_id):
    """Adultes concernés (parents séparés, autre MDS, autre département…) et « vit chez » de chaque enfant."""
    ip = get_ip(request, ip_id)
    user = request.user
    if not peut_composer(ip, user):
        return _refus()
    adultes_fs = AdulteFormSet(request.POST or None, instance=ip, prefix='adultes')
    enfants_fs = EnfantFamilleFormSet(request.POST or None, instance=ip, prefix='enfants',
                                      adultes=ip.adultes.all())
    if request.method == 'POST' and adultes_fs.is_valid() and enfants_fs.is_valid():
        with transaction.atomic():
            adultes_fs.save()
            enfants_fs.save()
            # Un seul adulte qui héberge : les enfants sans « vit chez » vivent chez lui
            hebergeants = list(ip.adultes.filter(heberge_enfants=True))
            if len(hebergeants) == 1:
                ip.enfants.filter(heberge_par__isnull=True).update(heberge_par=hebergeants[0])
            circuit.journal(ip, user, "Composition familiale mise à jour",
                            "; ".join(str(a) for a in ip.adultes.all()))
            for c in famille.synchroniser_territoires(ip, user):
                messages.info(request, c)
        messages.success(request, "Composition familiale enregistrée.")
        if request.POST.get('continuer'):
            return redirect('protection_enfance:ip_famille', ip_id=ip.numero)
        return redirect('protection_enfance:ip_detail', ip_id=ip.numero)
    return render(request, 'protection_enfance/ip_famille.html', {
        'ip': ip, 'adultes_fs': adultes_fs, 'enfants_fs': enfants_fs})
