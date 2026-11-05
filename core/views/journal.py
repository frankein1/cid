# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/views/journal.py
"""
Consultation du journal d'activité (voir core/journal.py) :
  - super-administrateur : tout ;
  - capacité voir_journal_activite (cadres de MDS) : ce qui touche aux dossiers des usagers de leurs MDS.
Filtres : agent, usager (code interne), action, période ; export CSV (« ; », UTF-8).
"""
import csv
from datetime import date, datetime, time, timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone

from core.models import AuditLog


def peut_voir_journal(user):
    return user.is_authenticated and (user.is_superuser or user.a_la_capacite('voir_journal_activite'))


def journal_visible(user):
    qs = AuditLog.objects.select_related('utilisateur', 'beneficiaire', 'content_type')
    if user.is_superuser:
        return qs
    from mds.models import UserMDSProfile
    mds = UserMDSProfile.objects.filter(user=user, actif=True).values('mds_id')
    return qs.filter(beneficiaire__mds_id__in=mds)


def _date(texte):
    try:
        return date.fromisoformat(texte) if texte else None
    except ValueError:
        return None


@login_required
def journal_activite(request):
    if not peut_voir_journal(request.user):
        return HttpResponseForbidden("Accès réservé.")
    g = request.GET
    qs = journal_visible(request.user)
    debut, fin = _date(g.get("du")), _date(g.get("au"))
    if not debut and not fin and not g.get("beneficiaire"):
        debut = timezone.localdate() - timedelta(days=30)
    if debut:
        qs = qs.filter(timestamp__gte=timezone.make_aware(datetime.combine(debut, time.min)))
    if fin:
        qs = qs.filter(timestamp__lte=timezone.make_aware(datetime.combine(fin, time.max)))
    if g.get("action"):
        actions = ["LOGIN", "LOGIN_SUCCESS"] if g["action"] == "LOGIN" else [g["action"]]
        qs = qs.filter(action__in=actions)
    if g.get("agent"):
        a = g["agent"].strip()
        qs = qs.filter(Q(utilisateur__username__icontains=a) | Q(utilisateur__last_name__icontains=a)
                       | Q(utilisateur__first_name__icontains=a) | Q(utilisateur_nom__icontains=a))
    beneficiaire = None
    if g.get("beneficiaire"):
        from beneficiaire.models import Beneficiaire
        beneficiaire = Beneficiaire.objects.filter(code_interne=g["beneficiaire"].strip()).first()
        qs = qs.filter(beneficiaire=beneficiaire) if beneficiaire else qs.none()
    qs = qs.order_by('-timestamp')
    if g.get("export") == "csv":
        reponse = HttpResponse(content_type="text/csv; charset=utf-8")
        reponse["Content-Disposition"] = f'attachment; filename="journal_activite_{timezone.localdate():%Y-%m-%d}.csv"'
        reponse.write("﻿")
        w = csv.writer(reponse, delimiter=";")
        w.writerow(["Date", "Agent", "Action", "Usager", "Objet", "Description", "Adresse IP"])
        for l in qs[:50000]:
            w.writerow([timezone.localtime(l.timestamp).strftime("%d/%m/%Y %H:%M:%S"),
                        l.utilisateur_nom or (l.utilisateur.username if l.utilisateur else ""), l.get_action_display(),
                        l.beneficiaire.code_interne if l.beneficiaire else "", l.objet_libelle, l.description,
                        l.ip_address or ""])
        return reponse
    filtres = g.copy()
    filtres.pop("page", None)
    actions = [("READ", "Consultation"), ("CREATE", "Création"), ("UPDATE", "Modification"), ("DELETE", "Suppression"),
               ("EXPORT", "Export"), ("DOWNLOAD", "Téléchargement"), ("LOGIN", "Connexion"),
               ("LOGIN_FAILED", "Échec de connexion"), ("LOGOUT", "Déconnexion")]
    return render(request, "core/journal_activite.html", {
        "page_obj": Paginator(qs, 100).get_page(g.get("page")), "f": g, "requete": filtres.urlencode(),
        "actions": actions, "beneficiaire": beneficiaire, "du": debut, "au": fin,
        "tout": request.user.is_superuser,
    })
