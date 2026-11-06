# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/journal.py
"""Journal unique de l'accompagnement : entretiens, et en regard ce que le reste de CID sait déjà du parcours
(rendez-vous, aides financières, contrats et prescriptions RSA, ateliers, budgets), chaque source avec ses propres
droits. Les informations préoccupantes et l'ASE n'y figurent pas : elles gardent leur cloisonnement."""
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time

from django.urls import reverse
from django.utils import timezone

log = logging.getLogger(__name__)

GENRES = [("entretien", "Entretiens"), ("rdv", "Rendez-vous"), ("aide", "Aides financières"),
          ("rsa", "RSA – Insertion"), ("atelier", "Ateliers"), ("budget", "Budget")]


@dataclass
class Ligne:
    jour: date
    heure: time | None
    genre: str
    titre: str
    detail: str = ""
    url: str = ""
    auteur: str = ""
    legal: bool = False
    types: list = field(default_factory=list)
    entretien: object = None
    creneau: object = None        # RDV réalisé sans compte rendu : proposer d'en rédiger un

    @property
    def cle(self):
        return (self.jour, self.heure or time(0))


def _nom(u):
    return (u.get_full_name() or u.username) if u else ""


def _entretiens(b, user):
    from .models_journal import EntretienSocial
    for e in (EntretienSocial.objects.filter(beneficiaire=b).select_related('auteur', 'orientation')
              .prefetch_related('types', 'co_intervenants', 'personnes_presentes')):
        types = list(e.types.all())
        yield Ligne(e.date, e.heure, "entretien", e.objet, e.get_mode_display(), auteur=_nom(e.auteur),
                    legal=any(t.legal for t in types), types=types, entretien=e)


def _rdv(b, user):
    from planning.models import STATUTS_REALISES, CreneauRdv
    rdvs = (CreneauRdv.objects.filter(beneficiaire=b).exclude(statut='DISPONIBLE').exclude(domaine__in=('IP', 'ENFANCE'))
            .select_related('agent'))
    avec_cr = set(b.entretiens.exclude(creneau=None).values_list('creneau_id', flat=True))
    for c in rdvs:
        yield Ligne(c.date, c.heure_debut, "rdv", f"Rendez-vous – {c.get_nature_display()}", c.get_statut_display(),
                    auteur=_nom(c.agent),
                    creneau=c if (c.statut in STATUTS_REALISES and c.pk not in avec_cr and c.date <= date.today()) else None)


def _aides(b, user):
    from AidFi.models.m_generique import DemandeAide
    for d in DemandeAide.objects.filter(beneficiaire=b).select_related('type_aide', 'cree_par'):
        if not user.peut_agir_sur_objet(d, "peut_voir"):
            continue
        url = ""
        if hasattr(d, 'demandeafase'):
            url = reverse('AidFi:afase_detail', args=[d.pk])
        yield Ligne(timezone.localtime(d.date_creation).date(), None, "aide", f"Demande d'aide – {d.type_aide}", d.get_statut_display(),
                    url=url, auteur=_nom(d.cree_par))


def _rsa(b, user):
    from insertion.acces import peut_voir_module
    if not peut_voir_module(user):
        return
    from insertion.models import ContratInsertion, PrescriptionInsertion
    for c in ContratInsertion.objects.filter(beneficiaire=b):
        jour = c.date_signature or c.date_etablissement
        if jour:
            yield Ligne(jour, None, "rsa", f"Contrat RSA – {c.get_type_contrat_display().lower()}", c.get_statut_display(),
                        url=reverse('insertion:contrat_detail', args=[c.pk]), legal=True)
    for p in PrescriptionInsertion.objects.filter(beneficiaire=b).select_related('action'):
        jour = p.date_prescription or p.date_signature
        if jour:
            yield Ligne(jour, None, "rsa", f"Prescription – {p.action}", p.get_statut_display(),
                        url=reverse('insertion:prescription_detail', args=[p.pk]), legal=True)


def _ateliers(b, user):
    for p in b.participations_ateliers.select_related('seance__atelier'):
        s = p.seance
        yield Ligne(s.date, s.heure_debut, "atelier", f"Atelier – {s.titre}",
                    p.get_presence_display() or ("liste d'attente" if p.liste == 'ATTENTE' else "inscrit(e)"),
                    url=reverse('planning:seance_atelier', args=[s.pk]))


def _budgets(b, user):
    for bf in b.budgets_foyer.select_related('cree_par'):
        yield Ligne(bf.date_etabli, None, "budget", "Budget du foyer",
                    f"reste à vivre {bf.reste_a_vivre} € / jour / personne",
                    url=reverse('beneficiaire:budget_foyer', args=[b.code_interne]), auteur=_nom(bf.cree_par))


SOURCES = {"entretien": _entretiens, "rdv": _rdv, "aide": _aides, "rsa": _rsa, "atelier": _ateliers, "budget": _budgets}


def journal(b, user, genres=None, type_code=None):
    lignes = []
    for genre, source in SOURCES.items():
        if genres and genre not in genres:
            continue
        try:
            lignes.extend(source(b, user))
        except Exception:      # une source en défaut ne doit pas empêcher de lire le journal
            log.exception("Journal : source %s indisponible", genre)
    if type_code:
        lignes = [l for l in lignes if any(t.code == type_code for t in l.types)]
    return sorted(lignes, key=lambda l: l.cle, reverse=True)
