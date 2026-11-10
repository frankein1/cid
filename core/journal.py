# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/journal.py
"""
Journal d'activité des agents (traçabilité RGPD), écrit dans core.AuditLog :

  - connexions, échecs de connexion (core/authentication/backends.py), déconnexions ;
  - CONSULTATIONS des dossiers (fiche usager, contrat, prescription, IP, AFASE…) : middleware, à partir du nom
    de la vue (VUES_CONSULTEES) ; une même page rouverte par le même agent dans les 10 minutes n'est notée qu'une fois ;
  - CRÉATIONS, MODIFICATIONS (avec l'avant / après des champs modifiés) et SUPPRESSIONS des modèles de
    MODELES_JOURNALISES, quand elles sont faites par un agent connecté (pas par les scripts d'installation) ;
  - EXPORTS et TÉLÉCHARGEMENTS (PDF, CSV, documents de la GED).

Les valeurs des champs sensibles (n° de sécurité sociale, mots de passe…) ne sont jamais recopiées dans le journal.
Le journal est purgé après DUREE_CONSERVATION_MOIS (12 par défaut, clé de configuration JOURNAL_DUREE_MOIS),
une fois par jour, à la première connexion (python manage.py purger_journal le fait aussi).
"""
import logging
from datetime import timedelta

from django.apps import apps
from django.db.models.signals import post_delete, post_save, pre_save
from django.urls import resolve, Resolver404
from django.utils import timezone

from core.utilisateur_courant import get_utilisateur_courant

logger = logging.getLogger(__name__)

DUREE_CONSERVATION_MOIS = 12
DEDOUBLONNAGE_MINUTES = 10

# Modèles dont les créations, modifications et suppressions sont journalisées
MODELES_JOURNALISES = [
    "beneficiaire.Beneficiaire", "beneficiaire.LienFamilial", "beneficiaire.TransfertMDS",
    "ged.DocumentGED",
    "protection_enfance.InformationPreoccupante",
    "AidFi.DemandeAFASE", "AidFi.DecisionAFASE",
    "planning.CreneauRdv",
    "insertion.ContratInsertion", "insertion.PrescriptionInsertion", "insertion.DemandeReorientation",
    "core.User",
]
# Champs dont la valeur n'est jamais écrite (seul le fait qu'ils ont changé est noté)
CHAMPS_MASQUES = {"nir", "password", "numero_fiscal", "numero_secu", "iban", "bic", "token", "secret"}
CHAMPS_IGNORES = {"modifie_le", "updated_at", "date_modification", "last_login", "cree_le", "date_creation"}

# Vues de consultation : nom de vue → (modèle, paramètre d'URL, champ de recherche)
VUES_CONSULTEES = {
    "beneficiaire:detail_beneficiaire": ("beneficiaire.Beneficiaire", "code_interne", "code_interne"),
    "beneficiaire:modifier_beneficiaire": ("beneficiaire.Beneficiaire", "code_interne", "code_interne"),
    "insertion:contrats_beneficiaire": ("beneficiaire.Beneficiaire", "code_interne", "code_interne"),
    "insertion:contrat_detail": ("insertion.ContratInsertion", "pk", "pk"),
    "insertion:prescription_detail": ("insertion.PrescriptionInsertion", "pk", "pk"),
    "insertion:reorientation_detail": ("insertion.DemandeReorientation", "pk", "pk"),
    "ged:document_detail": ("ged.DocumentGED", "pk", "pk"),
}


# ---------------------------------------------------------------------- écriture
def _ip(request):
    if request is None:
        return None
    fwd = request.META.get("HTTP_X_FORWARDED_FOR")
    return (fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR")) or None


def beneficiaire_de(objet):
    """Usager concerné par un objet (pour retrouver tout ce qui touche à un dossier)."""
    from beneficiaire.models import Beneficiaire, LienFamilial
    if objet is None:
        return None
    if isinstance(objet, Beneficiaire):
        return objet
    if isinstance(objet, LienFamilial):
        return objet.personne_a
    for champ in ("beneficiaire", "famille"):
        try:
            valeur = getattr(objet, champ, None)
        except Exception:
            valeur = None
        if isinstance(valeur, Beneficiaire):
            return valeur
    if objet.__class__.__name__ == "DocumentGED":
        try:
            if objet.content_type.model_class() is Beneficiaire:
                return Beneficiaire.objects.filter(pk=objet.object_id).first()
        except Exception:
            return None
    return None


def journaliser(action, description, *, objet=None, beneficiaire=None, details=None, request=None, user=None):
    """N'empêche jamais l'action journalisée : une erreur d'écriture est seulement notée dans les logs."""
    from django.contrib.contenttypes.models import ContentType
    from core.models import AuditLog
    try:
        user = user or get_utilisateur_courant()
        log = AuditLog(utilisateur=user, action=action, description=description[:1000], details=details or {},
                       beneficiaire=beneficiaire or beneficiaire_de(objet), ip_address=_ip(request))
        if user is not None:
            log.utilisateur_nom = (user.get_full_name() or user.username)[:150]
        if objet is not None and objet.pk is not None:
            log.content_type = ContentType.objects.get_for_model(objet)
            log.object_id = objet.pk if isinstance(objet.pk, int) else None
            log.objet_libelle = str(objet)[:255]
        if request is not None:
            log.url = request.path[:500]
            log.methode_http = request.method
            log.user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
        log.save()
        return log
    except Exception as e:   # pragma: no cover
        logger.error("Journal d'activité : %s", e)
        return None


# ---------------------------------------------------------------------- créations, modifications, suppressions
def _valeur(instance, champ):
    v = getattr(instance, champ.attname, None)
    return None if v is None else str(v)[:200]


def _avant(sender, instance, **kwargs):
    if get_utilisateur_courant() is None or instance.pk is None:
        return
    ancien = sender._default_manager.filter(pk=instance.pk).first()
    if ancien is not None:
        instance._journal_avant = {f.name: _valeur(ancien, f) for f in sender._meta.concrete_fields}


def _apres(sender, instance, created, **kwargs):
    if get_utilisateur_courant() is None:
        return
    nom = sender._meta.verbose_name
    if created:
        journaliser("CREATE", f"Création : {nom} « {instance} »", objet=instance)
        return
    avant = getattr(instance, "_journal_avant", None)
    if avant is None:
        return
    changements = {}
    for f in sender._meta.concrete_fields:
        if f.name in CHAMPS_IGNORES:
            continue
        nouveau = _valeur(instance, f)
        if avant.get(f.name) != nouveau:
            if f.name in CHAMPS_MASQUES or any(m in f.name for m in ("password", "token", "secret")):
                changements[f.name] = {"avant": "(masqué)", "apres": "(masqué)"}
            else:
                changements[f.name] = {"avant": avant.get(f.name), "apres": nouveau}
            changements[f.name]["libelle"] = str(f.verbose_name)
    instance._journal_avant = None
    if changements:
        libelles = ", ".join(str(sender._meta.get_field(c).verbose_name) for c in changements)
        journaliser("UPDATE", f"Modification : {nom} « {instance} » ({libelles})", objet=instance,
                    details={"changements": changements})


def _suppression(sender, instance, **kwargs):
    if get_utilisateur_courant() is None:
        return
    journaliser("DELETE", f"Suppression : {sender._meta.verbose_name} « {instance} »", objet=instance,
                details={"pk": str(instance.pk)})


def brancher_signaux():
    for nom in MODELES_JOURNALISES:
        try:
            modele = apps.get_model(nom)
        except LookupError:
            continue
        uid = f"journal-{nom}"
        pre_save.connect(_avant, sender=modele, dispatch_uid=uid + "-avant", weak=False)
        post_save.connect(_apres, sender=modele, dispatch_uid=uid + "-apres", weak=False)
        post_delete.connect(_suppression, sender=modele, dispatch_uid=uid + "-suppr", weak=False)


# ---------------------------------------------------------------------- connexions
def connexion(sender, request, user, **kwargs):
    purger_si_besoin()


def deconnexion(sender, request, user, **kwargs):
    if user is not None:
        journaliser("LOGOUT", f"Déconnexion : {user.username}", request=request, user=user)


# ---------------------------------------------------------------------- consultations et exports (middleware)
class JournalConsultationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            if request.method == "GET" and response.status_code == 200 and getattr(request, "user", None) \
                    and request.user.is_authenticated:
                self._noter(request, response)
        except Exception as e:   # pragma: no cover
            logger.error("Journal d'activité (middleware) : %s", e)
        return response

    def _noter(self, request, response):
        if request.path.startswith(("/static/", "/media/", "/admin/jsi18n")):
            return
        try:
            match = resolve(request.path)
        except Resolver404:
            return
        nom_vue = f"{match.namespace}:{match.url_name}" if match.namespace else match.url_name
        type_contenu = response.get("Content-Type", "")
        export = ("attachment" in response.get("Content-Disposition", "") or "application/pdf" in type_contenu
                  or "text/csv" in type_contenu or request.GET.get("export"))
        objet = None
        if nom_vue in VUES_CONSULTEES:
            modele, param, champ = VUES_CONSULTEES[nom_vue]
            valeur = match.kwargs.get(param)
            if valeur is not None:
                objet = apps.get_model(modele)._default_manager.filter(**{champ: valeur}).first()
        elif export:
            for param, valeur in match.kwargs.items():   # PDF d'un contrat, d'une prescription, document GED…
                if param in ("pk", "code_interne"):
                    objet = self._objet_depuis_vue(match, valeur, param)
                    break
        if export:
            action = "DOWNLOAD" if nom_vue == "ged:download_document" else "EXPORT"
            journaliser(action, f"{'Téléchargement' if action == 'DOWNLOAD' else 'Export'} : {request.path}"
                        + (f" ({request.GET.urlencode()})" if request.GET else ""), objet=objet, request=request)
        elif objet is not None:
            self._consultation(request, objet)

    @staticmethod
    def _objet_depuis_vue(match, valeur, param):
        prefixes = {"insertion:contrat": "insertion.ContratInsertion", "insertion:prescription":
                    "insertion.PrescriptionInsertion", "insertion:reorientation": "insertion.DemandeReorientation",
                    "ged:": "ged.DocumentGED"}
        nom_vue = f"{match.namespace}:{match.url_name}"
        if param == "code_interne":
            return apps.get_model("beneficiaire.Beneficiaire").objects.filter(code_interne=valeur).first()
        for prefixe, modele in prefixes.items():
            if nom_vue.startswith(prefixe):
                return apps.get_model(modele)._default_manager.filter(pk=valeur).first()
        return None

    @staticmethod
    def _consultation(request, objet):
        from django.contrib.contenttypes.models import ContentType
        from core.models import AuditLog
        recent = AuditLog.objects.filter(
            utilisateur=request.user, action="READ", content_type=ContentType.objects.get_for_model(objet),
            object_id=objet.pk, timestamp__gte=timezone.now() - timedelta(minutes=DEDOUBLONNAGE_MINUTES)).exists()
        if not recent:
            journaliser("READ", f"Consultation : {objet._meta.verbose_name} « {objet} »", objet=objet,
                        request=request)


# ---------------------------------------------------------------------- purge
def duree_conservation_mois():
    """Durée du journal : importée du DPO (JOURNAL_ACTIVITE, base active + archivage), sinon JOURNAL_DUREE_MOIS,
    sinon 12 mois."""
    from core.conservation import mois
    try:
        total = (mois('JOURNAL_ACTIVITE', 'base', 'JOURNAL_DUREE_MOIS') or DUREE_CONSERVATION_MOIS) \
            + (mois('JOURNAL_ACTIVITE', 'archivage') or 0)
        return max(1, total)
    except Exception:      # noqa: BLE001
        return DUREE_CONSERVATION_MOIS


def duree_recherches_mois():
    """Recherches dans l'annuaire des usagers (ANNUAIRE_RECHERCHES) : jamais plus que le journal lui-même."""
    from core.conservation import mois
    try:
        total = (mois('ANNUAIRE_RECHERCHES', 'base') or 0) + (mois('ANNUAIRE_RECHERCHES', 'archivage') or 0)
        return max(1, min(total, duree_conservation_mois())) if total else duree_conservation_mois()
    except Exception:      # noqa: BLE001
        return duree_conservation_mois()


def purger(maintenant=None):
    from dateutil.relativedelta import relativedelta
    from core.models import AuditLog
    maintenant = maintenant or timezone.now()
    n, _ = AuditLog.objects.filter(timestamp__lt=maintenant - relativedelta(months=duree_conservation_mois())).delete()
    m, _ = AuditLog.objects.filter(description__startswith="Annuaire des usagers",
                                   timestamp__lt=maintenant - relativedelta(months=duree_recherches_mois())).delete()
    return n + m


def purger_si_besoin():
    """Une fois par jour au plus (Render gratuit : pas de tâche planifiée)."""
    from core.models import Configuration
    try:
        aujourd_hui = timezone.localdate().isoformat()
        c, _ = Configuration.objects.get_or_create(
            cle="JOURNAL_DERNIERE_PURGE",
            defaults={"valeur": "", "categorie": "SECURITE", "modifiable": False,
                      "description": "Date de la dernière purge du journal d'activité (automatique)."})
        if c.valeur != aujourd_hui:
            n = purger()
            try:
                from logement.services.conservation import purger as purger_expulsions
                purger_expulsions()
            except Exception as e:   # noqa: BLE001 – la purge du journal ne dépend pas du reste
                logger.error("Durées de conservation (expulsions) : %s", e)
            try:
                from logement.services.conservation import purger_hebergement
                from logement.services.hebergement import alerter
                purger_hebergement()
                alerter()
            except Exception as e:   # noqa: BLE001
                logger.error("Hébergement d'urgence (échéances, durées de conservation) : %s", e)
            Configuration.objects.filter(pk=c.pk).update(valeur=aujourd_hui)
            if n:
                logger.info("Journal d'activité : %s ligne(s) purgée(s)", n)
    except Exception as e:   # pragma: no cover
        logger.error("Purge du journal d'activité : %s", e)
