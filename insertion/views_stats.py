# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/views_stats.py
"""
File active RSA et statistiques, chacun dans son périmètre (référent, cadre de MDS, pôle, département),
avec export CSV (séparateur « ; », UTF-8 avec BOM : s'ouvre dans LibreOffice, Excel ou tout autre outil).
"""
import csv
from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone

from insertion import acces
from insertion.models import ContratInsertion as C
from insertion.services import statistiques as st


def _csv(nom, entete, lignes):
    reponse = HttpResponse(content_type="text/csv; charset=utf-8")
    reponse["Content-Disposition"] = f'attachment; filename="{nom}"'
    reponse.write("﻿")
    w = csv.writer(reponse, delimiter=";")
    if entete:
        w.writerow(entete)
    for l in lignes:
        w.writerow(l)
    return reponse


def _date(texte):
    try:
        return date.fromisoformat(texte) if texte else None
    except ValueError:
        return None


def _mds_choisie(request, perimetre):
    mds = request.GET.get("mds", "")
    if mds and perimetre.mds_disponibles().filter(pk=mds).exists():
        return int(mds)
    return None


@login_required
def file_active(request):
    u = request.user
    if not acces.peut_voir_module(u):
        return HttpResponseForbidden("Accès réservé au module RSA – Insertion.")
    perimetre = st.Perimetre(u)
    mds = _mds_choisie(request, perimetre)
    g = request.GET
    reorientes = g.get("reorientes") == "1"
    toutes = st.file_active(perimetre, mds, inclure_reorientes=reorientes)
    if reorientes:
        toutes = [l for l in toutes if l["reoriente"]]
    lignes = st.filtrer_file_active(toutes, alerte=g.get("alerte", ""), nature=g.get("nature", ""),
                                    referent=g.get("referent", ""), ville=g.get("ville", ""), q=g.get("q", ""))
    if g.get("export") == "csv":
        return _csv(f"file_active_RSA_{timezone.localdate():%Y-%m-%d}.csv", st.COLONNES_FILE_ACTIVE,
                    st.lignes_csv_file_active(lignes))
    referents = sorted({l["referent"] for l in toutes if l["referent"]}, key=lambda x: (x.last_name, x.first_name))
    filtres = g.copy()
    filtres.pop("page", None)
    filtres.pop("export", None)
    return render(request, "insertion/file_active.html", {
        "page_obj": Paginator(lignes, 100).get_page(g.get("page")), "nb": len(lignes), "nb_total": len(toutes),
        "perimetre": perimetre, "mds_liste": perimetre.mds_disponibles(), "mds_choisie": mds,
        "alertes": st.ALERTES, "natures": C.NATURES, "referents": referents,
        "villes": sorted({l["beneficiaire"].ville for l in toutes if l["beneficiaire"].ville}),
        "f": g, "requete": filtres.urlencode(), "reorientes": reorientes,
    })


@login_required
def statistiques(request):
    u = request.user
    if not acces.peut_voir_module(u):
        return HttpResponseForbidden("Accès réservé au module RSA – Insertion.")
    perimetre = st.Perimetre(u)
    mds = _mds_choisie(request, perimetre)
    debut, fin = st.periode(_date(request.GET.get("debut")), _date(request.GET.get("fin")))
    if debut > fin:
        debut, fin = fin, debut
    stats = st.statistiques(perimetre, debut, fin, mds)
    if request.GET.get("export") == "csv":
        return _csv(f"statistiques_RSA_{debut:%Y-%m-%d}_{fin:%Y-%m-%d}.csv", None, st.tableaux_csv(stats))
    return render(request, "insertion/statistiques.html", {
        "s": stats, "perimetre": perimetre, "debut": debut, "fin": fin, "mds_liste": perimetre.mds_disponibles(),
        "mds_choisie": mds,
    })
