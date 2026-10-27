# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/services/ip_famille.py
"""
Composition familiale d'une IP : enfants et adultes repris du dossier CID, « vit chez »,
MDS associées et enquête conjointe avec un autre département (familles séparées, déménagement).
"""
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from protection_enfance.models import AdulteIP, EnfantIP


def _adulte(ip, b, heberge):
    return AdulteIP.objects.create(
        ip=ip, beneficiaire=b, qualite='PERE' if b.civilite == 'M.' else 'MERE',
        civilite='M.' if b.civilite == 'M.' else 'MME', nom=b.nom, prenom=b.prenom,
        adresse=(b.adresse or '')[:255], code_postal=b.code_postal or '', ville=b.ville or '',
        telephone=b.telephone_mobile or b.telephone_fixe or '', mds=b.mds,
        autorite_parentale=True, heberge_enfants=heberge, convoque=True)


def completer_depuis_dossier(ip):
    """Enfants mineurs, puis parents de chaque enfant, à partir des liens familiaux du dossier CID."""
    if ip.famille_id and not ip.enfants.exists():
        for m in ip.famille.reseau_familial():
            p = m['personne']
            if m['type_lien'] == 'ENFANT' and p.date_naissance and \
                    relativedelta(timezone.localdate(), p.date_naissance).years < 18:
                EnfantIP.objects.create(ip=ip, beneficiaire=p, nom=p.nom, prenom=p.prenom,
                                        date_naissance=p.date_naissance)
    if ip.adultes.exists():
        return
    adultes = {}
    for enfant in ip.enfants.exclude(beneficiaire__isnull=True).select_related('beneficiaire'):
        for m in enfant.beneficiaire.reseau_familial():
            if m['type_lien'] != 'PARENT':
                continue
            parent, vit = m['personne'], m['vit_au_foyer']
            if parent.pk not in adultes:
                adultes[parent.pk] = _adulte(ip, parent, vit)
            elif vit and not adultes[parent.pk].heberge_enfants:
                adultes[parent.pk].heberge_enfants = True
                adultes[parent.pk].save(update_fields=['heberge_enfants'])
            if vit and not enfant.heberge_par_id:
                enfant.heberge_par = adultes[parent.pk]
                enfant.save(update_fields=['heberge_par'])
    if ip.famille_id and ip.famille_id not in adultes:
        adultes[ip.famille_id] = _adulte(ip, ip.famille, not adultes)
    hebergeants = [a for a in adultes.values() if a.heberge_enfants]
    if len(hebergeants) == 1:
        ip.enfants.filter(heberge_par__isnull=True).update(heberge_par=hebergeants[0])


def synchroniser_territoires(ip, user=None):
    """
    Un adulte suivi par une autre MDS → MDS associée ; un adulte hors du département → enquête conjointe.
    Retourne la liste des changements (pour l'afficher et le journal).
    """
    from protection_enfance.services.ip_circuit import journal
    changements = []
    partage = set(ip.mds_partage.values_list('pk', flat=True))
    for a in ip.adultes.select_related('mds'):
        if a.mds_id and a.mds_id != ip.mds_id and a.mds_id not in partage:
            ip.mds_partage.add(a.mds)
            partage.add(a.mds_id)
            changements.append(f"MDS associée : {a.mds} ({a})")
    hors = [a for a in ip.adultes.all() if a.hors_departement]
    if hors and not ip.autre_departement:
        ip.autre_departement = "Enquête conjointe : " + ", ".join(
            f"{a} à {a.ville or '?'} ({a.departement})" for a in hors)[:180]
        ip.save(update_fields=['autre_departement', 'date_modification'])
        changements.append(ip.autre_departement)
    for c in changements:
        journal(ip, user, c)
    return changements


def hebergeants_meme_adresse(adulte):
    """L'adulte qui héberge + les autres adultes hébergeants à la même adresse (couple) : en-tête du courrier."""
    if not adulte:
        return []
    autres = [a for a in adulte.ip.adultes.filter(heberge_enfants=True).exclude(pk=adulte.pk)
              if a.adresse.strip().lower() == adulte.adresse.strip().lower() and a.adresse.strip()]
    return [adulte] + autres
