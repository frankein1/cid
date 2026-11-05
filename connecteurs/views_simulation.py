# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/views_simulation.py
"""Simulation des droits (OpenFisca) depuis la fiche usager — rien n'est enregistré ni envoyé hors du serveur."""
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render

from beneficiaire.models import Beneficiaire
from . import simulation_droits as sd


def _montant(texte):
    try:
        return max(0.0, float((texte or "0").replace(",", ".").replace(" ", "")))
    except ValueError:
        return 0.0


@login_required
def simuler_droits(request, code_interne):
    beneficiaire = get_object_or_404(Beneficiaire, code_interne=code_interne)
    if beneficiaire.niveau_acces(request.user) != 'complet':
        return HttpResponseForbidden("Réservé aux agents de la MDS de l'usager.")
    conjoint, enfants = sd.foyer(beneficiaire)
    p = request.POST
    saisie = {
        "ressources": {qui: {v: _montant(p.get(f"{qui}_{v}")) for v, _ in sd.RESSOURCES}
                       for qui in (["demandeur", "conjoint"] if conjoint else ["demandeur"])},
        "logement": p.get("logement") if p.get("logement") in dict(sd.LOGEMENTS) else "locataire_vide",
        "loyer": _montant(p.get("loyer")),
        "zone": p.get("zone") if p.get("zone") in dict(sd.ZONES) else "zone_2",
    }
    resultats = version = erreur = None
    if request.method == "POST":
        try:
            resultats, version = sd.simuler(beneficiaire, saisie)
        except sd.SimulationErreur as e:
            erreur = str(e)
    personnes = [("demandeur", beneficiaire)] + ([("conjoint", conjoint)] if conjoint else [])
    lignes_ressources = [(v, lib, [(qui, f"{qui}_{v}", saisie["ressources"][qui][v]) for qui, _ in personnes])
                         for v, lib in sd.RESSOURCES]
    return render(request, 'connecteurs/simulation_droits.html', {
        'beneficiaire': beneficiaire, 'conjoint': conjoint, 'enfants': enfants, 'personnes': personnes,
        'lignes_ressources': lignes_ressources, 'saisie': saisie, 'logements': sd.LOGEMENTS, 'zones': sd.ZONES,
        'resultats': resultats, 'total': sum(m for _, m in resultats) if resultats else None,
        'version': version, 'erreur': erreur, 'disponible': sd.disponible(),
    })
