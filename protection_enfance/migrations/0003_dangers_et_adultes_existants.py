# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/migrations/0003_dangers_et_adultes_existants.py
"""
1. Liste de départ des types de danger (modifiable ensuite dans l'administration).
2. IP déjà enregistrées : création des adultes à partir du dossier de la famille (parents des enfants),
   et « vit chez » pour chaque enfant. Aucune donnée existante n'est supprimée.
"""
from django.db import migrations

TYPES = [
    ('carence-educative', "Carence éducative, négligence"),
    ('violences-physiques', "Violences physiques"),
    ('violences-psychologiques', "Violences psychologiques (dont exposition aux violences conjugales)"),
    ('violences-sexuelles', "Violences sexuelles"),
    ('conduites-addictives', "Conduites addictives (parent ou enfant)"),
    ('defaut-soins', "Défaut de soins, santé"),
    ('scolarite', "Absentéisme, déscolarisation"),
    ('conditions-vie', "Conditions de vie (logement, hygiène)"),
    ('conflit-parental', "Conflit parental"),
    ('mise-en-danger-enfant', "Mise en danger par l'enfant lui-même (fugues, conduites à risque)"),
    ('autre', "Autre (à préciser)"),
]


def types_danger(apps, schema_editor):
    TypeDanger = apps.get_model('protection_enfance', 'TypeDanger')
    for i, (code, libelle) in enumerate(TYPES, start=1):
        TypeDanger.objects.get_or_create(code=code, defaults={'libelle': libelle, 'ordre': i * 10})


def adultes_existants(apps, schema_editor):
    IP = apps.get_model('protection_enfance', 'InformationPreoccupante')
    AdulteIP = apps.get_model('protection_enfance', 'AdulteIP')
    LienFamilial = apps.get_model('beneficiaire', 'LienFamilial')

    def creer(ip, b, heberge):
        return AdulteIP.objects.create(
            ip=ip, beneficiaire=b, qualite='PERE' if b.civilite == 'M.' else 'MERE',
            civilite='M.' if b.civilite == 'M.' else 'MME', nom=b.nom, prenom=b.prenom,
            adresse=(b.adresse or '')[:255], code_postal=b.code_postal or '', ville=b.ville or '',
            telephone=b.telephone_mobile or b.telephone_fixe or '', mds_id=b.mds_id,
            autorite_parentale=True, heberge_enfants=heberge, convoque=True)

    for ip in IP.objects.filter(adultes__isnull=True):
        adultes = {}
        for enfant in ip.enfants.exclude(beneficiaire__isnull=True):
            liens = [(l.personne_a, l.vit_au_foyer) for l in LienFamilial.objects.filter(
                        personne_b_id=enfant.beneficiaire_id, type_lien='ENFANT').select_related('personne_a')]
            liens += [(l.personne_b, l.vit_au_foyer) for l in LienFamilial.objects.filter(
                        personne_a_id=enfant.beneficiaire_id, type_lien='PARENT').select_related('personne_b')]
            for parent, vit in liens:
                if parent is None:
                    continue
                if parent.pk not in adultes:
                    adultes[parent.pk] = creer(ip, parent, vit)
                elif vit and not adultes[parent.pk].heberge_enfants:
                    adultes[parent.pk].heberge_enfants = True
                    adultes[parent.pk].save(update_fields=['heberge_enfants'])
                if vit and not enfant.heberge_par_id:
                    enfant.heberge_par = adultes[parent.pk]
                    enfant.save(update_fields=['heberge_par'])
        if ip.famille_id and ip.famille_id not in adultes:
            adultes[ip.famille_id] = creer(ip, ip.famille, not adultes)
        if not adultes and ip.famille_libelle:
            adultes[0] = AdulteIP.objects.create(ip=ip, qualite='AUTRE', nom=ip.famille_libelle[:60], prenom='',
                                                 adresse=(ip.famille_adresse or '')[:255],
                                                 autorite_parentale=True, heberge_enfants=True, convoque=True)
        hebergeants = [a for a in adultes.values() if a.heberge_enfants]
        if len(hebergeants) == 1:
            ip.enfants.filter(heberge_par__isnull=True).update(heberge_par=hebergeants[0])


class Migration(migrations.Migration):
    dependencies = [
        ('protection_enfance', '0002_adultes_auditions_dangers'),
        ('beneficiaire', '0005_beneficiaire_code_insee_naissance_and_more'),
    ]
    operations = [
        migrations.RunPython(types_danger, migrations.RunPython.noop),
        migrations.RunPython(adultes_existants, migrations.RunPython.noop),
    ]
