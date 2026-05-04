# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# ged/admin.py
from django.contrib import admin
from .models import (
    DocumentGED,
    DocumentType,
    HistoriqueDocument,
    PartageDocument,
    DocumentVersion,
)

@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ('code', 'nom', 'categorie', 'actif', 'est_sensible')
    list_filter = ('categorie', 'actif', 'est_sensible')
    search_fields = ('code', 'nom')


class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 0
    can_delete = False
    readonly_fields = (
        'numero',
        'seaweedfs_id',
        'extension',
        'taille_octets',
        'hash_md5',
        'cree_par',
        'date_creation',
    )
    ordering = ('-numero',)


@admin.register(DocumentGED)
class DocumentGEDAdmin(admin.ModelAdmin):
    list_display = (
        'titre',
        'get_categorie',
        'statut',
        'uploaded_by',
        'date_creation',
    )
    list_filter = ('statut', 'confidentialite', 'type_document__categorie')
    search_fields = ('titre', 'hash_md5', 'seaweedfs_id')
    readonly_fields = ('hash_md5', 'taille_octets', 'extension', 'date_creation')
    inlines = [DocumentVersionInline]

    def get_categorie(self, obj):
        return obj.type_document.get_categorie_display()
    get_categorie.short_description = "Catégorie"


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = (
        'document',
        'numero',
        'extension',
        'taille_octets',
        'cree_par',
        'date_creation',
    )
    readonly_fields = list_display
    ordering = ('-date_creation',)


@admin.register(HistoriqueDocument)
class HistoriqueDocumentAdmin(admin.ModelAdmin):
    list_display = ('date_action', 'action', 'utilisateur', 'document_titre_archive')
    readonly_fields = list_display


@admin.register(PartageDocument)
class PartageDocumentAdmin(admin.ModelAdmin):
    list_display = ('document', 'email_destinataire', 'date_expiration', 'utilise')
