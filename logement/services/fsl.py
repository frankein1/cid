# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/fsl.py
"""FSL accès : rubriques du formulaire, préremplissage depuis CID (fiche, foyer, budget, CAF), pièces, plafonds."""
from decimal import Decimal, InvalidOperation

from django.utils import timezone

# Lignes de ressources du formulaire FSL accès, et lignes du budget du foyer qui les alimentent
RESSOURCES_FSL = [
    ('salaires', "Salaires", ['salaire', 'autres_activite']),
    ('france_travail', "Allocations France Travail", ['chomage']),
    ('rsa', "RSA", ['rsa']),
    ('prime_activite', "Prime d'activité", ['prime_activite']),
    ('ij', "Indemnités journalières", ['ij']),
    ('pension', "Pension (préciser)", ['retraite', 'invalidite']),
    ('pension_complementaire', "Pension complémentaire", []),
    ('prestations_familiales', "Prestations familiales (préciser)",
     ['familiales', 'complement_familial', 'asf', 'paje', 'prepare', 'aeeh']),
    ('autres_1', "Autres ressources", ['aah', 'pension_alimentaire']),
    ('autres_2', "Autres ressources", ['pch', 'ada', 'bourses']),
    ('autres_3', "Autres ressources", ['autres_prestations']),
]
COLONNES = [('demandeur', "Demandeur"), ('conjoint', "Conjoint"), ('autres', "Autres personnes au foyer")]
LIBELLES_BUDGET = {
    'retraite': "retraite", 'invalidite': "invalidité", 'familiales': "AF", 'complement_familial': "CF",
    'asf': "ASF", 'paje': "PAJE", 'prepare': "PreParE", 'aeeh': "AEEH", 'aah': "AAH",
    'pension_alimentaire': "pension alimentaire", 'pch': "PCH", 'ada': "ADA", 'bourses': "bourses",
    'autres_prestations': "autres",
}

PROPOSITION = [
    ('caution', "Caution"),
    ('caution_differentielle', "Caution différentielle"),
    ('premier_loyer', "1er mois de loyer chargé"),
    ('compteurs', "Frais d'ouverture des compteurs"),
    ('assurance', "Assurance (seul le 1er mois)"),
    ('equipements', "Équipements de première nécessité"),
]
EQUIPEMENTS = [('table_cuisson', "Table de cuisson"), ('refrigerateur', "Réfrigérateur"),
               ('lave_linge', "Lave-linge"), ('lit_140', "Lit 140"), ('lit_90', "Lit 90"),
               ('table_chaises', "Table et chaises")]
GARANTIES = [('', "Pas de garantie de paiement"), ('4_12', "4 mois sur 12"), ('12_36', "12 mois sur 36")]
SITUATIONS_FAMILIALES = [('CELIBATAIRE', "Célibataire"), ('SEPARE', "Séparé(e)"), ('MARITALE', "Vie maritale"),
                         ('DIVORCE', "Divorcé(e)"), ('MARIE', "Marié(e)"), ('VEUF', "Veuf(ve)")]
ROLES = [('DEMANDEUR', "Demandeur"), ('CONJOINT', "Conjoint"), ('ENFANT', "Enfant"), ('AUTRE', "Autre personne")]

LOGEMENT_ANTERIEUR = [
    ('bailleur', "Nom ou raison sociale du bailleur"),
    ('nature', "Nature (HLM, secteur privé, hébergement, hôtel…)"),
    ('typologie', "Typologie du logement"),
    ('statut', "Statut d'occupation (locataire, hébergé…)"),
    ('loyer', "Loyer"), ('charges', "Charges locatives"),
    ('al', "Montant AL ou APL"), ('loyer_residuel', "Loyer résiduel"),
    ('motif', "Motif de la demande de relogement"),
]
LOGEMENT_NOUVEAU = [
    ('bailleur', "Nom ou raison sociale du bailleur"),
    ('typologie', "Typologie du logement"), ('classe_energetique', "Classe énergétique"),
    ('loyer', "Loyer"), ('charges', "Charges locatives"),
    ('montant_caution', "Montant de la caution"),
    ('al_previsionnel', "Montant AL ou APL prévisionnel"), ('loyer_residuel', "Loyer résiduel"),
    ('date_entree', "Date d'entrée dans les lieux"), ('demande_al_le', "Demande d'AL/APL déposée le"),
]

# Pièces du dossier d'accès. condition : bailleur privé, SCI, prêt, garantie, équipements…
PIECES = [
    ('formulaire', "Formulaire rempli, daté, signé (travailleur social et demandeur), cachet de la structure", None),
    ('avis', "Avis motivé et proposition du travailleur social, signé", None),
    ('identite', "Pièces d'identité de toutes les personnes majeures du foyer (titre de séjour en cours de validité)", None),
    ('etat_civil_mineurs', "Mineurs : extrait d'acte de naissance ou livret de famille", None),
    ('ressources', "Justificatifs des ressources du foyer, mois précédant la signature", None),
    ('ressources_majeurs', "Enfants majeurs : justificatifs de ressources ou de non-ressources", None),
    ('rib', "Relevé d'identité bancaire du demandeur", None),
    ('bail', "Bail daté et signé (IML : contrat de location et bail initial)", None),
    ('etat_lieux', "État des lieux signé", None),
    ('assurance', "Attestation d'assurance habitation du nouveau logement", None),
    ('compteurs', "Justificatifs d'ouverture des compteurs", None),
    ('caution_precedente', "Restitution ou non de la caution du logement précédent", None),
    ('situation_precedente', "Justificatifs de la situation précédente (si équipement demandé)", 'equipements'),
    ('contrat_pret', "Contrat de prêt signé", None),
    ('prelevement', "Autorisation et demande de prélèvement", None),
    ('garantie', "Contrat de mise en jeu de la garantie", 'garantie'),
    ('ident_logement', "Fiche d'identification du logement (bailleur privé)", 'prive'),
    ('rib_bailleur', "RIB du bailleur privé ou de la SCI", 'prive'),
    ('kbis', "Extrait K-bis de la SCI", 'prive'),
    ('convention', "Convention d'accès au logement signée", None),
    ('versement_direct', "Demande de versement direct de l'AL / APL", None),
    ('surendettement', "Plan conventionnel de surendettement, le cas échéant", 'facultatif'),
]
ETATS_PIECE = [('MANQUANTE', "À fournir"), ('FOURNIE', "Fournie"), ('SANS_OBJET', "Sans objet")]


def d(valeur):
    try:
        return Decimal(str(valeur if valeur not in (None, '') else 0).replace(',', '.').replace(' ', ''))
    except (InvalidOperation, ValueError):
        return Decimal(0)


def montant(valeur):
    """Affichage français, vide si zéro."""
    v = d(valeur)
    if not v:
        return ""
    return f"{v:,.2f}".replace(',', ' ').replace('.', ',')


def _date(dt):
    return dt.strftime('%d/%m/%Y') if dt else ""


def _situation(b):
    return b.get_situation_display() if getattr(b, 'situation', '') else ""


def _role(lien, beneficiaire):
    """Place d'une personne du foyer par rapport au demandeur, d'après le lien enregistré (dans un sens ou l'autre)."""
    t = lien.type_lien
    if lien.personne_a_id == beneficiaire.pk:          # b est « type_lien » de a
        return {'CONJOINT': 'CONJOINT', 'ENFANT': 'ENFANT'}.get(t, 'AUTRE'), lien.get_type_lien_display()
    inverse = {'PARENT': 'ENFANT', 'ENFANT': 'AUTRE', 'CONJOINT': 'CONJOINT'}
    return inverse.get(t, 'AUTRE'), ("Parent" if t == 'ENFANT' else lien.get_type_lien_display())


def composition(beneficiaire):
    from beneficiaire.models import LienFamilial
    lignes = [{'role': 'DEMANDEUR', 'nom': beneficiaire.nom, 'prenom': beneficiaire.prenom,
               'date_naissance': _date(beneficiaire.date_naissance), 'nationalite': '',
               'situation': _situation(beneficiaire), 'lien': ''}]
    vus = {beneficiaire.pk}
    liens = (LienFamilial.objects.filter(personne_a=beneficiaire, vit_au_foyer=True)
             | LienFamilial.objects.filter(personne_b=beneficiaire, vit_au_foyer=True)).select_related(
        'personne_a', 'personne_b')
    for lien in liens:
        autre = lien.personne_b if lien.personne_a_id == beneficiaire.pk else lien.personne_a
        if autre is None or autre.pk in vus:
            continue
        vus.add(autre.pk)
        role, libelle = _role(lien, beneficiaire)
        lignes.append({'role': role, 'nom': autre.nom, 'prenom': autre.prenom,
                       'date_naissance': _date(autre.date_naissance), 'nationalite': '',
                       'situation': _situation(autre), 'lien': libelle if role == 'AUTRE' else ''})
    ordre = {'DEMANDEUR': 0, 'CONJOINT': 1, 'ENFANT': 2, 'AUTRE': 3}
    return sorted(lignes, key=lambda l: (ordre[l['role']], l['date_naissance'][-4:] if l['date_naissance'] else ''))


def ressources_depuis_budget(budget):
    """Lignes FSL à partir du budget du foyer (mêmes colonnes demandeur / conjoint / autres)."""
    res, precisions = {}, {}
    lignes = (budget.ressources or {}).get('lignes', {}) if budget else {}
    for code, _, sources in RESSOURCES_FSL:
        valeurs = {col: Decimal(0) for col, _ in COLONNES}
        noms = []
        for s in sources:
            if s in lignes:
                for col, _ in COLONNES:
                    valeurs[col] += d(lignes[s].get(col))
                if any(d(lignes[s].get(col)) for col, _ in COLONNES) and s in LIBELLES_BUDGET:
                    noms.append(LIBELLES_BUDGET[s])
        if any(valeurs.values()):
            res[code] = {col: str(v) for col, v in valeurs.items() if v}
            if noms:
                precisions[code] = ", ".join(noms)
    return res, precisions


def totaux_ressources(ressources):
    par_col = {col: sum((d(v.get(col)) for v in (ressources or {}).values()), Decimal(0)) for col, _ in COLONNES}
    return par_col, sum(par_col.values(), Decimal(0))


def taux_effort(donnees):
    """(Loyer + charges − AL prévisionnelle) / total des ressources, en %. Indicatif : le règlement intérieur fait foi."""
    n = donnees.get('logement_nouveau', {})
    _, total = totaux_ressources(donnees.get('ressources'))
    if not total:
        return ""
    reste = d(n.get('loyer')) + d(n.get('charges')) - d(n.get('al_previsionnel'))
    return f"{(reste / total * 100).quantize(Decimal('0.1'))}".replace('.', ',')


def _profil_mds(user, mds):
    from mds.models import UserMDSProfile
    return UserMDSProfile.objects.filter(user=user, mds=mds, actif=True).first()


def coordonnees_ts(user, mds):
    """Le courriel est celui de la MDS : l'adresse nominative des agents reste interne (choix de Fred, 7/11/2026)."""
    p = _profil_mds(user, mds) if user else None
    adresse = " ".join(x for x in [mds.adresse, mds.code_postal, mds.ville] if x) if mds else ""
    return {'nom': user.last_name if user else '', 'prenom': user.first_name if user else '',
            'qualite': p.intitule if p else '', 'telephone': (p.telephone_interne if p else '') or (mds.telephone if mds else ''),
            'portable': '', 'email': mds.email if mds else '',
            'organisme': f"{mds.nom} – {adresse}" if mds else ''}


def preremplir(beneficiaire, user):
    from beneficiaire.budget import budget_en_cours
    from connecteurs.models import SituationExterne
    budget = budget_en_cours(beneficiaire)
    ressources, precisions = ressources_depuis_budget(budget)
    statut = beneficiaire.marital_status or ''
    situation = {'PACSE': 'MARITALE', 'CONCUBINAGE': 'MARITALE'}.get(statut, statut)
    qf = SituationExterne.objects.filter(beneficiaire=beneficiaire, source='QUOTIENT_FAMILIAL', statut_appel='OK').first()
    charges = (budget.charges or {}).get('lignes', {}) if budget else {}
    loyer = d(charges.get('loyer', {}).get('payee')) + d(charges.get('loyer', {}).get('non_payee'))
    al = sum((d(v) for v in ((budget.ressources or {}).get('lignes', {}).get('logement', {}) if budget else {}).values()),
             Decimal(0))
    return {
        'num_caf': beneficiaire.numero_caf or '',
        'autres_numero': '',
        'bailleur_type': '',
        'adresse_objet': '', 'cp_commune': '',
        'nouveau_bailleur': '', 'contact_bailleur': '',
        'situation_familiale': situation if situation in dict(SITUATIONS_FAMILIALES) else '',
        'composition': composition(beneficiaire),
        'ressources': ressources, 'ressources_precisions': precisions,
        'quotient_familial': str(qf.donnees.get('valeur', '')) if qf else '',
        'logement_anterieur': {'loyer': str(loyer) if loyer else '', 'al': str(al) if al else '',
                               'loyer_residuel': str(loyer - al) if loyer else ''},
        'logement_nouveau': {},
        'garantie': '', 'proposition': {}, 'proposition_fsl': {}, 'equipements': [],
        'adresse_actuelle': f"{beneficiaire.adresse}, {beneficiaire.code_postal} {beneficiaire.ville}",
        'ts': coordonnees_ts(user, beneficiaire.mds),
        'origine': (f"budget du foyer du {budget.date_etabli:%d/%m/%Y}" if budget else "pas de budget du foyer")
                   + (", quotient familial CAF" if qf else ""),
        'date_preremplissage': timezone.localdate().strftime('%d/%m/%Y'),
    }


def pieces_attendues(demande):
    """Pièces qui concernent cette demande (bailleur privé, garantie, équipements…)."""
    donnees = demande.donnees or {}
    prive = donnees.get('bailleur_type') == 'PRIVE'
    garantie = bool(donnees.get('garantie'))
    equipements = bool(d((donnees.get('proposition') or {}).get('equipements')))
    out = []
    for code, libelle, cond in PIECES:
        if cond == 'prive' and not prive:
            continue
        if cond == 'garantie' and not garantie:
            continue
        if cond == 'equipements' and not equipements:
            continue
        out.append((code, libelle, cond == 'facultatif'))
    return out


def alertes(demande):
    """Plafonds du règlement intérieur (paramétrés sur le gestionnaire) : CID prévient, le FSL décide."""
    g = demande.gestionnaire
    p = (g.parametres if g else {}) or {}
    donnees = demande.donnees or {}
    prop = donnees.get('proposition') or {}
    out = []
    total = sum((d(v) for v in prop.values()), Decimal(0))
    if p.get('plafond_acces') and total > d(p['plafond_acces']):
        out.append(f"Le total proposé ({montant(total)} €) dépasse le plafond de l'aide à l'accès "
                   f"({montant(p['plafond_acces'])} €).")
    equip = d(prop.get('equipements'))
    enfants = any(l.get('role') == 'ENFANT' for l in donnees.get('composition', []))
    cle = 'plafond_equipement_famille' if enfants else 'plafond_equipement_seul'
    if equip and p.get(cle) and equip > d(p[cle]):
        out.append(f"Équipements : {montant(equip)} € pour un plafond de {montant(p[cle])} € "
                   f"({'ménage avec enfants' if enfants else 'personne seule ou couple'}).")
    if not donnees.get('bailleur_type'):
        out.append("Indiquez si le bailleur est social ou privé.")
    return out
