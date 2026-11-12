# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/views/v_dalo.py
"""Recours amiable DALO : saisie des données du Cerfa 15036*02 (préremplies depuis CID) et PDF rempli."""
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from beneficiaire.models import LienFamilial
from mds.models import UserMDSProfile

from ..models import DemandeLogementSocial, RecoursDALO
from ..services import dalo_cerfa
from .v_copp import _usager

CHAMPS_TEXTE = ['nom_naissance', 'nom_usage', 'prenoms', 'date_naissance', 'telephone', 'telephone_portable',
                'email', 'adresse_numero', 'adresse_voie', 'adresse_complement', 'code_postal', 'commune',
                'logement_autre', 'bailleur', 'numero_allocataire', 'nud', 'nature_local', 'hebergement_nb_personnes',
                'hebergement_surface', 'hebergement_pieces', 'structure_nom', 'structure_date', 'surface_totale',
                'nombre_pieces', 'assistant_nom', 'assistant_organisme', 'assistant_adresse_numero',
                'assistant_adresse_voie', 'assistant_code_postal', 'assistant_commune', 'assistant_telephone']
CHAMPS_LONGS = ['personnes', 'hebergeurs', 'argumentaire']


def _decouper_adresse(texte):
    """« 12 rue des Lilas » -> ('12', 'rue des Lilas') ; sinon (‘’, texte)."""
    m = re.match(r'^\s*(\d+\s*(?:bis|ter|[A-Za-z])?)\s+(.+)$', texte or '')
    return (m.group(1).strip(), m.group(2).strip()) if m else ('', (texte or '').strip())


def _preremplir(r, b, user):
    """Complète en mémoire les rubriques vides depuis la fiche usager, la demande de logement et le foyer."""
    def vide(champ, valeur):
        if not getattr(r, champ) and valeur:
            setattr(r, champ, valeur)
    vide('civilite', 'MME' if b.civilite == 'MME' else 'M')
    vide('nom_naissance', b.nom_naissance)
    vide('nom_usage', b.nom)
    vide('prenoms', b.prenom)
    vide('date_naissance', b.date_naissance.strftime('%d/%m/%Y') if b.date_naissance else '')
    vide('telephone', b.telephone_fixe)
    vide('telephone_portable', b.telephone_mobile)
    vide('email', b.email)
    vide('numero_allocataire', b.numero_caf)
    numero, voie = _decouper_adresse(b.adresse)
    vide('adresse_numero', numero)
    vide('adresse_voie', voie)
    vide('code_postal', b.code_postal)
    vide('commune', b.ville)
    dl = DemandeLogementSocial.objects.filter(beneficiaire=b).first()
    if dl:
        vide('nud', dl.nud)
    if not r.personnes:
        liens = (LienFamilial.objects.filter(Q(personne_a=b) | Q(personne_b=b), vit_au_foyer=True)
                 .select_related('personne_a', 'personne_b'))
        lignes = []
        for lien in liens:
            autre = lien.personne_b if lien.personne_a_id == b.pk else lien.personne_a
            if autre is None:
                continue
            naissance = autre.date_naissance.strftime('%d/%m/%Y') if autre.date_naissance else ''
            lignes.append(f"{autre.nom};{autre.prenom};{naissance};{lien.get_type_lien_display()}")
        r.personnes = "\n".join(lignes)
    if not r.lieux_travail:
        r.lieux_travail = [{} for _ in range(RecoursDALO.NB_LIEUX)]
        for i, morceaux in enumerate([l.split(';') for l in (r.personnes or '').splitlines() if l.strip()][:7], 1):
            r.lieux_travail[i] = {'nom': ' '.join(m for m in morceaux[:2] if m).strip()}
    prof = UserMDSProfile.objects.filter(user=user, actif=True).order_by('-principale').select_related('mds').first()
    mds = prof.mds if prof else b.mds
    vide('assistant_nom', (user.get_full_name() or user.username))
    vide('assistant_organisme', mds.nom if mds else '')
    numero, voie = _decouper_adresse(mds.adresse if mds else '')
    vide('assistant_adresse_numero', numero)
    vide('assistant_adresse_voie', voie)
    vide('assistant_code_postal', mds.code_postal if mds else '')
    vide('assistant_commune', mds.ville if mds else '')


def _enregistrer(r, p, user):
    for champ in CHAMPS_TEXTE:
        setattr(r, champ, (p.get(champ) or '').strip()[:250])
    for champ in CHAMPS_LONGS:
        setattr(r, champ, (p.get(champ) or '').replace('\r\n', '\n').strip())
    r.civilite = p.get('civilite') if p.get('civilite') in dict(RecoursDALO._meta.get_field('civilite').choices) else ''
    r.nationalite = p.get('nationalite') if p.get('nationalite') in dict(RecoursDALO.NATIONALITES) else ''
    r.logement = p.get('logement') if p.get('logement') in dict(RecoursDALO.LOGEMENTS) else ''
    r.situations = [c for c in p.getlist('situations') if c in dict(RecoursDALO.SITUATIONS)]
    r.ressources_mois = (p.get('ressources_mois') or '').strip()[:40]
    r.ressources_annee_avis = re.sub(r'\D', '', p.get('ressources_annee_avis') or '')[:4]
    r.pcb = p.get('pcb') if p.get('pcb') in dict(RecoursDALO.OUI_NON) else ''
    r.surendettement = p.get('surendettement') if p.get('surendettement') in dict(RecoursDALO.OUI_NON) else ''
    r.ressources = {f'{code}|{col}': (p.get(f'res_{code}_{col}') or '').strip()[:20]
                    for code, _ in RecoursDALO.RESSOURCES_NATURES for col, _ in RecoursDALO.COLONNES_RESSOURCES
                    if (p.get(f'res_{code}_{col}') or '').strip()}
    r.lieux_travail = [{
        'nom': (p.get(f'lieu{i}_nom') or '').strip()[:120],
        'activite': (p.get(f'lieu{i}_activite') or '').strip()[:120],
        'contrat': p.get(f'lieu{i}_contrat') if p.get(f'lieu{i}_contrat') in dict(RecoursDALO.CONTRATS) else '',
        'entreprise': (p.get(f'lieu{i}_entreprise') or '').strip()[:150],
        'commune': (p.get(f'lieu{i}_commune') or '').strip()[:100],
        'transport': (p.get(f'lieu{i}_transport') or '').strip()[:60],
        'temps': (p.get(f'lieu{i}_temps') or '').strip()[:20],
    } for i in range(RecoursDALO.NB_LIEUX)]
    r.modifie_par = user
    r.save()


@login_required
def dalo_formulaire(request, code_interne):
    b, refus = _usager(request, code_interne)
    if refus:
        return refus
    r, _ = RecoursDALO.objects.get_or_create(beneficiaire=b)
    if request.method == 'POST':
        _enregistrer(r, request.POST, request.user)
        messages.success(request, "Recours DALO enregistré. Le PDF se génère avec les données enregistrées.")
        return redirect('logement:dalo_formulaire', code_interne=b.code_interne)
    _preremplir(r, b, request.user)
    return render(request, 'logement/dalo_form.html', {
        'b': b, 'r': r, 'situations': RecoursDALO.SITUATIONS, 'nationalites': RecoursDALO.NATIONALITES,
        'logements': RecoursDALO.LOGEMENTS, 'civilites': [('M', "Monsieur"), ('MME', "Madame")],
        'ressources_lignes': [(code, libelle, [(col, lc, (r.ressources or {}).get(f'{code}|{col}', ''))
                                               for col, lc in RecoursDALO.COLONNES_RESSOURCES])
                              for code, libelle in RecoursDALO.RESSOURCES_NATURES],
        'colonnes_ressources': RecoursDALO.COLONNES_RESSOURCES,
        'contrats': RecoursDALO.CONTRATS, 'oui_non': RecoursDALO.OUI_NON,
        'lieux': list(enumerate(r.lieux_travail))})


@login_required
def dalo_pdf(request, code_interne):
    b, refus = _usager(request, code_interne, ecriture=False)
    if refus:
        return refus
    r, _ = RecoursDALO.objects.get_or_create(beneficiaire=b)
    _preremplir(r, b, request.user)
    rep = HttpResponse(dalo_cerfa.remplir(r), content_type='application/pdf')
    rep['Content-Disposition'] = f'inline; filename="Cerfa_15036_{b.code_interne}.pdf"'
    return rep
