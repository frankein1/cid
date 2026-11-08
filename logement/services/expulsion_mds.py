# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/expulsion_mds.py
"""Travail de la MDS sur un dossier d'expulsion : convocations au diagnostic (avec le rendez-vous dans l'agenda de
l'agent), questionnaire au bailleur, DSF ou bordereau de carence, visa du cadre en un clic, transmission."""
from datetime import timedelta

from django.utils import timezone

from logement.models import ConvocationExpulsion as C, DiagnosticExpulsion as G, EtapeExpulsion

from .expulsion import _message, prevenir_sl


def _etape(dossier, type_etape, user, commentaire=""):
    EtapeExpulsion.objects.create(dossier=dossier, type_etape=type_etape, date=timezone.localdate(),
                                  commentaire=commentaire, saisi_par=user)


# ------------------------------------------------------------------------------------------------- convocations
def convoquer(dossier, user, date_rdv, agent=None, lieu="", duree=45):
    """1re convocation, ou 2e et dernière si une première est restée sans réponse. Le rendez-vous est posé dans
    l'agenda de l'agent qui reçoit (planning de CID)."""
    from planning.models import CreneauRdv
    rang = C.DSF_2 if dossier.convocations.filter(type_convocation=C.DSF_1).exists() else C.DSF_1
    agent = agent or dossier.referent or user
    local = timezone.localtime(date_rdv)
    rdv = CreneauRdv.objects.create(
        date=local.date(), heure_debut=local.time(), heure_fin=(local + timedelta(minutes=duree)).time(),
        duree_minutes=duree, mds=dossier.mds, agent=agent, beneficiaire=dossier.beneficiaire,
        nature='HORS_PERMANENCE', domaine='SOCIAL', type_rdv='HORS_PERMANENCE', statut='RESERVE',
        modalite='MDS' if not lieu else 'AUTRE', lieu_precis=lieu[:200],
        description=f"Prévention des expulsions – diagnostic social et financier ({dossier.numero}, "
                    f"{dossier.nom_complet})", cree_par=user, reserve_par=user, date_reservation=timezone.now())
    conv = C.objects.create(dossier=dossier, type_convocation=rang, date_rdv=date_rdv, lieu=lieu, agent=agent,
                            rdv=rdv, cree_par=user)
    dossier.tracer(user, "Convocation", f"{conv.get_type_convocation_display()} : {local:%d/%m/%Y à %H:%M}")
    dossier.save()
    return conv


_STATUT_RDV = {C.VENU: 'VENU_RECU', C.ABSENT: 'ABSENT', C.ANNULE: 'ANNULE_MDS'}


def noter(conv, statut, user):
    """Venu, absent, annulé : la convocation et le rendez-vous de l'agenda suivent."""
    conv.statut = statut
    conv.save(update_fields=['statut'])
    if conv.rdv_id and statut in _STATUT_RDV:
        conv.rdv.statut = _STATUT_RDV[statut]
        conv.rdv.save(update_fields=['statut'])
    conv.dossier.tracer(user, "Convocation", f"{conv.get_type_convocation_display()} : {conv.get_statut_display().lower()}")
    conv.dossier.save()


def carence_possible(dossier):
    """Deux convocations sans réponse : le bordereau de carence remplace le DSF."""
    return dossier.convocations.filter(statut=C.ABSENT).count() >= 2 and not dossier.convocations.filter(
        statut=C.VENU).exists()


def questionnaire_envoye(dossier, user, date_retour):
    dossier.questionnaire_bailleur_le = timezone.localdate()
    dossier.tracer(user, "Questionnaire envoyé au bailleur", f"retour souhaité avant le {date_retour:%d/%m/%Y}")
    dossier.save()
    _etape(dossier, 'QUESTIONNAIRE_BAILLEUR', user, f"Retour souhaité avant le {date_retour:%d/%m/%Y}.")


# ------------------------------------------------------------------------------------------------- DSF / carence
def nouveau_diagnostic(dossier, user, type_document):
    from .dsf import preremplir
    from .expulsion_documents import valeurs_carence
    g = G(dossier=dossier, type_document=type_document, redacteur=user)
    if type_document == G.DSF:
        g.donnees = preremplir(dossier, user)
    else:
        v = valeurs_carence(g)
        g.donnees = {k: v[k] for k in ('convocations',) if v.get(k)}
    g.tracer(user, "Ouvert", g.get_type_document_display())
    g.save()
    return g


def demander_visa(g, user):
    from beneficiaire.transfert import responsable_mds
    g.statut = G.A_VISER
    g.tracer(user, "Visa du cadre demandé")
    g.save()
    cadre = responsable_mds(g.dossier.mds)
    _message(user, cadre, g.dossier, f"Visa demandé : {g.get_type_document_display().lower()} – {g.dossier.nom_complet}",
             f"{user.get_full_name() or user.username} demande votre visa sur le {g.get_type_document_display().lower()} "
             f"du dossier {g.dossier.numero}. Un clic suffit : « Viser » sur la page du document.")
    return cadre


def viser(g, user):
    g.statut, g.cadre, g.date_validation_cadre = G.VISE, user, timezone.now()
    g.tracer(user, "Visé par le cadre")
    g.save()
    if g.redacteur_id and g.redacteur_id != user.pk:
        _message(user, g.redacteur, g.dossier, f"Visé : {g.get_type_document_display().lower()} – {g.dossier.nom_complet}",
                 f"Le {g.get_type_document_display().lower()} du dossier {g.dossier.numero} est visé : vous pouvez le "
                 "transmettre.")


def marquer_transmis(g, user, mode):
    g.statut, g.date_envoi = G.ENVOYE, timezone.localdate()
    g.tracer(user, "Transmis" + (" par mail" if mode == 'MAIL' else " (imprimé)"))
    g.save()
    _etape(g.dossier, 'DSF' if g.type_document == G.DSF else 'CARENCE', user,
           "Transmis par mail." if mode == 'MAIL' else "Imprimé pour envoi.")
    prevenir_sl(g.dossier, user, f"Prévention des expulsions : {g.get_type_document_display().lower()} transmis – "
                                 f"{g.dossier.nom_complet}",
                f"La MDS a transmis le {g.get_type_document_display().lower()} du dossier {g.dossier.numero}.")


def peut_viser(user, g):
    return bool(g.dossier.mds_id and user.a_la_capacite('peut_valider') and user.a_acces_mds(g.dossier.mds))
