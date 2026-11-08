# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/admin_conservation.py
"""Administration → Durées de conservation (RGPD) : télécharger le modèle CSV pour le DPO, importer le fichier
rempli (tout ou rien : la moindre erreur bloque l'import et est affichée ligne par ligne)."""
from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path

from core import conservation as C
from core.models import DureeConservation


class FichierForm(forms.Form):
    fichier = forms.FileField(label="Tableau rempli par le DPO (CSV)")


@admin.register(DureeConservation)
class DureeConservationAdmin(admin.ModelAdmin):
    list_display = ("__str__", "code", "base_active", "archivage", "sort_final", "applique", "importe_le", "importe_par")
    readonly_fields = ("code", "importe_le", "importe_par", "donnees", "reglage_cid")
    fields = ("code", "donnees", "reglage_cid", "base_active_mois", "point_de_depart", "archivage_mois",
              "sort_final", "reference", "commentaire", "importe_le", "importe_par")
    change_list_template = "admin/core/dureeconservation/change_list.html"

    def has_add_permission(self, request):
        return False        # la liste des traitements vient du code (core/conservation.py)

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        existants = set(DureeConservation.objects.values_list("code", flat=True))
        DureeConservation.objects.bulk_create([DureeConservation(code=t[0]) for t in C.TRAITEMENTS
                                               if t[0] not in existants])
        return super().changelist_view(request, extra_context)

    def save_model(self, request, obj, form, change):
        obj.importe_par = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Base active (mois)")
    def base_active(self, obj):
        v = C.mois(obj.code, 'base')
        return "—" if v is None else (f"{v}" if obj.base_active_mois is not None else f"{v} (CID)")

    @admin.display(description="Archivage (mois)")
    def archivage(self, obj):
        v = C.mois(obj.code, 'archivage')
        return "—" if v is None else (f"{v}" if obj.archivage_mois is not None else f"{v} (CID)")

    @admin.display(description="Appliqué par CID", boolean=True)
    def applique(self, obj):
        t = C.PAR_CODE.get(obj.code)
        return bool(t and t[6])

    @admin.display(description="Données concernées")
    def donnees(self, obj):
        t = C.PAR_CODE.get(obj.code)
        return t[2] if t else ""

    @admin.display(description="Réglage d'origine de CID")
    def reglage_cid(self, obj):
        t = C.PAR_CODE.get(obj.code)
        if not t:
            return ""
        return (f"base active {t[3] if t[3] is not None else '—'} mois, archivage {t[4] if t[4] is not None else '—'} "
                f"mois ; point de départ : {t[5]}")

    def get_urls(self):
        return [path("modele.csv", self.admin_site.admin_view(self.vue_modele), name="core_dureeconservation_modele"),
                path("importer/", self.admin_site.admin_view(self.vue_importer), name="core_dureeconservation_importer"),
                ] + super().get_urls()

    def vue_modele(self, request):
        r = HttpResponse(C.modele_csv(), content_type="text/csv; charset=utf-8")
        r["Content-Disposition"] = 'attachment; filename="CID_durees_conservation_a_remplir.csv"'
        return r

    def vue_importer(self, request):
        form = FichierForm(request.POST or None, request.FILES or None)
        erreurs = []
        if request.method == "POST" and form.is_valid():
            n, erreurs = C.importer(form.cleaned_data["fichier"].read(), request.user)
            if not erreurs:
                messages.success(request, f"{n} traitement(s) mis à jour. Les lignes non remplies gardent le réglage "
                                          "de CID.")
                return redirect("admin:core_dureeconservation_changelist")
        return render(request, "admin/core/dureeconservation/importer.html", {
            "form": form, "erreurs": erreurs, "title": "Importer les durées de conservation",
            **self.admin_site.each_context(request)})
