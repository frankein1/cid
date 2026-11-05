# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/admin.py
from django.contrib import admin

from insertion.models import (ActionInsertion, ContratInsertion, HistoriqueContrat, HistoriquePrescription,
                              LigneActionContrat, ParametresRSA, PoleInsertion, PrescriptionInsertion, QuestionAction,
                              ReponseQuestion, TypeActionInsertion)


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


@admin.register(ParametresRSA)
class ParametresRSAAdmin(admin.ModelAdmin):
    """Une seule ligne : nom du contrat, durées, alerte de renouvellement, heures hebdomadaires, âge du certificat."""
    list_display = ['nom_contrat', 'duree_defaut_mois', 'duree_max_mois', 'duree_sauf_action_mois',
                    'delai_alerte_jours', 'heures_hebdo_min', 'age_limite_certificat']

    def has_add_permission(self, request):
        return not ParametresRSA.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        from django.shortcuts import redirect
        return redirect('admin:insertion_parametresrsa_change', ParametresRSA.courant().pk)


class LigneActionContratInline(admin.TabularInline):
    model = LigneActionContrat
    extra = 0
    raw_id_fields = ['action']


class HistoriqueContratInline(admin.TabularInline):
    model = HistoriqueContrat
    extra = 0
    readonly_fields = ['date', 'user', 'action', 'commentaire']
    can_delete = False


@admin.register(ContratInsertion)
class ContratInsertionAdmin(admin.ModelAdmin):
    """Dépannage seulement : le contrat se rédige et circule dans le module RSA – Insertion."""
    list_display = ['numero', 'beneficiaire', 'type_contrat', 'nature', 'statut', 'mds', 'pole', 'date_fin']
    list_filter = ['statut', 'type_contrat', 'nature', 'pole']
    search_fields = ['beneficiaire__nom', 'beneficiaire__prenom', 'beneficiaire__code_interne']
    raw_id_fields = ['beneficiaire', 'conjoint', 'precedent', 'referent', 'recu_par', 'avis_par', 'decide_par']
    inlines = [LigneActionContratInline, HistoriqueContratInline]


class QuestionActionInline(admin.TabularInline):
    model = QuestionAction
    extra = 0


ActionInsertionAdmin.inlines = list(getattr(ActionInsertionAdmin, 'inlines', [])) + [QuestionActionInline]


class ReponseQuestionInline(admin.TabularInline):
    model = ReponseQuestion
    extra = 0


class HistoriquePrescriptionInline(admin.TabularInline):
    model = HistoriquePrescription
    extra = 0
    readonly_fields = ['date', 'user', 'action', 'commentaire']
    can_delete = False


@admin.register(PrescriptionInsertion)
class PrescriptionInsertionAdmin(admin.ModelAdmin):
    """Dépannage seulement : la prescription se rédige et circule dans le module RSA – Insertion."""
    list_display = ['numero', 'beneficiaire', 'action', 'statut', 'mds', 'date_prescription']
    list_filter = ['statut', 'pole']
    search_fields = ['beneficiaire__nom', 'beneficiaire__prenom', 'action__libelle', 'action__code']
    raw_id_fields = ['beneficiaire', 'action', 'contrat', 'prescripteur', 'valide_par']
    inlines = [ReponseQuestionInline, HistoriquePrescriptionInline]


from insertion.models import CommissionReorientation, DemandeReorientation, ExamenReorientation, OrganismeOrientation  # noqa: E402


@admin.register(OrganismeOrientation)
class OrganismeOrientationAdmin(admin.ModelAdmin):
    list_display = ['nom', 'categorie', 'ville', 'email', 'actif']
    list_filter = ['categorie', 'actif']
    search_fields = ['nom', 'ville']
    filter_horizontal = ['poles']


class ExamenInline(admin.TabularInline):
    model = ExamenReorientation
    extra = 0


@admin.register(CommissionReorientation)
class CommissionReorientationAdmin(admin.ModelAdmin):
    """Dépannage seulement : la commission se prépare et se tient dans le module RSA – Insertion."""
    list_display = ['date', 'pole', 'statut', 'lieu']
    list_filter = ['statut', 'pole']
    filter_horizontal = ['participants']
    inlines = [ExamenInline]


@admin.register(DemandeReorientation)
class DemandeReorientationAdmin(admin.ModelAdmin):
    list_display = ['numero', 'beneficiaire', 'statut', 'orientation_proposee', 'commission', 'organisme_retenu']
    list_filter = ['statut', 'orientation_proposee', 'pole']
    search_fields = ['beneficiaire__nom', 'beneficiaire__prenom']
    raw_id_fields = ['beneficiaire', 'referent', 'contrat', 'commission', 'decide_par']
