# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/views_contrats.py
"""
Contrats RSA : contrats d'un bénéficiaire, rédaction, fiche du contrat (actions selon le rôle),
liste « à traiter » et file active (alertes de renouvellement), documents PDF.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from beneficiaire.models import Beneficiaire
from insertion import acces
from insertion.forms import AvisForm, ContratForm, DecisionForm, LignesFormSet, ReceptionForm
from insertion.models import ActionInsertion, ContratInsertion, ParametresRSA
from insertion.services import contrat_circuit as circuit
from insertion.services import contrat_pdf as documents

C = ContratInsertion


def _refus(texte="Accès réservé."):
    return HttpResponseForbidden(texte)


def _contrat(request, pk):
    return get_object_or_404(acces.contrats_visibles(request.user), pk=pk)


def actions_pour(contrat):
    """Actions proposées dans un contrat : départementales (de tout le département ou du pôle du contrat)
    et locales de la MDS du contrat."""
    qs = ActionInsertion.objects.filter(actif=True).select_related('type_action')
    dep = Q(niveau=ActionInsertion.DEPARTEMENTAL) & (Q(poles__isnull=True) | Q(poles=contrat.pole_id))
    return qs.filter(dep | Q(niveau=ActionInsertion.LOCAL, mds=contrat.mds_id)).distinct()


# ---------------------------------------------------------------------- bénéficiaire
@login_required
def contrats_beneficiaire(request, code_interne):
    b = get_object_or_404(Beneficiaire.objects.select_related('mds'), code_interne=code_interne)
    if not b.peut_etre_vu_par(request.user):
        return _refus("Accès refusé à ce bénéficiaire.")
    contrats = list(b.contrats_insertion.select_related('referent', 'pole').prefetch_related('lignes'))
    dernier_valide = next((c for c in contrats if c.statut in (C.VALIDE, C.VALIDE_SAUF_ACTION)), None)
    return render(request, "insertion/contrats_beneficiaire.html", {
        "beneficiaire": b, "contrats": contrats, "peut_rediger": acces.peut_rediger(request.user, b),
        "en_preparation": next((c for c in contrats if c.statut in C.MODIFIABLES), None),
        "dernier_valide": dernier_valide, "parametres": ParametresRSA.courant(),
        "pole": acces.pole_de_mds(b.mds),
    })


@login_required
@require_POST
def contrat_nouveau(request, code_interne):
    b = get_object_or_404(Beneficiaire, code_interne=code_interne)
    if not acces.peut_rediger(request.user, b):
        return _refus()
    if b.contrats_insertion.filter(statut__in=C.MODIFIABLES).exists():
        messages.warning(request, "Un contrat est déjà en préparation : reprenez-le.")
        return redirect("insertion:contrats_beneficiaire", code_interne=b.code_interne)
    type_contrat = request.POST.get("type_contrat", C.OUVERTURE)
    if type_contrat not in dict(C.TYPES):
        type_contrat = C.OUVERTURE
    precedent = None
    if type_contrat != C.OUVERTURE:
        precedent = (b.contrats_insertion.filter(statut__in=(C.VALIDE, C.VALIDE_SAUF_ACTION))
                     .order_by('-date_fin', '-pk').first())
    c = circuit.creer(b, request.user, type_contrat, precedent)
    messages.success(request, f"Contrat {c.numero} créé" + (f", repris du contrat {precedent.numero}" if precedent else "")
                     + " : complétez-le.")
    return redirect("insertion:contrat_modifier", pk=c.pk)


# ---------------------------------------------------------------------- rédaction
@login_required
def contrat_modifier(request, pk):
    c = _contrat(request, pk)
    if not acces.peut_rediger(request.user, c.beneficiaire):
        return _refus()
    if not c.modifiable:
        messages.warning(request, "Ce contrat n'est plus modifiable (transmis au pôle ou décidé).")
        return redirect("insertion:contrat_detail", pk=c.pk)
    form = ContratForm(request.POST or None, instance=c)
    lignes = LignesFormSet(request.POST or None, instance=c, actions=actions_pour(c), prefix="lignes")
    if request.method == "POST" and form.is_valid() and lignes.is_valid():
        form.save()
        lignes.save()
        circuit.journal(c, request.user, "Contrat modifié")
        if request.POST.get("suite") == "transmettre":
            try:
                circuit.transmettre(c, request.user)
                messages.success(request, f"Contrat {c.numero} transmis au {c.pole.nom}.")
            except circuit.ErreurCircuit as e:
                messages.error(request, str(e))
                return redirect("insertion:contrat_modifier", pk=c.pk)
        else:
            messages.success(request, "Contrat enregistré.")
        return redirect("insertion:contrat_detail", pk=c.pk)
    return render(request, "insertion/contrat_form.html", {
        "contrat": c, "form": form, "lignes": lignes, "parametres": ParametresRSA.courant(),
        "reseau": c.beneficiaire.reseau_familial(),
    })


# ---------------------------------------------------------------------- fiche
@login_required
def contrat_detail(request, pk):
    c = _contrat(request, pk)
    u = request.user
    role = {
        "referent": acces.peut_rediger(u, c.beneficiaire),
        "admin": acces.est_admin_pole(u, c), "cadre": acces.est_cadre_pole(u, c), "medecin": acces.est_medecin_pole(u, c),
    }
    p = ParametresRSA.courant()
    aujourd_hui = timezone.localdate()
    decision = DecisionForm(initial={
        "date_decision": aujourd_hui, "date_debut": c.date_debut or aujourd_hui,
        "duree_mois": c.duree_validee_mois or c.duree_proposee_mois, "decision_transport": c.decision_transport,
    })
    return render(request, "insertion/contrat_detail.html", {
        "contrat": c, "role": role, "parametres": p, "lignes": c.lignes.select_related('action'),
        "historique": c.historique.select_related('user')[:30],
        "manques": c.manques_transmission() if c.modifiable else [],
        "reception": ReceptionForm(initial={"date_reception": aujourd_hui}),
        "avis": AvisForm(initial={"certificat_recu_le": c.certificat_recu_le or aujourd_hui,
                                  "avis": c.avis_medical, "motivation": c.avis_motivation}),
        "decision": decision, "enfants": [m for m in c.beneficiaire.reseau_familial() if m['type_lien'] == 'ENFANT'],
        "peut_renouveler": role["referent"] and c.statut in (C.VALIDE, C.VALIDE_SAUF_ACTION)
        and not c.suivants.exclude(statut__in=(C.ANNULE, C.NON_VALIDE)).exists(),
    })


def _action(request, pk, autorise, faire, ok):
    c = _contrat(request, pk)
    if not autorise(request.user, c):
        return _refus()
    try:
        faire(c)
        messages.success(request, ok(c))
    except circuit.ErreurCircuit as e:
        messages.error(request, str(e))
    return redirect("insertion:contrat_detail", pk=c.pk)


@login_required
@require_POST
def contrat_transmettre(request, pk):
    return _action(request, pk, lambda u, c: acces.peut_rediger(u, c.beneficiaire),
                   lambda c: circuit.transmettre(c, request.user), lambda c: f"Contrat transmis au {c.pole.nom}.")


@login_required
@require_POST
def contrat_annuler(request, pk):
    return _action(request, pk, lambda u, c: acces.peut_rediger(u, c.beneficiaire),
                   lambda c: circuit.annuler(c, request.user, request.POST.get("motif", "")),
                   lambda c: "Contrat annulé.")


@login_required
@require_POST
def contrat_renouveler(request, pk):
    c = _contrat(request, pk)
    if not acces.peut_rediger(request.user, c.beneficiaire):
        return _refus()
    if c.beneficiaire.contrats_insertion.filter(statut__in=C.MODIFIABLES).exists():
        messages.warning(request, "Un contrat est déjà en préparation pour ce bénéficiaire.")
        return redirect("insertion:contrats_beneficiaire", code_interne=c.beneficiaire.code_interne)
    type_contrat = C.RETABLISSEMENT if request.POST.get("type_contrat") == C.RETABLISSEMENT else C.PROLONGEMENT
    nouveau = circuit.creer(c.beneficiaire, request.user, type_contrat, c)
    messages.success(request, f"{nouveau.get_type_contrat_display()} : contrat {nouveau.numero} créé à partir du "
                              f"contrat {c.numero}. Mettez-le à jour avec le bénéficiaire.")
    return redirect("insertion:contrat_modifier", pk=nouveau.pk)


@login_required
@require_POST
def contrat_receptionner(request, pk):
    form = ReceptionForm(request.POST)
    le = form.cleaned_data["date_reception"] if form.is_valid() else None
    return _action(request, pk, acces.est_admin_pole, lambda c: circuit.receptionner(c, request.user, le),
                   lambda c: "Contrat réceptionné : le cadre du pôle est prévenu.")


@login_required
@require_POST
def contrat_avis(request, pk):
    form = AvisForm(request.POST)

    def faire(c):
        if not form.is_valid():
            raise circuit.ErreurCircuit("Indiquez la date de réception du certificat et l'avis.")
        circuit.donner_avis(c, request.user, certificat_recu_le=form.cleaned_data["certificat_recu_le"],
                            avis=form.cleaned_data["avis"], motivation=form.cleaned_data["motivation"])
    return _action(request, pk, acces.est_medecin_pole, faire, lambda c: "Avis enregistré : le cadre du pôle est prévenu.")


@login_required
@require_POST
def contrat_decision(request, pk):
    form = DecisionForm(request.POST)

    def faire(c):
        if not form.is_valid():
            raise circuit.ErreurCircuit("Décision incomplète : " + " ".join(
                f"{form.fields[k].label} : {' '.join(v)}" for k, v in form.errors.items()))
        d = form.cleaned_data
        non_retenues = {k.split("_", 2)[2]: request.POST.get(f"motif_non_retenue_{k.split('_', 2)[2]}", "")
                        for k in request.POST if k.startswith("non_retenue_")}
        circuit.decider(c, request.user, decision=d["decision"], date_decision=d["date_decision"],
                        date_debut=d["date_debut"], duree_mois=d["duree_mois"], motif=d["motif"],
                        decision_transport=d["decision_transport"], motif_transport=d["motif_transport"],
                        commentaire=d["commentaire"], non_retenues=non_retenues)
    return _action(request, pk, acces.est_cadre_pole, faire,
                   lambda c: f"Décision enregistrée ({c.get_decision_display().lower()}) : le référent est prévenu.")


# ---------------------------------------------------------------------- PDF
def _pdf(buffer, nom):
    return FileResponse(buffer, as_attachment=False, filename=nom, content_type="application/pdf")


@login_required
def contrat_pdf(request, pk):
    c = _contrat(request, pk)
    return _pdf(documents.contrat_pdf(c), f"contrat_{c.numero}.pdf")


@login_required
def contrat_courrier_medecin(request, pk):
    c = _contrat(request, pk)
    if not acces.peut_rediger(request.user, c.beneficiaire):
        return _refus()
    return _pdf(documents.courrier_medecin_pdf(c), f"certificat_medical_{c.numero}.pdf")


@login_required
def contrat_notification(request, pk):
    c = _contrat(request, pk)
    if not c.decision:
        return _refus("La commission n'a pas encore décidé.")
    return _pdf(documents.notification_pdf(c), f"notification_{c.numero}.pdf")


# ---------------------------------------------------------------------- listes
VUES = [
    ("a_traiter", "À traiter"), ("en_cours", "En vigueur"), ("a_renouveler", "À renouveler"),
    ("expires", "Échus, sans renouvellement"), ("sauf_action", "Validés sauf action"),
    ("en_preparation", "En préparation"), ("tous", "Tous"),
]


def a_traiter(user, qs):
    """Ce que l'utilisateur doit faire : réceptionner, donner un avis, décider, reprendre un contrat ajourné."""
    filtre = Q(pk__in=[])
    poles = acces.poles_de(user)
    if user.is_superuser or user.a_la_capacite('rsa_pole_admin'):
        filtre |= Q(statut=C.TRANSMIS, pole__in=poles) if not user.is_superuser else Q(statut=C.TRANSMIS)
    if user.is_superuser or user.a_la_capacite('rsa_pole_cadre'):
        filtre |= Q(statut=C.RECU, pole__in=poles) if not user.is_superuser else Q(statut=C.RECU)
    if user.is_superuser or user.a_la_capacite('rsa_pole_medecin'):
        sante = Q(statut__in=(C.TRANSMIS, C.RECU), nature='SANTE', avis_medical='')
        filtre |= (sante & Q(pole__in=poles)) if not user.is_superuser else sante
    if user.a_la_capacite('peut_creer'):
        filtre |= Q(statut=C.AJOURNE, referent=user)
    return qs.filter(filtre)


def _filtrer(qs, vue):
    """Les alertes (à renouveler, échus) dépendent de la date de fin et d'un éventuel contrat suivant."""
    aujourd_hui = timezone.localdate()
    p = ParametresRSA.courant()
    decides = Q(statut__in=(C.VALIDE, C.VALIDE_SAUF_ACTION))
    sans_suite = ~Q(suivants__statut__in=[s for s, _ in C.STATUTS if s not in (C.ANNULE, C.NON_VALIDE)])
    if vue == "en_cours":
        return qs.filter(decides, date_debut__lte=aujourd_hui, date_fin__gte=aujourd_hui)
    if vue == "a_renouveler":
        from datetime import timedelta
        return qs.filter(decides, sans_suite, date_fin__gte=aujourd_hui,
                         date_fin__lte=aujourd_hui + timedelta(days=p.delai_alerte_jours))
    if vue == "expires":
        return qs.filter(decides, sans_suite, date_fin__lt=aujourd_hui)
    if vue == "sauf_action":
        return qs.filter(statut=C.VALIDE_SAUF_ACTION, date_fin__gte=aujourd_hui)
    if vue == "en_preparation":
        return qs.filter(statut__in=C.MODIFIABLES)
    return qs


@login_required
def contrats_liste(request):
    u = request.user
    if not acces.peut_voir_module(u):
        return _refus("Accès réservé au module RSA – Insertion.")
    base = acces.contrats_visibles(u).exclude(statut=C.ANNULE)
    vue = request.GET.get("vue") or "a_traiter"
    qs = a_traiter(u, base) if vue == "a_traiter" else _filtrer(base, vue)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(beneficiaire__nom__icontains=q) | Q(beneficiaire__prenom__icontains=q)
                       | Q(beneficiaire__code_interne__icontains=q))
    mds = request.GET.get("mds", "")
    if mds:
        qs = qs.filter(mds__code_mds=mds)
    qs = qs.distinct().order_by('date_fin' if vue in ("a_renouveler", "expires", "en_cours", "sauf_action")
                                else '-date_transmission', '-pk')
    compteurs = {"a_traiter": a_traiter(u, base).distinct().count(),
                 "a_renouveler": _filtrer(base, "a_renouveler").distinct().count(),
                 "expires": _filtrer(base, "expires").distinct().count()}
    from mds.models import MDS
    return render(request, "insertion/contrats_liste.html", {
        "page_obj": Paginator(qs, 50).get_page(request.GET.get("page")), "vue": vue, "vues": VUES, "q": q,
        "mds_choisie": mds, "compteurs": compteurs,
        "mds_liste": MDS.objects.filter(pk__in=base.values('mds_id')).order_by('nom'),
    })
