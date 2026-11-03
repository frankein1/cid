# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/admin_courriers.py
"""
Administration des modèles de courriers : texte modifiable, variables disponibles, aperçu PDF,
retour au texte d'origine, export et import JSON (pour reprendre les modèles d'un serveur à l'autre).
"""
import json

from django import forms
from django.contrib import admin, messages
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from core.courriers import rendu
from core.courriers.registre import CHAMPS, COURRIERS
from core.models import ModeleCourrier

FORMAT_EXPORT = "cid-modeles-courriers"


def erreurs_modele(code, textes):
    d = COURRIERS[code]
    erreurs = {}
    for champ in CHAMPS:
        e = rendu.verifier(textes.get(champ, ""), d["variables"], d.get("conditions", {}))
        if e:
            erreurs[champ] = e
    return erreurs


class ModeleCourrierForm(forms.ModelForm):
    class Meta:
        model = ModeleCourrier
        fields = ("objet", "corps", "signature")
        widgets = {"corps": forms.Textarea(attrs={"rows": 24, "cols": 110, "style": "font-family: monospace"}),
                   "signature": forms.Textarea(attrs={"rows": 4, "cols": 60}),
                   "objet": forms.TextInput(attrs={"size": 110})}

    def clean(self):
        donnees = super().clean()
        for champ, liste in erreurs_modele(self.instance.code, donnees).items():
            self.add_error(champ, "; ".join(liste))
        return donnees


class ImportForm(forms.Form):
    fichier = forms.FileField(label="Fichier JSON exporté depuis CID")


@admin.register(ModeleCourrier)
class ModeleCourrierAdmin(admin.ModelAdmin):
    form = ModeleCourrierForm
    list_display = ("__str__", "rubrique", "est_modifie", "modifie_le", "modifie_par")
    actions = ("remettre_origine", "exporter")
    readonly_fields = ("courrier", "mode_d_emploi", "variables_disponibles", "apercu")
    change_list_template = "admin/core/modelecourrier/change_list.html"

    def get_fieldsets(self, request, obj=None):
        champs = ["objet", "corps"] + (["signature"] if obj and obj.definition and "signature" in obj.definition else [])
        return [(None, {"fields": ["courrier", "apercu"]}),
                ("Texte", {"fields": champs}),
                ("Aide à la saisie", {"fields": ["mode_d_emploi", "variables_disponibles"]})]

    def has_add_permission(self, request):
        return False      # la liste des courriers vient du code (core/courriers/registre.py)

    def has_delete_permission(self, request, obj=None):
        return False      # pour revenir au texte de départ : action « Remettre le texte d'origine »

    def changelist_view(self, request, extra_context=None):
        ModeleCourrier.creer_manquants()
        return super().changelist_view(request, extra_context)

    def save_model(self, request, obj, form, change):
        obj.modifie_par = request.user
        super().save_model(request, obj, form, change)

    # ------------------------------------------------------------------ affichages
    @admin.display(description="Rubrique")
    def rubrique(self, obj):
        return (obj.definition or {}).get("rubrique", "")

    @admin.display(description="Courrier")
    def courrier(self, obj):
        return format_html("<b>{}</b> <code>{}</code>", obj, obj.code)

    @admin.display(description="Aperçu")
    def apercu(self, obj):
        if not obj.pk:
            return "-"
        return format_html('<a class="button" href="{}" target="_blank">Aperçu PDF (texte enregistré, données '
                           "d'exemple)</a>", reverse("admin:core_modelecourrier_apercu", args=[obj.pk]))

    @admin.display(description="Mode d'emploi")
    def mode_d_emploi(self, obj):
        return mark_safe(
            "<ul style='margin:0'>"
            "<li><code>{nom}</code> : valeur tirée du dossier (liste ci-dessous).</li>"
            "<li><code>{si_condition:texte si oui|texte si non}</code> : texte qui dépend du dossier "
            "(« |texte si non » est facultatif ; les textes peuvent contenir des variables).</li>"
            "<li><code>**texte**</code> : gras ; <code>[petit]texte[/petit]</code> : petits caractères.</li>"
            "<li>Ligne vide : nouveau paragraphe. Un paragraphe dont toutes les variables sont vides n'est pas imprimé.</li>"
            "<li>L'en-tête (MDS, destinataire, date), le n° de recommandé et les signatures des professionnels "
            "restent ajoutés par CID.</li></ul>")

    @admin.display(description="Variables disponibles")
    def variables_disponibles(self, obj):
        d = obj.definition
        if not d:
            return "-"
        lignes = format_html_join("", "<tr><td><code>{{{}}}</code></td><td>{}</td><td><i>{}</i></td></tr>",
                                  ((n, desc, ex) for n, (desc, ex) in d["variables"].items()))
        conds = format_html_join("", "<tr><td><code>{{{}:…|…}}</code></td><td colspan='2'>si {}</td></tr>",
                                 ((n, desc) for n, desc in d.get("conditions", {}).items()))
        return format_html("<table><tr><th>Variable</th><th>Contenu</th><th>Exemple</th></tr>{}{}</table>",
                           lignes, conds)

    # ------------------------------------------------------------------ actions
    @admin.action(description="Remettre le texte d'origine")
    def remettre_origine(self, request, queryset):
        for m in queryset:
            m.remettre_texte_origine()
            m.modifie_par = request.user
            m.save()
        messages.success(request, f"{queryset.count()} modèle(s) remis au texte d'origine.")

    @admin.action(description="Exporter (fichier JSON)")
    def exporter(self, request, queryset):
        contenu = {"format": FORMAT_EXPORT, "version": 1, "exporte_le": timezone.now().isoformat(),
                   "modeles": [{"code": m.code, **{c: getattr(m, c) for c in CHAMPS}} for m in queryset]}
        r = HttpResponse(json.dumps(contenu, ensure_ascii=False, indent=2), content_type="application/json")
        r["Content-Disposition"] = f'attachment; filename="modeles_courriers_{timezone.localdate():%Y%m%d}.json"'
        return r

    # ------------------------------------------------------------------ vues supplémentaires
    def get_urls(self):
        return [path("<int:pk>/apercu/", self.admin_site.admin_view(self.vue_apercu), name="core_modelecourrier_apercu"),
                path("importer/", self.admin_site.admin_view(self.vue_importer), name="core_modelecourrier_importer"),
                ] + super().get_urls()

    def vue_apercu(self, request, pk):
        if not self.has_view_permission(request):
            return HttpResponse(status=403)
        from core.courriers.apercu import apercu_pdf
        m = get_object_or_404(ModeleCourrier, pk=pk)
        if not m.definition:
            messages.error(request, "Ce courrier n'existe plus dans CID.")
            return redirect("admin:core_modelecourrier_changelist")
        return FileResponse(apercu_pdf(m.code, {c: getattr(m, c) for c in CHAMPS}), content_type="application/pdf",
                            filename=f"apercu_{m.code.lower()}.pdf")

    def vue_importer(self, request):
        if not self.has_change_permission(request):
            return HttpResponse(status=403)
        form = ImportForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            try:
                contenu = json.load(form.cleaned_data["fichier"])
                if contenu.get("format") != FORMAT_EXPORT:
                    raise ValueError("ce fichier n'est pas un export des modèles de courriers de CID")
                modeles = contenu["modeles"]
            except (ValueError, KeyError, AttributeError, UnicodeDecodeError) as e:
                messages.error(request, f"Import impossible : {e}.")
                return redirect("admin:core_modelecourrier_importer")
            importes, refuses = 0, []
            for item in modeles:
                code = item.get("code")
                if code not in COURRIERS:
                    refuses.append(f"{code} : courrier inconnu dans cette version de CID")
                    continue
                textes = {c: str(item.get(c) or "") for c in CHAMPS}
                erreurs = erreurs_modele(code, textes)
                if erreurs:
                    refuses.append(f"{code} : " + " ; ".join(e for liste in erreurs.values() for e in liste))
                    continue
                m, _ = ModeleCourrier.objects.get_or_create(code=code)
                for c, v in textes.items():
                    setattr(m, c, v)
                m.modifie_par = request.user
                m.save()
                importes += 1
            messages.success(request, f"{importes} modèle(s) importé(s).")
            for r in refuses:
                messages.warning(request, f"Non importé – {r}")
            return redirect("admin:core_modelecourrier_changelist")
        return render(request, "admin/core/modelecourrier/importer.html",
                      {**self.admin_site.each_context(request), "form": form, "title": "Importer des modèles de courriers",
                       "opts": self.model._meta})
