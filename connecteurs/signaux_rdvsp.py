# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/signaux_rdvsp.py
"""
Ce qui change dans l'agenda CID est répercuté dans RDV-Solidarités (connecteurs/rdvsp_synchro.py) :
créneau pris ou libéré, jour bloqué, statut venu / absent. Seulement si la passerelle est prête ;
jamais d'erreur pour l'agent (tout est tracé), et toujours après l'enregistrement en base.
"""
import logging

from django.db import transaction
from django.db.models.signals import post_save, pre_delete

from . import rdv_service_public as api

logger = logging.getLogger(__name__)


def _actif():
    if not api.est_actif():        # démo : simple lecture des variables d'environnement, aucun accès base
        return False
    from . import rdvsp_synchro
    return rdvsp_synchro.prete()


def _apres(fonction, *args, **kw):
    def lancer():
        try:
            fonction(*args, **kw)
        except Exception:
            logger.exception("rdvsp: synchronisation d'un changement CID impossible")
    transaction.on_commit(lancer)


def creneau_enregistre(sender, instance, **kwargs):
    if getattr(instance, "_depuis_rdvsp", False) or not _actif():
        return
    from . import rdvsp_synchro
    _apres(rdvsp_synchro.maj_blocage_creneau, instance)
    _apres(rdvsp_synchro.renvoyer_statut, instance)


def creneau_supprime(sender, instance, **kwargs):
    if not _actif():
        return
    from . import rdvsp_synchro
    from .models import AbsenceRDVSP
    absences = list(AbsenceRDVSP.objects.filter(raison=AbsenceRDVSP.CRENEAU, creneau_id=instance.pk))
    if absences:
        _apres(lambda: rdvsp_synchro._supprimer_absences(rdvsp_synchro.client(),
                                                         AbsenceRDVSP.objects.filter(pk__in=[a.pk for a in absences])))


def jour_bloque_enregistre(sender, instance, **kwargs):
    if _actif():
        from . import rdvsp_synchro
        _apres(rdvsp_synchro.maj_blocage_jour, instance)


def jour_bloque_supprime(sender, instance, **kwargs):
    if not _actif():
        return
    from . import rdvsp_synchro
    from .models import AbsenceRDVSP
    ids = list(AbsenceRDVSP.objects.filter(raison=AbsenceRDVSP.JOUR_BLOQUE, jour_bloque_id=instance.pk)
               .values_list("pk", flat=True))
    if ids:
        _apres(lambda: rdvsp_synchro._supprimer_absences(rdvsp_synchro.client(),
                                                         AbsenceRDVSP.objects.filter(pk__in=ids)))


def connexion(sender, request, user, **kwargs):
    """Sans tâche planifiée (Render) : synchronisation au plus une fois par jour, à une connexion, en arrière-plan."""
    import sys
    if not api.est_actif() or sys.argv[1:2] == ["test"]:   # jamais de tâche en arrière-plan pendant les tests
        return
    import threading
    from datetime import timedelta
    from django.utils import timezone
    from . import rdvsp_synchro
    from .models import ParametresRDVSP
    p = ParametresRDVSP.get()
    if not rdvsp_synchro.prete():
        return
    _invitations_si_besoin()
    if p.derniere_synchro and timezone.now() - p.derniere_synchro < timedelta(hours=24):
        return
    ParametresRDVSP.objects.filter(pk=p.pk).update(derniere_synchro=timezone.now())   # évite les lancements en double

    def lancer():
        try:
            rdvsp_synchro.synchroniser()
            rdvsp_synchro.purger_avis()
        except Exception:
            logger.exception("rdvsp: synchronisation quotidienne impossible")
        finally:
            from django.db import connection
            connection.close()
    threading.Thread(target=lancer, daemon=True).start()


def _invitations_si_besoin():
    """Étape 2 : préparation (1er lundi) et envoi (le lendemain soir) des invitations, en arrière-plan."""
    import threading
    from . import rdvsp_invitations
    if not rdvsp_invitations.a_traiter():
        return
    global _ENVOI_EN_COURS
    if _ENVOI_EN_COURS:
        return
    _ENVOI_EN_COURS = True

    def lancer():
        global _ENVOI_EN_COURS
        try:
            rdvsp_invitations.traiter()
        except Exception:
            logger.exception("rdvsp: invitations non traitées")
        finally:
            _ENVOI_EN_COURS = False
            from django.db import connection
            connection.close()
    threading.Thread(target=lancer, daemon=True).start()


_ENVOI_EN_COURS = False


def brancher():
    from django.contrib.auth.signals import user_logged_in
    user_logged_in.connect(connexion, dispatch_uid="rdvsp_connexion_quotidienne")
    from planning.models import CreneauRdv, JourBloque
    post_save.connect(creneau_enregistre, sender=CreneauRdv, dispatch_uid="rdvsp_creneau_save")
    # pre_delete : avant que la suppression ne détache les blocages (SET_NULL)
    pre_delete.connect(creneau_supprime, sender=CreneauRdv, dispatch_uid="rdvsp_creneau_delete")
    post_save.connect(jour_bloque_enregistre, sender=JourBloque, dispatch_uid="rdvsp_jb_save")
    pre_delete.connect(jour_bloque_supprime, sender=JourBloque, dispatch_uid="rdvsp_jb_delete")
