# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

"""
Administration Django pour l'application bénéficiaire - VERSION RÉSEAU FAMILIAL
Fichier : beneficiaire/admin.py
✅ CRÉATION OK + LIENS AFFICHAGE SANS ERREUR
"""

from django.contrib import admin
from .models import Beneficiaire, DocumentBeneficiaireLink, LienFamilial

# ---------------------------------------------------------------------
# INLINE LIENS FAMILIAUX - LECTURE SEULE (SANS ERREUR)
# ---------------------------------------------------------------------
class LienFamilialInline(admin.TabularInline):
    model = LienFamilial
    fk_name = "personne_a"
    extra = 0
    can_delete = False
    show_change_link = True
    fields = ['personne_b', 'type_lien', 'vit_au_foyer']
    readonly_fields = ['personne_b', 'type_lien', 'vit_au_foyer']
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Beneficiaire)
class BeneficiaireAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'code_interne', 'mds', 'statut', 'compte_liens')  # ✅ Nom différent
    list_filter = ('statut', 'mds', 'civilite')
    search_fields = ('nom', 'prenom', 'code_interne', 'nir')
    
    readonly_fields = ['code_interne', 'date_creation', 'date_modification']
    
    inlines = [LienFamilialInline]
    
    fieldsets = (
        ('Identification', {'fields': ('code_interne', 'statut')}),
        ('Informations Personnelles', {
            'fields': ('civilite', 'nom', 'prenom', 'nom_naissance', 'date_naissance', 'lieu_naissance', 'marital_status')
        }),
        ('Coordonnées', {
            'fields': ('telephone_mobile', 'telephone_fixe', 'email', 'adresse', 'code_postal', 'ville')
        }),
        ('Informations Administratives', {
            'fields': ('nir', 'numero_caf', 'numero_france_travail', 'numero_fiscal', 'numero_dossier_pmi', 'date_entree', 'date_sortie', 'motif_sortie', 'detail_sortie')
        }),
        ('Rattachement', {'fields': ('mds', 'referent_mds')}),
        ('Tracking', {
            'fields': ('date_creation', 'date_modification', 'cree_par'),
            'classes': ('collapse',), 
        }),
    )
    
    def compte_liens(self, obj):
        """✅ SANS format_html - simple texte"""
        if not obj:
            return "0"
        try:
            count = obj.liens_familiaux.count()
            return f"{count}" if count > 0 else "0"
        except:
            return "0"
    compte_liens.short_description = "Liens"

@admin.register(LienFamilial)
class LienFamilialAdmin(admin.ModelAdmin):
    list_display = ('personne_a', 'type_lien', 'personne_b', 'vit_au_foyer')
    list_filter = ('type_lien', 'vit_au_foyer')
    search_fields = ('personne_a__nom', 'personne_b__nom')

@admin.register(DocumentBeneficiaireLink)
class DocumentBeneficiaireLinkAdmin(admin.ModelAdmin):
    list_display = ['beneficiaire', 'type_document', 'document_ged', 'valide', 'date_creation']
    list_filter = ['type_document', 'valide', 'date_creation']
    search_fields = ['beneficiaire__nom', 'beneficiaire__prenom', 'document_ged__titre']
    readonly_fields = ['date_creation']
    
    fieldsets = (
        ('Liaison', {'fields': ('beneficiaire', 'document_ged', 'type_document')}),
        ('Validation', {'fields': ('valide',)}),
        ('Métadonnées', {
            'fields': ('date_creation', 'cree_par'),
            'classes': ('collapse',),
        }),
    )


from .models import OperationRGPD  # noqa: E402


@admin.register(OperationRGPD)
class OperationRGPDAdmin(admin.ModelAdmin):
    """Traces des archivages et effacements : consultation seulement."""
    list_display = ('date', 'action', 'motif', 'mds', 'beneficiaire', 'par')
    list_filter = ('action', 'motif', 'mds')
    readonly_fields = [f.name for f in OperationRGPD._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


from .models import ValeurListe  # noqa: E402


@admin.register(ValeurListe)
class ValeurListeAdmin(admin.ModelAdmin):
    """Listes de valeurs de la fiche usager : renommer, réordonner, désactiver ou ajouter une valeur."""
    list_display = ('libelle', 'liste', 'ordre', 'actif')
    list_editable = ('ordre', 'actif')
    list_filter = ('liste', 'actif')
    search_fields = ('libelle',)

    def has_delete_permission(self, request, obj=None):
        return False   # une valeur déjà utilisée ne se supprime pas : on la désactive


from .models_budget import BudgetFoyer  # noqa: E402


@admin.register(BudgetFoyer)
class BudgetFoyerAdmin(admin.ModelAdmin):
    list_display = ('beneficiaire', 'date_etabli', 'nb_personnes_foyer', 'reste_a_vivre')
    raw_id_fields = ('beneficiaire',)
    readonly_fields = ('reste_a_vivre', 'cree_par', 'modifie_par')


from .models_journal import EntretienSocial, TypeAccompagnement  # noqa: E402


@admin.register(TypeAccompagnement)
class TypeAccompagnementAdmin(admin.ModelAdmin):
    list_display = ('libelle', 'code', 'legal', 'ordre', 'actif')
    list_editable = ('legal', 'ordre', 'actif')
    list_filter = ('legal', 'actif')
    prepopulated_fields = {'code': ('libelle',)}


@admin.register(EntretienSocial)
class EntretienSocialAdmin(admin.ModelAdmin):
    """Pas de synthèse dans l'administration : la synthèse privée n'est lisible que par son auteur, dans CID."""
    list_display = ('date', 'beneficiaire', 'objet', 'mode', 'auteur')
    list_filter = ('mode', 'types')
    raw_id_fields = ('beneficiaire', 'creneau')
    exclude = ('synthese_privee',)
    readonly_fields = ('auteur', 'cree_par', 'modifie_par')
