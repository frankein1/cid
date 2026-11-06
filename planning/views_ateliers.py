# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# planning/views_ateliers.py
"""Ateliers collectifs : séances, inscriptions (usagers et personnes extérieures), présences, émargement."""
import csv

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from beneficiaire.models import Beneficiaire
from mds.models import MDS, UserMDSProfile

from . import ateliers as regles
from .models_ateliers import Atelier, ParticipantAtelier as P, SeanceAtelier


def _cellule(texte):
    """Texte saisi exporté en CSV : jamais interprété comme une formule par le tableur."""
    texte = texte or ""
    return "'" + texte if texte[:1] in ("=", "+", "-", "@", "\t", "\r") else texte


def _mds_ids(u):
    if u.is_superuser or u.a_la_capacite('peut_administrer'):
        return None
    return list(UserMDSProfile.objects.filter(user=u, actif=True).values_list('mds_id', flat=True))


def _peut_voir(u, seance=None):
    if not u.a_la_capacite('peut_voir'):
        return False
    return seance is None or u.a_acces_mds(seance.mds)


def _peut_gerer(u, seance=None):
    return u.a_la_capacite('peut_creer') and _peut_voir(u, seance)


class SeanceForm(forms.ModelForm):
    class Meta:
        model = SeanceAtelier
        fields = ['atelier', 'mds', 'intitule', 'date', 'heure_debut', 'heure_fin', 'lieu', 'animateur', 'partenaire',
                  'action_insertion', 'places', 'condition_age', 'age_limite', 'payant', 'tarif', 'description']
        widgets = {'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                   'heure_debut': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
                   'heure_fin': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
                   'description': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        ids = _mds_ids(user)
        self.fields['mds'].queryset = MDS.objects.all() if ids is None else MDS.objects.filter(pk__in=ids)
        self.fields['atelier'].queryset = Atelier.objects.filter(actif=True).filter(
            Q(mds__isnull=True) | Q(mds_id__in=ids or [])) if ids is not None else Atelier.objects.filter(actif=True)
        from insertion.models import ActionInsertion
        self.fields['action_insertion'].queryset = ActionInsertion.objects.filter(
            Q(mds__isnull=True) | Q(mds_id__in=ids or [])) if ids is not None else ActionInsertion.objects.all()
        self.fields['action_insertion'].required = False
        for f in self.fields.values():
            if not isinstance(f.widget, (forms.CheckboxInput,)):
                f.widget.attrs['class'] = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm'

    def clean(self):
        d = super().clean()
        if d.get('heure_debut') and d.get('heure_fin') and d['heure_fin'] <= d['heure_debut']:
            self.add_error('heure_fin', "L'heure de fin doit suivre l'heure de début.")
        if d.get('condition_age') and d.get('age_limite') is None:
            self.add_error('age_limite', "Indiquez l'âge.")
        if d.get('payant') and not d.get('tarif'):
            self.add_error('tarif', "Indiquez le tarif.")
        return d


@login_required
def ateliers_liste(request):
    u = request.user
    if not _peut_voir(u):
        return HttpResponseForbidden("Accès réservé aux agents.")
    ids = _mds_ids(u)
    qs = SeanceAtelier.objects.select_related('atelier', 'mds').annotate(
        nb_inscrits=Count('participants', filter=Q(participants__liste=P.PRINCIPALE)),
        nb_attente=Count('participants', filter=Q(participants__liste=P.ATTENTE)))
    if ids is not None:
        qs = qs.filter(mds_id__in=ids)
    if request.GET.get('atelier', '').isdigit():
        qs = qs.filter(atelier_id=request.GET['atelier'])
    aujourd_hui = timezone.localdate()
    return render(request, 'planning/ateliers_liste.html', {
        'a_venir': qs.filter(date__gte=aujourd_hui).order_by('date', 'heure_debut'),
        'passees': qs.filter(date__lt=aujourd_hui).order_by('-date')[:50],
        'ateliers': Atelier.objects.filter(actif=True).filter(Q(mds__isnull=True) | Q(mds_id__in=ids or []))
        if ids is not None else Atelier.objects.filter(actif=True), 'atelier_choisi': request.GET.get('atelier', ''),
        'peut_gerer': _peut_gerer(u),
    })


@login_required
def seance_form(request, pk=None):
    u = request.user
    seance = get_object_or_404(SeanceAtelier, pk=pk) if pk else None
    if not _peut_gerer(u, seance):
        return HttpResponseForbidden("Réservé aux agents de la MDS.")
    form = SeanceForm(request.POST or None, instance=seance, user=u,
                      initial=None if seance else {'mds': u.mds_principale})
    if request.method == 'POST' and form.is_valid():
        s = form.save(commit=False)
        if not s.pk:
            s.cree_par = u
        s.save()
        messages.success(request, "Séance enregistrée.")
        return redirect('planning:seance_atelier', pk=s.pk)
    return render(request, 'planning/seance_form.html', {'form': form, 'seance': seance})


def _libelles(b, s):
    d = {"Inscrits": b["inscrits"], "En attente": b["attente"], "Présents": b["presents"], "Absents": b["absents"],
         "Excusés": b["excuses"]}
    if s.payant:
        d["Paiements reçus"] = b["paiements"]
    return d


@login_required
def seance_detail(request, pk):
    u = request.user
    s = get_object_or_404(SeanceAtelier.objects.select_related('atelier', 'mds', 'partenaire', 'action_insertion'), pk=pk)
    if not _peut_voir(u, s):
        return HttpResponseForbidden("Réservé aux agents de la MDS.")
    q = request.GET.get('q', '').strip()
    trouves = []
    if q and len(q) >= 2:
        trouves = (Beneficiaire.objects.filter(mds=s.mds).filter(Q(nom__icontains=q) | Q(prenom__icontains=q) |
                                                                  Q(code_interne__icontains=q))
                   .exclude(participations_ateliers__seance=s).order_by('nom', 'prenom')[:15])
    return render(request, 'planning/seance_detail.html', {
        's': s, 'trouves': [(b, regles.controle_age(s, b.date_naissance)) for b in trouves], 'inscrits': s.inscrits().select_related('beneficiaire'),
        'attente': s.attente().select_related('beneficiaire'), 'bilan': _libelles(regles.bilan(s), s), 'q': q,
        'peut_gerer': _peut_gerer(u, s), 'presences': P.PRESENCES,
    })


@login_required
@require_POST
def seance_action(request, pk):
    u = request.user
    s = get_object_or_404(SeanceAtelier, pk=pk)
    if not _peut_gerer(u, s):
        return HttpResponseForbidden("Réservé aux agents de la MDS.")
    action = request.POST.get('action')
    try:
        if action == 'inscrire_usager':
            b = get_object_or_404(Beneficiaire, pk=request.POST.get('beneficiaire'), mds=s.mds)
            p = regles.inscrire(s, u, beneficiaire=b, forcer_age=request.POST.get('forcer_age') == '1')
            messages.success(request, f"{p.nom_complet} inscrit(e)" + (" en liste d'attente." if p.liste == P.ATTENTE else "."))
        elif action == 'inscrire_externe':
            champs = {k: request.POST.get(k, '').strip() for k in ('prenom', 'nom', 'telephone', 'email', 'ville')}
            champs['type'] = P.ACCOMPAGNANT if request.POST.get('accompagnant') == '1' else P.EXTERNE
            p = regles.inscrire(s, u, **champs)
            messages.success(request, f"{p.nom_complet} inscrit(e)" + (" en liste d'attente." if p.liste == P.ATTENTE else "."))
        elif action == 'retirer':
            promu = regles.retirer(get_object_or_404(P, pk=request.POST.get('participant'), seance=s))
            messages.success(request, "Désinscrit." + (f" {promu.nom_complet} passe de la liste d'attente aux inscrits."
                                                       if promu else ""))
        elif action == 'presences':
            regles.noter_presences(s, {k[9:]: v for k, v in request.POST.items() if k.startswith('presence_')})
            payes = set(request.POST.getlist('paye'))
            for p in s.inscrits():
                p.paiement_recu = str(p.pk) in payes
                p.save(update_fields=['paiement_recu'])
            messages.success(request, "Présences enregistrées.")
        elif action == 'annuler':
            s.statut = SeanceAtelier.ANNULEE
            s.save(update_fields=['statut'])
            messages.warning(request, "Séance annulée : prévenez les inscrits.")
        elif action == 'retablir':
            s.statut = SeanceAtelier.PREVUE
            s.save(update_fields=['statut'])
    except regles.ErreurAtelier as e:
        messages.error(request, str(e))
    return redirect('planning:seance_atelier', pk=s.pk)


@login_required
def seance_export(request, pk, format):
    u = request.user
    s = get_object_or_404(SeanceAtelier.objects.select_related('atelier', 'mds'), pk=pk)
    if not _peut_voir(u, s):
        return HttpResponseForbidden("Réservé aux agents de la MDS.")
    inscrits = list(s.inscrits().select_related('beneficiaire'))
    if format == 'csv':
        r = HttpResponse(content_type='text/csv; charset=utf-8')
        r['Content-Disposition'] = f'attachment; filename="atelier_{s.date:%Y-%m-%d}_{s.pk}.csv"'
        r.write('﻿')
        w = csv.writer(r, delimiter=';')
        w.writerow(["Nom", "Type", "Code CID", "Présence", "Paiement reçu", "Commentaire"])
        for p in inscrits:
            w.writerow([_cellule(p.nom_complet), p.get_type_display(), p.beneficiaire.code_interne if p.beneficiaire else "",
                        p.get_presence_display(), "oui" if p.paiement_recu else "", _cellule(p.commentaire)])
        return r
    from .ateliers_pdf import emargement_pdf
    return HttpResponse(emargement_pdf(s, inscrits).getvalue(), content_type='application/pdf',
                        headers={'Content-Disposition': f'inline; filename="emargement_{s.date:%Y-%m-%d}.pdf"'})
