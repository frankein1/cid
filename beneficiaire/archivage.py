# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/archivage.py
"""
Cycle de vie RGPD d'un dossier usager (inspiré de Mon Suivi Social, réécrit pour CID).

1. Proposition : un dossier sans activité depuis N ans (3 par défaut, réglable) est proposé
   à l'archivage, aux cadres de sa MDS. Jamais s'il a une information préoccupante ou un
   suivi enfance (protection de l'enfance).
2. Archivage : le dossier est MASQUÉ partout dans CID (gestionnaire par défaut) et en LECTURE SEULE.
   Il peut être désarchivé (retour de l'usager).
3. Effacement définitif : uniquement sur décision d'un administrateur, qui confirme une liste de
   dossiers archivés depuis au moins M mois (12 par défaut, réglable). Tout ce qui dépend du dossier
   est supprimé (documents de la GED compris) ; il ne reste qu'une trace anonyme (OperationRGPD).

Durées : Administration → Durées de conservation (USAGER_DOSSIER), sinon les anciennes clés de configuration
RGPD_ARCHIVAGE_ANS et RGPD_EFFACEMENT_MOIS.
"""
from datetime import date, datetime, timedelta

from django.contrib.contenttypes.models import ContentType
from django.db import models, router, transaction
from django.db.models import Max, Q
from django.db.models.deletion import Collector, ProtectedError, RestrictedError
from django.utils import timezone

from core.models import Configuration
from .models import Beneficiaire, OperationRGPD

MOTIFS = [
    ('FIN_SUIVI', "Fin d'accompagnement"),
    ('SANS_NOUVELLES', "Sans nouvelles de l'usager"),
    ('DEMENAGEMENT', "Déménagement hors département"),
    ('REORIENTATION', "Réorientation vers un autre organisme"),
    ('DECES', "Décès"),
    ('AUTRE', "Autre"),
]
MOTIFS_DESARCHIVAGE = [
    ('RETOUR', "Retour de l'usager"),
    ('ERREUR', "Archivé par erreur"),
    ('AUTRE', "Autre"),
]

# Champs qui datent une activité dans les tables liées au dossier (le premier trouvé ne suffit pas :
# on prend le plus récent de tous ceux présents, y compris la date d'un RDV à venir).
CHAMPS_ACTIVITE = ('date_modification', 'modifie_le', 'updated_at', 'date_maj', 'date_creation', 'cree_le',
                   'created_at', 'date', 'date_transfert', 'date_debut', 'date_inscription')
# Relations qui ne sont pas une activité de l'usager
RELATIONS_IGNOREES = {('beneficiaire', 'OperationRGPD')}


def _conf(cle, defaut):
    try:
        return int(Configuration.objects.get(cle=cle).valeur)
    except (Configuration.DoesNotExist, ValueError, TypeError):
        return defaut


def delai_archivage_mois():
    """Durée de conservation importée du DPO (USAGER_DOSSIER), sinon RGPD_ARCHIVAGE_ANS, sinon 36 mois."""
    from core.conservation import mois
    return mois('USAGER_DOSSIER', 'base', 'RGPD_ARCHIVAGE_ANS', facteur=12)


def delai_archivage_ans():
    """Conservé pour compatibilité ; préférer delai_archivage_mois()."""
    return round(delai_archivage_mois() / 12, 1)


def delai_effacement_mois():
    from core.conservation import mois
    return mois('USAGER_DOSSIER', 'archivage', 'RGPD_EFFACEMENT_MOIS')


def _jour(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return timezone.localtime(v).date() if timezone.is_aware(v) else v.date()
    return v


def _relations():
    """Relations inverses vers Beneficiaire (y compris related_name='+')."""
    for f in Beneficiaire._meta.get_fields(include_hidden=True):
        if f.auto_created and not f.concrete and (f.one_to_many or f.one_to_one) and f.related_model:
            m = f.related_model
            if (m._meta.app_label, m.__name__) in {(a, n) for a, n in RELATIONS_IGNOREES}:
                continue
            champs = [c for c in CHAMPS_ACTIVITE
                      if any(x.name == c and isinstance(x, models.DateField) for x in m._meta.concrete_fields)]
            if champs:
                yield m, f.field.name, champs


def derniere_activite(ids):
    """{id usager: date de la dernière activité}, toutes tables confondues (fiche, RDV, aides, RSA, GED…)."""
    ids = list(ids)
    res = {}

    def garder(i, d):
        d = _jour(d)
        if i is not None and d and (res.get(i) is None or d > res[i]):
            res[i] = d

    for i, dc, dm in Beneficiaire.tous.filter(pk__in=ids).values_list('pk', 'date_creation', 'date_modification'):
        garder(i, dc)
        garder(i, dm)
    for m, fk, champs in _relations():
        lignes = (m._base_manager.filter(**{f"{fk}__in": ids}).values(fk)
                  .annotate(**{f"m_{c}": Max(c) for c in champs}))
        for l in lignes:
            for c in champs:
                garder(l[fk], l[f"m_{c}"])
    from ged.models import DocumentGED
    ct = ContentType.objects.get_for_model(Beneficiaire)
    for l in (DocumentGED.objects.filter(content_type=ct, object_id__in=ids).values('object_id')
              .annotate(m=Max('date_creation'))):
        garder(l['object_id'], l['m'])
    return res


def exclus(ids=None):
    """Dossiers jamais proposés : information préoccupante (famille, adulte, enfant) ou RDV IP / enfance."""
    from planning.models import CreneauRdv
    from protection_enfance.models import AdulteIP, EnfantIP, InformationPreoccupante
    ens = set(InformationPreoccupante.objects.exclude(famille=None).values_list('famille_id', flat=True))
    ens |= set(AdulteIP.objects.exclude(beneficiaire=None).values_list('beneficiaire_id', flat=True))
    ens |= set(EnfantIP.objects.exclude(beneficiaire=None).values_list('beneficiaire_id', flat=True))
    ens |= set(CreneauRdv.objects.filter(domaine__in=('IP', 'ENFANCE')).exclude(beneficiaire=None)
               .values_list('beneficiaire_id', flat=True))
    return ens if ids is None else ens & set(ids)


def candidats(mds_ids=None, aujourd_hui=None):
    """[(usager, date de dernière activité)] proposés à l'archivage, du plus ancien au plus récent."""
    aujourd_hui = aujourd_hui or timezone.localdate()
    from dateutil.relativedelta import relativedelta
    limite = aujourd_hui - relativedelta(months=delai_archivage_mois())
    qs = Beneficiaire.objects.all()  # sans les archivés
    if mds_ids is not None:
        qs = qs.filter(mds_id__in=mds_ids)
    # pré-filtre : fiche elle-même inactive depuis la limite
    ids = list(qs.filter(date_modification__date__lt=limite).values_list('pk', flat=True))
    if not ids:
        return []
    activite = derniere_activite(ids)
    retenus = [i for i in ids if (activite.get(i) or date.min) < limite]
    retenus = set(retenus) - exclus(retenus)
    usagers = Beneficiaire.objects.filter(pk__in=retenus).select_related('mds', 'referent_mds')
    return sorted(((b, activite.get(b.pk)) for b in usagers), key=lambda x: x[1] or date.min)


class ErreurRGPD(Exception):
    pass


@transaction.atomic
def archiver(beneficiaire, user, motif, commentaire=""):
    if beneficiaire.statut == 'ARCHIVE':
        raise ErreurRGPD("Ce dossier est déjà archivé.")
    if motif not in dict(MOTIFS):
        raise ErreurRGPD("Motif d'archivage inconnu.")
    if beneficiaire.pk in exclus([beneficiaire.pk]):
        raise ErreurRGPD("Dossier lié à une information préoccupante ou à un suivi enfance : jamais archivé.")
    activite = derniere_activite([beneficiaire.pk]).get(beneficiaire.pk)
    # Feuilles jaunes : notes personnelles et synthèses privées sont détruites avant l'archivage
    from core.models import AuditLog
    from beneficiaire.models_journal import EntretienSocial, NotePersonnelle
    nb_notes = beneficiaire.notes_personnelles.count()
    nb_synth = EntretienSocial.objects.filter(beneficiaire=beneficiaire).exclude(synthese_privee='').count()
    beneficiaire.notes_personnelles.all().delete()
    EntretienSocial.objects.filter(beneficiaire=beneficiaire).exclude(synthese_privee='').update(synthese_privee='')
    if nb_notes or nb_synth:
        AuditLog.log_action(user, 'DELETE', f"Archivage : {nb_notes} note(s) et {nb_synth} synthèse(s) privée(s) détruites",
                            objet=beneficiaire)
        commentaire = (commentaire + f" ; notes détruites : {nb_notes}, synthèses privées : {nb_synth}").strip(" ;")
    Beneficiaire.tous.filter(pk=beneficiaire.pk).update(
        statut_avant_archivage=beneficiaire.statut, statut='ARCHIVE', date_archivage=timezone.now(),
        archive_par=user, motif_archivage=motif)
    return OperationRGPD.objects.create(beneficiaire=beneficiaire, action=OperationRGPD.ARCHIVAGE, motif=motif,
                                        commentaire=commentaire[:255], mds=beneficiaire.mds,
                                        derniere_activite=activite, par=user)


@transaction.atomic
def desarchiver(beneficiaire, user, motif, commentaire=""):
    if beneficiaire.statut != 'ARCHIVE':
        raise ErreurRGPD("Ce dossier n'est pas archivé.")
    Beneficiaire.tous.filter(pk=beneficiaire.pk).update(
        statut=beneficiaire.statut_avant_archivage or 'ACTIF', statut_avant_archivage='', date_archivage=None,
        archive_par=None, motif_archivage='')
    return OperationRGPD.objects.create(beneficiaire=beneficiaire, action=OperationRGPD.DESARCHIVAGE, motif=motif,
                                        commentaire=commentaire[:255], mds=beneficiaire.mds, par=user)


def archives(mds_ids=None):
    qs = Beneficiaire.tous.filter(statut='ARCHIVE').select_related('mds', 'archive_par')
    return qs.filter(mds_id__in=mds_ids) if mds_ids is not None else qs


def effacables():
    limite = timezone.now() - timedelta(days=round(delai_effacement_mois() * 30.44))
    return archives().filter(date_archivage__lte=limite).order_by('date_archivage')


def _collecte(beneficiaire):
    """Tout ce qui serait effacé avec le dossier (cascades + documents de la GED rattachés)."""
    from ged.models import DocumentGED
    collecteur = Collector(using=router.db_for_write(Beneficiaire))
    collecteur.collect([beneficiaire])
    docs = Q(pk__in=[])
    for modele, objets in collecteur.data.items():
        ct = ContentType.objects.get_for_model(modele)
        docs |= Q(content_type=ct, object_id__in=[o.pk for o in objets])
    documents = list(DocumentGED.objects.filter(docs))
    return collecteur, documents


def bilan(beneficiaire):
    """{'elements': {libellé: nombre}, 'blocage': message ou None}."""
    try:
        collecteur, documents = _collecte(beneficiaire)
    except (ProtectedError, RestrictedError) as e:
        protegees = sorted({o._meta.verbose_name for o in e.protected_objects if hasattr(o, '_meta')}
                           if isinstance(e, ProtectedError) else
                           {o._meta.verbose_name for o in e.restricted_objects if hasattr(o, '_meta')})
        return {'elements': {}, 'blocage': "Effacement impossible : le dossier est cité par " + ", ".join(
            str(p) for p in protegees) + " d'un autre dossier (à conserver)."}
    elements = {}
    for modele, objets in collecteur.data.items():
        if modele is Beneficiaire:
            continue
        nom = str(modele._meta.verbose_name_plural)
        elements[nom] = elements.get(nom, 0) + len(objets)
    if documents:
        elements["documents de la GED"] = len(documents)
    return {'elements': elements, 'blocage': None}


def effacer(beneficiaire, user):
    """Effacement définitif d'un dossier archivé. Renvoie la trace anonyme."""
    if beneficiaire.statut != 'ARCHIVE':
        raise ErreurRGPD("Seul un dossier archivé peut être effacé.")
    b = bilan(beneficiaire)
    if b['blocage']:
        raise ErreurRGPD(b['blocage'])
    with transaction.atomic():
        _, documents = _collecte(beneficiaire)
        for d in documents:
            d.delete()           # les fichiers sont purgés du stockage par les signaux de la GED
        trace = OperationRGPD.objects.create(
            action=OperationRGPD.EFFACEMENT, motif=beneficiaire.motif_archivage, mds=beneficiaire.mds,
            derniere_activite=beneficiaire.operations_rgpd.filter(action=OperationRGPD.ARCHIVAGE)
            .values_list('derniere_activite', flat=True).first(), elements_effaces=b['elements'], par=user)
        pk = beneficiaire.pk
        beneficiaire.delete()    # les traces d'archivage perdent leur lien : elles deviennent anonymes
        _anonymiser_journal(pk)
    return trace


def _anonymiser_journal(pk):
    """
    Journal d'activité (s'il est installé) : les lignes du dossier effacé, y compris celles écrites pendant
    l'effacement, perdent le lien et le nom de l'usager ; il reste qui a fait quoi, et quand.
    """
    from core.models import AuditLog
    champs = {f.name for f in AuditLog._meta.concrete_fields}
    if 'beneficiaire' not in champs:
        return
    maj = {'beneficiaire': None}
    if 'objet_libelle' in champs:
        maj['objet_libelle'] = "(dossier effacé)"
    AuditLog.objects.filter(beneficiaire_id=pk).update(**maj)
