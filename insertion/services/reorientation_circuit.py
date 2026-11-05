# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/services/reorientation_circuit.py
"""
Réorientation d'un bénéficiaire du RSA par la commission trimestrielle du pôle insertion
(un membre de chaque MDS, administratifs et cadres du pôle) : vers France Travail, la CAF ou une association,
qui devient alors son référent RSA.

  Demande en préparation ──(référent : inscrire)──▶ Inscrite (en attente de la prochaine commission, ou rattachée)
       ──(commission : décision)──▶ Acceptée · Refusée · Ajournée ──(clôture)──▶ ajournée = réinscrite pour la suivante

Le référent inscrit seul, sans validation de son cadre. Une demande inscrite rejoint la prochaine commission
en préparation de son pôle ; une commission créée reprend toutes les demandes en attente.
À la date d'effet d'une réorientation acceptée, la personne sort de la file active RSA de sa MDS.
"""
from django.db import transaction
from django.utils import timezone

from insertion import acces
from insertion.models import (CommissionReorientation as Commission, DemandeReorientation as D, ExamenReorientation,
                              HistoriqueReorientation)
from insertion.services.contrat_circuit import ErreurCircuit, prevenir


def journal(d, user, action, commentaire=""):
    return HistoriqueReorientation.objects.create(demande=d, user=user, action=action[:200], commentaire=commentaire)


def _usager(d):
    return f"{d.beneficiaire.prenom} {d.beneficiaire.nom.upper()}"


def gestionnaires(pole):
    if not pole:
        return []
    return [u for u in pole.membres.filter(is_active=True)
            if u.a_la_capacite('rsa_pole_admin') or u.a_la_capacite('rsa_pole_cadre')]


def prochaine_commission(pole):
    if not pole:
        return None
    return (Commission.objects.filter(pole=pole, statut=Commission.PREPARATION, date__gte=timezone.localdate())
            .order_by('date').first())


def reorientation_effective(beneficiaire):
    """Dernière réorientation acceptée dont la date d'effet est passée (la personne a changé de référent RSA)."""
    return (beneficiaire.reorientations.filter(statut=D.ACCEPTEE, date_effet__lte=timezone.localdate())
            .select_related('organisme_retenu').order_by('-date_effet').first())


# ---------------------------------------------------------------------- référent
@transaction.atomic
def creer(beneficiaire, user):
    from insertion.services.prescription_circuit import contrat_courant
    d = D(beneficiaire=beneficiaire, mds=beneficiaire.mds, pole=acces.pole_de_mds(beneficiaire.mds), referent=user,
          contrat=contrat_courant(beneficiaire), date_demande=timezone.localdate())
    derniere = beneficiaire.prescriptions_insertion.exclude(freins=[]).order_by('-pk').first()
    if derniere:
        d.freins = list(derniere.freins)
    d.save()
    journal(d, user, "Demande de réorientation créée")
    return d


@transaction.atomic
def inscrire(d, user):
    if d.statut != D.BROUILLON:
        raise ErreurCircuit("Cette demande est déjà inscrite.")
    if not d.pole_id:
        d.pole = acces.pole_de_mds(d.mds)
    manques = d.manques_inscription()
    if manques:
        raise ErreurCircuit("Avant d'inscrire la demande, renseignez : " + ", ".join(manques) + ".")
    d.statut, d.commission = D.INSCRITE, prochaine_commission(d.pole)
    d.save()
    quand = f"à la commission du {d.commission.date:%d/%m/%Y}" if d.commission else "en attente de la prochaine commission"
    journal(d, user, f"Inscrite {quand}")
    prevenir(user, gestionnaires(d.pole), d, f"Réorientation {d.numero} inscrite",
             f"{user.get_full_name() or user.username} ({d.mds}) inscrit une demande de réorientation de {_usager(d)} "
             f"vers : {d.orientation_libelle}"
             f", {quand}.")


@transaction.atomic
def annuler(d, user):
    if not d.modifiable:
        raise ErreurCircuit("Cette demande ne peut plus être annulée.")
    d.statut, d.commission = D.ANNULEE, None
    d.save()
    journal(d, user, "Demande annulée")


# ---------------------------------------------------------------------- pôle : commission
@transaction.atomic
def creer_commission(pole, user, *, date, heure=None, lieu=""):
    c = Commission.objects.create(pole=pole, date=date, heure=heure, lieu=lieu, cree_par=user)
    n = D.objects.filter(pole=pole, statut=D.INSCRITE, commission__isnull=True).update(commission=c)
    return c, n


@transaction.atomic
def ajouter_en_attente(c):
    return D.objects.filter(pole=c.pole, statut=D.INSCRITE, commission__isnull=True).update(commission=c)


@transaction.atomic
def retirer(d, user, motif=""):
    if d.statut != D.INSCRITE or not d.commission_id or d.commission.statut != Commission.PREPARATION:
        raise ErreurCircuit("Seule une demande inscrite à une commission en préparation peut en être retirée.")
    date = d.commission.date
    ExamenReorientation.objects.filter(commission=d.commission, demande=d).delete()
    d.commission, d.decision = None, ""
    d.save()
    journal(d, user, f"Retirée de la commission du {date:%d/%m/%Y} (en attente de la suivante)", motif)


@transaction.atomic
def decider(d, user, *, decision, organisme_retenu=None, date_effet=None, motif=""):
    if not d.commission_id or d.commission.statut != Commission.PREPARATION or d.statut != D.INSCRITE:
        raise ErreurCircuit("La décision se prend sur une demande inscrite à une commission en préparation.")
    if decision not in dict(D.DECISIONS):
        raise ErreurCircuit("Choisissez une décision.")
    if decision == D.ACCEPTEE and not (organisme_retenu and date_effet):
        raise ErreurCircuit("Réorientation acceptée : indiquez l'organisme retenu et la date d'effet.")
    if decision in (D.REFUSEE, D.AJOURNEE) and not motif.strip():
        raise ErreurCircuit("Indiquez le motif du refus ou de l'ajournement.")
    d.decision, d.motif_decision = decision, motif
    d.organisme_retenu = organisme_retenu if decision == D.ACCEPTEE else None
    d.date_effet = date_effet if decision == D.ACCEPTEE else None
    d.decide_par, d.date_decision = user, d.commission.date
    d.save()
    ExamenReorientation.objects.update_or_create(commission=d.commission, demande=d, defaults={
        "decision": decision, "organisme_retenu": d.organisme_retenu, "date_effet": d.date_effet, "motif": motif})
    journal(d, user, f"Décision notée : {d.get_decision_display().lower()}", motif)


@transaction.atomic
def cloturer(c, user):
    if c.statut != Commission.PREPARATION:
        raise ErreurCircuit("Cette commission est déjà clôturée.")
    demandes = list(c.demandes.filter(statut=D.INSCRITE).select_related('referent', 'beneficiaire', 'organisme_retenu'))
    sans = [d for d in demandes if not d.decision]
    if sans:
        raise ErreurCircuit(f"{len(sans)} dossier(s) sans décision : notez la décision, ou retirez le dossier "
                            "pour la commission suivante.")
    c.statut, c.cloturee_le, c.cloturee_par = Commission.CLOTUREE, timezone.now(), user
    c.save()
    suivante = prochaine_commission(c.pole)   # déjà programmée, ou None : en attente de la prochaine
    for d in demandes:
        libelle = d.get_decision_display().lower()
        if d.decision == D.AJOURNEE:
            d.statut, d.commission, d.decision = D.INSCRITE, suivante, ""
            d.nb_ajournements += 1
            texte = (f"La commission du {c.date:%d/%m/%Y} a ajourné la réorientation de {_usager(d)}.\n"
                     f"Motif : {d.motif_decision}\nLa demande sera présentée à la commission suivante.")
        else:
            d.statut = d.decision
            texte = f"Commission du {c.date:%d/%m/%Y} : {libelle} pour {_usager(d)}."
            if d.decision == D.ACCEPTEE:
                texte += (f"\nNouveau référent RSA : {d.organisme_retenu}, à compter du {d.date_effet:%d/%m/%Y}. "
                          "La personne sortira alors de la file active RSA de la MDS.")
            if d.motif_decision:
                texte += f"\nMotif : {d.motif_decision}"
        d.save()
        journal(d, user, f"Commission du {c.date:%d/%m/%Y} : {libelle}", d.motif_decision)
        prevenir(user, [d.referent], d, f"Réorientation {d.numero} : {libelle}", texte, avec_usager=True)
    return len(demandes)
