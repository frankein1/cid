# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# ru/admin.py
from django.contrib import admin

from .models import DemandeRelationUsager, FicheRetourSAS, HistoriqueRU, RelanceRU


class RelanceInline(admin.TabularInline):
    model = RelanceRU
    extra = 0
    readonly_fields = ("date_relance", "commentaire", "effectuee_par", "transmission_direction")


class HistoriqueInline(admin.TabularInline):
    model = HistoriqueRU
    extra = 0
    can_delete = False
    readonly_fields = ("action", "detail", "acteur", "date_action")


class FicheRetourSASInline(admin.StackedInline):
    model = FicheRetourSAS
    extra = 0
    max_num = 1
    readonly_fields = ("date_transmission", "transmis_par")


@admin.register(DemandeRelationUsager)
class DemandeRelationUsagerAdmin(admin.ModelAdmin):
    list_display = ("reference", "nom_usager", "objet", "mds", "priorite", "statut", "date_reception")
    list_filter = ("statut", "priorite", "circuit", "mds")
    search_fields = ("nom_usager", "prenom_usager", "objet", "reference_externe")
    readonly_fields = ("cree_par", "modifie_par", "created_at", "updated_at", "date_escalade_direction")
    inlines = (FicheRetourSASInline, RelanceInline, HistoriqueInline)
