# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/views_reorientation.py
"""
Réorientations : la demande (référent), la commission trimestrielle du pôle (ordre du jour, participants,
décisions, clôture, documents) et les organismes de réorientation (France Travail, CAF, associations).
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from beneficiaire.models import Beneficiaire
from core.models import User
from insertion import acces
from insertion.forms import (CommissionForm, DecisionReorientationForm, DemandeReorientationForm, OrganismesFormSet,
                             ParticipantsForm)
from insertion.models import CommissionReorientation as Commission, DemandeReorientation as D, OrganismeOrientation
from insertion.services import reorientation_circuit as circuit
from insertion.services.contrat_circuit import ErreurCircuit


def _refus(texte="Accès réservé."):
    return HttpResponseForbidden(texte)


def _demande(request, pk):
    return get_object_or_404(acces.reorientations_visibles(request.user), pk=pk)


def _commission(request, pk):
    return get_object_or_404(acces.commissions_visibles(request.user), pk=pk)


# ---------------------------------------------------------------------- demande (référent)
@login_required
@require_POST
def reorientation_nouvelle(request, code_interne):
    b = get_object_or_404(Beneficiaire, code_interne=code_interne)
    if not acces.peut_rediger(request.user, b):
        return _refus()
    en_cours = b.reorientations.filter(statut__in=(D.BROUILLON, D.INSCRITE)).first()
    if en_cours:
        messages.warning(request, "Une demande de réorientation est déjà en cours pour cette personne.")
        return redirect("insertion:reorientation_detail", pk=en_cours.pk)
    d = circuit.creer(b, request.user)
    messages.success(request, f"Demande {d.numero} créée : complétez-la puis inscrivez-la en commission.")
    return redirect("insertion:reorientation_modifier", pk=d.pk)


@login_required
def reorientation_modifier(request, pk):
    d = _demande(request, pk)
    if not acces.peut_rediger(request.user, d.beneficiaire):
        return _refus()
    if not d.modifiable:
        messages.warning(request, "Cette demande n'est plus modifiable.")
        return redirect("insertion:reorientation_detail", pk=d.pk)
    form = DemandeReorientationForm(request.POST or None, instance=d)
    if request.method == "POST" and form.is_valid():
        form.save()
        circuit.journal(d, request.user, "Demande modifiée")
        if request.POST.get("suite") == "inscrire" and d.statut == D.BROUILLON:
            try:
                circuit.inscrire(d, request.user)
                messages.success(request, "Demande inscrite en commission.")
            except ErreurCircuit as e:
                messages.error(request, str(e))
                return redirect("insertion:reorientation_modifier", pk=d.pk)
        else:
            messages.success(request, "Demande enregistrée.")
        return redirect("insertion:reorientation_detail", pk=d.pk)
    return render(request, "insertion/reorientation_form.html", {"d": d, "form": form})


@login_required
def reorientation_detail(request, pk):
    d = _demande(request, pk)
    return render(request, "insertion/reorientation_detail.html", {
        "d": d, "referent": acces.peut_rediger(request.user, d.beneficiaire),
        "gestion": acces.peut_gerer_commission(request.user, d.pole),
        "manques": d.manques_inscription() if d.statut == D.BROUILLON else [],
        "historique": d.historique.select_related('user')[:30],
        "prochaine": circuit.prochaine_commission(d.pole),
    })


def _action_demande(request, pk, autorise, faire, ok):
    d = _demande(request, pk)
    if not autorise(request.user, d):
        return _refus()
    try:
        faire(d)
        messages.success(request, ok(d))
    except ErreurCircuit as e:
        messages.error(request, str(e))
    return redirect(request.POST.get("retour") or d.get_absolute_url())


@login_required
@require_POST
def reorientation_inscrire(request, pk):
    return _action_demande(request, pk, lambda u, d: acces.peut_rediger(u, d.beneficiaire),
                           lambda d: circuit.inscrire(d, request.user), lambda d: "Demande inscrite en commission.")


@login_required
@require_POST
def reorientation_annuler(request, pk):
    return _action_demande(request, pk, lambda u, d: acces.peut_rediger(u, d.beneficiaire),
                           lambda d: circuit.annuler(d, request.user), lambda d: "Demande annulée.")


@login_required
@require_POST
def reorientation_retirer(request, pk):
    return _action_demande(request, pk, lambda u, d: acces.peut_gerer_commission(u, d.pole),
                           lambda d: circuit.retirer(d, request.user, request.POST.get("motif", "")),
                           lambda d: "Dossier retiré : il sera présenté à la commission suivante.")


@login_required
def reorientation_notification(request, pk):
    from insertion.services.commission_pdf import notification_pdf
    d = _demande(request, pk)
    if d.statut not in (D.ACCEPTEE, D.REFUSEE):
        return _refus("La commission n'a pas encore décidé.")
    return FileResponse(notification_pdf(d), as_attachment=False, filename=f"reorientation_{d.numero}.pdf",
                        content_type="application/pdf")


# ---------------------------------------------------------------------- commissions (pôle)
@login_required
def commissions_liste(request):
    u = request.user
    poles = acces.poles_de(u) if not u.is_superuser else None
    from insertion.models import PoleInsertion
    poles_gerables = [p for p in (PoleInsertion.objects.filter(actif=True) if u.is_superuser else poles)
                      if acces.peut_gerer_commission(u, p)]
    if not poles_gerables and not u.is_superuser:
        return _refus("Accès réservé aux administratifs et cadres des pôles insertion.")
    form = CommissionForm(request.POST or None)
    if request.method == "POST":
        pole = next((p for p in poles_gerables if str(p.pk) == request.POST.get("pole")), None)
        if pole and form.is_valid():
            c, n = circuit.creer_commission(pole, u, **form.cleaned_data)
            messages.success(request, f"Commission du {c.date:%d/%m/%Y} créée ; {n} demande(s) en attente inscrite(s) "
                                      "à son ordre du jour.")
            return redirect("insertion:commission_detail", pk=c.pk)
        messages.error(request, "Indiquez le pôle et la date de la commission.")
    commissions = acces.commissions_visibles(u).annotate(nb=Count('demandes', filter=~Q(demandes__statut=D.ANNULEE)))
    attente = (acces.reorientations_visibles(u).filter(statut=D.INSCRITE, commission__isnull=True)
               .order_by('mds__nom', 'beneficiaire__nom'))
    aujourd_hui = timezone.localdate()
    return render(request, "insertion/commissions_liste.html", {
        "form": form, "poles": poles_gerables, "attente": attente,
        "a_venir": commissions.filter(statut=Commission.PREPARATION).order_by('date'),
        "passees": commissions.filter(statut=Commission.CLOTUREE).order_by('-date')[:20],
        "aujourd_hui": aujourd_hui,
    })


def _candidats(c):
    """Agents qui peuvent siéger : membres du pôle et agents des MDS du pôle."""
    from mds.models import UserMDSProfile
    ids = set(c.pole.membres.values_list('pk', flat=True))
    ids |= set(UserMDSProfile.objects.filter(mds__in=c.pole.mds.all(), actif=True).values_list('user_id', flat=True))
    return User.objects.filter(pk__in=ids, is_active=True).order_by('last_name', 'first_name')


@login_required
def commission_detail(request, pk):
    c = _commission(request, pk)
    gestion = acces.peut_gerer_commission(request.user, c.pole) and c.statut == Commission.PREPARATION
    form = ParticipantsForm(request.POST or None, instance=c, candidats=_candidats(c))
    if request.method == "POST":
        if not gestion:
            return _refus()
        if form.is_valid():
            form.save()
            messages.success(request, "Commission enregistrée.")
            return redirect("insertion:commission_detail", pk=c.pk)
    demandes = (c.demandes.exclude(statut=D.ANNULEE)
                .select_related('beneficiaire', 'mds', 'referent', 'organisme_propose', 'organisme_retenu')
                .order_by('mds__nom', 'beneficiaire__nom'))
    dossiers = [(d, DecisionReorientationForm(pole=c.pole, prefix=f"d{d.pk}", initial={
        "decision": d.decision, "organisme_retenu": d.organisme_retenu_id or d.organisme_propose_id,
        "date_effet": d.date_effet or c.date, "motif": d.motif_decision})) for d in demandes]
    return render(request, "insertion/commission_detail.html", {
        "c": c, "form": form, "gestion": gestion, "dossiers": dossiers,
        "sans_decision": sum(1 for d in demandes if d.statut == D.INSCRITE and not d.decision),
        "en_attente": D.objects.filter(pole=c.pole, statut=D.INSCRITE, commission__isnull=True).count(),
    })


@login_required
@require_POST
def commission_decision(request, pk, demande_pk):
    """Décision d'un dossier depuis la page de la commission (formulaire préfixé)."""
    c = _commission(request, pk)
    d = get_object_or_404(c.demandes, pk=demande_pk)
    if not acces.peut_gerer_commission(request.user, c.pole):
        return _refus()
    form = DecisionReorientationForm(request.POST, pole=c.pole, prefix=f"d{d.pk}")
    try:
        if not form.is_valid():
            raise ErreurCircuit("Décision incomplète.")
        circuit.decider(d, request.user, decision=form.cleaned_data["decision"],
                        organisme_retenu=form.cleaned_data["organisme_retenu"],
                        date_effet=form.cleaned_data["date_effet"], motif=form.cleaned_data["motif"])
        messages.success(request, f"{d.beneficiaire.prenom} {d.beneficiaire.nom.upper()} : {d.get_decision_display().lower()}.")
    except ErreurCircuit as e:
        messages.error(request, f"{d.beneficiaire.prenom} {d.beneficiaire.nom.upper()} : {e}")
    return redirect(f"{c.get_absolute_url()}#dossier-{d.pk}")


@login_required
@require_POST
def commission_ajouter_attente(request, pk):
    c = _commission(request, pk)
    if not acces.peut_gerer_commission(request.user, c.pole) or c.statut != Commission.PREPARATION:
        return _refus()
    n = circuit.ajouter_en_attente(c)
    messages.success(request, f"{n} demande(s) ajoutée(s) à l'ordre du jour.")
    return redirect("insertion:commission_detail", pk=c.pk)


@login_required
@require_POST
def commission_cloturer(request, pk):
    c = _commission(request, pk)
    if not acces.peut_gerer_commission(request.user, c.pole):
        return _refus()
    try:
        n = circuit.cloturer(c, request.user)
        messages.success(request, f"Commission clôturée : {n} décision(s) transmise(s) aux référents.")
    except ErreurCircuit as e:
        messages.error(request, str(e))
    return redirect("insertion:commission_detail", pk=c.pk)


@login_required
def commission_pdf(request, pk, document):
    from insertion.services import commission_pdf as docs
    c = _commission(request, pk)
    if document == "ordre-du-jour":
        return FileResponse(docs.ordre_du_jour_pdf(c), filename=f"ordre_du_jour_{c.numero}.pdf",
                            content_type="application/pdf")
    return FileResponse(docs.releve_pdf(c), filename=f"releve_decisions_{c.numero}.pdf", content_type="application/pdf")


# ---------------------------------------------------------------------- organismes
@login_required
def organismes(request):
    if not acces.peut_gerer_organismes(request.user):
        return _refus()
    formset = OrganismesFormSet(request.POST or None, queryset=OrganismeOrientation.objects.all())
    if request.method == "POST" and formset.is_valid():
        formset.save()
        messages.success(request, "Organismes enregistrés.")
        return redirect("insertion:organismes")
    return render(request, "insertion/organismes.html", {"formset": formset})
