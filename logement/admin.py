# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/admin.py
from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse
from django.urls import path, reverse
from django.utils.html import format_html

from .models import (CommissionPublicsPrioritaires, ConvocationExpulsion, DemandeFSL, DemandeLogementSocial,
                     DestinataireExpulsion, DiagnosticExpulsion, DossierExpulsion, EnvoiDossier, EtapeExpulsion,
                     FormulaireOfficiel, GestionnaireFSL, SaisineCOPP)


@admin.register(GestionnaireFSL)
class GestionnaireFSLAdmin(admin.ModelAdmin):
    list_display = ['nom', 'par_defaut', 'actif']
    list_filter = ['actif']


class FormulaireOfficielForm(forms.ModelForm):
    fichier = forms.FileField(required=False, label="PDF vierge",
                              help_text="Le formulaire officiel vierge (sans aucune donnée d'usager). Il est gardé en base.")

    class Meta:
        model = FormulaireOfficiel
        fields = ['gestionnaire', 'code', 'version', 'reglages', 'actif']

    def clean_fichier(self):
        f = self.cleaned_data.get('fichier')
        if f:
            debut = f.read(5)
            f.seek(0)
            if debut != b'%PDF-':
                raise forms.ValidationError("Le fichier n'est pas un PDF.")
            if f.size > 8 * 1024 * 1024:
                raise forms.ValidationError("PDF trop lourd (8 Mo au plus).")
        elif not (self.instance and self.instance.pk and self.instance.contenu):
            raise forms.ValidationError("Déposez le PDF vierge.")
        return f

    def save(self, commit=True):
        obj = super().save(commit=False)
        f = self.cleaned_data.get('fichier')
        if f:
            obj.contenu = f.read()
            obj.nom_fichier = f.name[:200]
        if commit:
            obj.save()
        return obj


@admin.register(FormulaireOfficiel)
class FormulaireOfficielAdmin(admin.ModelAdmin):
    form = FormulaireOfficielForm
    list_display = ['code', 'gestionnaire', 'version', 'nom_fichier', 'actif', 'apercu']
    list_filter = ['code', 'gestionnaire', 'actif']
    readonly_fields = ['nom_fichier', 'date_depot', 'apercu']

    def apercu(self, obj):
        if not obj.pk or not obj.contenu:
            return "—"
        return format_html('<a href="{}" target="_blank">Aperçu avec des données fictives</a>',
                           reverse('admin:logement_formulaire_apercu', args=[obj.pk]))
    apercu.short_description = "Aperçu"

    def get_urls(self):
        return [path('<int:pk>/apercu/', self.admin_site.admin_view(self.vue_apercu),
                     name='logement_formulaire_apercu')] + super().get_urls()

    def vue_apercu(self, request, pk):
        """Remplit le formulaire avec une demande fictive : on voit où tombe chaque champ ; les clés non placées
        sont listées en en-tête de réponse et en message."""
        from .services.apercu import demande_fictive
        from .services.pdf_officiel import remplir
        from .services.placements_fsl import placements, valeurs
        obj = FormulaireOfficiel.objects.get(pk=pk)
        if obj.code.startswith('EXP_'):
            from .services.expulsion_apercu import apercu
            pdf, rapport = apercu(obj)
        else:
            pdf, rapport = remplir(bytes(obj.contenu), placements(obj.code), valeurs(demande_fictive(), obj.code),
                                   obj.reglages)
        manque = [k for k, v in rapport.items() if v not in ('ok', 'vide')]
        if manque:
            messages.warning(request, f"Champs non placés : {', '.join(manque)}")
        rep = HttpResponse(pdf, content_type='application/pdf')
        rep['Content-Disposition'] = f'inline; filename="apercu_{obj.code}.pdf"'
        rep['X-CID-Champs-Non-Places'] = ",".join(manque)[:2000]
        return rep


@admin.register(DemandeFSL)
class DemandeFSLAdmin(admin.ModelAdmin):
    list_display = ['beneficiaire', 'mds', 'type_aide', 'statut', 'date_envoi', 'date_creation']
    list_filter = ['statut', 'type_aide', 'mds', 'gestionnaire']
    search_fields = ['beneficiaire__nom', 'beneficiaire__code_interne']
    raw_id_fields = ['beneficiaire', 'cadre', 'cree_par']


@admin.register(CommissionPublicsPrioritaires)
class CommissionPublicsPrioritairesAdmin(admin.ModelAdmin):
    list_display = ['date', 'date_limite_depot', 'nom', 'territoire', 'lieu', 'horaire']
    list_filter = ['territoire']
    filter_horizontal = ['mds']


@admin.register(SaisineCOPP)
class SaisineCOPPAdmin(admin.ModelAdmin):
    list_display = ['beneficiaire', 'mds', 'commission', 'statut', 'date_creation']
    list_filter = ['statut', 'mds']
    raw_id_fields = ['beneficiaire', 'cree_par', 'pieces']


@admin.register(DemandeLogementSocial)
class DemandeLogementSocialAdmin(admin.ModelAdmin):
    list_display = ['beneficiaire', 'nud', 'date_creation', 'dalo_depose', 'dalo_etat']
    raw_id_fields = ['beneficiaire']


@admin.register(EnvoiDossier)
class EnvoiDossierAdmin(admin.ModelAdmin):
    """Lecture seule : le compteur de papier évité se remplit tout seul."""
    list_display = ['date', 'nature', 'mds', 'mode', 'pages']
    list_filter = ['mode', 'nature', 'mds']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class EtapeExpulsionInline(admin.TabularInline):
    model = EtapeExpulsion
    extra = 0
    raw_id_fields = ['saisi_par']


@admin.register(DossierExpulsion)
class DossierExpulsionAdmin(admin.ModelAdmin):
    list_display = ['numero', 'nom', 'prenom', 'mds', 'date_audience', 'statut', 'date_reception']
    list_filter = ['statut', 'origine', 'mds']
    search_fields = ['numero', 'nom', 'prenom', 'numero_allocataire']
    raw_id_fields = ['beneficiaire', 'referent', 'cree_par']
    inlines = [EtapeExpulsionInline]


@admin.register(DestinataireExpulsion)
class DestinataireExpulsionAdmin(admin.ModelAdmin):
    list_display = ['nom', 'type_destinataire', 'email', 'actif']
    list_filter = ['type_destinataire', 'actif']
    filter_horizontal = ['mds']


@admin.register(DiagnosticExpulsion)
class DiagnosticExpulsionAdmin(admin.ModelAdmin):
    list_display = ['dossier', 'type_document', 'statut', 'redacteur', 'cadre', 'date_envoi']
    list_filter = ['type_document', 'statut']
    raw_id_fields = ['dossier', 'redacteur', 'cadre']


@admin.register(ConvocationExpulsion)
class ConvocationExpulsionAdmin(admin.ModelAdmin):
    list_display = ['dossier', 'type_convocation', 'date_rdv', 'agent', 'statut']
    list_filter = ['type_convocation', 'statut']
    raw_id_fields = ['dossier', 'agent', 'rdv', 'cree_par']
