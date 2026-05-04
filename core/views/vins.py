# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================


from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.core.management import call_command

@staff_member_required
def run_install(request):
    try:
        call_command("install")
        return HttpResponse("Installation terminée !")
    except Exception as e:
        return HttpResponse(f"Erreur lors de l'installation : {e}", status=500)
