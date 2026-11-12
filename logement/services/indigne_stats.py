# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/indigne_stats.py
"""Statistiques de l'habitat indigne : signalements par origine et statut, suites données, réponses de la fiche
PDLHI (oui / non / je ne sais pas gardés séparés, et non renseigné). L'export CSV est agrégé : il ne contient
aucune identité d'usager."""
import csv
import io

from mds.models import UserMDSProfile

from ..models import SignalementHabitatIndigne as S
from . import indigne


def peut_voir_stats(user):
    return user.is_authenticated and (user.is_superuser or user.a_la_capacite('stats_departement')
                                      or user.a_la_capacite('peut_voir_stats'))


def _perimetre(user, qs):
    """Département entier pour les habilités départementales, sinon les MDS de l'utilisateur."""
    if user.is_superuser or user.a_la_capacite('stats_departement'):
        return qs
    return qs.filter(mds__in=UserMDSProfile.objects.filter(user=user, actif=True).values('mds'))


def annees(user):
    return sorted({d.year for d in _perimetre(user, S.objects.all()).dates('date_creation', 'year')}, reverse=True)


def statistiques(user, annee=None):
    qs = _perimetre(user, S.objects.select_related('mds'))
    if annee:
        qs = qs.filter(date_creation__year=annee)
    dossiers = list(qs)
    departemental = user.is_superuser or user.a_la_capacite('stats_departement')

    def compte(predicat):
        return sum(1 for d in dossiers if predicat(d))

    synthese = [
        ("Signalements", len(dossiers)),
        ("Envoyés au PDLHI", compte(lambda d: d.date_envoi is not None)),
        ("Clos", compte(lambda d: d.statut == S.CLOS)),
        ("Enquête de salubrité", compte(lambda d: d.enquete_salubrite)),
        ("Bascule sur dispositif DALO", compte(lambda d: d.bascule_dalo)),
        ("Ville soumise au permis de louer", compte(lambda d: d.permis_ville)),
        ("Logement soumis au permis de louer", compte(lambda d: d.permis_logement)),
        ("Hors suivi MDS (renvoyés au CIAS ou CCAS)", compte(lambda d: d.beneficiaire_id is None)),
    ]
    origines = [(libelle, compte(lambda d, c=code: d.origine == c)) for code, libelle in S.ORIGINES]
    statuts = [(libelle, compte(lambda d, c=code: d.statut == c)) for code, libelle in S.STATUTS]

    reponses = []
    for _, titre, champs in indigne.SECTIONS:
        if titre.startswith("1."):
            continue
        lignes = []
        for key, label, kind, choix in champs:
            if kind not in ('ond', 'bmn'):
                continue
            valeurs = [(d.donnees or {}).get(key, '') for d in dossiers]
            lignes.append({
                'label': label,
                'choix': [(libelle, sum(1 for v in valeurs if v == code)) for code, libelle in choix],
                'sans': sum(1 for v in valeurs if v not in dict(choix)),
            })
        if lignes:  # une section sans réponse oui / non / je ne sais pas n'a pas de tableau
            reponses.append({'titre': titre, 'lignes': lignes})

    occupants = []
    for code, libelle in indigne.STATUT_OCCUPANT:
        occupants.append((libelle, sum(1 for d in dossiers if (d.donnees or {}).get('statut_occupant') == code)))
    occupants.append(("Non renseigné", sum(1 for d in dossiers
                                          if (d.donnees or {}).get('statut_occupant') not in dict(indigne.STATUT_OCCUPANT))))

    par_mds = []
    if departemental:
        noms = sorted({d.mds.nom for d in dossiers})
        par_mds = [(nom, sum(1 for d in dossiers if d.mds.nom == nom)) for nom in noms]

    return {'total': len(dossiers), 'synthese': synthese, 'origines': origines, 'statuts': statuts,
            'reponses': reponses, 'occupants': occupants, 'par_mds': par_mds, 'departemental': departemental}


def export_csv(s, annee=None):
    """CSV agrégé (séparateur point-virgule, pour Excel), sans identité d'usager."""
    tampon = io.StringIO()
    w = csv.writer(tampon, delimiter=';')
    w.writerow(["Habitat indigne – statistiques", f"année {annee}" if annee else "toutes années"])
    w.writerow([])
    w.writerow(["Synthèse", "Nombre"])
    w.writerows(s['synthese'])
    w.writerow([])
    w.writerow(["Origine", "Nombre"])
    w.writerows(s['origines'])
    w.writerow([])
    w.writerow(["Statut", "Nombre"])
    w.writerows(s['statuts'])
    w.writerow([])
    w.writerow(["Statut de l'occupant", "Nombre"])
    w.writerows(s['occupants'])
    for bloc in s['reponses']:
        w.writerow([])
        w.writerow([bloc['titre'], "Oui / Bon", "Non / Mauvais", "Je ne sais pas", "Non renseigné"])
        for ligne in bloc['lignes']:
            valeurs = {libelle: n for libelle, n in ligne['choix']}
            w.writerow([ligne['label']] + [valeurs.get(libelle, '') for libelle in valeurs] + [ligne['sans']])
    if s['par_mds']:
        w.writerow([])
        w.writerow(["MDS", "Nombre"])
        w.writerows(s['par_mds'])
    return '\ufeff' + tampon.getvalue()
