# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/views/demo.py
"""
Données de démonstration : remise à zéro depuis CID, pour les hébergements sans accès au shell
(offre gratuite de Render). Même effet que « python manage.py init_demo --reinitialiser ».
Réservé au super-administrateur.
"""
from io import StringIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render


@login_required
def demo_reinitialiser(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Réservé au super-administrateur.")
    journal = None
    if request.method == "POST":
        if request.POST.get("confirmation", "").strip().upper() != "REINITIALISER":
            messages.error(request, "Tapez REINITIALISER pour confirmer.")
            return redirect("core:demo_reinitialiser")
        sortie = StringIO()
        try:
            call_command("init_demo", reinitialiser=True, stdout=sortie)
            messages.success(request, "Données de démonstration recréées, avec des dates recalculées à partir d'aujourd'hui.")
        except Exception as e:  # le détail reste affiché pour le diagnostic
            messages.error(request, f"La réinitialisation a échoué : {e}")
        journal = sortie.getvalue()
    return render(request, "core/demo_reinitialiser.html", {"journal": journal})
