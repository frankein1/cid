# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# partenaires/admin.py
from django.contrib import admin

from .models import Partenaire


@admin.register(Partenaire)
class PartenaireAdmin(admin.ModelAdmin):
    list_display = ('organisme', 'contact', 'thematique', 'email', 'telephone', 'ville', 'actif')
    list_filter = ('thematique', 'actif')
    search_fields = ('organisme', 'service', 'nom_contact', 'email', 'ville')
