# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/dsf.py
"""Diagnostic social et financier (DSF, Cerfa 16227*01) : saisie dans CID rubrique par rubrique, préremplie depuis le
dossier d'expulsion, la fiche usager et le budget du foyer, puis Cerfa rempli (formulaire PDF national livré avec CID ;
une version plus récente peut être déposée en administration, code EXP_DSF).

Les clés des données sont les noms des champs du Cerfa : la correspondance est directe."""
import difflib
import io
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.utils import timezone

CERFA = Path(__file__).resolve().parent.parent / "formulaires" / "cerfa_16227-01_dsf.pdf"

T, D, M, L, R, C = 'texte', 'date', 'montant', 'long', 'choix', 'case'   # types de champ


def _c(cle, label, type_=T, options=None, largeur=1, aide=""):
    return {'cle': cle, 'label': label, 'type': type_, 'options': options or [], 'largeur': largeur, 'aide': aide}


OUI_NON = ["oui", "non"]
RESS = [("Salaire_net", "Salaire net avant impôt ou revenus imposables"), ("Indemnites", "Indemnités journalières"),
        ("Indemnites_chomage", "Indemnités de chômage"), ("RSA", "RSA"),
        ("Total_retraites", "Retraites et allocations personnes âgées"), ("Autres", "Autres revenus d'activité"),
        ("Allocations_logement", "Allocations logement"), ("Autres_allocations", "Autres allocations"),
        ("Pensions", "Pension(s) alimentaire(s)"), ("Autres_ressources", "Autre(s) ressource(s)")]
COLS = [("1", "Locataire"), ("2", "Conjoint"), ("3", "Autre(s)")]

SECTIONS = [
    ("1.1 Identité du locataire", [
        _c('Noms', "Nom(s)"), _c('Prénoms', "Prénom(s)"), _c('Date de naissance', "Date de naissance", D),
        _c('Adresse numéro et voie', "Adresse (numéro et voie)", largeur=2), _c('Code postal', "Code postal"),
        _c('Commune', "Commune"),
        _c('Situation professionnelle', "Situation professionnelle", largeur=2), _c('Depuis le', "Depuis le", D),
        _c('Adresse mail', "Adresse mail"), _c('Numéro de téléphone personnel', "Téléphone")]),
    ("1.2 Situation familiale", [
        _c('situation loca', "Le locataire est", R, ["célibataire", "en concubinage", "pacsé", "marié", "divorcé",
                                                     "en cours de séparation ou divorce", "veuf"]),
        _c('Depuis le 1', "Depuis le", D),
        _c('situation ménage', "Le ménage est", R, ["une personne seule", "un couple", "une famille avec deux parents",
                                                     "une famille monoparentale", "une colocation"]),
        _c('Autre', "Autre, précisez")]),
    ("1.3 Composition du ménage", [
        *[x for i in range(1, 8) for x in (
            _c(f'Relation {i}', f"Personne {i} : relation avec le locataire"), _c(f'Age {i}', "Âge"),
            _c(f'Situation {i}', "Situation professionnelle ou scolaire"),
            _c(f'rel {i}', "Peut contribuer au loyer", R, OUI_NON))],
        _c('Nombre de personnes à charge', "Nombre total de personnes à charge")]),
    ("1.4 Mesure de protection juridique", [
        _c('mesure de protection juridique', "Mesure", R, ["tutelle", "curatelle"]),
        _c('Nom du tuteur ou du curateur', "Nom du tuteur ou curateur"),
        _c('Prénoms du tuteur ou du curateur', "Prénom(s)"), _c('Adresse mail_1', "Adresse mail"),
        _c('Numéro de téléphone', "Téléphone")]),
    ("2.1 Ressources mensuelles du ménage", [
        *[_c(f"{code}_{n}", f"{lib} – {col}", M) for code, lib in RESS for n, col in COLS],
        _c('Autres ressources, précisez', "Autre(s) ressource(s) : précisez", largeur=3)]),
    ("2.1 Charges mensuelles du ménage", [
        _c('Loyer', "Loyer", M), _c('Provisions_sur_charges', "Provisions sur charges", M),
        _c('Autres_charges_logement', "Autres charges du logement (électricité…)", M),
        _c('Assurance_habitation', "Assurance habitation", M),
        _c('Abonnements', "Téléphone, internet, abonnements", M), _c('Transports', "Transports", M),
        _c('Assurances_hors_habitation', "Assurances (hors habitation)", M), _c('Mutuelle', "Mutuelle, santé", M),
        _c('Pensions_alimentaires', "Pensions alimentaires versées", M),
        _c('Frais_de_garde', "Frais de garde et de scolarité", M), _c('Impots_et_taxes', "Impôts et taxes", M),
        _c('Total_credits', "Crédits, autres dettes", M),
        _c('Autre precisez 1-1', "Autre charge 1 : laquelle"), _c('Autre_precisez_1', "montant", M),
        _c('Autre precisez 2-2', "Autre charge 2 : laquelle"), _c('Autre_precisez_2', "montant", M)]),
    ("3.1 Dette locative", [
        _c('Montant dette', "Montant de la dette figurant sur l'assignation", M),
        _c('présence garantie', "Présence d'une garantie", R, ["Oui", "Non"]),
        _c('Date 1', "Date du 1er impayé", D),
        _c('loyer élevé', "Loyer trop élevé", C), _c('Augmentation loyer', "Augmentation du loyer ou des charges", C),
        _c('Perte emploi', "Perte d'emploi", C), _c('Changement situation', "Changement de situation familiale", C),
        _c('Difficulté gestion', "Difficulté de gestion du budget", C),
        _c("Suspension d'allocations", "Suspension d'allocation", C), _c('Maladie', "Maladie, raisons médicales", C),
        _c('Palcement en détention', "Placement en détention", C), _c('Litige avec le bailleur', "Litige avec le bailleur", C),
        _c('Passage à la retraite', "Passage à la retraite", C), _c('Autre précisez 3', "Autre cause", C),
        _c('Autre précisez', "Autre cause : précisez", largeur=2),
        _c('aides versées au bailleur', "Aides au logement versées au bailleur", R, ["Oui", "non"]),
        _c('Oui dun montant de', "d'un montant de", M),
        _c('aides suspendues', "Aides au logement suspendues", R, ["Oui", "non"]), _c('Date 2', "depuis le", D)]),
    ("4.1 Remboursement de la dette", [
        _c('reprise de loyer', "Reprise du paiement du loyer", R,
           ["Oui totalement", "Oui partiellement", "Oui irrégulier", "non"]),
        _c('Date 3', "En totalité depuis le", D), _c('Oui partiellement à raison de', "Partiellement : € par mois", M),
        _c('Date 4', "depuis le", D),
        _c('capacite de rembourser', "Capacité à rembourser", R, ["oui", "non", "ne sait pas"]),
        _c('montant', "Montant maximum par mois en plus du loyer", M), _c('mois', "Durée (mois)"),
        _c('Informations complémentaires', "Informations complémentaires (1280 caractères)", L, largeur=3)]),
    ("4.2 Mesures d'apurement", [
        _c('Dossier surrendettement', "Dossier de surendettement", R,
           ["non ou non eligible", "envisagé ou en cours de constitution", "déposé", "refusé", "jugé recevable"]),
        _c('Date 5', "Surendettement déposé le", D),
        _c('FSL', "Dossier FSL", R, ["non ou non eligible", "en cours de constitution", "déposé le", "refusé",
                                     "jugé recevable", "aide versée"]),
        _c('Date 6', "FSL déposé le", D),
        _c('plan ou mesure', "Plan ou mesure de la commission", R,
           ["plan de traitement", "suspension de l'exigibilité", "rétablissement sans liquidation",
            "rétablissement avec liquidation", "effacement partiel"]),
        _c('mois 1', "Plan de traitement : durée (mois)"), _c('mois_2', "Suspension : durée (mois)"),
        _c("Autres mesures d'apurement", "Autres mesures d'apurement et d'ouverture de droits (800 caractères)", L, largeur=3)]),
    ("5 Logement actuel et relogement", [
        _c('type logement', "Type de logement", R, ["social", "privé"]), _c('Nb de pièces', "Nombre de pièces"),
        _c('Date 7', "Date d'entrée dans les lieux"),
        _c('assurance habitation', "Assurance habitation en cours", R, OUI_NON),
        _c('arrete de mise en securite', "Arrêté de mise en sécurité ou d'insalubrité", R, OUI_NON),
        _c('certificat de non decence', "Certificat de non-décence", R, ["oui", "non", "NSP"]),
        _c('Précisions supplémentaires', "Précisions sur le logement actuel (800 caractères)", L, largeur=3),
        _c('rester', "Le locataire souhaite rester dans les lieux", R, OUI_NON),
        _c('Date 8', "Demande de logement social déposée le", D), _c('Date 9', "Dernier renouvellement le", D)]),
    ("6 Évaluation sociale", [
        _c('bailleur observation', "Le bailleur a été invité à apporter ses observations", R, OUI_NON),
        _c('locataire participe DSF', "Le locataire a participé à la rédaction", R, OUI_NON),
        _c('Evaluation sociale', "Évaluation sociale (6480 caractères)", L, largeur=3,
           aide="Situation, parcours, démarches engagées, perspectives de relogement, mesures (MASP…).")]),
    ("7 Préparation à l'audience", [
        _c('Date 10', "Date de l'audience", D), _c('Heure', "Heure"), _c('Lieu', "Lieu"),
        _c('Locataire informé', "Informé de l'importance de se présenter à l'audience", C),
        _c('Locataire informé 1', "Informé d'apporter ses justificatifs à l'audience", C),
        _c('aide juridictionnelle', "Aide juridictionnelle", R,
           ["non ou non souhaitée", "en cours", "demandée", "accordée", "refusée"]),
        _c('Loyers non dus', "Contesté : loyers non dus ou déjà réglés", C), _c('Charges non dues', "Charges non dues", C),
        _c("Frais d'huissiers", "Frais d'huissiers", C), _c('Autre précisez 4', "Autre", C),
        _c('undefined_4', "Autre : précisez"),
        _c('CCAPEX', "Étude par la CCAPEX", R, ["non", "envisagée", "réalisée"])]),
    ("8 Rédacteur", [
        _c('Nom', "Nom"), _c('Prénom', "Prénom"), _c('Organisme de rattachement', "Organisme", largeur=3),
        _c('Adresse mail_2', "Adresse mail (celle de la MDS)"), _c('Numéro de téléphone fixe ou mobile', "Téléphone")]),
]
CHAMPS = {c['cle']: c for _, champs in SECTIONS for c in champs}
TEXTES_LONGS = ('Evaluation sociale', 'Informations complémentaires', "Autres mesures d'apurement",
                'Précisions supplémentaires')
LIMITES = {'Evaluation sociale': 6480, 'Informations complémentaires': 1280, "Autres mesures d'apurement": 800,
           'Précisions supplémentaires': 800}

# Budget du foyer → lignes du Cerfa
_RESS_BUDGET = {
    'Salaire_net': ['salaire'], 'Indemnites': ['ij'], 'Indemnites_chomage': ['chomage'], 'RSA': ['rsa'],
    'Total_retraites': ['retraite'], 'Autres': ['autres_activite', 'prime_activite'],
    'Allocations_logement': ['logement'],
    'Autres_allocations': ['familiales', 'complement_familial', 'asf', 'paje', 'prepare', 'aah', 'aeeh', 'pch', 'ada',
                           'bourses', 'autres_prestations'],
    'Pensions': ['pension_alimentaire'], 'Autres_ressources': ['invalidite'],
}
_CHARGES_BUDGET = {
    'Autres_charges_logement': ['electricite', 'combustibles', 'taxes_logement', 'autres_logement'],
    'Assurance_habitation': ['assurance_habitation'], 'Abonnements': ['telephone'],
    'Assurances_hors_habitation': ['assurances'], 'Pensions_alimentaires': ['pensions_versees'],
    'Frais_de_garde': ['garde_scolarite'], 'Impots_et_taxes': ['impots'], 'Total_credits': ['credits'],
    'Autre_precisez_1': ['autres_charges'],
}
_SITUATION_LOCA = {'CELIBATAIRE': "célibataire", 'CONCUBINAGE': "en concubinage", 'PACSE': "pacsé", 'MARIE': "marié",
                   'DIVORCE': "divorcé", 'SEPARE': "en cours de séparation ou divorce", 'VEUF': "veuf"}
_RELATION = {'CONJOINT': "conjoint", 'ENFANT': "enfant", 'AUTRE': "autre"}


def d(v):
    try:
        return Decimal(str(v).replace(',', '.').replace(' ', '').replace('€', '') or 0)
    except (InvalidOperation, ValueError):
        return Decimal(0)


def montant(v):
    v = d(v)
    return "" if not v else (f"{v:.2f}".replace('.', ',').replace(',00', ''))


def _date(x):
    return x.strftime('%d/%m/%Y') if x else ""


def _age(date_texte):
    try:
        j, m, a = (int(x) for x in date_texte.split('/'))
    except (ValueError, AttributeError):
        return ""
    t = timezone.localdate()
    return str(t.year - a - ((t.month, t.day) < (m, j)))


def preremplir(dossier, user):
    """Ce que CID sait déjà : dossier d'expulsion, fiche usager, budget du foyer, FSL, demande de logement."""
    from .fsl import composition, coordonnees_ts
    b, mds = dossier.beneficiaire, dossier.mds
    v = {'Noms': dossier.nom.upper(), 'Prénoms': dossier.prenom, 'Adresse numéro et voie': dossier.adresse,
         'Code postal': dossier.code_postal, 'Commune': dossier.ville,
         'Montant dette': montant(dossier.dette), 'Loyer': montant(dossier.loyer or dossier.loyer_total),
         'Provisions_sur_charges': montant(dossier.charges),
         'type logement': "social" if dossier.type_bailleur == 'SOCIAL' else ("privé" if dossier.type_bailleur else ""),
         'Date 7': _date(dossier.date_signature_bail),
         'Date 10': _date(dossier.date_audience), 'Heure': dossier.heure_audience, 'Lieu': dossier.tribunal,
         'bailleur observation': "oui" if dossier.questionnaire_bailleur_le else ""}
    if b:
        v.update({'Noms': b.nom.upper(), 'Prénoms': b.prenom, 'Date de naissance': _date(b.date_naissance),
                  'Adresse numéro et voie': b.adresse or dossier.adresse, 'Code postal': b.code_postal or dossier.code_postal,
                  'Commune': b.ville or dossier.ville, 'Adresse mail': b.email,
                  'Numéro de téléphone personnel': b.telephone_mobile or b.telephone_fixe,
                  'situation loca': _SITUATION_LOCA.get(b.marital_status or '', '')})
        comp = composition(b)
        if comp:
            v['Situation professionnelle'] = comp[0].get('situation', '')
        autres = comp[1:8]
        for i, p in enumerate(autres, 1):
            v[f'Relation {i}'] = p.get('lien') or _RELATION.get(p['role'], '')
            v[f'Age {i}'] = _age(p.get('date_naissance'))
            v[f'Situation {i}'] = p.get('situation', '')
            v[f'rel {i}'] = "oui" if p['role'] == 'CONJOINT' else ("non" if p['role'] == 'ENFANT' else "")
        a_charge = [p for p in autres if p['role'] != 'CONJOINT']
        if a_charge:
            v['Nombre de personnes à charge'] = str(len(a_charge))
        conj = any(p['role'] == 'CONJOINT' for p in autres)
        enfants = any(p['role'] == 'ENFANT' for p in autres)
        v['situation ménage'] = ("une famille avec deux parents" if conj and enfants else "un couple" if conj
                                 else "une famille monoparentale" if enfants else "une personne seule")
        _budget(b, v)
        _fsl_et_logement(b, v)
        _mesures_asell(b, v)
    ts = coordonnees_ts(user, mds)
    v.update({'Nom': (ts['nom'] or '').upper(), 'Prénom': ts['prenom'], 'Organisme de rattachement': ts['organisme'],
              'Adresse mail_2': ts['email'], 'Numéro de téléphone fixe ou mobile': ts['telephone']})
    return {k: x for k, x in v.items() if x not in (None, "")}


def _budget(b, v):
    from beneficiaire.budget import budget_en_cours
    budget = budget_en_cours(b)
    if not budget:
        return
    r = (budget.ressources or {}).get('lignes', {})
    for cle, codes in _RESS_BUDGET.items():
        for n, col in (("1", 'demandeur'), ("2", 'conjoint'), ("3", 'autres')):
            m = sum((d(r.get(c, {}).get(col)) for c in codes), Decimal(0))
            if m:
                v[f"{cle}_{n}"] = montant(m)
    ch = (budget.charges or {}).get('lignes', {})
    total = lambda c: d(ch.get(c, {}).get('payee')) + d(ch.get(c, {}).get('non_payee'))   # noqa: E731
    for cle, codes in _CHARGES_BUDGET.items():
        m = sum((total(c) for c in codes), Decimal(0))
        if m:
            v[cle] = montant(m)
    if 'Autre_precisez_1' in v:
        v['Autre precisez 1-1'] = (budget.charges or {}).get('precisions', {}).get('autres_charges', "Autres charges")
    if not v.get('Loyer') and total('loyer'):
        v['Loyer'] = montant(total('loyer'))


def _fsl_et_logement(b, v):
    from logement.models import DemandeFSL, DemandeLogementSocial
    f = DemandeFSL.objects.filter(beneficiaire=b, type_aide=DemandeFSL.MAINTIEN).order_by('-pk').first()
    if f and f.statut != DemandeFSL.ABANDONNEE:
        v['FSL'] = {DemandeFSL.ENVOYEE: "déposé le", DemandeFSL.ACCORDEE: "jugé recevable",
                    DemandeFSL.REFUSEE: "refusé"}.get(f.statut, "en cours de constitution")
        if f.statut == DemandeFSL.ENVOYEE:
            v['Date 6'] = _date(f.date_envoi)
    dl = DemandeLogementSocial.objects.filter(beneficiaire=b).first()
    if dl and dl.date_creation:
        v['Date 8'] = _date(dl.date_creation)
        if dl.date_renouvellement:
            v['Date 9'] = _date(dl.date_renouvellement)


def _mesures_asell(b, v):
    """ASELL : le CERFA n'a pas de case ASELL. Une mesure engagée (ou une demande en attente) est écrite dans
    « Autres mesures d'apurement et d'ouverture de droits », à relire dans l'aperçu avant impression."""
    from logement.models import OrientationASELL as A
    orientations = A.objects.filter(beneficiaire=b).exclude(statut=A.ABANDONNEE)
    engagee = orientations.filter(reponse=A.ACCORD).order_by('-date_reponse', '-pk').first()
    if engagee:
        genre = "renforcée" if engagee.type_mesure == A.RENFORCE else "généraliste"
        txt = f"ASELL {genre} engagée"
        if engagee.date_reponse:
            txt += f" depuis le {_date(engagee.date_reponse)}"
        if engagee.nom_operateur:
            txt += f" (opérateur : {engagee.nom_operateur})"
        v["Autres mesures d'apurement"] = txt + "."
        return
    attente = orientations.filter(statut=A.ENVOYEE, reponse__in=['', A.ATTENTE]).order_by('-date_envoi', '-pk').first()
    if attente:
        txt = "ASELL demandée"
        if attente.date_envoi:
            txt += f" le {_date(attente.date_envoi)}"
        v["Autres mesures d'apurement"] = txt + ", en attente de réponse."


def calculs(v):
    """Totaux, reste à vivre et taux d'effort, comme le Cerfa les calcule (l'aperçu ne lance pas ses scripts)."""
    r = {n: sum((d(v.get(f"{code}_{n}")) for code, _ in RESS), Decimal(0)) for n, _ in COLS}
    total_r = sum(r.values(), Decimal(0))
    logement = sum((d(v.get(k)) for k in ('Loyer', 'Provisions_sur_charges', 'Autres_charges_logement',
                                           'Assurance_habitation')), Decimal(0))
    autres = sum((d(v.get(k)) for k in ('Abonnements', 'Transports', 'Assurances_hors_habitation', 'Mutuelle',
                                         'Pensions_alimentaires', 'Frais_de_garde', 'Impots_et_taxes', 'Total_credits',
                                         'Autre_precisez_1', 'Autre_precisez_2')), Decimal(0))
    sortie = {f'Total_des_ressources_mensuelles_{n}': montant(x) for n, x in r.items()}
    sortie.update({'TOTAL': montant(logement), 'TOTAL0': montant(autres), 'TOTAL1': montant(total_r),
                   'TOTAL2': montant(logement + autres),
                   'Reste_a_vivre_mensuel_total_ressources_total_depenses': montant(total_r - logement - autres)
                   if total_r else "",
                   'Taux_d_effort': (f"{(logement / total_r * 100).quantize(Decimal('0.1'))} %".replace('.', ',')
                                     if total_r else "")})
    return sortie


# ------------------------------------------------------------------------------------------------- Cerfa rempli
def _norme(t):
    t = "".join(c for c in unicodedata.normalize("NFD", str(t)) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z]", "", t.lower())


def _etat(etats, voulu):
    """L'état d'une case du Cerfa le plus proche du libellé voulu (certains noms sont mal encodés dans le PDF)."""
    if not etats or not voulu:
        return None
    cible = _norme(voulu)
    exact = [e for e in etats if _norme(e) == cible]
    if exact:
        return exact[0]
    scores = sorted(((difflib.SequenceMatcher(None, _norme(e), cible).ratio(), e) for e in etats), reverse=True)
    return scores[0][1] if scores and scores[0][0] >= 0.6 else None


def modele_cerfa():
    from logement.models import FormulaireOfficiel as F
    f = F.objects.filter(code=F.EXP_DSF, actif=True).exclude(contenu=b'').first()
    return bytes(f.contenu) if f else CERFA.read_bytes()


def _decouper(texte, n=3000):
    """Évaluation sociale : la première partie dans le cadre de la page 4, la suite page 5."""
    texte = texte or ""
    if len(texte) <= n:
        return texte, ""
    coupe = texte.rfind("\n", 0, n)
    coupe = coupe if coupe > n * 0.6 else texte.rfind(" ", 0, n)
    return texte[:coupe].rstrip(), texte[coupe:].lstrip()


def remplir_cerfa(donnees, visa=("", None)):
    """Cerfa 16227*01 rempli (pages du formulaire seulement, sans la notice), visa du cadre en bas de la page 5."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject, BooleanObject, TextStringObject
    v = dict(donnees or {})
    v.update(calculs(v))
    v['Evaluation sociale'], v['Evaluation sociale suite'] = _decouper(v.get('Evaluation sociale'))
    rester = v.pop('rester', "")
    v['oui_18'], v['non_16'] = rester == "oui", rester == "non"
    refus_aj = v.get('aide juridictionnelle') == "refusée"
    if refus_aj:
        v['aide juriditionnelle'], v['aide juridictionnelle'] = "refusée", ""
    w = PdfWriter(clone_from=PdfReader(io.BytesIO(modele_cerfa())))
    if len(w.pages) >= 10:                                  # la notice (5 pages) n'est pas transmise
        for _ in range(5):
            w.remove_page(0)
    for page in w.pages:
        for annot in page.get('/Annots') or []:
            a = annot.get_object()
            if a.get('/Subtype') != '/Widget':
                continue
            parent = a.get('/Parent').get_object() if a.get('/Parent') else None
            nom = a.get('/T') or (parent.get('/T') if parent else None)
            cible = a if a.get('/T') else parent
            type_ = a.get('/FT') or (parent.get('/FT') if parent else None)
            if nom is None or nom not in v:
                continue
            valeur = v[nom]
            if type_ == '/Btn':
                etats = [k for k in (a.get('/AP') or {}).get('/N', {}).keys() if k != '/Off']
                if isinstance(valeur, bool):
                    choisi = etats[0] if (valeur and etats) else None
                else:
                    choisi = _etat(etats, valeur)
                if choisi:
                    a[NameObject('/AS')] = NameObject(choisi)
                    cible[NameObject('/V')] = NameObject(choisi)
                else:
                    a[NameObject('/AS')] = NameObject('/Off')
            elif valeur not in (None, "") and not isinstance(valeur, bool):
                ff = int(cible.get('/Ff', 0) or 0)
                maxlen = int(cible.get('/MaxLen', 0) or (parent.get('/MaxLen', 0) if parent else 0) or 0)
                if ff & (1 << 24) and maxlen:              # cases « en peigne » (dates, heure) : chiffres seuls
                    chiffres = re.sub(r"\D", "", str(valeur))
                    if len(chiffres) < maxlen:      # heure « 930 » → 0930 ; date « 042021 » → __042021
                        chiffres = chiffres.zfill(maxlen) if maxlen <= 4 else chiffres.rjust(maxlen)
                    valeur = chiffres[:maxlen]
                cible[NameObject('/V')] = TextStringObject(str(valeur))
                if '/AP' in a:
                    del a['/AP']                    # le lecteur redessine le champ avec sa valeur
    if '/AcroForm' in w._root_object:
        w._root_object['/AcroForm'][NameObject('/NeedAppearances')] = BooleanObject(True)
    texte, image = visa
    if texte or image:
        _tamponner(w, len(w.pages) - 1, texte, image)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def _tamponner(w, index, texte, image):
    """Visa du cadre en bas de la dernière page, dans la marge, sous les coordonnées du rédacteur."""
    from pypdf import PdfReader
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    page = w.pages[index]
    largeur, hauteur = float(page.mediabox.width), float(page.mediabox.height)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(largeur, hauteur))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(37, 28, texte)
    if image:
        try:
            c.drawImage(ImageReader(io.BytesIO(image['image'])), 200, 14, width=90, height=26,
                        preserveAspectRatio=True, mask='auto')
        except Exception:      # noqa: BLE001 – une image illisible ne bloque pas le DSF
            pass
    c.save()
    page.merge_page(PdfReader(io.BytesIO(buf.getvalue())).pages[0])
