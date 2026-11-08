# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/views/v_copp.py
"""Demande de logement social (NUD, DALO, mutation, Al'In) et saisine de la commission des publics prioritaires."""
from datetime import datetime
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from beneficiaire.models import Beneficiaire
from beneficiaire.views import user_peut_agir_sur_beneficiaire

from ..models import (ETATS_ALIN, ETATS_DOSSIER, CommissionPublicsPrioritaires, DemandeLogementSocial,
                      SaisineCOPP)
from ..services import copp

# Pièces ajoutées depuis la saisine : type de document de la GED (créé au besoin)
TYPES_PIECE = [('CI', "Identité", 'identite'), ('LOG_SITFAM', "Situation familiale", 'administratif'),
               ('LOG_SITPRO', "Situation professionnelle", 'social'), ('LOG_RESS', "Ressources", 'finances'),
               ('AVIS_IMPOT', "Avis d'imposition", 'finances'), ('LOG_LOGT', "Logement (bail, quittance…)", 'logement'),
               ('LOG_DALO', "DALO, demande de logement", 'logement'), ('AUTRE', "Autre", 'divers')]


def _usager(request, code_interne, ecriture=True):
    b = get_object_or_404(Beneficiaire.tous.select_related('mds'), code_interne=code_interne)
    if b.niveau_acces(request.user) != 'complet' or (ecriture and not user_peut_agir_sur_beneficiaire(request.user, b)):
        return b, HttpResponseForbidden("Réservé aux agents de la MDS de l'usager.")
    return b, None


def _date(v):
    for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(v, fmt).date()
        except (TypeError, ValueError):
            continue
    return None


# ---------------------------------------------------------------------------------------------------------------
@login_required
def logement_social(request, code_interne):
    b, refus = _usager(request, code_interne)
    if refus:
        return refus
    dl, _ = DemandeLogementSocial.objects.get_or_create(beneficiaire=b)
    if request.method == 'POST':
        p = request.POST
        dl.nud = (p.get('nud') or '').strip()[:30]
        for champ in ('date_creation', 'date_renouvellement', 'dalo_date', 'mutation_date', 'alin_date'):
            setattr(dl, champ, _date(p.get(champ)))
        dl.dalo_depose, dl.mutation_deposee, dl.alin_inscrit = (bool(p.get('dalo_depose')), bool(p.get('mutation_deposee')),
                                                                bool(p.get('alin_inscrit')))
        dl.dalo_etat = p.get('dalo_etat') if p.get('dalo_etat') in dict(ETATS_DOSSIER) else ''
        dl.mutation_etat = p.get('mutation_etat') if p.get('mutation_etat') in dict(ETATS_DOSSIER) else ''
        dl.alin_etat = p.get('alin_etat') if p.get('alin_etat') in dict(ETATS_ALIN) else ''
        dl.communes_souhaitees = [c.strip() for c in p.getlist('communes') if c.strip()][:6]
        dl.typologie_souhaitee = (p.get('typologie_souhaitee') or '').strip()[:20]
        dl.etage_souhaite = (p.get('etage_souhaite') or '').strip()[:30]
        dl.pmr = bool(p.get('pmr'))
        dl.precisions = (p.get('precisions') or '').strip()
        dl.save()
        messages.success(request, "Demande de logement enregistrée.")
        return redirect('beneficiaire:detail_beneficiaire', code_interne=b.code_interne)
    communes = list(dl.communes_souhaitees) + [''] * (6 - len(dl.communes_souhaitees))
    return render(request, 'logement/logement_social_form.html', {
        'b': b, 'dl': dl, 'communes': communes, 'etats': ETATS_DOSSIER, 'etats_alin': ETATS_ALIN})


# ---------------------------------------------------------------------------------------------------------------
def _saisine(request, pk):
    s = get_object_or_404(SaisineCOPP.objects.select_related('beneficiaire', 'mds', 'commission'), pk=pk)
    voir = s.beneficiaire.niveau_acces(request.user) == 'complet'
    ecrire = voir and user_peut_agir_sur_beneficiaire(request.user, s.beneficiaire)
    return s, voir, ecrire


@login_required
@require_POST
def copp_nouvelle(request, code_interne):
    b, refus = _usager(request, code_interne)
    if refus:
        return refus
    s = SaisineCOPP.objects.create(beneficiaire=b, mds=b.mds, donnees=copp.preremplir(b, request.user),
                                   commission=CommissionPublicsPrioritaires.prochaine(b.mds), cree_par=request.user)
    s.tracer(request.user, "Saisine créée", f"préremplie : {s.donnees.get('origine')}")
    s.save()
    messages.success(request, "Fiche de saisine préremplie : vérifiez chaque rubrique, puis rédigez le rapport social.")
    return redirect('logement:copp_modifier', pk=s.pk)


CHAMPS_TEXTE = ['date_saisie', 'nud', 'date_creation_nud', 'anciennete', 'situation_famille', 'garcons', 'filles',
                'annees_garcons', 'annees_filles', 'modalites_garde', 'naissance_attendue', 'logement_actuel', 'adresse',
                'typologie', 'loyer', 'charges', 'apl', 'bailleur', 'taux_effort', 'reste_a_vivre',
                'nature_ressources_demandeur', 'montant_ressources_demandeur', 'nature_ressources_conjoint',
                'montant_ressources_conjoint', 'rfr_n1_demandeur', 'rfr_n2_demandeur', 'rfr_n1_conjoint',
                'rfr_n2_conjoint', 'plafonds_ressources', 'endettement', 'montant_dettes', 'demarches_dettes',
                'typologie_souhaitee', 'etage', 'pmr', 'precisions', 'mesure_accompagnement']


def _deposer_pieces(request, s):
    """Pièces ajoutées depuis la saisine : déposées dans la GED de l'usager, puis jointes à la saisine."""
    from ged.models import DocumentGED, DocumentType
    from ged.validation import erreurs_fichier
    types = {c: (lib, cat) for c, lib, cat in TYPES_PIECE}
    for i, f in enumerate(request.FILES.getlist('nouvelles_pieces')):
        code = request.POST.getlist('type_piece')[i] if i < len(request.POST.getlist('type_piece')) else 'AUTRE'
        lib, cat = types.get(code, types['AUTRE'])
        type_doc, _ = DocumentType.objects.get_or_create(code=code, defaults={'nom': lib, 'categorie': cat})
        erreurs = erreurs_fichier(f, type_doc)
        if erreurs:
            messages.error(request, f"{f.name} : {' '.join(erreurs)}")
            continue
        buf = BytesIO(f.read())
        buf.name = f.name
        doc = DocumentGED.create_from_buffer(buffer=buf, filename=f.name, content_object=s.beneficiaire,
                                             type_document=type_doc, user=request.user, confidentialite='RESTREINT',
                                             raison="Pièce de la saisine de la commission des publics prioritaires",
                                             request=request)
        s.pieces.add(doc)
        s.tracer(request.user, "Pièce ajoutée", f"{lib} : {f.name}")


@login_required
def copp_modifier(request, pk):
    s, voir, ecrire = _saisine(request, pk)
    if not ecrire:
        return HttpResponseForbidden("Réservé aux agents de la MDS de l'usager.")
    if not s.modifiable:
        return redirect('logement:copp_detail', pk=pk)
    from .v_envoi import _documents_usager
    docs = _documents_usager(s.beneficiaire, request.user)
    if request.method == 'POST':
        p = request.POST
        dn = dict(s.donnees or {})
        for c in CHAMPS_TEXTE:
            if c in p:
                dn[c] = (p.get(c) or '').strip()
        dn['referent'] = {k: (p.get(f'ref_{k}') or '').strip() for k in ('nom', 'telephone', 'courriel', 'structure')}
        for qui in ('demandeur', 'conjoint'):
            dn[qui] = {k: (p.get(f'{qui}_{k}') or '').strip()
                       for k in ('nom', 'prenom', 'date_naissance', 'telephone', 'courriel', 'nir')}
        for bloc in ('dalo', 'mutation', 'alin'):
            dn[bloc] = {k: (p.get(f'{bloc}_{k}') or '').strip() for k in ('depose', 'date', 'etat')}
        dn['communes'] = [c.strip() for c in p.getlist('communes') if c.strip()][:6]
        s.donnees = dn
        s.motifs = [m for m, _ in SaisineCOPP.MOTIFS if p.get(f'motif_{m}')]
        s.motif_autre = (p.get('motif_autre') or '').strip()[:200]
        s.rapport_social = (p.get('rapport_social') or '').strip()
        c = p.get('commission')
        s.commission = CommissionPublicsPrioritaires.objects.filter(pk=c).first() if c and c.isdigit() else None
        ids = {int(x) for x in p.getlist('pieces') if x.isdigit()}
        s.pieces.set([d for d in docs if d.pk in ids])
        _deposer_pieces(request, s)
        s.tracer(request.user, "Saisine modifiée")
        s.save()
        messages.success(request, "Saisine enregistrée.")
        return redirect('logement:copp_detail', pk=pk)
    dn = s.donnees or {}
    communes = list(dn.get('communes') or []) + [''] * (6 - len(dn.get('communes') or []))
    return render(request, 'logement/copp_form.html', {
        's': s, 'b': s.beneficiaire, 'dn': dn, 'communes': communes[:6], 'motifs': SaisineCOPP.MOTIFS,
        'situations': copp.SITUATIONS_FAMILLE, 'logements': copp.SITUATIONS_LOGEMENT_COPP,
        'mesures': copp.MESURES_ACCOMPAGNEMENT, 'etats': ETATS_DOSSIER, 'etats_alin': ETATS_ALIN,
        'commissions': CommissionPublicsPrioritaires.objects.filter(mds=s.mds, date__gte=timezone.localdate()),
        'docs': docs, 'joints': set(s.pieces.values_list('pk', flat=True)), 'types_piece': TYPES_PIECE,
    })


@login_required
def copp_detail(request, pk):
    s, voir, ecrire = _saisine(request, pk)
    if not voir:
        return HttpResponseForbidden("Dossier complet de la MDS de l'usager.")
    j = timezone.localdate()
    alerte = None
    if s.statut == s.BROUILLON and s.commission:
        restant = (s.commission.date_limite_depot - j).days
        if restant < 0:
            alerte = "La date limite de dépôt de cette séance est passée : choisissez la séance suivante."
        elif restant <= 7:
            alerte = f"Date limite de dépôt dans {restant} jour{'s' if restant > 1 else ''} ({s.commission.date_limite_depot:%d/%m/%Y})."
    return render(request, 'logement/copp_detail.html', {
        's': s, 'b': s.beneficiaire, 'dn': s.donnees or {}, 'peut_ecrire': ecrire, 'alerte': alerte,
        'pieces': s.pieces.all(), 'imprimer': request.GET.get('imprimer'),
    })


@login_required
def copp_pdf(request, pk):
    s, voir, _ = _saisine(request, pk)
    if not voir:
        return HttpResponseForbidden("Dossier complet de la MDS de l'usager.")
    pdf, _ = copp.dossier(s)
    rep = HttpResponse(pdf, content_type='application/pdf')
    rep['Content-Disposition'] = f'inline; filename="COPP_{s.beneficiaire.code_interne}_{s.pk}.pdf"'
    return rep


@login_required
@require_POST
def copp_action(request, pk):
    s, voir, ecrire = _saisine(request, pk)
    if not ecrire:
        return HttpResponseForbidden("Réservé aux agents de la MDS de l'usager.")
    action = request.POST.get('action')
    if action == 'decision' and s.statut == s.ENVOYEE:
        s.decision = (request.POST.get('decision') or '').strip()
        s.date_decision = _date(request.POST.get('date_decision')) or (s.commission.date if s.commission else j())
        s.statut = s.EXAMINEE
        s.tracer(request.user, "Décision ou préconisation de la commission enregistrée", s.decision[:200])
        s.save()
        messages.success(request, "Décision enregistrée.")
    elif action == 'abandonner' and s.statut in (s.BROUILLON, s.ENVOYEE):
        s.statut = s.ABANDONNEE
        s.tracer(request.user, "Abandonnée", (request.POST.get('motif') or '')[:200])
        s.save()
        messages.success(request, "Saisine abandonnée.")
    else:
        messages.error(request, "Action impossible dans l'état actuel de la saisine.")
    return redirect('logement:copp_detail', pk=pk)


def j():
    return timezone.localdate()
