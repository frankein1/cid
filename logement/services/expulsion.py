# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/expulsion.py
"""Prévention des expulsions : droits (Service Logement, MDS), affectation, notifications et statistiques.

Service Logement (SL) : cadres et adjoint (gestion + encadrement + stats), secrétariat (stats seules), agents
administratifs (gestion). Les MDS voient et suivent les dossiers qui leur sont affectés."""
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from logement.models import DossierExpulsion as D


# ------------------------------------------------------------------------------------------------- droits
def est_sl(user):
    return user.is_authenticated and (user.a_la_capacite('expulsion_sl_gestion')
                                      or user.a_la_capacite('expulsion_sl_pilotage'))


def est_admin(user):
    return user.is_authenticated and user.a_la_capacite('peut_administrer')


def peut_voir_module(user):
    return user.is_authenticated and (est_sl(user) or est_admin(user) or user.a_la_capacite('peut_voir'))


def peut_voir_stats(user):
    return user.is_authenticated and (est_sl(user) or est_admin(user) or user.a_la_capacite('expulsion_sl_stats')
                                      or user.a_la_capacite('peut_voir_stats'))


def stats_departementales(user):
    return est_sl(user) or est_admin(user) or user.a_la_capacite('expulsion_sl_stats')


def mds_de(user):
    from mds.models import MDS
    return MDS.objects.filter(profils_utilisateurs__user=user, profils_utilisateurs__actif=True).distinct()


def dossiers_visibles(user):
    qs = D.objects.select_related('mds', 'referent', 'beneficiaire')
    if est_sl(user) or est_admin(user):
        return qs
    if not user.a_la_capacite('peut_voir'):
        return qs.none()
    return qs.filter(mds__in=mds_de(user))


def peut_voir(user, d):
    return dossiers_visibles(user).filter(pk=d.pk).exists()


def peut_creer(user):
    """Le Service Logement ouvre les dossiers et les affecte (par arrondissement à Marseille, par ville ailleurs)."""
    return est_sl(user) or est_admin(user)


def peut_ecrire(user, d):
    """Fiche, décision, étapes : le Service Logement partout, les agents de la MDS sur les dossiers de leur MDS."""
    if est_sl(user) or est_admin(user):
        return True
    return bool(d.mds_id and user.a_la_capacite('peut_modifier') and user.a_acces_mds(d.mds))


def peut_affecter(user):
    return est_sl(user) or est_admin(user)


def peut_designer_referent(user, d):
    """Le cadre de la MDS désigne le référent ; un agent peut prendre le dossier lui-même."""
    if est_sl(user) or est_admin(user):
        return True
    return bool(d.mds_id and user.a_la_capacite('peut_valider') and user.a_acces_mds(d.mds))


def peut_prendre(user, d):
    return bool(d.mds_id and d.referent_id != user.pk and user.a_la_capacite('peut_instruire')
                and user.a_acces_mds(d.mds))


def peut_supprimer(user):
    return user.is_authenticated and (user.a_la_capacite('expulsion_sl_pilotage') or est_admin(user))


def referents_possibles(d):
    from django.contrib.auth import get_user_model
    if not d.mds_id:
        return get_user_model().objects.none()
    return (get_user_model().objects.filter(is_active=True, profils_mds__mds=d.mds, profils_mds__actif=True)
            .distinct().order_by('last_name', 'first_name'))


def peut_rattacher(user, d, b):
    """Le Service Logement rattache n'importe quel usager (identité de base, annuaire). Usager inconnu au départ : la
    MDS, après la mise à disposition, peut rattacher le dossier à l'usager qu'elle a créé chez elle (sans changer
    l'affectation, qui reste au Service Logement)."""
    if not peut_ecrire(user, d) or b.statut == 'ARCHIVE':
        return False
    if est_sl(user) or est_admin(user):
        return True
    return bool(d.mds_id and b.mds_id == d.mds_id)


def rattacher(d, b, user, affecter_mds=True):
    """Rattache l'usager. Côté Service Logement, le dossier suit la MDS de l'usager (le responsable est prévenu).
    L'appelant enregistre le dossier."""
    d.beneficiaire = b
    d.tracer(user, "Usager rattaché", f"{b.nom.upper()} {b.prenom} ({b.code_interne})")
    if affecter_mds and b.mds_id and b.mds_id != d.mds_id and (est_sl(user) or est_admin(user)):
        d.save()
        affecter(d, b.mds, user)


# ------------------------------------------------------------------------------------------------- messages
def _message(expediteur, destinataire, d, objet, contenu):
    from django.contrib.contenttypes.models import ContentType
    from messagerie.models import Message, StatutLecture
    if not destinataire or not destinataire.is_active or (expediteur and destinataire.pk == expediteur.pk):
        return None
    msg = Message.objects.create(
        expediteur=expediteur, destinataire=destinataire, beneficiaire=d.beneficiaire, objet=objet[:255],
        contenu=contenu + "\n\nMessage automatique de CID.", motif='autre', priorite='importante',
        content_type=ContentType.objects.get_for_model(d), object_id=d.pk, reference=d.numero)
    StatutLecture.objects.create(message=msg, utilisateur=destinataire, type_reception='destinataire')
    return msg


def _audience(d):
    return f" Audience le {d.date_audience:%d/%m/%Y}." if d.date_audience else ""


def affecter(d, mds, user):
    """Le Service Logement confie le dossier à une MDS : son responsable est prévenu dans CID (fin du mail PDF)."""
    from beneficiaire.transfert import responsable_mds
    ancienne = d.mds
    if ancienne == mds:
        return
    d.mds = mds
    if ancienne and ancienne != mds:
        d.referent = None
    d.tracer(user, "Affecté à la MDS", f"{mds}" + (f" (auparavant {ancienne})" if ancienne else ""))
    d.save()
    _message(user, responsable_mds(mds), d, f"Prévention des expulsions : nouveau dossier – {d.nom_complet}",
             f"Le Service Logement confie à votre MDS le dossier {d.numero} ({d.nom_complet}, {d.adresse_complete})."
             + _audience(d) + " Désignez le référent social depuis le dossier.")


def designer_referent(d, referent, user):
    d.referent = referent
    d.tracer(user, "Référent social désigné", referent.get_full_name() or referent.username)
    d.save()
    if referent != user:
        _message(user, referent, d, f"Prévention des expulsions : dossier {d.numero} – {d.nom_complet}",
                 f"Vous êtes désigné(e) référent(e) du dossier {d.numero} ({d.nom_complet})." + _audience(d))


def prevenir_sl(d, user, objet, contenu):
    """Prévenir les agents du Service Logement (ex. décision saisie par la MDS, dossier clos)."""
    from django.contrib.auth import get_user_model
    agents = get_user_model().objects.filter(is_active=True, profils__capacites__code='expulsion_sl_gestion').distinct()
    for a in agents:
        _message(user, a, d, objet, contenu)


# ------------------------------------------------------------------------------------------------- statistiques
def statistiques(user, annee=None):
    """Comptages sans aucune donnée par agent : par MDS, par étape, par origine, par motif de clôture."""
    from logement.models import EtapeExpulsion
    qs = D.objects.all() if stats_departementales(user) else D.objects.filter(mds__in=mds_de(user))
    if annee:
        qs = qs.filter(date_reception__year=annee)
    j = timezone.localdate()
    en_cours = qs.filter(statut=D.EN_COURS)
    derniere = {}
    for e in EtapeExpulsion.objects.filter(dossier__in=en_cours).order_by('dossier_id', 'date', 'pk'):
        derniere[e.dossier_id] = e.type_etape
    libelles = dict(EtapeExpulsion.CHOIX)
    par_etape = {}
    for code in derniere.values():
        par_etape[libelles[code]] = par_etape.get(libelles[code], 0) + 1
    sans_etape = en_cours.count() - len(derniere)
    if sans_etape:
        par_etape["Aucune étape saisie"] = sans_etape
    return {
        'total': qs.count(),
        'en_cours': en_cours.count(),
        'clos': qs.filter(statut=D.CLOS).count(),
        'non_affectes': en_cours.filter(mds__isnull=True).count(),
        'sans_referent': en_cours.filter(mds__isnull=False, referent__isnull=True).count(),
        'audiences_30j': en_cours.filter(date_audience__gte=j, date_audience__lte=j + timedelta(days=30)).count(),
        'dette_moyenne': _moyenne(qs.exclude(dette__isnull=True).values_list('dette', flat=True)),
        'par_mds': list(qs.values('mds__nom').annotate(n=Count('pk'), en_cours=Count('pk', filter=Q(statut=D.EN_COURS)))
                        .order_by('-n')),
        'par_etape': sorted(par_etape.items(), key=lambda x: -x[1]),
        'par_origine': [(dict(D.ORIGINES).get(r['origine'], r['origine']), r['n'])
                        for r in qs.values('origine').annotate(n=Count('pk')).order_by('-n')],
        'par_cloture': [(dict(D.MOTIFS_CLOTURE).get(r['motif_cloture'], "—"), r['n'])
                        for r in qs.filter(statut=D.CLOS).values('motif_cloture').annotate(n=Count('pk')).order_by('-n')],
        'departemental': stats_departementales(user),
    }


def _moyenne(valeurs):
    valeurs = list(valeurs)
    return round(sum(valeurs) / len(valeurs)) if valeurs else None
