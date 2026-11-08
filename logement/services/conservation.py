# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/conservation.py
"""Durées de conservation des dossiers de prévention des expulsions (importées du DPO : EXPULSION_DOSSIER,
EXPULSION_DSF). Point de départ : la clôture du dossier. Rien ne se passe tant que la durée n'est pas fixée.

Sort final :
  - suppression : le dossier (et tout ce qui en dépend) est supprimé ;
  - anonymisation : l'identité est effacée (nom, adresse, n° allocataire, EXPLOC, bailleur, fiche CAF, historique,
    commentaires, messages), les chiffres restent pour les statistiques (MDS, commune, dette, étapes, décision) ;
  - versement aux archives : CID ne détruit rien, le dossier est listé « à verser » en administration.
Le diagnostic (DSF, carence), les convocations et le questionnaire suivent EXPULSION_DSF, sinon le dossier."""
import logging

from dateutil.relativedelta import relativedelta
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from core.conservation import mois, sort_final
from logement.models import DossierExpulsion as D

logger = logging.getLogger(__name__)


def _duree(code):
    base, arch = mois(code, 'base'), mois(code, 'archivage')
    if base is None and arch is None:
        return None
    return (base or 0) + (arch or 0)


def _clos_depuis(mois_total, aujourd_hui):
    limite = aujourd_hui - relativedelta(months=mois_total)
    return D.objects.filter(statut=D.CLOS, date_cloture__isnull=False, date_cloture__lt=limite)


def _messages(qs):
    from messagerie.models import Message
    Message.objects.filter(content_type=ContentType.objects.get_for_model(D),
                           object_id__in=list(qs.values_list('pk', flat=True))).delete()


def _effacer_pieces(qs):
    """Diagnostics, convocations (et le libellé nominatif des rendez-vous de l'agenda)."""
    from logement.models import ConvocationExpulsion, DiagnosticExpulsion
    from planning.models import CreneauRdv
    convs = ConvocationExpulsion.objects.filter(dossier__in=qs)
    CreneauRdv.objects.filter(pk__in=list(convs.exclude(rdv=None).values_list('rdv_id', flat=True))).update(
        description="Prévention des expulsions – diagnostic social et financier")
    n = convs.count() + DiagnosticExpulsion.objects.filter(dossier__in=qs).count()
    convs.delete()
    DiagnosticExpulsion.objects.filter(dossier__in=qs).delete()
    return n


def anonymiser(qs, aujourd_hui):
    from logement.models import EtapeExpulsion
    _messages(qs)
    _effacer_pieces(qs)
    EtapeExpulsion.objects.filter(dossier__in=qs).update(commentaire="")
    return qs.update(nom="ANONYME", prenom="", colocataire="", adresse="", proprietaire="", proprietaire_email="",
                     numero_allocataire="", numero_exploc="", caf={}, observations="", historique=[],
                     beneficiaire=None, referent=None, tribunal="", heure_audience="", anonymise_le=aujourd_hui)


def purger(aujourd_hui=None):
    """Applique les durées. Renvoie un bilan {'pieces': n, 'dossiers': n, 'a_verser': n}."""
    aujourd_hui = aujourd_hui or timezone.localdate()
    bilan = {'pieces': 0, 'dossiers': 0, 'a_verser': 0}
    duree_dsf = _duree('EXPULSION_DSF')
    if duree_dsf is not None and sort_final('EXPULSION_DSF') in ('SUPPRESSION', 'ANONYMISATION'):
        bilan['pieces'] = _effacer_pieces(_clos_depuis(duree_dsf, aujourd_hui))
    duree = _duree('EXPULSION_DOSSIER')
    if duree is not None:
        qs = _clos_depuis(duree, aujourd_hui).filter(anonymise_le__isnull=True)
        sort = sort_final('EXPULSION_DOSSIER')
        if sort == 'SUPPRESSION':
            _messages(qs)
            _effacer_pieces(qs)
            bilan['dossiers'], _ = qs.delete()
        elif sort == 'ANONYMISATION':
            bilan['dossiers'] = anonymiser(qs, aujourd_hui)
        else:
            bilan['a_verser'] = qs.count()
    if bilan['pieces'] or bilan['dossiers']:
        logger.info("Prévention des expulsions, durées de conservation : %s", bilan)
    return bilan


def a_verser(aujourd_hui=None):
    """Dossiers clos dont la durée est atteinte et dont le sort final est le versement aux archives."""
    duree = _duree('EXPULSION_DOSSIER')
    if duree is None or sort_final('EXPULSION_DOSSIER') != 'ARCHIVES':
        return D.objects.none()
    return _clos_depuis(duree, aujourd_hui or timezone.localdate()).filter(anonymise_le__isnull=True)
