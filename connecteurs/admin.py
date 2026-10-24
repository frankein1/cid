# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/admin.py
from django.contrib import admin

from .models import SituationExterne, JournalAppelAPI


@admin.register(SituationExterne)
class SituationExterneAdmin(admin.ModelAdmin):
    list_display = ('beneficiaire', 'source', 'statut_appel', 'resume', 'date_maj', 'maj_par', 'environnement')
    list_filter = ('source', 'statut_appel', 'environnement')
    search_fields = ('beneficiaire__nom', 'beneficiaire__code_interne')


@admin.register(JournalAppelAPI)
class JournalAppelAPIAdmin(admin.ModelAdmin):
    list_display = ('date', 'utilisateur', 'beneficiaire', 'source', 'code_http', 'statut_appel', 'environnement')
    list_filter = ('source', 'statut_appel', 'environnement')
    readonly_fields = [f.name for f in JournalAppelAPI._meta.fields]
