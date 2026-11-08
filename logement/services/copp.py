# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/copp.py
"""Commission des publics prioritaires (COPP / CTPP) : fiche de saisine préremplie, rapport social, pièces de la GED.

Dispositif local (Pays de Martigues pour la MDS de Fred), paramétré en administration : séances et formulaire
officiel déposé vierge. Données préremplies depuis la fiche, le foyer, le budget et la demande de logement."""
import io
from decimal import Decimal
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from logement.models import DemandeLogementSocial, FormulaireOfficiel as F

from .fsl import COLONNES, d, montant, totaux_ressources, ressources_depuis_budget

# Mesures d'accompagnement les plus courantes (guide PDALHPD 13, 2024) : suggestions, la saisie reste libre
MESURES_ACCOMPAGNEMENT = [
    "Suivi social de droit commun (MDS)", "ASELL courte durée", "ASELL généraliste", "ASELL renforcé",
    "AVDL DALO", "AVDL hors DALO", "AVDL PPSMJ", "Gestion locative adaptée (GLA)", "Intermédiation locative (IML)",
    "MASP", "MAJ", "MJAGBF", "Sauvegarde de justice", "Curatelle", "Tutelle", "Un chez soi d'abord",
    "Accompagnement spécifique prévention des expulsions",
]
SITUATIONS_LOGEMENT_COPP = [('PARC_SOCIAL', "Parc social"), ('PARC_PRIVE', "Parc privé"), ('HEBERGEMENT', "Hébergement"),
                            ('SDF', "Sans domicile fixe"), ('AUTRE', "Autre")]
SITUATIONS_FAMILLE = [('CELIBATAIRE', "Célibataire"), ('MARIE', "Marié(e)"), ('PACSE', "Pacsé(e)"),
                      ('CONCUBINAGE', "Concubin(e)"), ('DIVORCE', "Divorcé(e)"), ('SEPARE', "Séparé(e)"), ('VEUF', "Veuf(ve)")]
NATURES = {'salaire': "Salaire", 'chomage': "France Travail", 'rsa': "RSA", 'prime_activite': "Prime d'activité",
           'ij': "IJ", 'retraite': "Retraite", 'invalidite': "Invalidité", 'aah': "AAH", 'familiales': "AF",
           'complement_familial': "CF", 'asf': "ASF", 'paje': "PAJE", 'aeeh': "AEEH", 'pch': "PCH",
           'pension_alimentaire': "Pension alimentaire", 'logement': "AL/APL", 'autres_activite': "Autres",
           'autres_prestations': "Autres prestations", 'bourses': "Bourses", 'ada': "ADA", 'prepare': "PreParE"}


def _date(x):
    return x.strftime('%d/%m/%Y') if x else ""


def _ressources_par_personne(budget, col):
    lignes = (budget.ressources or {}).get('lignes', {}) if budget else {}
    natures, total = [], Decimal(0)
    for code, v in lignes.items():
        m = d(v.get(col))
        if m:
            natures.append(f"{NATURES.get(code, code)} {montant(m)} €")
            total += m
    return ", ".join(natures), (str(total) if total else "")


def preremplir(beneficiaire, user):
    from beneficiaire.budget import budget_en_cours
    from .fsl import composition, coordonnees_ts
    budget = budget_en_cours(beneficiaire)
    comp = composition(beneficiaire)
    conj_l = next((p for p in comp if p['role'] == 'CONJOINT'), None)
    conj = None
    if conj_l:
        from beneficiaire.models import Beneficiaire
        conj = Beneficiaire.tous.filter(nom=conj_l['nom'], prenom=conj_l['prenom']).first()
    enfants = [p for p in comp if p['role'] == 'ENFANT']
    nature_d, montant_d = _ressources_par_personne(budget, 'demandeur')
    nature_c, montant_c = _ressources_par_personne(budget, 'conjoint')
    charges = (budget.charges or {}).get('lignes', {}) if budget else {}
    loyer = d(charges.get('loyer', {}).get('payee')) + d(charges.get('loyer', {}).get('non_payee'))
    al = sum((d(v) for v in ((budget.ressources or {}).get('lignes', {}).get('logement', {}) if budget else {}).values()),
             Decimal(0))
    _, total_r = totaux_ressources(ressources_depuis_budget(budget)[0]) if budget else (None, Decimal(0))
    total_r += al
    taux = f"{((loyer - al) / total_r * 100).quantize(Decimal('0.1'))} %".replace('.', ',') if total_r and loyer else ""
    rav = f"{budget.reste_a_vivre} €".replace('.', ',') if budget else ""
    dettes = sum((d(x.get('montant')) for x in (budget.dettes or [])), Decimal(0)) if budget else Decimal(0)
    dl = DemandeLogementSocial.objects.filter(beneficiaire=beneficiaire).first()
    ts = coordonnees_ts(user, beneficiaire.mds)

    def personne(b, ligne):
        if not ligne:
            return {}
        return {'nom': (ligne.get('nom') or '').upper(), 'prenom': ligne.get('prenom'),
                'date_naissance': ligne.get('date_naissance'),
                'telephone': (b.telephone_mobile or b.telephone_fixe) if b else '', 'courriel': b.email if b else '',
                'nir': b.nir if b else ''}
    statut = beneficiaire.marital_status or ''
    return {
        'date_saisie': timezone.localdate().strftime('%d/%m/%Y'),
        'referent': {'nom': f"{ts['nom'].upper()} {ts['prenom']}".strip(), 'telephone': ts['telephone'],
                     'courriel': ts['email'], 'structure': ts['organisme']},
        'nud': dl.nud if dl else '', 'date_creation_nud': _date(dl.date_creation) if dl else '',
        'anciennete': dl.anciennete() if dl else '',
        'demandeur': personne(beneficiaire, comp[0]), 'conjoint': personne(conj, conj_l),
        'situation_famille': statut if statut in dict(SITUATIONS_FAMILLE) else '',
        'garcons': '', 'filles': '', 'annees_garcons': '', 'annees_filles': '',
        'enfants': ", ".join(f"{p['prenom']} ({p['date_naissance'][-4:]})" for p in enfants if p.get('date_naissance')),
        'nb_enfants': str(len(enfants)) if enfants else '', 'modalites_garde': '', 'naissance_attendue': '',
        'logement_actuel': '', 'adresse': f"{beneficiaire.adresse}, {beneficiaire.code_postal} {beneficiaire.ville}",
        'typologie': '', 'loyer': str(loyer) if loyer else '', 'charges': '', 'apl': str(al) if al else '',
        'bailleur': '', 'taux_effort': taux, 'reste_a_vivre': rav,
        'nature_ressources_demandeur': nature_d, 'montant_ressources_demandeur': montant_d,
        'nature_ressources_conjoint': nature_c, 'montant_ressources_conjoint': montant_c,
        'rfr_n1_demandeur': '', 'rfr_n2_demandeur': '', 'rfr_n1_conjoint': '', 'rfr_n2_conjoint': '',
        'plafonds_ressources': '',
        'endettement': 'OUI' if dettes else '', 'montant_dettes': str(dettes) if dettes else '', 'demarches_dettes': '',
        'dalo': ({'depose': 'OUI' if dl.dalo_depose else 'NON', 'date': _date(dl.dalo_date), 'etat': dl.dalo_etat}
                 if dl else {}),
        'mutation': ({'depose': 'OUI' if dl.mutation_deposee else 'NON', 'date': _date(dl.mutation_date),
                      'etat': dl.mutation_etat} if dl else {}),
        'alin': ({'depose': 'OUI' if dl.alin_inscrit else 'NON', 'date': _date(dl.alin_date), 'etat': dl.alin_etat}
                 if dl else {}),
        'communes': list(dl.communes_souhaitees) if dl else [], 'typologie_souhaitee': dl.typologie_souhaitee if dl else '',
        'etage': dl.etage_souhaite if dl else '', 'pmr': ('OUI' if dl.pmr else 'NON') if dl else '',
        'precisions': dl.precisions if dl else '',
        'mesure_accompagnement': '',
        'origine': (f"budget du foyer du {budget.date_etabli:%d/%m/%Y}" if budget else "pas de budget du foyer")
                   + (", demande de logement" if dl else ", pas de demande de logement renseignée"),
    }


# ---------------------------------------------------------------------------------------------------------------
# Placements sur la fiche de saisine (2 pages A4 déposées séparément)

XD, XC = 135, 405        # colonnes « demandeur » et « co-demandeur » des tableaux de la page 1


def placements(code):
    if code == F.COPP_FICHE_1:
        c = [{'cle': 'date_saisie', 'ancre': 'Date de Saisie', 'x_abs': XD},
             {'cle': 'ref_nom', 'ancre': 'Nom-Prenom', 'x_abs': XD},
             {'cle': 'ref_telephone', 'ancre': 'Téléphone', 'x_max': 100, 'top_max': 235, 'x_abs': XD},
             {'cle': 'ref_courriel', 'ancre': 'Courriel', 'x_min': 200, 'top_max': 235, 'x_abs': 330, 'taille': 8},
             {'cle': 'ref_structure', 'ancre': 'Structure', 'x_abs': XD, 'taille': 8},
             {'cle': 'nud', 'ancre': 'DEMANDE DE LOGEMENT', 'x_abs': 140, 'taille': 8},
             {'cle': 'date_creation_nud', 'ancre': 'DEMANDE DE LOGEMENT', 'x_abs': 300, 'taille': 8},
             {'cle': 'anciennete', 'ancre': 'DEMANDE DE LOGEMENT', 'x_abs': 440, 'taille': 8}]
        for prefixe, filtre, x in (('dem', {'x_max': 100}, XD), ('conj', {'x_min': 200}, XC)):
            for cle, ancre in (('nom', 'Nom'), ('prenom', 'Prénom'), ('date_naissance', 'Date de'),
                               ('telephone', 'Téléphone'), ('courriel', 'Courriel'), ('nir', 'Numero S.S')):
                c.append(dict({'cle': f'{prefixe}_{cle}', 'ancre': ancre, 'top_min': 285, 'top_max': 370, 'x_abs': x,
                               'taille': 8}, **filtre))
        for code, ancre in SITUATIONS_FAMILLE:
            ancre = {'CELIBATAIRE': 'Célibataire', 'MARIE': 'Marié', 'PACSE': 'Pacsé', 'CONCUBINAGE': 'Concubin',
                     'DIVORCE': 'Divorcé', 'SEPARE': 'Séparé', 'VEUF': 'Veuf'}[code]
            c.append({'cle': f'sf_{code}', 'ancre': ancre, 'top_min': 370, 'top_max': 385, 'mode': 'case', 'dx': 1})
        c += [{'cle': 'nb_garcons', 'ancre': 'Garçon', 'x_abs': 220, 'taille': 8},
              {'cle': 'annees_garcons', 'ancre': 'Garçon', 'x_abs': 270, 'taille': 8},
              {'cle': 'nb_filles', 'ancre': 'Fille', 'x_abs': 220, 'taille': 8},
              {'cle': 'annees_filles', 'ancre': 'Fille', 'x_abs': 270, 'taille': 8},
              {'cle': 'modalites_garde', 'ancre': 'Garçon', 'x_abs': 470, 'taille': 7, 'largeur': 110, 'lignes': 3},
              {'cle': 'naissance_attendue', 'ancre': 'Naissance attendue', 'x_abs': 270, 'taille': 8}]
        for code, ancre in (('PARC_SOCIAL', 'Parc Social'), ('PARC_PRIVE', 'arc Privé'), ('HEBERGEMENT', 'Hébergement'),
                            ('SDF', 'Sans Domicile fixe'), ('AUTRE', 'Autre')):
            c.append({'cle': f'lg_{code}', 'ancre': ancre, 'top_min': 440, 'top_max': 460, 'mode': 'case',
                      'dx': -1 if code != 'PARC_PRIVE' else -6})
        c += [{'cle': 'adresse', 'ancre': 'Adresse', 'top_min': 465, 'x_max': 100, 'mode': 'dessous', 'dy': -3,
               'taille': 5, 'largeur': 75, 'lignes': 2, 'interligne': 6},
              {'cle': 'typologie', 'ancre': 'Typologie :', 'top_min': 465, 'dx': 2, 'taille': 8},
              {'cle': 'loyer', 'ancre': 'Loyer :', 'dx': 2, 'taille': 8},
              {'cle': 'charges', 'ancre': 'Charges :', 'dx': 2, 'taille': 8},
              {'cle': 'apl', 'ancre': 'APL :', 'dx': 2, 'taille': 8},
              {'cle': 'bailleur', 'ancre': 'Bailleur :', 'dx': 2, 'taille': 7, 'largeur': 75, 'lignes': 2},
              {'cle': 'taux_effort', 'ancre': "Taux d'effort", 'x_abs': XD},
              {'cle': 'reste_a_vivre', 'ancre': 'Reste à vivre', 'x_abs': XC},
              {'cle': 'nature_d', 'ancre': 'Nature des ressources', 'x_max': 100, 'x_abs': XD, 'taille': 6,
               'largeur': 120, 'lignes': 2, 'interligne': 7, 'dy': -3},
              {'cle': 'nature_c', 'ancre': 'Nature des ressources', 'x_min': 200, 'x_abs': XC, 'taille': 6,
               'largeur': 120, 'lignes': 2, 'interligne': 7, 'dy': -3},
              {'cle': 'montant_d', 'ancre': 'Montant :', 'x_max': 100, 'top_min': 540, 'top_max': 560, 'x_abs': XD},
              {'cle': 'montant_c', 'ancre': 'Montant :', 'x_min': 200, 'top_min': 540, 'top_max': 560, 'x_abs': XC},
              {'cle': 'rfr_n1_d', 'ancre': 'N-1', 'x_max': 250, 'x_abs': 200},
              {'cle': 'rfr_n2_d', 'ancre': 'N-2', 'x_max': 250, 'x_abs': 200},
              {'cle': 'rfr_n1_c', 'ancre': 'N-1', 'x_min': 250, 'x_abs': 470},
              {'cle': 'rfr_n2_c', 'ancre': 'N-2', 'x_min': 250, 'x_abs': 470},
              {'cle': 'plafonds', 'ancre': 'PLAFONDS DE RESSOURCES', 'x_abs': 200, 'taille': 8},
              {'cle': 'endettement_oui', 'ancre': 'OUI', 'top_min': 655, 'mode': 'case', 'dx': 1},
              {'cle': 'endettement_non', 'ancre': 'NON', 'top_min': 675, 'mode': 'case', 'dx': 1},
              {'cle': 'montant_dettes', 'ancre': 'Montant :', 'top_min': 655, 'x_max': 250, 'dx': 2, 'taille': 8},
              {'cle': 'demarches_dettes', 'ancre': 'Démarches effectués :', 'mode': 'dessous', 'dy': -2, 'taille': 7,
               'largeur': 150, 'lignes': 2},
              {'cle': 'motif', 'ancre': 'Justificatifs Oui/Non', 'mode': 'abs', 'dx': -446, 'dy': 9, 'taille': 7,
               'largeur': 430, 'lignes': 8, 'interligne': 9.6},
              {'cle': 'justificatifs', 'ancre': 'Justificatifs Oui/Non', 'mode': 'abs', 'dx': 4, 'dy': 9, 'taille': 7,
               'largeur': 90, 'lignes': 8, 'interligne': 9.6}]
        return c
    # page 2
    c = []
    for i, bloc in enumerate(('dalo', 'mutation', 'alin')):
        c += [{'cle': f'{bloc}_oui', 'ancre': 'Oui', 'occ': i, 'mode': 'case', 'dx': 0},
              {'cle': f'{bloc}_non', 'ancre': 'Non', 'occ': i, 'mode': 'case', 'dx': 0},
              {'cle': f'{bloc}_date', 'ancre': 'Date dépôt :', 'occ': i, 'dx': 4}]
    for i, bloc in enumerate(('dalo', 'mutation', 'alin')):
        c += [{'cle': f'{bloc}_EN_COURS', 'ancre': 'En cours', 'occ': i, 'mode': 'case', 'dx': 1},
              {'cle': f'{bloc}_REFUSE', 'ancre': 'Refusé', 'occ': i, 'mode': 'case', 'dx': 1}]
    c += [{'cle': 'dalo_ACCEPTE', 'ancre': 'Accépté', 'occ': 0, 'mode': 'case', 'dx': 1},
          {'cle': 'mutation_ACCEPTE', 'ancre': 'Accépté', 'occ': 1, 'mode': 'case', 'dx': 1},
          {'cle': 'alin_EN_PROPOSITION', 'ancre': 'En proposition', 'mode': 'case', 'dx': 1}]
    for n, x in ((1, 160), (2, 160), (3, 160), (4, 420), (5, 420), (6, 420)):
        c.append({'cle': f'choix_{n}', 'ancre': f'Choix {n}', 'x_abs': x})
    c += [{'cle': 'typologie_souhaitee', 'ancre': 'Typologie', 'top_min': 495, 'x_abs': 160},
          {'cle': 'etage', 'ancre': 'Etage', 'x_abs': 420},
          {'cle': 'pmr_oui', 'ancre': 'Oui', 'occ': 3, 'mode': 'case', 'dx': 0},
          {'cle': 'pmr_non', 'ancre': 'Non', 'occ': 3, 'mode': 'case', 'dx': 0},
          {'cle': 'precisions', 'ancre': 'Précisions complèmentaires', 'mode': 'dessous', 'dy': 2, 'largeur': 460,
           'lignes': 5, 'taille': 8},
          {'cle': 'mesure', 'ancre': "Mesure d'accompagnement actuelle", 'mode': 'dessous', 'dx': 4, 'dy': 2,
           'largeur': 470, 'lignes': 4, 'taille': 8},
          {'cle': 'visa_referent', 'ancre': 'Tampon de la structure', 'mode': 'dessous', 'dy': 8, 'taille': 7}]
    return c


def valeurs(saisine, code):
    dn = saisine.donnees or {}
    if code == F.COPP_FICHE_1:
        r, dem, conj = dn.get('referent') or {}, dn.get('demandeur') or {}, dn.get('conjoint') or {}
        v = {'date_saisie': dn.get('date_saisie'), 'ref_nom': r.get('nom'), 'ref_telephone': r.get('telephone'),
             'ref_courriel': r.get('courriel'), 'ref_structure': r.get('structure'), 'nud': dn.get('nud'),
             'date_creation_nud': dn.get('date_creation_nud'), 'anciennete': dn.get('anciennete'),
             f"sf_{dn.get('situation_famille')}": bool(dn.get('situation_famille')),
             'nb_garcons': dn.get('garcons'), 'annees_garcons': dn.get('annees_garcons'),
             'nb_filles': dn.get('filles'), 'annees_filles': dn.get('annees_filles'),
             'modalites_garde': dn.get('modalites_garde'), 'naissance_attendue': dn.get('naissance_attendue'),
             f"lg_{dn.get('logement_actuel')}": bool(dn.get('logement_actuel')),
             'adresse': dn.get('adresse'), 'typologie': dn.get('typologie'), 'loyer': montant(dn.get('loyer')),
             'charges': montant(dn.get('charges')), 'apl': montant(dn.get('apl')), 'bailleur': dn.get('bailleur'),
             'taux_effort': dn.get('taux_effort'), 'reste_a_vivre': dn.get('reste_a_vivre'),
             'nature_d': dn.get('nature_ressources_demandeur'), 'nature_c': dn.get('nature_ressources_conjoint'),
             'montant_d': montant(dn.get('montant_ressources_demandeur')),
             'montant_c': montant(dn.get('montant_ressources_conjoint')),
             'rfr_n1_d': montant(dn.get('rfr_n1_demandeur')), 'rfr_n2_d': montant(dn.get('rfr_n2_demandeur')),
             'rfr_n1_c': montant(dn.get('rfr_n1_conjoint')), 'rfr_n2_c': montant(dn.get('rfr_n2_conjoint')),
             'plafonds': dn.get('plafonds_ressources'),
             'endettement_oui': dn.get('endettement') == 'OUI', 'endettement_non': dn.get('endettement') == 'NON',
             'montant_dettes': montant(dn.get('montant_dettes')), 'demarches_dettes': dn.get('demarches_dettes'),
             'motif': " ; ".join(saisine.libelles_motifs()),
             'justificatifs': f"Oui : {saisine.pieces.count()} pièce(s)" if saisine.pk and saisine.pieces.exists() else ""}
        for prefixe, p in (('dem', dem), ('conj', conj)):
            for cle in ('nom', 'prenom', 'date_naissance', 'telephone', 'courriel', 'nir'):
                v[f'{prefixe}_{cle}'] = p.get(cle)
        return v
    v = {}
    for bloc in ('dalo', 'mutation', 'alin'):
        b = dn.get(bloc) or {}
        v[f'{bloc}_oui'], v[f'{bloc}_non'] = b.get('depose') == 'OUI', b.get('depose') == 'NON'
        v[f'{bloc}_date'] = b.get('date') if b.get('depose') == 'OUI' else ''
        if b.get('depose') == 'OUI' and b.get('etat'):
            v[f"{bloc}_{b['etat']}"] = True
    for i, commune in enumerate((dn.get('communes') or [])[:6], 1):
        v[f'choix_{i}'] = commune
    v.update({'typologie_souhaitee': dn.get('typologie_souhaitee'), 'etage': dn.get('etage'),
              'pmr_oui': dn.get('pmr') == 'OUI', 'pmr_non': dn.get('pmr') == 'NON',
              'precisions': dn.get('precisions'), 'mesure': dn.get('mesure_accompagnement'),
              'visa_referent': f"{(dn.get('referent') or {}).get('nom', '')} – {timezone.localdate():%d/%m/%Y}"})
    return v


# ---------------------------------------------------------------------------------------------------------------
# PDF : fiche (officielle ou trame CID) + rapport social

def _t(v):
    return escape(str(v or "")).replace("\n", "<br/>")


def _page_cid(saisine, avec_fiche):
    from AidFi.services.afase_pdf import draw_page_template, get_ditas_styles
    st = get_ditas_styles()
    P = lambda t, s="Normal": Paragraph(t, st[s])  # noqa: E731
    dn = saisine.donnees or {}
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=3.5 * cm,
                            bottomMargin=2 * cm, title="Saisine COPP", author="CID")
    el = [P("COMMISSION DES PUBLICS PRIORITAIRES – " + ("FICHE DE SAISINE ET RAPPORT SOCIAL" if avec_fiche
                                                        else "RAPPORT SOCIAL"), "TitreOfficiel")]
    b = saisine.beneficiaire
    el.append(P(f"<b>Ménage :</b> {_t(b.nom.upper())} {_t(b.prenom)} – <b>NUD :</b> {_t(dn.get('nud'))} "
                f"(ancienneté {_t(dn.get('anciennete'))}) – <b>Commission :</b> {_t(saisine.commission or 'à préciser')}"))
    if avec_fiche:
        r = dn.get('referent') or {}
        dem, conj = dn.get('demandeur') or {}, dn.get('conjoint') or {}
        lignes = [["", "Demandeur", "Co-demandeur / conjoint"]]
        for cle, lib in (('nom', "Nom"), ('prenom', "Prénom"), ('date_naissance', "Naissance"), ('telephone', "Téléphone"),
                         ('courriel', "Courriel"), ('nir', "N° de sécurité sociale")):
            lignes.append([lib, dem.get(cle, ''), conj.get(cle, '')])
        lignes += [["Ressources", P(_t(dn.get('nature_ressources_demandeur'))), P(_t(dn.get('nature_ressources_conjoint')))],
                   ["Montant", montant(dn.get('montant_ressources_demandeur')), montant(dn.get('montant_ressources_conjoint'))],
                   ["RFR N-1 / N-2", f"{montant(dn.get('rfr_n1_demandeur'))} / {montant(dn.get('rfr_n2_demandeur'))}",
                    f"{montant(dn.get('rfr_n1_conjoint'))} / {montant(dn.get('rfr_n2_conjoint'))}"]]
        t = Table(lignes, colWidths=[4 * cm, 7 * cm, 7 * cm])
        t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.4, colors.grey), ('FONTSIZE', (0, 0), (-1, -1), 8),
                               ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb'))]))
        situations = dict(SITUATIONS_FAMILLE)
        logements = dict(SITUATIONS_LOGEMENT_COPP)
        el += [Spacer(1, 6), P(f"<b>Référent :</b> {_t(r.get('nom'))} – {_t(r.get('telephone'))} – {_t(r.get('courriel'))} "
                               f"– {_t(r.get('structure'))}"), Spacer(1, 4), t, Spacer(1, 4),
               P(f"<b>Situation de famille :</b> {_t(situations.get(dn.get('situation_famille'), ''))} – "
                 f"<b>Enfants :</b> {_t(dn.get('enfants'))} {_t(dn.get('modalites_garde'))} "
                 f"{('– naissance attendue ' + _t(dn.get('naissance_attendue'))) if dn.get('naissance_attendue') else ''}"),
               P(f"<b>Logement actuel :</b> {_t(logements.get(dn.get('logement_actuel'), ''))} – {_t(dn.get('adresse'))} – "
                 f"{_t(dn.get('typologie'))} – loyer {montant(dn.get('loyer'))} €, charges {montant(dn.get('charges'))} €, "
                 f"APL {montant(dn.get('apl'))} € – bailleur {_t(dn.get('bailleur'))}"),
               P(f"<b>Taux d'effort :</b> {_t(dn.get('taux_effort'))} – <b>Reste à vivre par personne et par jour :</b> "
                 f"{_t(dn.get('reste_a_vivre'))} – <b>Plafonds de ressources :</b> {_t(dn.get('plafonds_ressources'))}"),
               P(f"<b>Endettement :</b> {_t(dn.get('endettement'))} {montant(dn.get('montant_dettes'))} € – "
                 f"{_t(dn.get('demarches_dettes'))}")]
        for bloc, lib in (('dalo', "DALO"), ('mutation', "Mutation"), ('alin', "Al'In")):
            x = dn.get(bloc) or {}
            el.append(P(f"<b>{lib} :</b> {_t(x.get('depose'))} {('le ' + _t(x.get('date'))) if x.get('date') else ''} "
                        f"{_t(x.get('etat'))}"))
        el += [P(f"<b>Communes souhaitées :</b> {_t(', '.join(dn.get('communes') or []))} – <b>Typologie :</b> "
                 f"{_t(dn.get('typologie_souhaitee'))} – <b>Étage :</b> {_t(dn.get('etage'))} – <b>PMR :</b> {_t(dn.get('pmr'))}"),
               P(f"<b>Précisions :</b> {_t(dn.get('precisions'))}"),
               P(f"<b>Mesure d'accompagnement actuelle :</b> {_t(dn.get('mesure_accompagnement'))}")]
    el += [Spacer(1, 8), P("Motif de la demande", "SectionHeader"), P(_t(" ; ".join(saisine.libelles_motifs()))),
           Spacer(1, 4), P("Rapport social", "SectionHeader"), P(_t(saisine.rapport_social))]
    if saisine.pk and saisine.pieces.exists():
        el += [Spacer(1, 4), P("Justificatifs joints", "SectionHeader"),
               P("<br/>".join(_t(f"{p.titre}") for p in saisine.pieces.all()))]
    r = dn.get('referent') or {}
    el += [Spacer(1, 10), P(f"Fait le {timezone.localdate():%d/%m/%Y} – {_t(r.get('nom'))}, {_t(r.get('structure'))}"),
           P("<i>Signature du ménage :</i>")]
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    return buf.getvalue()


def dossier(saisine):
    """(pdf, mode) : fiche officielle remplie + rapport social, ou trame CID complète."""
    from pypdf import PdfReader, PdfWriter
    from .pdf_officiel import remplir
    f1 = F.objects.filter(code=F.COPP_FICHE_1, actif=True).exclude(contenu=b'').first()
    f2 = F.objects.filter(code=F.COPP_FICHE_2, actif=True).exclude(contenu=b'').first()
    sortie = PdfWriter()
    morceaux = []
    if f1 and f2:
        for modele in (f1, f2):
            pdf, _ = remplir(bytes(modele.contenu), placements(modele.code), valeurs(saisine, modele.code), modele.reglages)
            morceaux.append(pdf)
        morceaux.append(_page_cid(saisine, avec_fiche=False))
        mode = 'officiel'
    else:
        morceaux.append(_page_cid(saisine, avec_fiche=True))
        mode = 'trame CID'
    for pdf in morceaux:
        for page in PdfReader(io.BytesIO(pdf)).pages:
            sortie.add_page(page)
    out = io.BytesIO()
    sortie.write(out)
    return out.getvalue(), mode
