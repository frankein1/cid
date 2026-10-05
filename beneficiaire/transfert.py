# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

# beneficiaire/transfert.py
"""
Transfert d'un usager (et des membres de son foyer) vers une autre MDS.

Les documents GED et les aides sont rattachés à l'USAGER : ils le suivent
automatiquement. Ce module trace le transfert et prévient l'ancienne MDS.
"""

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Beneficiaire, LienFamilial, TransfertMDS

# Ordre de recherche du responsable à prévenir dans la MDS d'origine
PROFILS_RESPONSABLE = ('MDS_ADJOINT_PREVENTION', 'MDS_RESPONSABLE')


def membres_famille(beneficiaire):
    """Membres liés au bénéficiaire, avec la proposition 'à transférer' par défaut."""
    liens = LienFamilial.objects.filter(
        Q(personne_a=beneficiaire) | Q(personne_b=beneficiaire)
    ).select_related('personne_a__mds', 'personne_b__mds', 'personne_a__referent_mds', 'personne_b__referent_mds')

    membres = {}
    for lien in liens:
        autre = lien.personne_b if lien.personne_a_id == beneficiaire.pk else lien.personne_a
        if autre.pk in membres or autre.statut in ('SORTI', 'DECEDE'):
            continue
        membres[autre.pk] = {
            'personne': autre,
            'lien': lien,
            # Coché par défaut : vit au foyer ET suivi dans la même MDS
            'coche': lien.vit_au_foyer and autre.mds_id == beneficiaire.mds_id,
        }
    return list(membres.values())


def responsable_mds(mds):
    """Adjoint prévention (MDS de territoire), sinon responsable (MDS de proximité), sinon directeur de la fiche MDS."""
    if not mds:
        return None
    from mds.models import UserMDSProfile
    for code in PROFILS_RESPONSABLE:
        ump = UserMDSProfile.objects.filter(
            mds=mds, actif=True, user__is_active=True, user__profils__code=code
        ).select_related('user').first()
        if ump:
            return ump.user
    return mds.responsable


def aides_en_cours(personne):
    from AidFi.models.m_generique import DemandeAide
    return DemandeAide.objects.filter(beneficiaire=personne).exclude(
        statut__in=('ACCORDEE', 'REFUSEE', 'ANNULEE', 'VALIDE')
    )


@transaction.atomic
def transferer(beneficiaire, membres, mds_destination, demandeur, request=None):
    """
    Transfère 'beneficiaire' + 'membres' vers 'mds_destination'.
    Retourne la liste des TransfertMDS créés.
    """
    from messagerie.models import Message, StatutLecture
    from core.models.audit import AuditLog

    personnes = [beneficiaire] + [m for m in membres if m.pk != beneficiaire.pk]
    transferts = []
    # Regroupement des avis par (MDS d'origine, référent sortant)
    a_prevenir = {}

    for p in personnes:
        if p.mds_id == mds_destination.pk:
            continue
        t = TransfertMDS.objects.create(
            beneficiaire=p,
            mds_origine=p.mds,
            mds_destination=mds_destination,
            referent_sortant=p.referent_mds,
            demande_par=demandeur,
            transfere_avec=beneficiaire if p.pk != beneficiaire.pk else None,
        )
        transferts.append(t)
        a_prevenir.setdefault((p.mds, p.referent_mds), []).append(p)

        p.mds = mds_destination
        p.referent_mds = None          # le référent appartenait à l'ancienne MDS
        p.save(update_fields=['mds', 'referent_mds'])

        AuditLog.log_action(
            demandeur, 'UPDATE',
            f"Transfert de MDS : {t.mds_origine} → {mds_destination}",
            objet=p, request=request,
            details={'mds_origine': t.mds_origine_id, 'mds_destination': mds_destination.pk,
                     'referent_sortant': t.referent_sortant_id, 'transfert_id': t.pk},
        )

    # Messages à l'ancienne MDS : référent sortant + son responsable
    date_txt = timezone.localtime().strftime('%d/%m/%Y à %H:%M')
    for (mds_origine, referent), groupe in a_prevenir.items():
        responsable = responsable_mds(mds_origine)
        destinataire = referent or responsable
        if not destinataire:
            continue
        copie = responsable if (responsable and responsable != destinataire) else None
        noms = "\n".join(f"- {p.prenom} {p.nom.upper()} ({p.code_interne})" for p in groupe)
        msg = Message.objects.create(
            expediteur=demandeur,
            destinataire=destinataire,
            copie=copie,
            beneficiaire=beneficiaire,
            objet=f"Transfert de MDS : {beneficiaire.prenom} {beneficiaire.nom.upper()}",
            contenu=(
                f"Le dossier suivant a été transféré de {mds_origine} vers {mds_destination} "
                f"le {date_txt}.\n\n{noms}\n\n"
                f"Transfert demandé par : {demandeur.get_full_name() or demandeur.username}.\n"
                f"Message automatique de CID."
            ),
            motif='changement_situation',
            priorite='importante',
        )
        StatutLecture.objects.create(message=msg, utilisateur=destinataire, type_reception='destinataire')
        if copie:
            StatutLecture.objects.create(message=msg, utilisateur=copie, type_reception='copie')

    return transferts
