# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# planning/ateliers.py
"""Règles des ateliers collectifs : inscription (âge, places, liste d'attente), retrait, présences."""
from django.db import transaction
from django.utils import timezone

from .models_ateliers import ParticipantAtelier as P
from .models_ateliers import SeanceAtelier


class ErreurAtelier(Exception):
    pass


def age_le(date_naissance, jour):
    return jour.year - date_naissance.year - ((jour.month, jour.day) < (date_naissance.month, date_naissance.day))


def controle_age(seance, date_naissance):
    """Message si la condition d'âge n'est pas remplie, sinon None."""
    if not seance.condition_age or seance.age_limite is None or not date_naissance:
        return None
    age = age_le(date_naissance, seance.date)
    if seance.condition_age == SeanceAtelier.PLUS_DE and age < seance.age_limite:
        return f"Atelier à partir de {seance.age_limite} ans ({age} ans le jour de la séance)."
    if seance.condition_age == SeanceAtelier.MOINS_DE and age > seance.age_limite:
        return f"Atelier jusqu'à {seance.age_limite} ans ({age} ans le jour de la séance)."
    return None


@transaction.atomic
def inscrire(seance, user, beneficiaire=None, forcer_age=False, **externe):
    """Inscrit un usager (ou une personne extérieure) ; s'il n'y a plus de place, en liste d'attente."""
    seance = SeanceAtelier.objects.select_for_update().get(pk=seance.pk)
    if seance.statut == SeanceAtelier.ANNULEE:
        raise ErreurAtelier("Séance annulée.")
    if beneficiaire is not None:
        if seance.participants.filter(beneficiaire=beneficiaire).exists():
            raise ErreurAtelier("Déjà inscrit à cette séance.")
        msg = controle_age(seance, beneficiaire.date_naissance)
        if msg and not forcer_age:
            raise ErreurAtelier(msg)
    elif not (externe.get("nom") or externe.get("prenom")):
        raise ErreurAtelier("Nom ou prénom de la personne extérieure obligatoire.")
    complet = seance.places is not None and seance.inscrits().count() >= seance.places
    return P.objects.create(
        seance=seance, beneficiaire=beneficiaire, inscrit_par=user,
        type=P.USAGER if beneficiaire else externe.pop("type", P.EXTERNE),
        liste=P.ATTENTE if complet else P.PRINCIPALE,
        montant=seance.tarif if seance.payant else None, **externe)


@transaction.atomic
def retirer(participant):
    """Désinscrit ; une place libérée revient au premier de la liste d'attente. Renvoie le promu éventuel."""
    seance = SeanceAtelier.objects.select_for_update().get(pk=participant.seance_id)
    liberait = participant.liste == P.PRINCIPALE
    participant.delete()
    if liberait and (seance.places is None or seance.inscrits().count() < seance.places):
        premier = seance.attente().first()
        if premier:
            premier.liste = P.PRINCIPALE
            premier.save(update_fields=["liste"])
            return premier
    return None


def noter_presences(seance, valeurs):
    """valeurs : {participant_id: 'VENU' | 'ABSENT' | 'EXCUSE' | ''} ; seulement la liste principale."""
    for p in seance.inscrits():
        if str(p.pk) in valeurs and valeurs[str(p.pk)] in ("", P.VENU, P.ABSENT, P.EXCUSE):
            p.presence = valeurs[str(p.pk)]
            p.save(update_fields=["presence"])


def bilan(seance):
    inscrits = list(seance.inscrits())
    return {"inscrits": len(inscrits), "attente": seance.attente().count(),
            "presents": sum(p.presence == P.VENU for p in inscrits),
            "absents": sum(p.presence == P.ABSENT for p in inscrits),
            "excuses": sum(p.presence == P.EXCUSE for p in inscrits),
            "paiements": sum(p.paiement_recu for p in inscrits)}


def a_venir(seances):
    return seances.filter(date__gte=timezone.localdate())
