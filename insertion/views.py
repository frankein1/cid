# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/views.py
"""Module RSA – Insertion : accueil du module et référentiel des actions (liste, fiche, saisie, CSV)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from insertion import acces
from insertion.forms import ActionInsertionForm, ImportCSVForm
from insertion.models import ActionInsertion, PoleInsertion, TypeActionInsertion
from insertion.services import csv_actions

SESSION_IMPORT = "insertion_import_csv"
TAILLE_MAX_CSV = 2 * 1024 * 1024


def _refus(request):
    return HttpResponseForbidden("Accès réservé au module RSA – Insertion.")


@login_required
def accueil(request):
    if not acces.peut_voir_module(request.user):
        return _refus(request)
    poles = PoleInsertion.objects.filter(Q(membres=request.user) | Q(mds__profils_utilisateurs__user=request.user),
                                         actif=True).distinct()
    actions = acces.actions_visibles(request.user).filter(actif=True)
    return render(request, "insertion/accueil.html", {
        "poles": poles, "nb_departementales": actions.filter(niveau=ActionInsertion.DEPARTEMENTAL).count(),
        "nb_locales": actions.filter(niveau=ActionInsertion.LOCAL).count(),
    })


def _filtrer(request):
    qs = acces.actions_visibles(request.user)
    f = {k: request.GET.get(k, "").strip() for k in ("q", "type", "niveau", "pole", "etat")}
    if f["q"]:
        qs = qs.filter(Q(libelle__icontains=f["q"]) | Q(code__icontains=f["q"]) | Q(porteur__icontains=f["q"])
                       | Q(territoire__icontains=f["q"]) | Q(description__icontains=f["q"]))
    if f["type"]:
        qs = qs.filter(type_action__code=f["type"])
    if f["niveau"]:
        qs = qs.filter(niveau=f["niveau"])
    if f["pole"]:
        qs = qs.filter(Q(poles__code=f["pole"]) | Q(niveau=ActionInsertion.DEPARTEMENTAL, poles__isnull=True)
                       | Q(mds__poles_insertion__code=f["pole"])).distinct()
    if f["etat"] != "toutes":
        qs = qs.filter(actif=f["etat"] != "inactives")
    return qs, f


def _sans_page(request):
    q = request.GET.copy()
    q.pop("page", None)
    return q.urlencode()


@login_required
def actions_liste(request):
    if not acces.peut_voir_module(request.user):
        return _refus(request)
    qs, f = _filtrer(request)
    page = Paginator(qs, 50).get_page(request.GET.get("page"))
    return render(request, "insertion/actions_liste.html", {
        "page_obj": page, "filtres": f, "types": TypeActionInsertion.objects.filter(actif=True),
        "poles": PoleInsertion.objects.filter(actif=True), "niveaux": ActionInsertion.NIVEAUX,
        "peut_departemental": acces.peut_gerer_departemental(request.user),
        "peut_local": acces.mds_gerables(request.user).exists(),
        "requete": _sans_page(request),
    })


@login_required
def action_detail(request, pk):
    action = get_object_or_404(acces.actions_visibles(request.user), pk=pk)
    return render(request, "insertion/action_detail.html",
                  {"action": action, "peut_modifier": acces.peut_gerer(request.user, action)})


@login_required
def action_saisie(request, pk=None):
    user = request.user
    action = get_object_or_404(ActionInsertion, pk=pk) if pk else None
    if action and not acces.peut_gerer(user, action):
        return _refus(request)
    departemental = acces.peut_gerer_departemental(user)
    mds_possibles = acces.mds_gerables(user)
    if not action and not (departemental or mds_possibles.exists()):
        return _refus(request)
    if action is None:
        action = ActionInsertion(niveau=ActionInsertion.DEPARTEMENTAL if departemental else ActionInsertion.LOCAL,
                                 mds=mds_possibles.first() if not departemental and mds_possibles.count() == 1 else None)
    form = ActionInsertionForm(request.POST or None, instance=action, user=user, mds_possibles=mds_possibles,
                               departemental_possible=departemental)
    if request.method == "POST" and form.is_valid():
        a = form.save(commit=False)
        if not acces.peut_gerer(user, a):   # niveau ou MDS changés vers un périmètre non autorisé
            return _refus(request)
        a.modifie_par = user
        a.save()
        form.save_m2m()
        messages.success(request, f"Action « {a.libelle} » enregistrée.")
        return redirect("insertion:action_detail", pk=a.pk)
    return render(request, "insertion/action_form.html", {"form": form, "action": action if pk else None})


# ---------------------------------------------------------------------- CSV
def _reponse_csv(contenu, nom):
    r = HttpResponse(contenu, content_type="text/csv; charset=utf-8")
    r["Content-Disposition"] = f'attachment; filename="{nom}"'
    return r


@login_required
def actions_modele_csv(request):
    if not acces.peut_voir_module(request.user):
        return _refus(request)
    return _reponse_csv(csv_actions.modele_csv(list(TypeActionInsertion.objects.filter(actif=True))),
                        "modele_actions_insertion.csv")


@login_required
def actions_export_csv(request):
    if not acces.peut_voir_module(request.user):
        return _refus(request)
    qs, _ = _filtrer(request)
    return _reponse_csv(csv_actions.export_csv(qs), f"actions_insertion_{timezone.localdate():%Y%m%d}.csv")


@login_required
def actions_import(request):
    user = request.user
    if not (acces.peut_gerer_departemental(user) or acces.mds_gerables(user).exists()):
        return _refus(request)
    form = ImportCSVForm(request.POST or None, request.FILES or None)
    lignes = None
    if request.method == "POST" and request.POST.get("etape") == "enregistrer":
        texte = request.session.get(SESSION_IMPORT)
        if not texte:
            messages.error(request, "Analyse expirée : déposez de nouveau le fichier.")
            return redirect("insertion:actions_import")
        lignes = csv_actions.analyser(texte, user)   # analysées de nouveau, avec les droits actuels
        crees, maj = csv_actions.enregistrer(lignes, user)
        erreurs = sum(1 for l in lignes if l["operation"] == "erreur")
        request.session.pop(SESSION_IMPORT, None)
        messages.success(request, f"Import terminé : {crees} action(s) créée(s), {maj} mise(s) à jour"
                                  + (f", {erreurs} ligne(s) en erreur ignorée(s)." if erreurs else "."))
        return redirect("insertion:actions_liste")
    if request.method == "POST" and form.is_valid():
        fichier = form.cleaned_data["fichier"]
        if fichier.size > TAILLE_MAX_CSV:
            messages.error(request, "Fichier trop volumineux (2 Mo au plus).")
        else:
            brut = fichier.read()
            try:
                texte = brut.decode("utf-8-sig")
            except UnicodeDecodeError:
                texte = brut.decode("cp1252", errors="replace")   # CSV enregistré par Excel (Windows)
            try:
                lignes = csv_actions.analyser(texte, user)
                request.session[SESSION_IMPORT] = texte
            except ValueError as e:
                messages.error(request, f"Fichier illisible : {e}.")
    resume = None
    if lignes is not None:
        resume = {op: sum(1 for l in lignes if l["operation"] == op) for op in ("creation", "mise_a_jour", "erreur")}
    return render(request, "insertion/actions_import.html", {"form": form, "lignes": lignes, "resume": resume,
                                                            "types": TypeActionInsertion.objects.filter(actif=True),
                                                            "poles": PoleInsertion.objects.filter(actif=True)})
