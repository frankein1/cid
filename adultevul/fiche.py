# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# adultevul/fiche.py
"""Fiche de renseignements sur la personne à protéger, par parquet.

La saisie se fait dans CID (masque) ; le formulaire PDF remplissable à l'écran n'est
utile qu'en cas de nécessité absolue d'impression.
"""
from django import forms
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

CHOIX_LOGEMENT = [('PROPRIETAIRE', 'Propriétaire'), ('LOCATAIRE', 'Locataire'), ('HEBERGE', 'Hébergé'),
                  ('AUTRE', 'Autre')]
CHOIX_FAMILLE = [('CELIBATAIRE', 'Célibataire'), ('MARIE', 'Marié(e)'), ('CONCUBIN', 'Vivant maritalement'),
                 ('PACS', 'Pacsé(e)'), ('DIVORCE', 'Divorcé(e)'), ('SEPARE', 'Séparé(e)'), ('VEUF', 'Veuf(ve)')]
CHOIX_OUI_NON = [('OUI', 'Oui'), ('NON', 'Non')]
CHOIX_AVIS = [('FAVORABLE', 'Favorable à la demande'), ('OPPOSEE', 'Opposée à la demande'),
              ('NON_INFORMEE', "N'est pas informée")]

# clé : (libellé, type, choix)   type : 'court', 'long', 'choix'
CHAMPS = {
    'demandeur_nom': ("Nom et prénoms du requérant", 'court', None),
    'demandeur_lien': ("Lien de parenté avec la personne à protéger", 'court', None),
    'demandeur_contact': ("Adresse et téléphone du requérant", 'long', None),
    'demandeur_qualite': ("Qualité (degré de parenté ou autre)", 'court', None),
    'nom_jeune_fille': ("Nom de jeune fille", 'court', None),
    'lieu_naissance': ("Lieu de naissance", 'court', None),
    'nationalite': ("Nationalité", 'court', None),
    'profession': ("Profession", 'court', None),
    'telephone': ("Téléphone", 'court', None),
    'logement_statut': ("Logement", 'choix', CHOIX_LOGEMENT),
    'logement_disponible': ("Logement principal toujours à sa disposition ?", 'court', None),
    'hospitalisation': ("Lieu d'hébergement ou d'hospitalisation (avec date d'entrée)", 'court', None),
    'domicile_occupe': ("Domicile occupé en l'absence du majeur ?", 'choix', CHOIX_OUI_NON),
    'clefs': ("Qui a les clés ?", 'court', None),
    'situation_familiale': ("Situation de famille", 'choix', CHOIX_FAMILLE),
    'conjoint': ("Conjoint : nom, prénom, adresse", 'long', None),
    'secu': ("Numéro de sécurité sociale", 'court', None),
    'caf': ("Numéro CAF", 'court', None),
    'bureau_payeur': ("Bureau payeur (adresse et téléphone)", 'long', None),
    'medecin_traitant': ("Médecin traitant (nom, adresse, téléphone)", 'long', None),
    'membres_famille': ("Membres de la famille (nom, prénom, lien, adresse et téléphone, profession)", 'long', None),
    'enfants_freres': ("Enfants, frères et sœurs (nom, prénom, âge, adresse, téléphone)", 'long', None),
    'parents_relations': ("Parents et relations (nom, adresse, lien, téléphone)", 'long', None),
    'intervenants_sante': ("Médecins et infirmières (nom, adresse, téléphone)", 'long', None),
    'patrimoine_immobilier': ("Biens immobiliers (désignation, occupants, possesseurs des clés)", 'long', None),
    'patrimoine_mobilier': ("Biens mobiliers, meubles précieux, véhicules, objets d'art", 'long', None),
    'comptes': ("Comptes bancaires, livrets, placements (désignation, montant, lieu)", 'long', None),
    'notaire': ("Notaire ou avocat (nom et adresse)", 'long', None),
    'procuration': ("Existe-t-il des procurations ? À qui ?", 'long', None),
    'ressources': ("Ressources mensuelles (organisme payeur, montant)", 'long', None),
    'dernier_impot': ("Montant du dernier impôt sur le revenu", 'court', None),
    'charges': ("Charges mensuelles (loyer, énergie, assurances, téléphone, impôts…)", 'long', None),
    'dettes': ("Dettes (nature, montant, ancienneté)", 'long', None),
    'actes_urgents': ("Actes urgents nécessaires, actes importants accomplis pour la personne (par qui, quand)", 'long', None),
    'actions_justice': ("Action en justice ou succession en cours", 'long', None),
    'gestion_difficultes': ("Problèmes de gestion existants ou à prévoir", 'long', None),
    'pathologie': ("De quoi souffre la personne ?", 'long', None),
    'validite': ("La personne est-elle validée ?", 'court', None),
    'cotorep': ("La COTOREP est-elle déjà intervenue ?", 'court', None),
    'suivi_medical': ("Suivie par un médecin généraliste, un psychiatre, un assistant social (coordonnées)", 'long', None),
    'derniere_visite': ("Date de la dernière rencontre avec la personne", 'court', None),
    'visites_regulieres': ("Voyez-vous la personne régulièrement ? à quel rythme ?", 'court', None),
    'pret_a_gerer': ("Êtes-vous prêt à vous occuper de ses affaires ? sinon pourquoi", 'long', None),
    'autre_representant': ("En cas de refus, qui pourrait assumer cette tâche (coordonnées)", 'long', None),
    'necessite': ("Raisons concrètes pour lesquelles la mesure est demandée", 'long', None),
    'avis_personne': ("Avis de la personne concernée", 'choix', CHOIX_AVIS),
    'avis_famille': ("Avis de la famille", 'choix', CHOIX_AVIS),
    'personne_apte': ("Personne la plus apte à représenter l'intéressé, et pourquoi", 'long', None),
    'observations': ("Autres observations (mesures ou actes administratifs d'urgence à effectuer)", 'long', None),
}

# Présentation de chaque parquet : titre, puis sections dans l'ordre du formulaire du parquet.
PARQUETS = {
    'AIX': {
        'titre': "Notice de renseignements concernant la personne à protéger (rubriques 1 à 10)",
        'sections': [
            ("1 – Identité du majeur à protéger", ['nom_jeune_fille', 'lieu_naissance', 'nationalite', 'profession',
                                                   'logement_statut', 'logement_disponible', 'situation_familiale',
                                                   'conjoint']),
            ("2 – Renseignements administratifs", ['secu', 'caf']),
            ("3 – Parents et relations", ['parents_relations']),
            ("4 – Médecins et infirmières", ['medecin_traitant', 'intervenants_sante']),
            ("5 – Patrimoine", ['patrimoine_immobilier', 'patrimoine_mobilier', 'comptes', 'notaire']),
            ("6 – Ressources et charges", ['ressources', 'dernier_impot', 'charges', 'dettes']),
            ("7 – Actes et actions en cours", ['actes_urgents', 'actions_justice', 'procuration']),
            ("8 – Nécessité de la mesure de protection", ['necessite', 'avis_personne', 'avis_famille']),
            ("9 – Observations particulières", ['personne_apte', 'observations']),
            ("10 – Renseignements concernant le déclarant", ['demandeur_nom', 'demandeur_contact']),
        ],
    },
    'MARSEILLE': {
        'titre': "Fiche de renseignements – personne à protéger",
        'sections': [
            ("Identité du requérant", ['demandeur_nom', 'demandeur_lien', 'demandeur_contact']),
            ("Personne à protéger", ['nom_jeune_fille', 'lieu_naissance', 'nationalite', 'profession', 'telephone',
                                     'logement_statut', 'hospitalisation', 'domicile_occupe', 'clefs',
                                     'situation_familiale', 'conjoint', 'medecin_traitant', 'secu',
                                     'bureau_payeur']),
            ("Membres de la famille (obligatoire)", ['membres_famille']),
            ("Patrimoine de la personne à protéger", ['patrimoine_immobilier', 'patrimoine_mobilier', 'comptes']),
            ("Revenus de la personne à protéger", ['ressources']),
            ("Gestion", ['gestion_difficultes', 'procuration']),
        ],
    },
    'TARASCON': {
        'titre': "Fiche d'information à joindre à toute demande de régime de protection – Service civil du parquet de Tarascon",
        'sections': [
            ("Renseignements sur la personne faisant la demande", ['demandeur_nom', 'demandeur_qualite',
                                                                    'demandeur_contact']),
            ("Renseignements sur la personne qui nécessite une mesure de protection",
             ['nom_jeune_fille', 'conjoint', 'profession', 'telephone', 'logement_statut', 'hospitalisation',
              'logement_disponible']),
            ("Famille", ['enfants_freres', 'parents_relations']),
            ("Les biens", ['patrimoine_immobilier', 'patrimoine_mobilier', 'comptes', 'procuration', 'ressources',
                           'dernier_impot', 'actions_justice', 'notaire', 'dettes', 'actes_urgents']),
            ("Santé", ['pathologie', 'validite', 'cotorep', 'suivi_medical', 'derniere_visite',
                       'visites_regulieres', 'pret_a_gerer', 'autre_representant', 'observations']),
        ],
    },
}


def champs_formulaire():
    """Tous les champs de la fiche (union des trois parquets), dans l'ordre des sections du formulaire Aix."""
    return [k for _, cles in PARQUETS['AIX']['sections'] for k in cles]


class FicheForm(forms.Form):
    """Masque de saisie de la fiche : remplace l'impression et le formulaire papier."""

    def __init__(self, *args, fiche=None, **kwargs):
        super().__init__(*args, **kwargs)
        fiche = fiche or {}
        for cle, (libelle, type_, choix) in CHAMPS.items():
            if type_ == 'choix':
                champ = forms.ChoiceField(label=libelle, required=False, choices=[('', '—')] + choix)
            elif type_ == 'long':
                champ = forms.CharField(label=libelle, required=False, widget=forms.Textarea(attrs={'rows': 2}))
            else:
                champ = forms.CharField(label=libelle, required=False)
            champ.widget.attrs.setdefault('class', 'mt-1 block w-full rounded-lg border-gray-300')
            self.fields[cle] = champ
            self.initial[cle] = fiche.get(cle, '')


def _pdf(texte):
    """Police standard PDF : seuls les caractères WinAnsi sont disponibles (pas le symbole euro, par exemple)."""
    texte = str(texte).replace("€", "EUR").replace("\u2019", "'")
    return texte.encode("cp1252", "replace").decode("cp1252")


def _valeur_identite(situation):
    return {
        'nom': situation.personne_nom,
        'prenom': situation.personne_prenom,
        'naissance': situation.personne_naissance.strftime('%d/%m/%Y') if situation.personne_naissance else '',
        'adresse': situation.personne_adresse,
    }


def fiche_pdf(situation, tribunal, destination):
    """Formulaire PDF remplissable à l'écran, prérempli avec les données saisies dans CID."""
    parquet = PARQUETS[tribunal]
    valeurs = {**(situation.fiche or {}), **_valeur_identite(situation)}
    c = canvas.Canvas(destination, pagesize=A4)
    c.setTitle(f"Fiche de renseignements – {situation.numero} – {tribunal}")
    largeur, hauteur = A4
    marge = 16 * mm
    y = hauteur - 16 * mm

    def nouvelle_page(y_actuel, besoin):
        if y_actuel - besoin < 18 * mm:
            c.showPage()
            return hauteur - 16 * mm
        return y_actuel

    c.setFont("Helvetica-Bold", 11)
    c.drawString(marge, y, _pdf(parquet['titre'][:95]))
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    c.drawString(marge, y, _pdf(f"Majeur à protéger : {situation.libelle_personne} · dossier {situation.numero}"))
    y -= 9 * mm

    identite_cles = [('nom', "Nom"), ('prenom', "Prénom"), ('naissance', "Date de naissance"),
                     ('adresse', "Adresse")]
    c.setFont("Helvetica-Bold", 9)
    c.drawString(marge, y, "Identité")
    y -= 5 * mm
    for cle, libelle in identite_cles:
        y = nouvelle_page(y, 9 * mm)
        c.setFont("Helvetica", 8.5)
        c.drawString(marge, y + 1 * mm, _pdf(libelle))
        c.acroForm.textfield(name=cle, x=marge + 38 * mm, y=y - 2 * mm, width=largeur - 2 * marge - 38 * mm,
                             height=6 * mm, value=_pdf(valeurs.get(cle, '')), borderStyle='inset',
                             forceBorder=True, fontSize=9)
        y -= 8 * mm

    for titre, cles in parquet['sections']:
        y = nouvelle_page(y, 14 * mm)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(marge, y, _pdf(titre))
        y -= 5 * mm
        for cle in cles:
            libelle, type_, choix = CHAMPS[cle]
            if type_ == 'choix':
                y = nouvelle_page(y, 12 * mm)
                c.setFont("Helvetica", 8.5)
                c.drawString(marge, y, _pdf(libelle))
                y -= 5 * mm
                x = marge
                for valeur, texte in choix:
                    c.acroForm.checkbox(name=f"{cle}__{valeur}", x=x, y=y - 1 * mm, size=4 * mm,
                                        checked=valeurs.get(cle) == valeur, buttonStyle='check')
                    c.setFont("Helvetica", 8)
                    c.drawString(x + 5 * mm, y, _pdf(texte))
                    x += 5 * mm + c.stringWidth(texte, "Helvetica", 8) + 6 * mm
                y -= 8 * mm
            else:
                hauteur_champ = 6 * mm if type_ == 'court' else 22 * mm
                y = nouvelle_page(y, hauteur_champ + 8 * mm)
                c.setFont("Helvetica", 8.5)
                c.drawString(marge, y, _pdf(libelle))
                y -= 1.5 * mm
                c.acroForm.textfield(name=cle, x=marge, y=y - hauteur_champ, width=largeur - 2 * marge,
                                     height=hauteur_champ, value=_pdf(valeurs.get(cle, '')), borderStyle='inset',
                                     forceBorder=True, fontSize=8.5,
                                     fieldFlags='multiline' if type_ == 'long' else '')
                y -= hauteur_champ + 4 * mm
        y -= 3 * mm
    c.setFont("Helvetica-Oblique", 7.5)
    c.drawString(marge, 10 * mm, "Formulaire à remplir dans CID. N'imprimer qu'en cas de nécessité absolue.")
    c.save()
