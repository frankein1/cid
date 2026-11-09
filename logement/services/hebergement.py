# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/hebergement.py
"""Hébergement d'urgence : droits, rubriques des fiches, préremplissage, contrôles avant envoi, circuit (visa du
cadre, transmission, réponse), échéances de la prise en charge et statistiques.

Règles reprises de la procédure départementale (2024) :
  - avant toute fiche, les démarches de droit commun sont tracées (115, fiche SIAO, centres maternels s'il y a un
    enfant de moins de 3 ans, DAHO) : sans elles, la demande risque l'ajournement ;
  - demande au service départemental : femme enceinte ou mère isolée avec un enfant de moins de 3 ans ; les autres
    ménages (couple, personne isolée, mère avec enfants de plus de 3 ans) relèvent de l'orientation vers l'État ;
  - prise en charge de 3 mois, renouvelable une fois, puis par périodes de 2 mois : le renouvellement part avant
    l'échéance ;
  - toutes les fiches partent avec l'aval du cadre.

L'information préoccupante n'est jamais préremplie : l'agent coche lui-même (le module IP a ses propres droits).
Le numéro du titre d'identité ou de séjour, demandé par l'État, est effacé à la clôture du dossier."""
from datetime import timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db.models import Count
from django.utils import timezone

from logement.models import (DemarcheHebergement as M, DossierHebergement as D, FicheHebergement as F)

from .expulsion import est_admin, mds_de

T, L, R, J = 'texte', 'long', 'choix', 'date'
ALERTE_JOURS = 21            # le référent est prévenu 3 semaines avant la fin de la prise en charge
LIGNES_PERSONNES = 8


def _c(cle, label, type_=T, options=None, largeur=1, aide=""):
    return {'cle': cle, 'label': label, 'type': type_, 'options': options or [], 'largeur': largeur, 'aide': aide}


REVENUS = [('salaire', "Salaire"), ('caf', "Prestations CAF"), ('rsa', "RSA"), ('ij', "Indemnités journalières"),
           ('invalidite', "Invalidité"), ('chomage', "Allocations chômage"), ('autres', "Autres")]
# rubrique du budget du foyer -> ligne de la fiche
_BUDGET = {'salaire': 'salaire', 'rsa': 'rsa', 'ij': 'ij', 'invalidite': 'invalidite', 'chomage': 'chomage',
           'familiales': 'caf', 'complement_familial': 'caf', 'asf': 'caf', 'paje': 'caf', 'prepare': 'caf',
           'prime_activite': 'caf', 'aah': 'caf', 'aeeh': 'caf', 'logement': 'caf'}

_COORD = [_c('dernier_domicile', "Adresse du dernier domicile ou hébergement connu", largeur=2),
          _c('telephone', "Téléphone portable (pour joindre la famille)")]

SECTIONS = {
    F.SAS: [
        ("Situation administrative", [
            _c('identite_type', "Document d'identité (carte d'identité, passeport, livret de famille…)", largeur=2),
            _c('identite_validite', "Valable jusqu'au"),
            _c('sejour_validite', "Titre de séjour valable jusqu'au"), _c('sejour_mention', "Mention du titre de séjour", largeur=2),
            _c('ip', "Information préoccupante en cours", R, ["oui", "non"]),
            _c('mesure_educative', "Mesure éducative en cours", R, ["oui", "non"])] + _COORD),
        ("Parcours et projet", [
            _c('parcours_logement', "Parcours logement et hébergement", L,
               aide="Il doit apparaître clairement : où la famille a vécu, depuis quand elle est sans solution."),
            _c('historique_projet', "Historique de la situation familiale et projet de vie de la famille", L),
            _c('demarches_logement', "Démarches liées au logement engagées par la famille (logement social, DALO, "
                                     "ASELL accès…)", L),
            _c('analyse', "Analyse globale de la situation", L),
            _c('rdv_famille', "Dates des rendez-vous entre le référent et la famille", largeur=3)]),
    ],
    F.ETAT: [
        ("Situation administrative", [
            _c('identite_type', "Document d'identité ou de séjour (préciser)", largeur=2),
            _c('identite_validite', "Valable jusqu'au"),
            _c('identite_numero', "Numéro (carte d'identité, ou AGDREF à 10 chiffres du titre de séjour)", largeur=2,
               aide="Demandé par les services de l'État. Effacé de CID à la clôture du dossier.")] + _COORD),
        ("Situation familiale", [
            _c('situation_familiale', "Parcours familial, situation des enfants (scolarité, santé), projet de la "
                                      "famille", L,
               aide="Soulignez ce qui rend la situation du ménage vulnérable."),
            _c('parcours_logement', "Situation au regard du logement et de l'hébergement", L)]),
    ],
    F.RENOUVELLEMENT: [
        ("Prise en charge", [
            _c('structure', "Structure d'hébergement", largeur=2), _c('date_entree', "Entrée dans la structure le"),
            _c('renouvellement_du', "Renouvellement à compter du"), _c('duree', "Durée demandée", R, ["1 mois", "2 mois", "3 mois"]),
            _c('fin_prevue', "Fin de prise en charge prévue le")] + _COORD[1:]),
        ("Accompagnement depuis l'entrée", [
            _c('demarches_administratives', "Démarches administratives (droits, titre de séjour, ressources)", L),
            _c('parcours_demarches', "Parcours logement : démarches depuis le début de la prise en charge (SIAO, CHRS, "
                                     "logement social…)", L),
            _c('socio_educatif', "Éléments socio-éducatifs (place des parents, scolarité, suivi des enfants)", L),
            _c('projets', "Projets, orientations envisagées", L), _c('evaluation', "Évaluation sociale", L),
            _c('rdv_famille', "Dates des rencontres entre le référent, la famille et la structure", largeur=3)]),
    ],
}
SECTIONS[F.FINAL] = [
    ("Prise en charge", [
        _c('structure', "Structure d'hébergement", largeur=2), _c('date_entree', "Entrée dans la structure le"),
        _c('date_sortie', "Sortie le"), _c('orientation_sortie', "Solution à la sortie", largeur=2)]),
    SECTIONS[F.RENOUVELLEMENT][1],
]
CHAMPS = {t: {c['cle']: c for _, cs in s for c in cs} for t, s in SECTIONS.items()}
COLONNES_PERSONNE = ['qualite', 'autorite', 'nom', 'prenom', 'naissance', 'lieu']
QUALITES = ["Mère", "Père", "Enfant", "Autre"]


# ------------------------------------------------------------------------------------------------- droits
def peut_voir_module(user):
    return user.is_authenticated and (est_admin(user) or user.a_la_capacite('peut_voir'))


def dossiers_visibles(user):
    qs = D.objects.select_related('beneficiaire', 'mds', 'referent', 'structure')
    if est_admin(user):
        return qs
    if not user.is_authenticated or not user.a_la_capacite('peut_voir'):
        return qs.none()
    return qs.filter(mds__in=mds_de(user))


def peut_voir(user, d):
    if est_admin(user):
        return True
    b = d.beneficiaire
    if b is None:
        return dossiers_visibles(user).filter(pk=d.pk).exists()
    return b.niveau_acces(user) == 'complet'


def peut_ecrire(user, d):
    from beneficiaire.views import user_peut_agir_sur_beneficiaire
    b = d.beneficiaire
    return bool(b and d.statut != D.CLOS and b.niveau_acces(user) == 'complet'
                and user_peut_agir_sur_beneficiaire(user, b))


def peut_viser(user, d):
    return bool(user.a_la_capacite('peut_valider') and user.a_acces_mds(d.mds))


def peut_voir_stats(user):
    return user.is_authenticated and (est_admin(user) or user.a_la_capacite('peut_voir_stats')
                                      or user.a_la_capacite('stats_departement'))


# ------------------------------------------------------------------------------------------------- ménage
def _date(x):
    return x.strftime('%d/%m/%Y') if x else ""


def _lire_date(texte):
    from datetime import datetime
    try:
        return datetime.strptime((texte or '').strip(), '%d/%m/%Y').date()
    except ValueError:
        return None


def _age(naissance, jour=None):
    jour = jour or timezone.localdate()
    return jour.year - naissance.year - ((jour.month, jour.day) < (naissance.month, naissance.day))


def menage(b):
    """Personnes du foyer : [{'personne', 'role', 'responsable'}], le demandeur d'abord."""
    from beneficiaire.models import LienFamilial
    from .fsl import _role
    out, vus = [{'personne': b, 'role': 'DEMANDEUR', 'responsable': True}], {b.pk}
    liens = (LienFamilial.objects.filter(personne_a=b, vit_au_foyer=True)
             | LienFamilial.objects.filter(personne_b=b, vit_au_foyer=True)).select_related('personne_a', 'personne_b')
    for lien in liens:
        autre = lien.personne_b if lien.personne_a_id == b.pk else lien.personne_a
        if autre is None or autre.pk in vus:
            continue
        vus.add(autre.pk)
        out.append({'personne': autre, 'role': _role(lien, b)[0], 'responsable': lien.est_responsable_legal})
    ordre = {'DEMANDEUR': 0, 'CONJOINT': 1, 'ENFANT': 2, 'AUTRE': 3}
    return sorted(out, key=lambda x: (ordre[x['role']], x['personne'].date_naissance or timezone.localdate()))


def _qualite(p, role):
    if role == 'ENFANT':
        return "Enfant"
    if role in ('DEMANDEUR', 'CONJOINT'):
        return "Mère" if p.civilite == 'MME' else "Père"
    return "Autre"


def personnes(b):
    out = []
    for m in menage(b):
        p = m['personne']
        adulte = m['role'] in ('DEMANDEUR', 'CONJOINT')
        out.append({'qualite': _qualite(p, m['role']), 'autorite': "oui" if adulte else "",
                    'nom': p.nom.upper(), 'prenom': p.prenom, 'naissance': _date(p.date_naissance),
                    'lieu': p.lieu_naissance or ""})
    return out[:LIGNES_PERSONNES]


def fiche_conseillee(b):
    """(type de fiche, raison) d'après la composition du foyer. Une grossesse n'est pas connue de CID : à l'agent
    de choisir la demande d'hébergement si la personne est enceinte de plus de trois mois."""
    m = menage(b)
    couple = any(x['role'] == 'CONJOINT' for x in m)
    enfants = [x['personne'] for x in m if x['role'] == 'ENFANT']
    petit = any(e.date_naissance and _age(e.date_naissance) < 3 for e in enfants)
    if not couple and b.civilite == 'MME' and petit:
        return F.SAS, "mère isolée avec un enfant de moins de 3 ans"
    if couple:
        return F.ETAT, "couple" + (" avec enfant(s)" if enfants else " sans enfant")
    if enfants:
        return F.ETAT, "parent isolé dont les enfants ont plus de 3 ans"
    return F.ETAT, "personne isolée sans enfant à charge (sauf grossesse de plus de trois mois : demande d'hébergement)"


def controles(d, type_fiche):
    """Ce qui risque de faire ajourner la demande : à corriger avant le visa (jamais bloquant)."""
    faits = set(d.demarches.values_list('type_demarche', flat=True))
    out = []
    if type_fiche in (F.SAS, F.ETAT):
        if '115' not in faits:
            out.append("Aucun appel au 115 n'est tracé.")
        if 'SIAO' not in faits:
            out.append("La fiche SIAO n'est pas tracée (instruite ou mise à jour).")
        b = d.beneficiaire
        petit = b and any(x['role'] == 'ENFANT' and x['personne'].date_naissance
                          and _age(x['personne'].date_naissance) < 3 for x in menage(b))
        if petit and 'CENTRE_MATERNEL' not in faits:
            out.append("Enfant de moins de 3 ans : les centres maternels du territoire n'ont pas été sollicités.")
    return out


# ------------------------------------------------------------------------------------------------- préremplissage
def _montant(v):
    v = Decimal(v).quantize(Decimal('0.01'))
    return str(int(v)) if v == v.to_integral() else str(v).replace('.', ',')


def revenus(b):
    from AidFi.services.budget_afase import RESSOURCES
    from beneficiaire.budget import budget_en_cours
    from .dsf import d as dec
    budget = budget_en_cours(b)
    if not budget:
        return {}
    libelles = {code: lib.split(' (')[0] for _, ls in RESSOURCES for code, lib in ls}
    totaux, details = {}, {}
    for code, val in ((budget.ressources or {}).get('lignes', {})).items():
        m = sum((dec(val.get(c)) for c in ('demandeur', 'conjoint', 'autres')), Decimal(0))
        if not m:
            continue
        ligne = _BUDGET.get(code, 'autres')
        totaux[ligne] = totaux.get(ligne, Decimal(0)) + m
        if ligne in ('caf', 'autres'):
            details.setdefault(ligne, []).append(f"{libelles.get(code, code)} {_montant(m)} €")
    v = {f"rev_{k}": _montant(m) for k, m in totaux.items()}
    v.update({f"rev_{k}_detail": ", ".join(x) for k, x in details.items()})
    return v


def preremplir(d, type_fiche, user):
    b = d.beneficiaire
    v = {'personnes': personnes(b), 'telephone': b.telephone_mobile or b.telephone_fixe or "",
         'dernier_domicile': " ".join(x for x in (b.adresse.replace("\n", " "), b.code_postal, b.ville) if x)}
    v.update(revenus(b))
    precedente = d.fiches.exclude(donnees={}).order_by('-cree_le').first()
    if precedente:                           # on ne ressaisit pas ce qui a déjà été écrit pour ce ménage
        for cle in CHAMPS[type_fiche]:
            if precedente.donnees.get(cle):
                v[cle] = precedente.donnees[cle]
    if type_fiche in (F.SAS, F.ETAT):
        dl = getattr(b, 'demande_logement', None)
        if dl and dl.nud and type_fiche == F.SAS and 'demarches_logement' not in v:
            v['demarches_logement'] = (f"Demande de logement social n° {dl.nud}"
                                       + (f" du {_date(dl.date_creation)}" if dl.date_creation else "")
                                       + (f". Recours DALO déposé le {_date(dl.dalo_date)}" if dl.dalo_depose and dl.dalo_date
                                          else (". Recours DALO déposé" if dl.dalo_depose else "")) + ".")
    else:
        v['structure'] = d.nom_structure
        v['date_entree'] = _date(d.date_entree)
        if type_fiche == F.RENOUVELLEMENT:
            debut = d.date_fin_prevue or timezone.localdate()
            duree = duree_renouvellement(d)
            v['renouvellement_du'] = _date(debut)
            v['duree'] = f"{duree} mois" if isinstance(duree, int) else ""
            v['fin_prevue'] = _date(fin_apres(debut, duree))
            for cle in ('evaluation', 'projets', 'rdv_famille'):        # à réécrire à chaque période
                v.pop(cle, None)
        else:
            v['date_sortie'] = _date(d.date_sortie or d.date_fin_prevue)
    return {k: x for k, x in v.items() if x not in (None, "", [])}


def lire_formulaire(post, type_fiche):
    """Valeurs saisies : rubriques de la fiche, tableau des personnes, revenus."""
    v = {cle: (post.get(cle) or '').strip()[:6000] for cle in CHAMPS[type_fiche] if (post.get(cle) or '').strip()}
    lignes = []
    for i in range(LIGNES_PERSONNES):
        p = {c: (post.get(f"p{i}_{c}") or '').strip()[:60] for c in COLONNES_PERSONNE}
        if p['nom'] or p['prenom']:
            lignes.append(p)
    if lignes:
        v['personnes'] = lignes
    for code, _ in REVENUS:
        for suffixe in ('', '_detail'):
            x = (post.get(f"rev_{code}{suffixe}") or '').strip()[:150]
            if x:
                v[f"rev_{code}{suffixe}"] = x
    return v


def pour_gabarit(fiche):
    v = fiche.donnees or {}
    sections = [(t, [dict(c, valeur=v.get(c['cle'], '')) for c in cs]) for t, cs in SECTIONS[fiche.type_fiche]]
    lignes = list(v.get('personnes') or [])
    lignes += [{} for _ in range(max(0, min(LIGNES_PERSONNES, len(lignes) + 2) - len(lignes)))]
    pers = [dict(p, i=i) for i, p in enumerate(lignes)]
    rev = [{'code': c, 'label': lib, 'montant': v.get(f"rev_{c}", ''), 'detail': v.get(f"rev_{c}_detail", ''),
            'avec_detail': c in ('caf', 'autres')} for c, lib in REVENUS]
    return sections, pers, rev


# ------------------------------------------------------------------------------------------------- échéances
def duree_initiale(structure):
    return timedelta(days=structure.duree_initiale_jours) if structure and structure.duree_initiale_jours else 3


def duree_renouvellement(d):
    """Durée proposée : celle de la structure si elle est réglée ; sinon 3 mois pour le premier renouvellement, puis
    2 mois."""
    s = d.structure
    if s and s.duree_renouvellement_jours:
        return timedelta(days=s.duree_renouvellement_jours)
    return 3 if d.nb_renouvellements == 0 else 2


def fin_apres(debut, duree):
    return debut + (duree if isinstance(duree, timedelta) else relativedelta(months=duree))


def _message(expediteur, destinataire, d, objet, contenu):
    """expediteur None : rappel automatique, déposé dans la messagerie du destinataire à son propre nom."""
    from django.contrib.contenttypes.models import ContentType
    from messagerie.models import Message, StatutLecture
    if not destinataire or not destinataire.is_active or (expediteur and destinataire.pk == expediteur.pk):
        return None
    expediteur = expediteur or destinataire
    msg = Message.objects.create(
        expediteur=expediteur, destinataire=destinataire, beneficiaire=d.beneficiaire, objet=objet[:255],
        contenu=contenu + "\n\nMessage automatique de CID.", motif='autre', priorite='importante',
        content_type=ContentType.objects.get_for_model(d), object_id=d.pk, reference=d.numero)
    StatutLecture.objects.create(message=msg, utilisateur=destinataire, type_reception='destinataire')
    return msg


def alerter(aujourd_hui=None):
    """Chaque jour : prévenir le référent des prises en charge qui se terminent sous 3 semaines (une seule fois par
    échéance), s'il n'a pas déjà préparé le renouvellement ou le rapport final."""
    j = aujourd_hui or timezone.localdate()
    n = 0
    qs = D.objects.filter(statut=D.HEBERGE, date_fin_prevue__isnull=False, date_fin_prevue__lte=j + timedelta(days=ALERTE_JOURS),
                          referent__isnull=False).select_related('beneficiaire', 'referent', 'structure')
    for d in qs:
        if d.alerte_pour == d.date_fin_prevue:
            continue
        if d.fiches.filter(type_fiche__in=(F.RENOUVELLEMENT, F.FINAL), reponse='', cree_le__date__gte=d.date_fin_prevue
                           - timedelta(days=60)).exists():
            continue
        _message(None, d.referent, d, f"Hébergement d'urgence : échéance le {_date(d.date_fin_prevue)} – {d.nom_complet}",
                 f"La prise en charge de {d.nom_complet} ({d.nom_structure or 'structure à préciser'}) se termine le "
                 f"{_date(d.date_fin_prevue)}. Le renouvellement, ou le rapport final, part avant cette date : il est "
                 f"prérempli dans le dossier {d.numero}.")
        D.objects.filter(pk=d.pk).update(alerte_pour=d.date_fin_prevue)
        n += 1
    return n


# ------------------------------------------------------------------------------------------------- circuit
def ouvrir(b, user):
    """Un seul dossier ouvert par ménage : on reprend celui qui existe."""
    d = D.objects.filter(beneficiaire=b).exclude(statut=D.CLOS).first()
    if d:
        return d, False
    d = D(beneficiaire=b, mds=b.mds, referent=b.referent_mds or user, cree_par=user)
    d.tracer(user, "Dossier ouvert")
    d.save()
    return d, True


def creer_fiche(d, type_fiche, user):
    f = F(dossier=d, type_fiche=type_fiche, redacteur=user)
    f.donnees = preremplir(d, type_fiche, user)
    f.tracer(user, "Fiche créée (préremplie)")
    f.save()
    d.tracer(user, "Fiche créée", f.get_type_fiche_display())
    d.save()
    return f


def demander_visa(f, user):
    from beneficiaire.transfert import responsable_mds
    f.statut, f.redacteur = F.A_VISER, user
    f.tracer(user, "Visa du cadre demandé")
    f.save()
    cadre = responsable_mds(f.dossier.mds)
    _message(user, cadre, f.dossier, f"Visa demandé : hébergement d'urgence – {f.dossier.nom_complet}",
             f"{user.get_full_name() or user.username} demande votre visa : {f.get_type_fiche_display().lower()} "
             f"(dossier {f.dossier.numero}).")
    return cadre


def viser(f, user):
    f.statut, f.cadre, f.date_validation_cadre = F.VISEE, user, timezone.now()
    f.tracer(user, "Visée par le cadre")
    f.save()
    _message(user, f.redacteur, f.dossier, f"Fiche visée, prête à envoyer – {f.dossier.nom_complet}",
             f"{f.get_type_fiche_display()} (dossier {f.dossier.numero}) : visée, vous pouvez la transmettre.")


def renvoyer(f, user, motif):
    f.statut = F.BROUILLON
    f.tracer(user, "Renvoyée à l'agent par le cadre", motif[:200])
    f.save()
    _message(user, f.redacteur, f.dossier, f"Fiche à compléter – {f.dossier.nom_complet}",
             f"{f.get_type_fiche_display()} (dossier {f.dossier.numero}) : à compléter avant le visa."
             + (f"\n{motif}" if motif else ""))


def marquer_transmis(f, user, mode):
    f.statut, f.date_envoi = F.ENVOYEE, timezone.localdate()
    f.tracer(user, "Transmise" + (" par mail" if mode == 'MAIL' else " (imprimée)"))
    f.save()
    d = f.dossier
    d.tracer(user, "Fiche transmise", f.get_type_fiche_display())
    if f.type_fiche == F.FINAL and d.statut == D.HEBERGE and not d.date_sortie:
        d.date_sortie = _lire_date(f.donnees.get('date_sortie'))
    d.save()


def enregistrer_reponse(f, user, issue, date_reponse, detail="", structure=None, structure_libre="", date_entree=None,
                        date_fin=None):
    """Réponse reçue (mail, téléphone) : l'agent la saisit. Un accord ouvre ou prolonge la prise en charge."""
    d = f.dossier
    duree = duree_renouvellement(d)                    # avant d'enregistrer l'accord, qui compte comme un renouvellement
    f.reponse, f.date_reponse, f.reponse_detail = issue, date_reponse or timezone.localdate(), detail[:255]
    f.tracer(user, f"Réponse : {f.get_reponse_display().lower()}", detail[:200])
    f.save()
    if issue == F.ACCORD and f.type_fiche in (F.SAS, F.ETAT):
        d.statut = D.HEBERGE
        d.structure, d.structure_libre = structure, ("" if structure else structure_libre[:150])
        d.date_entree = date_entree or f.date_reponse
        d.date_fin_prevue = date_fin or fin_apres(d.date_entree, duree_initiale(structure))
        d.tracer(user, "Hébergé", f"{d.nom_structure or 'structure à préciser'}, jusqu'au {_date(d.date_fin_prevue)}")
    elif issue == F.ACCORD and f.type_fiche == F.RENOUVELLEMENT:
        debut = d.date_fin_prevue or timezone.localdate()
        d.date_fin_prevue = date_fin or _lire_date(f.donnees.get('fin_prevue')) or fin_apres(debut, duree)
        d.tracer(user, "Prise en charge renouvelée", f"jusqu'au {_date(d.date_fin_prevue)}")
    else:
        d.tracer(user, f"Réponse : {f.get_reponse_display().lower()}", f.get_type_fiche_display())
    d.save()


def cloturer(d, user, motif, date_sortie=None):
    d.statut, d.motif_cloture, d.date_cloture = D.CLOS, motif, timezone.localdate()
    if d.date_entree and not d.date_sortie:
        d.date_sortie = date_sortie or timezone.localdate()
    d.tracer(user, "Dossier clos", d.get_motif_cloture_display())
    d.save()
    for f in d.fiches.filter(donnees__has_key='identite_numero'):       # numéro du titre : plus aucune raison de le garder
        f.donnees.pop('identite_numero', None)
        f.save(update_fields=['donnees'])


def rouvrir(d, user):
    d.statut = D.HEBERGE if d.date_entree and not d.date_sortie else D.RECHERCHE
    d.motif_cloture, d.date_cloture = "", None
    d.tracer(user, "Dossier rouvert")
    d.save()


# ------------------------------------------------------------------------------------------------- statistiques
def statistiques(user, annee=None):
    """Comptages par dossier, sans aucune donnée par agent."""
    departemental = est_admin(user) or user.a_la_capacite('stats_departement')
    qs = D.objects.all() if departemental else D.objects.filter(mds__in=mds_de(user))
    if annee:
        qs = qs.filter(date_ouverture__year=annee)
    fiches = F.objects.filter(dossier__in=qs).exclude(statut=F.BROUILLON)
    types, reponses = dict(F.TYPES), dict(F.REPONSES)
    durees = [(x.date_sortie - x.date_entree).days for x in qs.filter(date_entree__isnull=False, date_sortie__isnull=False)]
    j = timezone.localdate()
    return {
        'total': qs.count(), 'recherche': qs.filter(statut=D.RECHERCHE).count(),
        'heberges': qs.filter(statut=D.HEBERGE).count(), 'clos': qs.filter(statut=D.CLOS).count(),
        'echeances': qs.filter(statut=D.HEBERGE, date_fin_prevue__lte=j + timedelta(days=ALERTE_JOURS)).count(),
        'duree_moyenne': round(sum(durees) / len(durees)) if durees else None,
        'par_mds': list(qs.values('mds__nom').annotate(n=Count('pk')).order_by('-n')),
        'par_fiche': [(types[r['type_fiche']], r['n']) for r in fiches.values('type_fiche').annotate(n=Count('pk')).order_by('-n')],
        'par_reponse': [(reponses.get(r['reponse'], "En attente"), r['n'])
                        for r in fiches.filter(statut=F.ENVOYEE).values('reponse').annotate(n=Count('pk')).order_by('-n')],
        'par_structure': [(r['structure__nom'] or "Autre", r['n']) for r in
                          qs.filter(date_entree__isnull=False).values('structure__nom').annotate(n=Count('pk')).order_by('-n')],
        'par_cloture': [(dict(D.MOTIFS_CLOTURE).get(r['motif_cloture'], "—"), r['n']) for r in
                        qs.filter(statut=D.CLOS).values('motif_cloture').annotate(n=Count('pk')).order_by('-n')],
        'par_demarche': [(dict(M.TYPES)[r['type_demarche']], r['n']) for r in
                         M.objects.filter(dossier__in=qs).values('type_demarche').annotate(n=Count('pk')).order_by('-n')],
        'departemental': departemental,
    }
