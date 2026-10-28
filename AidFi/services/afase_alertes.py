# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/services/afase_alertes.py
"""
Points de vigilance d'une demande d'AFASE (note de service, annexe 2) : affichés au travailleur social
et au cadre, ils n'empêchent pas la saisie ; c'est le cadre qui décide.
"""
from django.utils import timezone

STATUTS_IGNORES = ('REFUSEE', 'ANNULEE')


def _famille(beneficiaire):
    return {beneficiaire.pk} | {m['personne'].pk for m in beneficiaire.reseau_familial()}


def alertes(demande):
    """[(niveau, texte)] ; niveau : 'attention' (orange) ou 'info' (bleu)."""
    from AidFi.models.m_afase import DemandeAFASE
    sortie = []
    benef = demande.beneficiaire
    debut = timezone.localtime(demande.date_creation) if demande.date_creation else timezone.localtime()
    meme_mois = (DemandeAFASE.objects.filter(beneficiaire_id__in=_famille(benef),
                                             date_creation__year=debut.year, date_creation__month=debut.month)
                 .exclude(pk=demande.pk).exclude(statut__in=STATUTS_IGNORES))
    if meme_mois.exists():
        sortie.append(('attention', "Une autre AFASE est déjà demandée (ou en préparation) ce mois-ci pour cette famille "
                                    f"(n° {', '.join(str(d.pk) for d in meme_mois)}) : l'AFASE est attribuée "
                                    "une fois par mois au maximum."))
    demandeur = demande.demandeur or benef
    if demandeur.code_postal and not demandeur.code_postal.strip().startswith('13'):
        sortie.append(('attention', "Le demandeur ne réside pas dans les Bouches-du-Rhône : possible seulement en "
                                    "situation urgente et exceptionnelle relevant d'une mesure de protection de l'enfance."))
    if not demande.date_signature_demandeur:
        sortie.append(('attention', "Date de signature du demandeur non renseignée : elle est indispensable "
                                    "(le délai de traitement de 2 mois court à partir de cette date)."))
    evaluation = getattr(demande, 'evaluation_afase', None)
    if not demande.premiere_demande and evaluation and not (evaluation.situation_sociale or '').strip():
        sortie.append(('info', "Renouvellement : contextualisez la situation et son évolution dans l'évaluation."))
    if not demande.enfants.filter(concerne=True).exists() and demande.pk:
        sortie.append(('attention', "Aucun enfant coché comme concerné par la demande."))
    sortie.append(('info', "La demande est nominative : le RIB doit être au nom du demandeur (sauf versement à un tiers, "
                           "avec l'autorisation signée du demandeur)."))
    return sortie
