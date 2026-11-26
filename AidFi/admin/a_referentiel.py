# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/admin/a_referentiel.py
"""Référentiel d'aide à la décision AFASE et paramètres : saisis d'après la note de service en vigueur."""
from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path

from AidFi.models.m_referentiel import (
    DestinataireUAGAF, MontantIndicatifAFASE, MotifRefusAFASE, ParametresAides, ReferentielMotifAFASE
)
from AidFi.services.destinataires_uagaf import importer_destinataires


@admin.register(ParametresAides)
class ParametresAidesAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'seuil_montant_controle', 'seuil_nb_aides_12_mois', 'regie_montant_max']

    def has_add_permission(self, request):
        return not ParametresAides.objects.exists()   # une seule ligne


class MontantInline(admin.TabularInline):
    model = MontantIndicatifAFASE
    extra = 1


@admin.register(ReferentielMotifAFASE)
class ReferentielMotifAdmin(admin.ModelAdmin):
    list_display = ['code', 'libelle', 'actif']
    list_editable = ['actif']
    inlines = [MontantInline]


@admin.register(MotifRefusAFASE)
class MotifRefusAdmin(admin.ModelAdmin):
    list_display = ['code', 'libelle']


from AidFi.models.m_recours import RecoursAFASE   # noqa: E402


@admin.register(RecoursAFASE)
class RecoursAFASEAdmin(admin.ModelAdmin):
    list_display = ['demande', 'type_recours', 'date_recours', 'issue', 'date_issue', 'nouvelle_demande']
    list_filter = ['type_recours', 'issue']
    raw_id_fields = ['demande', 'nouvelle_demande']
    readonly_fields = ['enregistre_par', 'date_creation', 'date_modification']


class ImportDestinatairesForm(forms.Form):
    fichier = forms.FileField(label="Fichier CSV (séparateur « ; »)",
                              help_text="En-tête : nom;email;actif (actif : oui ou non)")


@admin.register(DestinataireUAGAF)
class DestinataireUAGAFAdmin(admin.ModelAdmin):
    """Adresses de l'UAGAF pour l'envoi des AFASE par mail. Saisies ici ou importées par fichier CSV."""
    list_display = ['nom', 'email', 'actif']
    list_editable = ['actif']
    search_fields = ['nom', 'email']
    change_list_template = 'admin/aidfi/destinataireuagaf/change_list.html'

    def get_urls(self):
        return [path('importer/', self.admin_site.admin_view(self.importer), name='aidfi_destinataireuagaf_importer')
                ] + super().get_urls()

    def importer(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied
        if request.method == 'POST':
            form = ImportDestinatairesForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    texte = request.FILES['fichier'].read().decode('utf-8-sig')
                    crees, maj = importer_destinataires(texte)
                except UnicodeDecodeError:
                    messages.error(request, "Le fichier doit être en UTF-8.")
                except ValueError as e:
                    messages.error(request, str(e))
                else:
                    messages.success(request, f"Import terminé : {crees} destinataire(s) créé(s), {maj} mis à jour.")
                    return redirect('admin:AidFi_destinataireuagaf_changelist')
        else:
            form = ImportDestinatairesForm()
        contexte = dict(self.admin_site.each_context(request), opts=self.model._meta, form=form,
                        title="Importer les destinataires de l'UAGAF")
        return TemplateResponse(request, 'admin/aidfi/destinataireuagaf/importer.html', contexte)
