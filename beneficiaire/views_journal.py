# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/views_journal.py
"""Journal de l'accompagnement : consultation, saisie d'un entretien, suites à donner de l'agent."""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.models import User
from partenaires.models import Partenaire
from planning.models import CreneauRdv

from . import journal as jr
from .budget import membres_du_foyer
from .models import Beneficiaire
from .models_journal import EntretienSocial, TypeAccompagnement
from .views import user_peut_agir_sur_beneficiaire

CHAMP = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm'
CORRESPONDANCE_MODE = {'VAD': EntretienSocial.VAD, 'TELEPHONIQUE': EntretienSocial.TELEPHONE,
                       'PARTENAIRE': EntretienSocial.EXTERIEUR}


class EntretienForm(forms.ModelForm):
    class Meta:
        model = EntretienSocial
        fields = ['date', 'heure', 'mode', 'duree_minutes', 'types', 'objet', 'personnes_presentes', 'co_intervenants',
                  'synthese', 'synthese_privee', 'suite_a_donner', 'echeance', 'suite_faite', 'orientation',
                  'orientation_precision']
        widgets = {'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                   'echeance': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                   'heure': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
                   'types': forms.CheckboxSelectMultiple, 'personnes_presentes': forms.CheckboxSelectMultiple,
                   'synthese': forms.Textarea(attrs={'rows': 6}), 'synthese_privee': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, beneficiaire=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and user is not None and not self.instance.peut_lire_prive(user):
            del self.fields['synthese_privee']      # un administrateur qui corrige ne lit pas les notes de l'auteur
        self.fields['types'].queryset = TypeAccompagnement.objects.filter(actif=True)
        self.fields['personnes_presentes'].queryset = Beneficiaire.objects.filter(pk__in=membres_du_foyer(beneficiaire))
        self.fields['co_intervenants'].queryset = (User.objects.filter(is_active=True, profils_mds__mds=beneficiaire.mds,
                                                                       profils_mds__actif=True).distinct()
                                                   .order_by('last_name', 'first_name'))
        self.fields['orientation'].queryset = Partenaire.objects.all()
        for nom, f in self.fields.items():
            if not isinstance(f.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                f.widget.attrs.setdefault('class', CHAMP)
        self.fields['co_intervenants'].widget.attrs['size'] = 4


def _usager(request, code_interne, ecriture=False):
    b = get_object_or_404(Beneficiaire.tous.select_related('mds'), code_interne=code_interne)
    if b.niveau_acces(request.user) != 'complet':
        return b, HttpResponseForbidden("Le journal fait partie du dossier complet de la MDS de l'usager.")
    if ecriture and not user_peut_agir_sur_beneficiaire(request.user, b):
        return b, HttpResponseForbidden("Saisie réservée aux agents de la MDS de l'usager.")
    return b, None


@login_required
def journal(request, code_interne):
    b, refus = _usager(request, code_interne)
    if refus:
        return refus
    genres = [g for g in request.GET.getlist('genre') if g in jr.SOURCES]
    type_code = request.GET.get('type', '')
    lignes = jr.journal(b, request.user, genres or None, type_code or None)
    return render(request, 'beneficiaire/journal.html', {
        'beneficiaire': b, 'lignes': lignes, 'genres': jr.GENRES, 'genres_choisis': genres,
        'types': TypeAccompagnement.objects.filter(actif=True), 'type_choisi': type_code,
        'peut_saisir': user_peut_agir_sur_beneficiaire(request.user, b),
    })


@login_required
def entretien_form(request, code_interne, pk=None):
    b, refus = _usager(request, code_interne, ecriture=True)
    if refus:
        return refus
    e = get_object_or_404(EntretienSocial, pk=pk, beneficiaire=b) if pk else None
    if e and not e.peut_modifier(request.user):
        return HttpResponseForbidden("Seul l'auteur de l'entretien peut le modifier.")
    creneau = None
    initial = {}
    if not e and request.GET.get('creneau', '').isdigit():
        creneau = CreneauRdv.objects.filter(pk=request.GET['creneau'], beneficiaire=b).first()
        if creneau:
            initial = {'date': creneau.date, 'heure': creneau.heure_debut,
                       'mode': CORRESPONDANCE_MODE.get(creneau.nature, EntretienSocial.RDV),
                       'duree_minutes': creneau.duree_minutes,
                       'objet': f"Rendez-vous – {creneau.get_nature_display().lower()}",
                       'co_intervenants': list(creneau.co_intervenants.all())}
    form = EntretienForm(request.POST or None, instance=e, beneficiaire=b, user=request.user, initial=initial)
    if request.method == 'POST' and form.is_valid():
        ent = form.save(commit=False)
        if not ent.pk:
            ent.beneficiaire, ent.auteur, ent.cree_par = b, request.user, request.user
            if request.POST.get('creneau', '').isdigit():
                ent.creneau = CreneauRdv.objects.filter(pk=request.POST['creneau'], beneficiaire=b).first()
        ent.modifie_par = request.user
        ent.save()
        form.save_m2m()
        messages.success(request, "Entretien enregistré dans le journal.")
        return redirect('beneficiaire:journal', code_interne=b.code_interne)
    return render(request, 'beneficiaire/entretien_form.html', {
        'beneficiaire': b, 'form': form, 'entretien': e, 'creneau': creneau or (e.creneau if e else None)})


@login_required
def mes_suites(request):
    """Suites à donner des entretiens dont l'agent est l'auteur ou co-intervenant."""
    qs = (EntretienSocial.objects.filter(Q(auteur=request.user) | Q(co_intervenants=request.user))
          .exclude(suite_a_donner='').filter(suite_faite=False).select_related('beneficiaire').distinct()
          .order_by('echeance', 'date'))
    return render(request, 'beneficiaire/mes_suites.html', {'suites': qs, 'aujourd_hui': timezone.localdate()})


@login_required
@require_POST
def suite_faite(request, pk):
    e = get_object_or_404(EntretienSocial, pk=pk)
    if not (e.auteur_id == request.user.pk or e.co_intervenants.filter(pk=request.user.pk).exists()):
        return HttpResponseForbidden("Réservé à l'auteur et aux co-intervenants.")
    e.suite_faite = True
    e.save(update_fields=['suite_faite'])
    messages.success(request, "Suite marquée comme faite.")
    retour = request.POST.get('retour', '')
    if retour and url_has_allowed_host_and_scheme(retour, allowed_hosts={request.get_host()},
                                                  require_https=request.is_secure()):
        return redirect(retour)
    return redirect('beneficiaire:mes_suites')
