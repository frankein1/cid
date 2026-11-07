# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/views.py
"""Demandes FSL (accès au logement) depuis la fiche usager."""
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from beneficiaire.models import Beneficiaire
from beneficiaire.views import user_peut_agir_sur_beneficiaire

from .models import DemandeFSL, GestionnaireFSL
from .services import circuit, fsl
from .services.fsl_pdf import documents_du_dossier, dossier

MAX_COMPOSITION = 9


def _droits(user, demande):
    b = demande.beneficiaire
    voir = b.niveau_acces(user) == 'complet'
    ecrire = voir and user_peut_agir_sur_beneficiaire(user, b)
    cadre = voir and user.a_la_capacite('peut_valider') and user.a_acces_mds(demande.mds)
    return voir, ecrire, cadre


def _demande(request, pk):
    demande = get_object_or_404(DemandeFSL.objects.select_related('beneficiaire', 'mds', 'gestionnaire'), pk=pk)
    voir, ecrire, cadre = _droits(request.user, demande)
    return demande, voir, ecrire, cadre


@login_required
@require_POST
def fsl_nouvelle(request, code_interne):
    b = get_object_or_404(Beneficiaire.tous.select_related('mds'), code_interne=code_interne)
    if not user_peut_agir_sur_beneficiaire(request.user, b) or b.niveau_acces(request.user) != 'complet':
        return HttpResponseForbidden("Réservé aux agents de la MDS de l'usager.")
    donnees = fsl.preremplir(b, request.user)
    demande = DemandeFSL.objects.create(beneficiaire=b, mds=b.mds, gestionnaire=GestionnaireFSL.pour_code_postal(b.code_postal),
                                        donnees=donnees, cree_par=request.user,
                                        pieces={c: 'MANQUANTE' for c, _, fac in fsl.PIECES if not fac})
    demande.tracer(request.user, "Demande créée", f"préremplie : {donnees.get('origine')}")
    demande.save()
    messages.success(request, "Demande préremplie avec ce que CID connaît : vérifiez chaque rubrique.")
    return redirect('logement:fsl_modifier', pk=demande.pk)


def _lire(post, demande):
    dn = dict(demande.donnees or {})
    for cle in ('num_caf', 'autres_numero', 'bailleur_type', 'adresse_objet', 'cp_commune', 'nouveau_bailleur',
                'contact_bailleur', 'situation_familiale', 'quotient_familial', 'garantie'):
        dn[cle] = (post.get(cle) or '').strip()
    comp = []
    for i in range(MAX_COMPOSITION):
        ligne = {k: (post.get(f'comp_{i}_{k}') or '').strip()
                 for k in ('role', 'nom', 'prenom', 'date_naissance', 'nationalite', 'situation', 'lien')}
        if ligne['nom'] or ligne['prenom']:
            comp.append(ligne)
    if comp and comp[0]['role'] != 'DEMANDEUR':
        comp[0]['role'] = 'DEMANDEUR'
    dn['composition'] = comp
    res, prec = {}, {}
    for code, _, _ in fsl.RESSOURCES_FSL:
        valeurs = {col: str(fsl.d(post.get(f'res_{code}_{col}'))) for col, _ in fsl.COLONNES
                   if fsl.d(post.get(f'res_{code}_{col}'))}
        if valeurs:
            res[code] = valeurs
        if (post.get(f'prec_{code}') or '').strip():
            prec[code] = post.get(f'prec_{code}').strip()[:80]
    dn['ressources'], dn['ressources_precisions'] = res, prec
    dn['logement_anterieur'] = {c: (post.get(f'ant_{c}') or '').strip() for c, _ in fsl.LOGEMENT_ANTERIEUR}
    dn['logement_anterieur']['caution_restituee'] = post.get('ant_caution_restituee', '')
    dn['logement_nouveau'] = {c: (post.get(f'nv_{c}') or '').strip() for c, _ in fsl.LOGEMENT_NOUVEAU}
    dn['logement_nouveau']['chauffage_collectif'] = post.get('nv_chauffage_collectif', '')
    dn['proposition'] = {c: str(fsl.d(post.get(f'prop_{c}'))) for c, _ in fsl.PROPOSITION if fsl.d(post.get(f'prop_{c}'))}
    dn['equipements'] = [c for c, _ in fsl.EQUIPEMENTS if post.get(f'eq_{c}')]
    dn['ts'] = {k: (post.get(f'ts_{k}') or '').strip()
                for k in ('nom', 'prenom', 'qualite', 'telephone', 'portable', 'email', 'organisme')}
    demande.donnees = dn
    demande.avis = post.get('avis', '') if post.get('avis') in dict(DemandeFSL.AVIS) else ''
    demande.avis_motive = (post.get('avis_motive') or '').strip()
    demande.proposition_pret = fsl.d(post.get('proposition_pret')) or None
    demande.proposition_subvention = fsl.d(post.get('proposition_subvention')) or None
    demande.pieces = {c: post.get(f'piece_{c}') for c, _, _ in fsl.PIECES
                      if post.get(f'piece_{c}') in ('FOURNIE', 'MANQUANTE', 'SANS_OBJET')}
    g = post.get('gestionnaire')
    if g:
        demande.gestionnaire = GestionnaireFSL.objects.filter(pk=g, actif=True).first() or demande.gestionnaire


@login_required
def fsl_modifier(request, pk):
    demande, voir, ecrire, _ = _demande(request, pk)
    if not ecrire:
        return HttpResponseForbidden("Modification réservée aux agents de la MDS de l'usager.")
    if not demande.modifiable:
        messages.info(request, "La demande n'est plus modifiable dans son état actuel.")
        return redirect('logement:fsl_detail', pk=pk)
    if request.method == 'POST':
        _lire(request.POST, demande)
        demande.tracer(request.user, "Demande modifiée")
        demande.save()
        messages.success(request, "Demande enregistrée.")
        return redirect('logement:fsl_detail', pk=pk)
    dn = demande.donnees or {}
    comp = list(dn.get('composition') or []) + [{}] * MAX_COMPOSITION
    res = dn.get('ressources') or {}
    prec = dn.get('ressources_precisions') or {}
    attendues = {c for c, _, _ in fsl.pieces_attendues(demande)}
    return render(request, 'logement/fsl_form.html', {
        'demande': demande, 'b': demande.beneficiaire, 'dn': dn,
        'composition': list(enumerate(comp[:MAX_COMPOSITION])), 'roles': fsl.ROLES,
        'ressources': [(code, libelle, [(col, (res.get(code) or {}).get(col, '')) for col, _ in fsl.COLONNES],
                        prec.get(code, '')) for code, libelle, _ in fsl.RESSOURCES_FSL],
        'colonnes': fsl.COLONNES, 'situations': fsl.SITUATIONS_FAMILIALES, 'garanties': fsl.GARANTIES,
        'anterieur': [(c, l, (dn.get('logement_anterieur') or {}).get(c, '')) for c, l in fsl.LOGEMENT_ANTERIEUR],
        'nouveau': [(c, l, (dn.get('logement_nouveau') or {}).get(c, '')) for c, l in fsl.LOGEMENT_NOUVEAU],
        'proposition': [(c, l, (dn.get('proposition') or {}).get(c, '')) for c, l in fsl.PROPOSITION],
        'equipements': [(c, l, c in (dn.get('equipements') or [])) for c, l in fsl.EQUIPEMENTS],
        'pieces': [(c, l, (demande.pieces or {}).get(c, 'MANQUANTE' if c in attendues else 'SANS_OBJET'), c in attendues)
                   for c, l, _ in fsl.PIECES],
        'etats_piece': fsl.ETATS_PIECE, 'gestionnaires': GestionnaireFSL.objects.filter(actif=True),
        'ts': dn.get('ts') or {},
    })


@login_required
def fsl_detail(request, pk):
    demande, voir, ecrire, cadre = _demande(request, pk)
    if not voir:
        return HttpResponseForbidden("Dossier complet de la MDS de l'usager.")
    from .models import FormulaireOfficiel
    trame = {FormulaireOfficiel.FORMULAIRE_ACCES, FormulaireOfficiel.AVIS_MOTIVE, FormulaireOfficiel.ARGUMENTAIRE,
             FormulaireOfficiel.LISTE_PIECES}
    docs = [(dict(FormulaireOfficiel.CODES)[c], r,
             'officiel' if FormulaireOfficiel.pour(c, demande.gestionnaire) else ('trame' if c in trame else 'vierge'))
            for c, r in documents_du_dossier(demande)]
    dn = demande.donnees or {}
    par_col, total = fsl.totaux_ressources(dn.get('ressources'))
    return render(request, 'logement/fsl_detail.html', {
        'demande': demande, 'b': demande.beneficiaire, 'dn': dn, 'peut_ecrire': ecrire, 'est_cadre': cadre,
        'alertes': fsl.alertes(demande), 'documents': docs, 'total_ressources': total,
        'taux_effort': fsl.taux_effort(dn), 'total_propose': demande.total_propose,
        'pieces_manquantes': [l for c, l, _ in fsl.PIECES if c in demande.pieces_manquantes],
        'statuts_reponse': [(DemandeFSL.ACCORDEE, "Accordée"), (DemandeFSL.AJOURNEE, "Ajournée (pièces demandées)"),
                            (DemandeFSL.REFUSEE, "Refusée")],
    })


@login_required
def fsl_pdf(request, pk):
    demande, voir, _, _ = _demande(request, pk)
    if not voir:
        return HttpResponseForbidden("Dossier complet de la MDS de l'usager.")
    pdf, _ = dossier(demande)
    rep = HttpResponse(pdf, content_type='application/pdf')
    rep['Content-Disposition'] = f'inline; filename="FSL_acces_{demande.beneficiaire.code_interne}_{demande.pk}.pdf"'
    return rep


def _date(valeur):
    try:
        return datetime.strptime(valeur, '%Y-%m-%d').date() if valeur else None
    except ValueError:
        return None


@login_required
@require_POST
def fsl_action(request, pk):
    demande, voir, ecrire, cadre = _demande(request, pk)
    action = request.POST.get('action')
    p = request.POST
    try:
        if action == 'demander_cadre' and ecrire:
            circuit.demander_avis_cadre(demande, request.user)
            messages.success(request, "Le cadre est prévenu : il rédigera la note explicative.")
        elif action in ('cadre_accepte', 'cadre_renvoie') and cadre:
            circuit.avis_cadre(demande, request.user, action == 'cadre_accepte', p.get('note_cadre'))
            messages.success(request, "Avis enregistré : l'agent est prévenu.")
        elif action == 'envoyer' and ecrire:
            circuit.envoyer(demande, request.user, _date(p.get('date_envoi')))
            messages.success(request, "Envoi enregistré.")
        elif action == 'reponse' and ecrire:
            circuit.enregistrer_reponse(demande, request.user, p.get('issue'), _date(p.get('date_decision')),
                                        fsl.d(p.get('pret')) or None, fsl.d(p.get('subvention')) or None,
                                        (p.get('garantie') or '').strip()[:60], (p.get('commentaire') or '').strip())
            messages.success(request, "Réponse du FSL enregistrée.")
        elif action == 'abandonner' and ecrire:
            circuit.abandonner(demande, request.user, p.get('motif', ''))
            messages.success(request, "Demande abandonnée.")
        else:
            return HttpResponseForbidden("Action non autorisée.")
    except circuit.CircuitError as e:
        messages.error(request, str(e))
    return redirect('logement:fsl_detail', pk=pk)
