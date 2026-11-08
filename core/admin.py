# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

# core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from .models import User
from core.models.capacite import Capacite
from core.models.profil import Profil
from mds.models import UserMDSProfile


# ----------------------------------------------------------------------
# INLINE MDS
# ----------------------------------------------------------------------

class UserMDSProfileInline(admin.TabularInline):
    model = UserMDSProfile
    extra = 0
    fk_name = "user"
    fields = ("mds", "principale", "peut_gerer_utilisateurs", "actif")
    autocomplete_fields = ("mds",)


# ----------------------------------------------------------------------
# USER ADMIN (À NE JAMAIS SUPPRIMER)
# ----------------------------------------------------------------------

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    inlines = [UserMDSProfileInline]

    list_display = (
        "username",
        "matricule",
        "last_name",
        "first_name",
        "email",
        "is_active",
        "is_staff",
    )
    search_fields = ("username", "matricule", "last_name", "first_name", "email")
    ordering = ("last_name", "first_name")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email", "matricule")}),
        (_("Professional"), {
            "fields": ("telephone_professionnel", "telephone_mobile", "email_professionnel"),
        }),
        (_("Organization"), {
            "fields": ("mds_principale", "services_secondaires"),
        }),
        (_("Profiles & permissions"), {
            "fields": ("profils", "is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
        }),
        (_("Security"), {
            "fields": ("force_change_password", "double_authentification_active"),
        }),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "matricule", "email", "password1", "password2", "is_staff", "is_superuser"),
        }),
    )

    actions = ["reset_password_action"]

    def reset_password_action(self, request, queryset):
        """Règle CID : initiales en majuscules + date du jour (jjmmaaaa), à changer dès la connexion."""
        from core.mot_de_passe import reinitialiser
        provisoires = [f"{user.username} : {reinitialiser(user)}" for user in queryset]
        self.message_user(
            request,
            "Mots de passe provisoires (à changer dès la connexion) – " + " ; ".join(provisoires)
        )

    reset_password_action.short_description = (
        "Réinitialiser le mot de passe (et forcer le changement)"
    )


# ----------------------------------------------------------------------
# CAPACITÉS & PROFILS
# ----------------------------------------------------------------------

@admin.register(Capacite)
class CapaciteAdmin(admin.ModelAdmin):
    list_display = ("code", "nom", "actif")
    search_fields = ("code", "nom")
    list_filter = ("actif",)


@admin.register(Profil)
class ProfilAdmin(admin.ModelAdmin):
    list_display = ("code", "nom", "actif")
    search_fields = ("code", "nom")
    list_filter = ("actif",)
    filter_horizontal = ("capacites",)

from core import admin_courriers  # noqa: E402,F401  (modèles de courriers)
from core import admin_conservation  # noqa: E402,F401  (durées de conservation RGPD)


from .models import IdentiteProConnect  # noqa: E402


@admin.register(IdentiteProConnect)
class IdentiteProConnectAdmin(admin.ModelAdmin):
    """Comptes reliés à ProConnect : supprimer la ligne coupe le lien (la personne repasse par son courriel)."""
    list_display = ('user', 'courriel', 'siret', 'idp_id', 'date_lien', 'derniere_connexion')
    search_fields = ('user__username', 'courriel', 'siret')
    readonly_fields = ('sub', 'idp_id', 'siret', 'courriel', 'date_lien', 'derniere_connexion')
