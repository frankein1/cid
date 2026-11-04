# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/views_prescriptions.py
"""
Prescriptions vers les actions d'insertion : choix de l'action, fiche de liaison (tronc commun, freins,
questions propres à l'action, consentement), validation par le pôle, retour du porteur, listes, PDF ;
et les questions propres à chaque action (référentiel).
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from beneficiaire.models import Beneficiaire
from insertion import acces
from insertion.forms import PrescriptionForm, QuestionsFormSet, RetourPorteurForm, ValidationPrescriptionForm
from insertion.models import ActionInsertion, PrescriptionInsertion
from insertion.services import prescription_circuit as circuit
from insertion.services.contrat_circuit import ErreurCircuit
from insertion.views_contrats import actions_proposees

P = PrescriptionInsertion


def _refus(texte="Accès réservé."):
    return HttpResponseForbidden(texte)


def _prescription(request, pk):
    return get_object_or_404(acces.prescriptions_visibles(request.user), pk=pk)


# ---------------------------------------------------------------------- création
@login_required
def prescription_nouvelle(request, code_interne):
    b = get_object_or_404(Beneficiaire.objects.select_related('mds'), code_interne=code_interne)
    if not acces.peut_rediger(request.user, b):
        return _refus()
    pole = acces.pole_de_mds(b.mds)
    actions = actions_proposees(b.mds_id, pole.pk if pole else None).prefetch_related('questions')
    if request.method == "POST":
        action = get_object_or_404(actions, pk=request.POST.get("action"))
        p = circuit.creer(b, request.user, action)
        messages.success(request, f"Prescription {p.numero} créée : complétez la fiche de liaison.")
        return redirect("insertion:prescription_modifier", pk=p.pk)
    q = request.GET.get("q", "").strip()
    if q:
        actions = actions.filter(Q(libelle__icontains=q) | Q(code__icontains=q) | Q(porteur__icontains=q)
                                 | Q(type_action__libelle__icontains=q))
    return render(request, "insertion/prescription_choix.html", {
        "beneficiaire": b, "actions": actions, "q": q, "pole": pole,
        "contrat": circuit.contrat_courant(b),
    })


# ---------------------------------------------------------------------- rédaction
@login_required
def prescription_modifier(request, pk):
    p = _prescription(request, pk)
    if not acces.peut_rediger(request.user, p.beneficiaire):
        return _refus()
    if not p.modifiable:
        messages.warning(request, "Cette prescription a déjà été adressée.")
        return redirect("insertion:prescription_detail", pk=p.pk)
    form = PrescriptionForm(request.POST or None, instance=p)
    if request.method == "POST" and form.is_valid():
        form.save()
        circuit.enregistrer_reponses(p, form.reponses())
        circuit.journal(p, request.user, "Prescription modifiée")
        if request.POST.get("suite") == "adresser":
            try:
                circuit.adresser(p, request.user)
                messages.success(request, "Prescription adressée au pôle pour validation." if p.statut == P.A_VALIDER
                                 else "Prescription adressée au porteur.")
            except ErreurCircuit as e:
                messages.error(request, str(e))
                return redirect("insertion:prescription_modifier", pk=p.pk)
        else:
            messages.success(request, "Prescription enregistrée.")
        return redirect("insertion:prescription_detail", pk=p.pk)
    return render(request, "insertion/prescription_form.html", {"p": p, "form": form})


# ---------------------------------------------------------------------- fiche
@login_required
def prescription_detail(request, pk):
    p = _prescription(request, pk)
    u = request.user
    role = {"prescripteur": acces.peut_rediger(u, p.beneficiaire), "valider": acces.peut_valider_prescription(u, p),
            "retour": acces.peut_noter_retour(u, p)}
    restreintes = acces.voit_reponses_restreintes(u, p)
    reponses = {r.question_id: r.valeur for r in p.reponses.all()}
    questions = [(q, reponses.get(q.pk, ""), q.restreinte and not restreintes) for q in p.action.questions.all()]
    return render(request, "insertion/prescription_detail.html", {
        "p": p, "role": role, "questions": questions,
        "historique": p.historique.select_related('user')[:30],
        "manques": p.manques_envoi() if p.modifiable else [],
        "validation": ValidationPrescriptionForm(),
        "retour": RetourPorteurForm(prescription=p, initial={
            "premier_rdv_le": p.premier_rdv_le, "premier_rdv_issue": p.premier_rdv_issue,
            "diagnostic_finalise": p.diagnostic_finalise, "date_entree": p.date_entree,
            "commentaire_porteur": p.commentaire_porteur}),
    })


def _action(request, pk, autorise, faire, ok):
    p = _prescription(request, pk)
    if not autorise(request.user, p):
        return _refus()
    try:
        faire(p)
        messages.success(request, ok(p))
    except ErreurCircuit as e:
        messages.error(request, str(e))
    return redirect("insertion:prescription_detail", pk=p.pk)


@login_required
@require_POST
def prescription_adresser(request, pk):
    return _action(request, pk, lambda u, p: acces.peut_rediger(u, p.beneficiaire),
                   lambda p: circuit.adresser(p, request.user),
                   lambda p: "Prescription adressée au pôle pour validation." if p.statut == P.A_VALIDER
                   else "Prescription adressée au porteur.")


@login_required
@require_POST
def prescription_annuler(request, pk):
    return _action(request, pk, lambda u, p: acces.peut_rediger(u, p.beneficiaire),
                   lambda p: circuit.annuler(p, request.user, "Annulée par le prescripteur"),
                   lambda p: "Prescription annulée.")


@login_required
@require_POST
def prescription_valider(request, pk):
    form = ValidationPrescriptionForm(request.POST)

    def faire(p):
        if not form.is_valid():
            raise ErreurCircuit("Choisissez de valider ou de refuser.")
        circuit.valider(p, request.user, form.cleaned_data["decision"] == "valider", form.cleaned_data["motif"])
    return _action(request, pk, acces.peut_valider_prescription, faire,
                   lambda p: "Prescription validée : adressée au porteur." if p.statut == P.EN_ATTENTE
                   else "Prescription refusée : le prescripteur est prévenu.")


@login_required
@require_POST
def prescription_retour(request, pk):
    p0 = _prescription(request, pk)
    form = RetourPorteurForm(request.POST, prescription=p0)

    def faire(p):
        if not form.is_valid():
            raise ErreurCircuit("Retour incomplet : vérifiez les dates.")
        circuit.noter_retour(p, request.user, **form.cleaned_data)
    return _action(request, pk, acces.peut_noter_retour, faire, lambda p: f"Retour du porteur enregistré "
                   f"({p.get_statut_display().lower()}).")


@login_required
def prescription_pdf(request, pk):
    from insertion.services.prescription_pdf import fiche_pdf
    p = _prescription(request, pk)
    return FileResponse(fiche_pdf(p, restreintes=acces.voit_reponses_restreintes(request.user, p)),
                        as_attachment=False, filename=f"prescription_{p.numero}.pdf", content_type="application/pdf")


# ---------------------------------------------------------------------- listes
VUES = [("a_traiter", "À traiter"), ("en_attente", "En attente du porteur"), ("en_cours", "En cours"),
        ("terminees", "Sorties"), ("en_preparation", "En préparation"), ("toutes", "Toutes")]


def a_traiter(user, qs):
    """Pôle : prescriptions à valider. Prescripteur : prescriptions refusées à reprendre."""
    filtre = Q(pk__in=[])
    if user.is_superuser:
        filtre |= Q(statut=P.A_VALIDER)
    elif user.a_la_capacite('rsa_pole_admin') or user.a_la_capacite('rsa_pole_cadre'):
        filtre |= Q(statut=P.A_VALIDER, pole__in=acces.poles_de(user))
    if user.a_la_capacite('peut_creer'):
        filtre |= Q(statut=P.REFUSEE, prescripteur=user)
    return qs.filter(filtre)


FILTRES = {"en_attente": Q(statut=P.EN_ATTENTE), "en_cours": Q(statut=P.INTEGREE),
           "terminees": Q(statut__in=(P.TERMINEE, P.ARRETEE, P.REORIENTEE, P.NON_INTEGREE)),
           "en_preparation": Q(statut=P.BROUILLON)}


@login_required
def prescriptions_liste(request):
    u = request.user
    if not acces.peut_voir_module(u):
        return _refus("Accès réservé au module RSA – Insertion.")
    base = acces.prescriptions_visibles(u).exclude(statut=P.ANNULEE)
    vue = request.GET.get("vue") or "a_traiter"
    qs = a_traiter(u, base) if vue == "a_traiter" else base.filter(FILTRES.get(vue, Q()))
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(beneficiaire__nom__icontains=q) | Q(beneficiaire__prenom__icontains=q)
                       | Q(action__libelle__icontains=q) | Q(action__code__icontains=q))
    action = request.GET.get("action", "")
    if action:
        qs = qs.filter(action_id=action)
    return render(request, "insertion/prescriptions_liste.html", {
        "page_obj": Paginator(qs.order_by('-date_prescription', '-pk'), 50).get_page(request.GET.get("page")),
        "vue": vue, "vues": VUES, "q": q, "action_choisie": action,
        "compteurs": {"a_traiter": a_traiter(u, base).count(), "en_attente": base.filter(FILTRES["en_attente"]).count()},
        "actions": ActionInsertion.objects.filter(pk__in=base.values('action_id')).order_by('libelle'),
    })


# ---------------------------------------------------------------------- questions d'une action
@login_required
def action_questions(request, pk):
    action = get_object_or_404(acces.actions_visibles(request.user), pk=pk)
    if not acces.peut_gerer(request.user, action):
        return _refus()
    formset = QuestionsFormSet(request.POST or None, instance=action, prefix="q")
    if request.method == "POST" and formset.is_valid():
        formset.save()
        messages.success(request, "Questions enregistrées.")
        return redirect("insertion:action_detail", pk=action.pk)
    return render(request, "insertion/action_questions.html", {"action": action, "formset": formset})
