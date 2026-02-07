# core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import User
from mds.models import UserMDSProfile


class UserMDSProfileInline(admin.TabularInline):
    model = UserMDSProfile
    extra = 0
    fk_name = "user"
    fields = ("mds", "principale", "peut_gerer_utilisateurs", "actif")
    autocomplete_fields = ("mds",)


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
        """
        Action admin pour forcer un reset/mot de passe temporaire.
        Met force_change_password=True et définit un mot de passe temporaire.
        """
        for user in queryset:
            user.force_change_password = True
            user.set_password("ChangeMe123!")  # À adapter / sécuriser
            user.save()
        self.message_user(
            request,
            "Mot de passe réinitialisé pour les utilisateurs sélectionnés. "
            "Ils devront le modifier à la prochaine connexion."
        )

    reset_password_action.short_description = (
        "Réinitialiser le mot de passe (et forcer le changement)"
    )
