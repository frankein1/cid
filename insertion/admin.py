# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/admin.py
from django.contrib import admin

from insertion.models import ActionInsertion, PoleInsertion, TypeActionInsertion


@admin.register(PoleInsertion)
class PoleInsertionAdmin(admin.ModelAdmin):
    list_display = ['code', 'nom', 'ville', 'email_mssante_medecin', 'actif']
    list_filter = ['actif']
    search_fields = ['code', 'nom', 'ville']
    filter_horizontal = ['mds', 'membres']


@admin.register(TypeActionInsertion)
class TypeActionInsertionAdmin(admin.ModelAdmin):
    """Typologie commune des actions : désactiver plutôt que supprimer (les actions y sont rattachées)."""
    list_display = ['libelle', 'code', 'ordre', 'actif']
    list_editable = ['ordre', 'actif']
    prepopulated_fields = {'code': ('libelle',)}


@admin.register(ActionInsertion)
class ActionInsertionAdmin(admin.ModelAdmin):
    """Saisie courante : menu RSA – Insertion (avec import CSV). L'administration sert au dépannage."""
    list_display = ['code', 'libelle', 'type_action', 'niveau', 'mds', 'actif']
    list_filter = ['niveau', 'type_action', 'actif', 'poles']
    search_fields = ['code', 'libelle', 'porteur', 'territoire']
    filter_horizontal = ['poles']
    raw_id_fields = ['partenaire']

    def changelist_view(self, request, extra_context=None):
        from django.contrib import messages
        from django.urls import reverse
        from django.utils.html import format_html
        messages.info(request, format_html(
            "L'import et l'export CSV des actions se font dans le module : <a href=\"{}\">RSA – Insertion › Importer (CSV)</a>.",
            reverse('insertion:actions_import')))
        return super().changelist_view(request, extra_context)
