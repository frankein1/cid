# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/services/afase_recours.py
"""
Recours contre un refus d'AFASE : trace du recours et, s'il aboutit, nouvelle AFASE reprise de la demande
refusée (enfants, budget, évaluation, pièces), déposée directement au décideur. La demande refusée,
sa décision et son courrier ne sont jamais modifiés.
"""
from django.db import transaction

CHAMPS_NON_REPRIS = {"id", "demandeaide_ptr", "statut", "date_creation", "numero_dossier", "date_ajournement",
                     "rappels_envoyes"}


def peut_gerer(user, demande):
    """Enregistrer un recours et son issue : celui qui décide (cadre de la MDS ou inspecteur) ou l'administration."""
    return demande.statut == "REFUSEE" and (
        demande.peut_etre_decidee_par(user) or user.is_superuser or user.a_la_capacite("peut_administrer"))


@transaction.atomic
def creer_nouvelle_demande(recours, user):
    """Nouvelle AFASE déposée, reprise de la demande refusée. Retourne la nouvelle demande."""
    from AidFi.models import DemandeAFASE
    from AidFi.models.m_afase import BudgetAFASE, EnfantAFASE, EvaluationSocialeAFASE
    from AidFi.models.m_generique import PieceJustificative
    if recours.nouvelle_demande_id:
        return recours.nouvelle_demande
    origine = recours.demande
    valeurs = {f.attname: getattr(origine, f.attname) for f in DemandeAFASE._meta.concrete_fields
               if f.name not in CHAMPS_NON_REPRIS and not f.primary_key}
    nouvelle = DemandeAFASE(**valeurs)
    nouvelle.statut = "BROUILLON"
    nouvelle.save()

    def copier(obj, **remplacer):
        champs = {f.attname: getattr(obj, f.attname) for f in obj._meta.concrete_fields if not f.primary_key}
        champs.update(remplacer)
        return type(obj).objects.create(**champs)

    for e in EnfantAFASE.objects.filter(demande=origine):
        copier(e, demande_id=nouvelle.pk)
    for model in (BudgetAFASE, EvaluationSocialeAFASE):
        obj = model.objects.filter(demande=origine).first()
        if obj:
            copier(obj, demande_id=nouvelle.pk)
    # Pièces du dossier, sans le PDF de la décision de refus (il reste sur l'AFASE refusée)
    for p in PieceJustificative.objects.filter(demande_id=origine.pk).exclude(type_piece="DECISION"):
        copier(p, demande_id=nouvelle.pk)

    recours.nouvelle_demande = nouvelle
    recours.save(update_fields=["nouvelle_demande", "date_modification"])
    # Dépôt au décideur : la décision du recours s'impose, il reste à l'appliquer
    nouvelle.statut = "DEPOSEE"
    nouvelle._acteur = user
    nouvelle.save(update_fields=["statut"])
    return nouvelle


def recours_origine(demande):
    """Le recours dont découle cette AFASE, ou None."""
    from AidFi.models.m_recours import RecoursAFASE
    return RecoursAFASE.objects.filter(nouvelle_demande=demande).select_related("demande").first()
