# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

# mds/admin.py
from django.contrib import admin
from .models import MDS, MDSReception, DemiJourneeReception, UserMDSProfile

@admin.register(UserMDSProfile)
class UserMDSProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "mds", "fonction", "principale", "actif", "equipe_ip", "herite_de", "date_debut"]
    list_filter = ["mds", "fonction", "principale", "actif", "equipe_ip"]
    readonly_fields = ["herite_de"]
    search_fields = ["user__last_name", "user__first_name", "user__username", "mds__nom"]
    autocomplete_fields = ["user", "mds"]
    list_editable = ["actif", "principale"]

@admin.register(MDS)
class MDSAdmin(admin.ModelAdmin):
    list_display = ["code_mds", "nom", "type_mds", "mds_territoire", "ville", "active", "get_utilisateurs_count"]
    list_filter = ["active", "type_mds", "ville"]
    search_fields = ["code_mds", "nom", "ville", "communes", "adresse"]

    fieldsets = (
        ("Identification", {
            "fields": ("code_mds", "nom", "active", "type_mds", "mds_territoire"),
        }),
        ("Localisation", {
            "fields": ("adresse", "code_postal", "ville", "departement", "communes", "latitude", "longitude"),
        }),
        ("Contact", {
            "fields": ("telephone", "email", "site_web"),
        }),
        ("Gestion", {
            "fields": ("responsable", "date_ouverture", "date_fermeture", "nb_agents_max"),
        }),
        ("Services et configuration", {
            "fields": ("services_proposes", "configuration"),
            "classes": ("collapse",),
        }),
    )

    def get_utilisateurs_count(self, obj):
        return obj.profils_utilisateurs.filter(actif=True).count()
    get_utilisateurs_count.short_description = "Agents Actifs"

@admin.register(MDSReception)
class MDSReceptionAdmin(admin.ModelAdmin):
    list_display = ["nom", "mds", "type_salle", "capacite", "actif"]
    list_filter = ["mds", "type_salle", "actif"]
    search_fields = ["nom", "mds__code_mds"]

@admin.register(DemiJourneeReception)
class DemiJourneeReceptionAdmin(admin.ModelAdmin):
    list_display = ("agent", "mds", "jour_semaine", "type_demi_journee", "actif")
    list_filter = ("mds", "agent", "jour_semaine", "actif")
    list_editable = ("actif",)



from django import forms  # noqa: E402

from .models import SignatureAgent  # noqa: E402


class SignatureAgentForm(forms.ModelForm):
    fichier = forms.ImageField(required=False, label="Image de la signature (PNG ou JPG, fond blanc)")

    class Meta:
        model = SignatureAgent
        fields = ['user', 'validee']

    def clean_fichier(self):
        f = self.cleaned_data.get('fichier')
        if f and f.size > 1024 * 1024:
            raise forms.ValidationError("Image trop lourde (1 Mo au plus).")
        if not f and not (self.instance.pk and self.instance.image):
            raise forms.ValidationError("Déposez l'image de la signature.")
        return f

    def save(self, commit=True):
        obj = super().save(commit=False)
        f = self.cleaned_data.get('fichier')
        if f:
            obj.image, obj.type_image = f.read(), getattr(f, 'content_type', 'image/png') or 'image/png'
        if commit:
            obj.save()
        return obj


@admin.register(SignatureAgent)
class SignatureAgentAdmin(admin.ModelAdmin):
    """Signature numérisée d'un cadre : apposée avec son visa seulement une fois « usage validé »."""
    form = SignatureAgentForm
    list_display = ['user', 'validee', 'date_depot']
    list_filter = ['validee']
    autocomplete_fields = ['user']
