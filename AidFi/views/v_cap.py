# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/views/v_cap.py
"""
CAP - chèques service (alimentation, hygiène).

Circuit : l'AS demande → le cadre (ou adjoint, secrétaire générale) décide →
le cadre remet les chèques à l'AS (scan des numéros) → feuille de remise PDF
signée (cadre, AS, usager) → l'AS ou le cadre scanne la feuille signée : clôture.
Cas exceptionnel : remise par la paierie départementale (régisseur central).

Stock : le régisseur de la MDS saisit chaque arrivage à la douchette.
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from beneficiaire.models import Beneficiaire
from mds.models import MDS, UserMDSProfile
from AidFi.forms.f_cap import (
    DemandeCAPForm, DecisionCAPForm, ReceptionCAPForm, ClotureCAPForm,
)
from AidFi.models.m_generique import TypeAide
from AidFi.models.m_cap import DemandeCAP, ReceptionCAP, TitreCAP, InventaireCAP, VALEURS_CAP, est_regisseur
from AidFi.services import cap as svc

logger = logging.getLogger(__name__)

CAP_VALIDER = 'peut_valider_cheque_aidfi'   # cadre, adjoints, secrétaire générale


# =============================================================================
# OUTILS DE DROITS
# =============================================================================

def _peut_decider(user, demande):
    return user.peut_agir_sur_objet(demande, CAP_VALIDER)


def _peut_voir(user, demande):
    if user.peut_agir_sur_objet(demande, 'peut_voir') or _peut_decider(user, demande):
        return True
    if demande.remise_paierie and user.a_la_capacite('cap_regie_centrale'):
        return True
    return est_regisseur(user, demande.mds)


def _peut_cloturer(user, demande):
    if demande.statut != 'REMISE' or demande.remise_paierie:
        return False   # une remise par la paierie est clôturée par le régisseur de la paierie
    if user.pk in (demande.cree_par_id, demande.remis_a_id) or _peut_decider(user, demande):
        return True
    return demande.remise_paierie and user.a_la_capacite('cap_regie_centrale')


def _peut_voir_coffre(user, mds):
    return est_regisseur(user, mds) or (user.a_la_capacite(CAP_VALIDER) and user.a_acces_mds(mds))


def _agents_mds(mds):
    """Agents rattachés à la MDS pouvant recevoir des chèques pour un usager (AS, cadres)."""
    from core.models import User
    ids = UserMDSProfile.objects.filter(mds=mds, actif=True).values_list('user_id', flat=True)
    return User.objects.filter(pk__in=ids, is_active=True,
                               profils__capacites__code='peut_instruire').distinct().order_by('last_name')


# =============================================================================
# DEMANDE (AS)
# =============================================================================

@login_required
def cap_creer(request, beneficiaire_id):
    beneficiaire = get_object_or_404(Beneficiaire, pk=beneficiaire_id)
    if not request.user.peut_agir_sur_objet(beneficiaire, 'peut_instruire'):
        return HttpResponseForbidden("Seul un(e) assistant(e) social(e) de la MDS de l'usager peut demander des CAP.")

    if request.method == "POST":
        form = DemandeCAPForm(request.POST)
        if form.is_valid():
            type_cap, _ = TypeAide.objects.get_or_create(
                code='CAP',
                defaults={'nom': "Chèques service (CAP)",
                          'description': "Chèques d'accompagnement personnalisé - alimentation, hygiène",
                          'actif': True, 'cree_par': request.user})
            demande = DemandeCAP(
                beneficiaire=beneficiaire, demandeur=beneficiaire, type_aide=type_cap,
                montant_sollicite=form.cleaned_data['montant'],
                motivation=form.cleaned_data['motivation'],
                remise_paierie=form.cleaned_data['remise_paierie'],
                statut='DEPOSEE', cree_par=request.user,
            )
            demande._acteur = request.user      # journal + message au cadre
            demande.save()
            messages.success(request, "Demande de chèques service transmise au cadre.")
            return redirect("AidFi:cap_detail", demande_id=demande.pk)
    else:
        form = DemandeCAPForm()
    return render(request, "AidFi/cap_form.html", {"form": form, "beneficiaire": beneficiaire})


# =============================================================================
# FICHE DE LA DEMANDE (toutes les étapes)
# =============================================================================

def _render_detail(request, demande, **extra):
    user = request.user
    peut_decider = _peut_decider(user, demande)
    ctx = {
        "demande": demande,
        "beneficiaire": demande.beneficiaire,
        "suivis": demande.suivis.order_by('id'),
        "titres": demande.titres.order_by('valeur', 'numero'),
        "can_decider": peut_decider and demande.statut == 'DEPOSEE',
        "can_remettre": peut_decider and demande.statut == 'ACCORDEE',
        # La paierie remet ET clôture (y compris un ancien dossier resté « remis »)
        "can_remise_paierie": (demande.remise_paierie and demande.statut in ('TRANSMISE_PAIERIE', 'REMISE')
                               and user.a_la_capacite('cap_regie_centrale')),
        "can_cloturer": _peut_cloturer(user, demande),
        "can_feuille": demande.statut in ('REMISE', 'CLOTUREE'),
        "decision_form": DecisionCAPForm(initial={'decision': 'ACCORD',
                                                  'montant_accorde': demande.montant_sollicite}),
        "cloture_form": ClotureCAPForm(),
    }
    if demande.mds and peut_decider and demande.statut in ('DEPOSEE', 'ACCORDEE') and not demande.remise_paierie:
        montant = demande.montant_accorde or int(demande.montant_sollicite or 0)
        ctx["stock"] = svc.etat_stock(demande.mds)
        ctx["proposition"] = svc.proposer_composition(demande.mds, montant)
        ctx["agents"] = _agents_mds(demande.mds)
    ctx.update(extra)
    return render(request, "AidFi/cap_detail.html", ctx)


@login_required
def cap_detail(request, demande_id):
    demande = get_object_or_404(DemandeCAP.objects.select_related('beneficiaire__mds'), pk=demande_id)
    if not _peut_voir(request.user, demande):
        return HttpResponseForbidden("Accès refusé")
    return _render_detail(request, demande)


# =============================================================================
# DÉCISION (cadre, adjoint, secrétaire générale)
# =============================================================================

@login_required
@require_POST
def cap_decision(request, demande_id):
    demande = get_object_or_404(DemandeCAP, pk=demande_id)
    if not _peut_decider(request.user, demande):
        return HttpResponseForbidden("Accès refusé")
    if demande.statut != 'DEPOSEE':
        messages.error(request, "Cette demande n'est pas en attente de décision.")
        return redirect("AidFi:cap_detail", demande_id=demande.pk)

    form = DecisionCAPForm(request.POST)
    if not form.is_valid():
        return _render_detail(request, demande, decision_form=form)

    demande.decide_par = request.user
    demande.date_decision = timezone.now()
    if form.cleaned_data['decision'] == 'ACCORD':
        demande.montant_accorde = form.cleaned_data['montant_accorde']
        demande.statut = 'TRANSMISE_PAIERIE' if demande.remise_paierie else 'ACCORDEE'
    else:
        demande.motif_refus = form.cleaned_data['motif_refus']
        demande.statut = 'REFUSEE'
    demande._acteur = request.user      # journal + message à l'AS (+ régisseur central)
    demande.save()

    if demande.statut == 'ACCORDEE' and not svc.proposer_composition(demande.mds, demande.montant_accorde):
        messages.warning(request, "Demande accordée, mais le coffre ne permet pas actuellement de composer ce montant.")
    else:
        messages.success(request, f"Décision enregistrée : {demande.get_statut_display()}.")
    return redirect("AidFi:cap_detail", demande_id=demande.pk)


# =============================================================================
# REMISE DES CHÈQUES
# =============================================================================

@login_required
@require_POST
def cap_remise(request, demande_id):
    demande = get_object_or_404(DemandeCAP, pk=demande_id)
    if not _peut_decider(request.user, demande):
        return HttpResponseForbidden("Accès refusé")

    numeros = svc.lire_numeros(request.POST.get("numeros"))
    agents = _agents_mds(demande.mds)
    receveur = agents.filter(pk=request.POST.get("remis_a")).first() or demande.cree_par
    erreurs = svc.enregistrer_remise(demande, numeros, request.user, receveur)
    if erreurs:
        for e in erreurs:
            messages.error(request, e)
        return _render_detail(request, demande, numeros_saisis="\n".join(numeros), remis_a_id=receveur and receveur.pk)
    messages.success(request, "Remise enregistrée. Imprimez la feuille de remise pour les signatures.")
    return redirect("AidFi:cap_detail", demande_id=demande.pk)


@login_required
@require_POST
def cap_remise_paierie(request, demande_id):
    demande = get_object_or_404(DemandeCAP, pk=demande_id)
    if (not request.user.a_la_capacite('cap_regie_centrale') or not demande.remise_paierie
            or demande.statut not in ('TRANSMISE_PAIERIE', 'REMISE')):
        return HttpResponseForbidden("Accès refusé")
    svc.enregistrer_remise_paierie(demande, request.POST.get("numeros"), request.user)
    messages.success(request, "Remise enregistrée et dossier clôturé : l'AS et le cadre sont prévenus.")
    return redirect("AidFi:cap_detail", demande_id=demande.pk)


@login_required
def cap_feuille_pdf(request, demande_id):
    demande = get_object_or_404(DemandeCAP, pk=demande_id)
    if not _peut_voir(request.user, demande) or demande.statut not in ('REMISE', 'CLOTUREE'):
        return HttpResponseForbidden("Accès refusé")
    return FileResponse(svc.feuille_remise_pdf(demande), as_attachment=False,
                        filename=f"remise_CAP_{demande.beneficiaire.code_interne}_{demande.pk}.pdf", content_type="application/pdf")


@login_required
@require_POST
def cap_cloturer(request, demande_id):
    demande = get_object_or_404(DemandeCAP, pk=demande_id)
    if not _peut_cloturer(request.user, demande):
        return HttpResponseForbidden("Accès refusé")
    form = ClotureCAPForm(request.POST, request.FILES)
    if not form.is_valid():
        return _render_detail(request, demande, cloture_form=form)
    try:
        svc.cloturer(demande, form.cleaned_data['fichier'], request.user, request=request)
    except Exception as e:
        # La cause exacte part dans les journaux Render et s'affiche à l'écran
        logger.exception("Clôture CAP %s : échec du stockage GED", demande.pk)
        messages.error(request, f"La feuille n'a pas pu être stockée dans la GED : {e}")
        return redirect("AidFi:cap_detail", demande_id=demande.pk)
    messages.success(request, "Feuille signée archivée : dossier clôturé.")
    return redirect("AidFi:cap_detail", demande_id=demande.pk)


# =============================================================================
# COFFRE (régisseur de la MDS)
# =============================================================================

@login_required
def cap_coffres(request):
    """Point d'entrée du menu : les coffres que l'utilisateur peut consulter."""
    user = request.user
    if user.a_la_capacite('peut_administrer'):
        mds_list = MDS.objects.all()
    else:
        ids = UserMDSProfile.objects.filter(user=user, actif=True).values_list('mds_id', flat=True)
        mds_list = MDS.objects.filter(pk__in=ids) | MDS.objects.filter(regisseur=user)
    mds_list = [m for m in mds_list.distinct().order_by('nom') if _peut_voir_coffre(user, m)]
    if len(mds_list) == 1:
        return redirect("AidFi:cap_coffre", mds_id=mds_list[0].pk)
    return render(request, "AidFi/cap_coffres.html", {"mds_list": mds_list})


@login_required
def cap_coffre(request, mds_id):
    mds = get_object_or_404(MDS, pk=mds_id)
    user = request.user
    if not _peut_voir_coffre(user, mds):
        return HttpResponseForbidden("Accès refusé")

    titres = TitreCAP.objects.filter(mds=mds).select_related(
        'demande__beneficiaire', 'remis_par', 'remis_a', 'incident_par')
    q = request.GET.get("q", "").strip()
    statut = request.GET.get("statut", "EN_STOCK")
    if q:
        titres = titres.filter(numero__icontains=q)
    elif statut:
        titres = titres.filter(statut=statut)

    return render(request, "AidFi/cap_coffre.html", {
        "mds": mds,
        "etat": svc.etat_stock(mds),
        "receptions": mds.receptions_cap.all()[:12],
        "titres": titres.order_by('date_validite', 'valeur', 'numero')[:300],
        "q": q, "statut": statut, "statuts": TitreCAP.STATUTS,
        "a_remettre": DemandeCAP.objects.filter(beneficiaire__mds=mds, statut='ACCORDEE')
                                        .select_related('beneficiaire'),
        "est_regisseur": est_regisseur(user, mds),
        "inventaires": mds.inventaires_cap.all()[:6] if est_regisseur(user, mds) else [],
        "peut_designer": mds.peut_etre_modifiee_par(user),
        "candidats_regisseur": [p.user for p in UserMDSProfile.objects.filter(mds=mds, actif=True)
                                .select_related('user').order_by('user__last_name')],
        "aujourdhui": timezone.localdate(),
    })


@login_required
@require_POST
def cap_designer_regisseur(request, mds_id):
    mds = get_object_or_404(MDS, pk=mds_id)
    if not mds.peut_etre_modifiee_par(request.user):
        return HttpResponseForbidden("Désignation réservée à la direction de la MDS.")
    ids = UserMDSProfile.objects.filter(mds=mds, actif=True).values_list('user_id', flat=True)
    from core.models import User
    mds.regisseur = User.objects.filter(pk=request.POST.get("regisseur"), pk__in=ids).first()
    mds.save(update_fields=['regisseur'])
    messages.success(request, f"Régisseur : {mds.regisseur.get_full_name() if mds.regisseur else 'aucun'}.")
    return redirect("AidFi:cap_coffre", mds_id=mds.pk)


@login_required
@require_POST
def cap_titre_incident(request, titre_id):
    titre = get_object_or_404(TitreCAP, pk=titre_id)
    nouveau = request.POST.get("statut")
    autorise = {'PERDU', 'VOLE'} | ({'RETOURNE'} if est_regisseur(request.user, titre.mds) else set())
    if not _peut_voir_coffre(request.user, titre.mds) or nouveau not in autorise or titre.statut != 'EN_STOCK':
        return HttpResponseForbidden("Action impossible sur ce chèque.")
    svc.declarer_incident(titre, nouveau, request.user, request.POST.get("commentaire", ""))
    messages.success(request, f"Chèque {titre.numero} : {titre.get_statut_display()}.")
    from django.utils.http import url_has_allowed_host_and_scheme
    retour = request.POST.get("retour", "")
    if retour and url_has_allowed_host_and_scheme(retour, allowed_hosts={request.get_host()}):
        return redirect(retour)
    return redirect("AidFi:cap_coffre", mds_id=titre.mds_id)


# =============================================================================
# RÉCEPTION (douchette)
# =============================================================================

@login_required
def cap_reception_nouvelle(request, mds_id):
    mds = get_object_or_404(MDS, pk=mds_id)
    if not est_regisseur(request.user, mds):
        return HttpResponseForbidden("Réception réservée au régisseur de la MDS.")
    if request.method == "POST":
        form = ReceptionCAPForm(request.POST)
        if form.is_valid():
            reception = form.save(commit=False)
            reception.mds = mds
            reception.regisseur = request.user
            reception.save()
            return redirect("AidFi:cap_reception", reception_id=reception.pk)
    else:
        form = ReceptionCAPForm(initial={'date_reception': timezone.localdate()})
    return render(request, "AidFi/cap_reception_form.html", {"form": form, "mds": mds})


@login_required
def cap_reception(request, reception_id):
    reception = get_object_or_404(ReceptionCAP.objects.select_related('mds'), pk=reception_id)
    mds = reception.mds
    regisseur = est_regisseur(request.user, mds)
    if not (regisseur or _peut_voir_coffre(request.user, mds)):
        return HttpResponseForbidden("Accès refusé")

    valeur = int(request.POST.get("valeur") or request.GET.get("valeur") or 10)
    if valeur not in VALEURS_CAP:
        valeur = 10

    if request.method == "POST":
        if not regisseur or reception.saisie_terminee:
            return HttpResponseForbidden("Saisie close ou réservée au régisseur.")
        action = request.POST.get("action")
        if action == "scan":
            for numero in svc.lire_numeros(request.POST.get("numero")):
                try:
                    TitreCAP.objects.create(numero=numero, valeur=valeur, reception=reception, mds=mds,
                                            date_validite=reception.date_validite)
                    messages.success(request, f"✔ {numero} ({valeur} €)")
                except IntegrityError:
                    messages.error(request, f"✖ {numero} : numéro déjà enregistré.")
        elif action == "supprimer":
            t = reception.titres.filter(pk=request.POST.get("titre_id"), statut='EN_STOCK').first()
            if t:
                messages.info(request, f"Saisie annulée : {t.numero}")
                t.delete()
        elif action == "terminer":
            reception.saisie_terminee = True
            reception.save(update_fields=['saisie_terminee'])
            messages.success(request, "Saisie terminée. Le bordereau est disponible.")
        return redirect(f"{request.path}?valeur={valeur}")

    titres = reception.titres.order_by('-id')
    resume = [{'valeur': v, 'nombre': titres.filter(valeur=v).count()} for v in VALEURS_CAP]
    return render(request, "AidFi/cap_reception.html", {
        "reception": reception, "mds": mds, "titres": titres, "valeur": valeur,
        "valeurs": VALEURS_CAP, "resume": resume, "total": sum(r['valeur'] * r['nombre'] for r in resume),
        "nombre": sum(r['nombre'] for r in resume), "regisseur": regisseur,
    })


@login_required
def cap_reception_pdf(request, reception_id):
    reception = get_object_or_404(ReceptionCAP, pk=reception_id)
    if not _peut_voir_coffre(request.user, reception.mds):
        return HttpResponseForbidden("Accès refusé")
    return FileResponse(svc.bordereau_reception_pdf(reception), as_attachment=False,
                        filename=f"bordereau_CAP_{reception.date_reception:%Y_%m}_{reception.pk}.pdf",
                        content_type="application/pdf")


# =============================================================================
# INVENTAIRE DU COFFRE (régisseur uniquement, sans périodicité imposée)
# =============================================================================

@login_required
@require_POST
def cap_inventaire_nouveau(request, mds_id):
    mds = get_object_or_404(MDS, pk=mds_id)
    if not est_regisseur(request.user, mds):
        return HttpResponseForbidden("Inventaire réservé au régisseur de la MDS.")
    inventaire = mds.inventaires_cap.filter(termine=False).first() or \
        InventaireCAP.objects.create(mds=mds, regisseur=request.user)
    return redirect("AidFi:cap_inventaire", inventaire_id=inventaire.pk)


@login_required
def cap_inventaire(request, inventaire_id):
    inventaire = get_object_or_404(InventaireCAP.objects.select_related('mds'), pk=inventaire_id)
    mds = inventaire.mds
    if not est_regisseur(request.user, mds):
        return HttpResponseForbidden("Inventaire réservé au régisseur de la MDS.")

    if request.method == "POST" and not inventaire.termine:
        action = request.POST.get("action")
        if action == "scan":
            deja = set(inventaire.numeros)
            for numero in svc.lire_numeros(request.POST.get("numero")):
                if numero in deja:
                    messages.info(request, f"{numero} : déjà scanné.")
                    continue
                inventaire.numeros.append(numero)
                deja.add(numero)
                t = TitreCAP.objects.filter(numero=numero).first()
                if t and t.mds_id == mds.pk and t.statut == 'EN_STOCK':
                    messages.success(request, f"✔ {numero} ({t.valeur} €)")
                elif t:
                    messages.warning(request, f"⚠ {numero} : non attendu au coffre ({t.get_statut_display().lower()}"
                                              f"{', autre MDS' if t.mds_id != mds.pk else ''}).")
                else:
                    messages.error(request, f"✖ {numero} : numéro inconnu.")
            inventaire.save(update_fields=['numeros', 'updated_at'])
        elif action == "retirer":
            numero = request.POST.get("numero_retire")
            if numero in inventaire.numeros:
                inventaire.numeros.remove(numero)
                inventaire.save(update_fields=['numeros', 'updated_at'])
        elif action == "terminer":
            r = svc.terminer_inventaire(inventaire, request.user, request.POST.get("commentaire", ""))
            if r['ecart']:
                messages.warning(request, f"Inventaire terminé avec écarts : {len(r['manquants'])} manquant(s), "
                                          f"{len(r['inattendus'])} non attendu(s).")
            else:
                messages.success(request, "Inventaire terminé : aucun écart.")
        return redirect("AidFi:cap_inventaire", inventaire_id=inventaire.pk)

    resultat = inventaire.resultat if inventaire.termine else svc.comparer_inventaire(inventaire)
    return render(request, "AidFi/cap_inventaire.html", {
        "inventaire": inventaire, "mds": mds, "r": resultat,
        "bilan": svc.bilan_comptable(mds),
        "derniers_scans": list(reversed(inventaire.numeros[-15:])),
    })


@login_required
def cap_inventaire_pdf(request, inventaire_id):
    inventaire = get_object_or_404(InventaireCAP, pk=inventaire_id)
    if not est_regisseur(request.user, inventaire.mds):
        return HttpResponseForbidden("Accès refusé")
    return FileResponse(svc.proces_verbal_inventaire_pdf(inventaire), as_attachment=False,
                        filename=f"inventaire_CAP_{inventaire.date_debut:%Y_%m_%d}.pdf",
                        content_type="application/pdf")


# =============================================================================
# RÉGIE CENTRALE (paierie)
# =============================================================================

@login_required
def cap_paierie(request):
    if not request.user.a_la_capacite('cap_regie_centrale'):
        return HttpResponseForbidden("Accès réservé à la régie centrale.")
    return render(request, "AidFi/cap_paierie.html", {
        "demandes": DemandeCAP.objects.filter(statut__in=('TRANSMISE_PAIERIE', 'REMISE'), remise_paierie=True)
                                      .select_related('beneficiaire__mds').order_by('date_decision'),
    })
