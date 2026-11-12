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

from .models import (CommissionExpulsion, CommissionPublicsPrioritaires, ConvocationExpulsion, PassageCommission, DemandeFSL, DemandeLogementSocial,
                     DestinataireExpulsion, DiagnosticExpulsion, DossierExpulsion, EnvoiDossier, EtapeExpulsion,
                     FormulaireOfficiel, GestionnaireFSL, SaisineCOPP)
from .models import OperateurASELL, OrientationASELL
from .models import RecoursDALO
from .models import (DemarcheHebergement, DestinataireHebergement, DossierHebergement, FicheHebergement,
                     RappelHebergement, SignalementHabitatIndigne, StructureHebergement)


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


class PassageCommissionInline(admin.TabularInline):
    model = PassageCommission
    extra = 0
    fields = ['dossier', 'statut', 'avis']
    raw_id_fields = ['dossier']


@admin.register(CommissionExpulsion)
class CommissionExpulsionAdmin(admin.ModelAdmin):
    list_display = ['date', 'nom', 'type_commission', 'date_limite', 'tenue']
    list_filter = ['type_commission', 'tenue']
    filter_horizontal = ['mds']
    inlines = [PassageCommissionInline]


class DemarcheHebergementInline(admin.TabularInline):
    model = DemarcheHebergement
    extra = 0
    raw_id_fields = ['saisi_par']


@admin.register(StructureHebergement)
class StructureHebergementAdmin(admin.ModelAdmin):
    list_display = ['nom', 'ville', 'public', 'duree_initiale_jours', 'duree_renouvellement_jours', 'actif']
    list_filter = ['actif']
    search_fields = ['nom', 'ville']


@admin.register(DestinataireHebergement)
class DestinataireHebergementAdmin(admin.ModelAdmin):
    list_display = ['nom', 'email', 'est_sas', 'actif']
    list_editable = ['est_sas']


@admin.register(RappelHebergement)
class RappelHebergementAdmin(admin.ModelAdmin):
    list_display = ['code', 'actif']
    list_editable = ['actif']
    fields = ['code', 'texte', 'reference', 'actif']


@admin.register(DossierHebergement)
class DossierHebergementAdmin(admin.ModelAdmin):
    list_display = ['numero', 'beneficiaire', 'mds', 'statut', 'structure', 'date_entree', 'date_fin_prevue']
    list_filter = ['statut', 'mds']
    search_fields = ['numero', 'beneficiaire__nom', 'beneficiaire__prenom']
    raw_id_fields = ['beneficiaire', 'referent', 'cree_par']
    inlines = [DemarcheHebergementInline]


@admin.register(FicheHebergement)
class FicheHebergementAdmin(admin.ModelAdmin):
    list_display = ['dossier', 'type_fiche', 'statut', 'redacteur', 'cadre', 'date_envoi', 'reponse']
    list_filter = ['type_fiche', 'statut', 'reponse']
    raw_id_fields = ['dossier', 'redacteur', 'cadre']


class FichierOperateursForm(forms.Form):
    fichier = forms.FileField(label="Tableau des opérateurs (CSV ou Excel)")


@admin.register(OperateurASELL)
class OperateurASELLAdmin(admin.ModelAdmin):
    """Liste annuelle des opérateurs conventionnés : importée d'un fichier (tout ou rien), ligne à ligne ensuite."""
    list_display = ['sigle', 'nom', 'ville', 'thematique', 'nature', 'territoire_court', 'emails', 'annee', 'actif']
    list_filter = ['actif', 'annee', 'nature', 'thematique']
    search_fields = ['sigle', 'nom', 'territoire', 'cp_ville']
    fields = ['sigle', 'nom', 'adresse', 'cp_ville', 'telephone', 'emails', 'nature', 'thematique', 'territoire',
              'public_specifique', 'annee', 'actif']
    change_list_template = "admin/logement/operateurasell/change_list.html"

    @admin.display(description="Territoire")
    def territoire_court(self, obj):
        return (obj.territoire[:80] + "…") if len(obj.territoire or "") > 80 else obj.territoire

    def get_urls(self):
        return [path("modele.csv", self.admin_site.admin_view(self.vue_modele),
                     name="logement_operateurasell_modele"),
                path("importer/", self.admin_site.admin_view(self.vue_importer),
                     name="logement_operateurasell_importer")] + super().get_urls()

    def vue_modele(self, request):
        from .services import asell_operateurs as AO
        r = HttpResponse(AO.modele_csv(), content_type="text/csv; charset=utf-8")
        r["Content-Disposition"] = 'attachment; filename="CID_operateurs_ASELL_modele.csv"'
        return r

    def vue_importer(self, request):
        from django.shortcuts import redirect, render
        from .services import asell_operateurs as AO
        form = FichierOperateursForm(request.POST or None, request.FILES or None)
        erreurs, avertissements = [], []
        if request.method == "POST" and form.is_valid():
            f = form.cleaned_data["fichier"]
            n, anciens, erreurs, avertissements = AO.importer(f.read(), f.name)
            if not erreurs:
                messages.success(request, f"{n} ligne(s) importée(s). {anciens} ligne(s) de l'ancienne liste désactivée(s) "
                                          "(elles restent consultables, les fiches déjà envoyées gardent leur opérateur).")
                for a in avertissements:
                    messages.warning(request, a)
                return redirect("admin:logement_operateurasell_changelist")
        return render(request, "admin/logement/operateurasell/importer.html", {
            "form": form, "erreurs": erreurs, "title": "Importer la liste des opérateurs conventionnés",
            **self.admin_site.each_context(request)})


@admin.register(OrientationASELL)
class OrientationASELLAdmin(admin.ModelAdmin):
    list_display = ['beneficiaire', 'type_mesure', 'volet', 'operateur', 'statut', 'date_envoi', 'reponse']
    list_filter = ['type_mesure', 'volet', 'statut', 'reponse']
    raw_id_fields = ['beneficiaire', 'dossier_expulsion', 'cree_par']


@admin.register(SignalementHabitatIndigne)
class SignalementHabitatIndigneAdmin(admin.ModelAdmin):
    list_display = ('id', 'beneficiaire', 'mds', 'origine', 'statut', 'date_creation')
    list_filter = ('statut', 'origine', 'mds')
    search_fields = ('beneficiaire__nom', 'beneficiaire__prenom')
    readonly_fields = ('historique', 'date_creation', 'date_modification')


@admin.register(RecoursDALO)
class RecoursDALOAdmin(admin.ModelAdmin):
    list_display = ('id', 'beneficiaire', 'nationalite', 'date_modification', 'modifie_par')
    search_fields = ('beneficiaire__nom', 'beneficiaire__prenom', 'nud')
    readonly_fields = ('date_modification',)
