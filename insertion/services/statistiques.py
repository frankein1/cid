# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/services/statistiques.py
"""
File active RSA et statistiques, sans aucune saisie supplémentaire : tout vient des contrats, prescriptions et
réorientations déjà enregistrés.

Périmètre (« chacun le sien ») :
  - super-administrateur : tout le département ;
  - agent d'un pôle insertion : les MDS de son pôle ;
  - cadre de MDS (capacité rsa_actions_locales) : ses MDS ;
  - référent : sa file active (contrats dont il est le référent, prescriptions et réorientations qu'il a faites).

File active : personnes qui ont un contrat (hors annulé) ou une prescription (hors annulée et brouillon), sauf
celles réorientées (France Travail, CAF, association) depuis la date d'effet.
Taux de contractualisation : part de la file active qui a un contrat en vigueur aujourd'hui.
"""
from collections import Counter, OrderedDict
from datetime import date, timedelta

from django.db.models import Q
from django.utils import timezone

from insertion import acces
from insertion.models import (FREINS, ContratInsertion as C, DemandeReorientation as R, OrganismeOrientation,
                              ParametresRSA, PrescriptionInsertion as P)


# ---------------------------------------------------------------------- périmètre
class Perimetre:
    """Filtre à appliquer aux contrats, prescriptions et réorientations ; libellé lisible."""

    def __init__(self, user):
        from mds.models import MDS, UserMDSProfile
        self.user = user
        self.tout = user.is_superuser or user.a_la_capacite('peut_administrer')
        self.mds_ids, self.referent = None, None
        # Les agents du pôle n'ont pas accès au dossier social : pas de lien vers le parcours de la personne
        self.voit_dossiers = self.tout or not acces.est_agent_pole(user)
        if self.tout:
            self.libelle = "tout le département"
        elif acces.est_agent_pole(user):
            poles = list(acces.poles_de(user))
            self.mds_ids = set(MDS.objects.filter(poles_insertion__in=poles).values_list('pk', flat=True))
            self.libelle = ", ".join(p.nom for p in poles) or "aucun pôle"
        elif user.a_la_capacite('rsa_actions_locales'):
            self.mds_ids = set(UserMDSProfile.objects.filter(user=user, actif=True).values_list('mds_id', flat=True))
            self.libelle = ", ".join(MDS.objects.filter(pk__in=self.mds_ids).values_list('nom', flat=True)) or "aucune MDS"
        else:
            self.referent = user
            self.libelle = "ma file active"

    @property
    def est_referent(self):
        return self.referent is not None

    def mds_disponibles(self):
        from mds.models import MDS
        if self.tout:
            return MDS.objects.filter(contrats_insertion__isnull=False).distinct().order_by('nom')
        if self.mds_ids is not None:
            return MDS.objects.filter(pk__in=self.mds_ids).order_by('nom')
        return MDS.objects.none()

    def contrats(self, mds=None):
        qs = C.objects.exclude(statut=C.ANNULE)
        return self._filtre(qs, mds, Q(referent=self.referent))

    def prescriptions(self, mds=None):
        qs = P.objects.exclude(statut__in=(P.ANNULEE, P.BROUILLON))
        return self._filtre(qs, mds, Q(prescripteur=self.referent))

    def reorientations(self, mds=None):
        qs = R.objects.exclude(statut__in=(R.ANNULEE, R.BROUILLON))
        return self._filtre(qs, mds, Q(referent=self.referent))

    def _filtre(self, qs, mds, filtre_referent):
        if self.referent is not None:
            qs = qs.filter(filtre_referent)
        elif self.mds_ids is not None:
            qs = qs.filter(mds_id__in=self.mds_ids)
        if mds:
            qs = qs.filter(mds_id=mds)
        return qs


# ---------------------------------------------------------------------- file active
ALERTES = OrderedDict([
    ("sans_contrat", "Sans contrat en vigueur"), ("renouveler", "Contrat à renouveler"), ("expire", "Contrat échu"),
    ("sauf_action", "Validé sauf action"), ("en_validation", "Contrat en cours de validation"),
    ("ajourne", "Contrat ajourné"), ("reorientation", "Réorientation inscrite en commission"),
])


def _reorientes(aujourd_hui):
    return set(R.objects.filter(statut=R.ACCEPTEE, date_effet__lte=aujourd_hui).values_list('beneficiaire_id', flat=True))


def file_active(perimetre, mds=None, inclure_reorientes=False):
    """Une ligne par personne : dernier contrat, alerte, prescriptions en cours, réorientation."""
    aujourd_hui = timezone.localdate()
    delai = ParametresRSA.courant().delai_alerte_jours
    contrats = list(perimetre.contrats(mds).select_related('beneficiaire', 'mds', 'referent')
                    .order_by('beneficiaire_id', '-date_etablissement', '-pk'))
    prescriptions = list(perimetre.prescriptions(mds).select_related('beneficiaire', 'mds', 'prescripteur', 'action'))
    reorientations = list(perimetre.reorientations(mds).select_related('organisme_retenu', 'commission'))
    reorientes = _reorientes(aujourd_hui)

    personnes = OrderedDict()
    for c in contrats:
        personnes.setdefault(c.beneficiaire_id, {"beneficiaire": c.beneficiaire, "mds": c.mds, "referent": c.referent,
                                                 "contrats": [], "prescriptions": [], "reorientations": []})
        personnes[c.beneficiaire_id]["contrats"].append(c)
    for p in prescriptions:
        ligne = personnes.setdefault(p.beneficiaire_id, {"beneficiaire": p.beneficiaire, "mds": p.mds,
                                                         "referent": p.prescripteur, "contrats": [],
                                                         "prescriptions": [], "reorientations": []})
        ligne["prescriptions"].append(p)
    for r in reorientations:
        if r.beneficiaire_id in personnes:
            personnes[r.beneficiaire_id]["reorientations"].append(r)

    lignes = []
    for bid, l in personnes.items():
        reoriente = bid in reorientes
        if reoriente and not inclure_reorientes:
            continue
        contrat = l["contrats"][0] if l["contrats"] else None   # le plus récent
        en_vigueur = next((c for c in l["contrats"] if c.statut in (C.VALIDE, C.VALIDE_SAUF_ACTION) and c.date_debut
                           and c.date_debut <= aujourd_hui <= c.date_fin), None)
        alertes = []
        if en_vigueur:
            suivant = any(c.pk != en_vigueur.pk and c.statut != C.NON_VALIDE and (
                c.precedent_id == en_vigueur.pk or c.pk > en_vigueur.pk) for c in l["contrats"])
            if (en_vigueur.date_fin - aujourd_hui).days <= delai and not suivant:
                alertes.append("renouveler")
            if en_vigueur.statut == C.VALIDE_SAUF_ACTION:
                alertes.append("sauf_action")
        else:
            alertes.append("sans_contrat")
            dernier_valide = next((c for c in l["contrats"] if c.statut in (C.VALIDE, C.VALIDE_SAUF_ACTION)), None)
            if dernier_valide and dernier_valide.date_fin and dernier_valide.date_fin < aujourd_hui and not any(
                    c.statut in (C.BROUILLON, C.TRANSMIS, C.RECU, C.AJOURNE) for c in l["contrats"]):
                alertes.append("expire")
        if any(c.statut in (C.TRANSMIS, C.RECU) for c in l["contrats"]):
            alertes.append("en_validation")
        if any(c.statut == C.AJOURNE for c in l["contrats"]):
            alertes.append("ajourne")
        if any(r.statut == R.INSCRITE for r in l["reorientations"]):
            alertes.append("reorientation")
        b = l["beneficiaire"]
        lignes.append({
            "beneficiaire": b, "mds": l["mds"], "referent": (en_vigueur or contrat).referent if (en_vigueur or contrat) else l["referent"],
            "contrat": en_vigueur or contrat, "en_vigueur": en_vigueur, "alertes": alertes,
            "prescriptions_en_cours": [p for p in l["prescriptions"] if p.statut in (P.A_VALIDER, P.EN_ATTENTE, P.INTEGREE)],
            "reoriente": next((r for r in l["reorientations"] if r.statut == R.ACCEPTEE), None) if reoriente else None,
            "reorientation_inscrite": next((r for r in l["reorientations"] if r.statut == R.INSCRITE), None),
        })
    lignes.sort(key=lambda x: (x["mds"].nom if x["mds"] else "", x["beneficiaire"].nom, x["beneficiaire"].prenom))
    return lignes


def filtrer_file_active(lignes, *, alerte="", nature="", referent="", ville="", q=""):
    q = q.strip().lower()
    out = []
    for l in lignes:
        b, c = l["beneficiaire"], l["contrat"]
        if alerte and alerte not in l["alertes"]:
            continue
        if nature and not (c and c.nature == nature):
            continue
        if referent and not (l["referent"] and str(l["referent"].pk) == referent):
            continue
        if ville and (b.ville or "").lower() != ville.lower():
            continue
        if q and q not in f"{b.nom} {b.prenom} {b.code_interne}".lower():
            continue
        out.append(l)
    return out


COLONNES_FILE_ACTIVE = ["MDS", "Code", "Nom", "Prénom", "Âge", "Commune", "Référent", "Contrat", "Statut du contrat",
                        "Type", "Nature", "Du", "Au", "Alertes", "Prescriptions en cours", "Réorientation"]


def lignes_csv_file_active(lignes):
    for l in lignes:
        b, c = l["beneficiaire"], l["contrat"]
        age = ""
        if b.date_naissance:
            aujourd_hui = timezone.localdate()
            age = aujourd_hui.year - b.date_naissance.year - (
                (aujourd_hui.month, aujourd_hui.day) < (b.date_naissance.month, b.date_naissance.day))
        reo = l["reoriente"] or l["reorientation_inscrite"]
        yield [l["mds"].nom if l["mds"] else "", b.code_interne, b.nom.upper(), b.prenom, age, b.ville,
               (l["referent"].get_full_name() or l["referent"].username) if l["referent"] else "",
               c.numero if c else "", c.get_statut_display() if c else "", c.get_type_contrat_display() if c else "",
               c.get_nature_display() if c else "", _d(c.date_debut) if c else "", _d(c.date_fin) if c else "",
               ", ".join(ALERTES[a] for a in l["alertes"]),
               " ; ".join(p.action.libelle for p in l["prescriptions_en_cours"]),
               (f"{reo.get_statut_display()} : {reo.orientation_libelle}" if reo else "")]


def _d(d):
    return d.strftime("%d/%m/%Y") if d else ""


# ---------------------------------------------------------------------- statistiques
def periode(debut=None, fin=None):
    aujourd_hui = timezone.localdate()
    debut = debut or date(aujourd_hui.year, 1, 1)
    fin = fin or aujourd_hui
    return debut, fin


def _repartition(valeurs, libelles):
    compte = Counter(valeurs)
    total = sum(compte.values())
    return [{"libelle": libelles.get(k, k or "—"), "nombre": n, "part": round(100 * n / total) if total else 0}
            for k, n in sorted(compte.items(), key=lambda kv: -kv[1])]


def _moyenne(jours):
    jours = [j for j in jours if j is not None and j >= 0]
    return round(sum(jours) / len(jours), 1) if jours else None


def statistiques(perimetre, debut, fin, mds=None):
    aujourd_hui = timezone.localdate()
    lignes = file_active(perimetre, mds)
    nb_file = len(lignes)
    nb_en_vigueur = sum(1 for l in lignes if l["en_vigueur"])
    alertes = Counter(a for l in lignes for a in l["alertes"])

    contrats = perimetre.contrats(mds)
    etablis = list(contrats.filter(date_etablissement__range=(debut, fin)))
    decides = list(contrats.filter(date_decision__range=(debut, fin)).exclude(decision=""))
    transmis = [c for c in contrats.filter(date_transmission__range=(debut, fin))]
    en_vigueur = [l["en_vigueur"] for l in lignes if l["en_vigueur"]]

    prescriptions = perimetre.prescriptions(mds)
    prescrites = list(prescriptions.filter(date_prescription__range=(debut, fin)).select_related('action'))
    sorties = list(prescriptions.filter(Q(date_sortie__range=(debut, fin)) | Q(statut=P.NON_INTEGREE,
                                                                               modifie_le__date__range=(debut, fin))))
    par_action = OrderedDict()
    for p in sorted(prescrites, key=lambda x: x.action.libelle):
        a = par_action.setdefault(p.action_id, {"libelle": p.action.libelle, "code": p.action.code, "prescrites": 0,
                                                "integrees": 0, "non_integrees": 0, "refusees": 0, "en_attente": 0})
        a["prescrites"] += 1
        if p.date_entree:
            a["integrees"] += 1
        elif p.statut == P.NON_INTEGREE:
            a["non_integrees"] += 1
        elif p.statut == P.REFUSEE:
            a["refusees"] += 1
        elif p.statut in (P.EN_ATTENTE, P.A_VALIDER):
            a["en_attente"] += 1
    for a in par_action.values():
        decidees = a["integrees"] + a["non_integrees"]
        a["taux"] = round(100 * a["integrees"] / decidees) if decidees else None

    reorientations = perimetre.reorientations(mds)
    reo_decidees = list(reorientations.filter(date_decision__range=(debut, fin), statut__in=(R.ACCEPTEE, R.REFUSEE))
                        .select_related('organisme_retenu'))
    from insertion.models import ExamenReorientation
    ajournements = ExamenReorientation.objects.filter(demande__in=reorientations, decision=R.AJOURNEE,
                                                      commission__date__range=(debut, fin)).count()

    par_mds = []
    if not perimetre.est_referent and not mds:
        for m in perimetre.mds_disponibles():
            lm = [l for l in lignes if l["mds"] and l["mds"].pk == m.pk]
            if not lm:
                continue
            nv = sum(1 for l in lm if l["en_vigueur"])
            par_mds.append({"mds": m.nom, "file_active": len(lm), "en_vigueur": nv,
                            "taux": round(100 * nv / len(lm)) if lm else 0,
                            "renouveler": sum(1 for l in lm if "renouveler" in l["alertes"]),
                            "echus": sum(1 for l in lm if "expire" in l["alertes"])})

    return {
        "file_active": nb_file, "en_vigueur": nb_en_vigueur,
        "taux_contractualisation": round(100 * nb_en_vigueur / nb_file) if nb_file else None,
        "alertes": [{"code": k, "libelle": v, "nombre": alertes.get(k, 0)} for k, v in ALERTES.items()],
        "par_mds": par_mds,
        "contrats_etablis": len(etablis),
        "types": _repartition([c.type_contrat for c in etablis], dict(C.TYPES)),
        "natures_en_vigueur": _repartition([c.nature for c in en_vigueur], dict(C.NATURES)),
        "decisions": _repartition([c.decision for c in decides], dict(C.DECISIONS)),
        "nb_decisions": len(decides),
        "delai_reception": _moyenne([(c.date_reception - c.date_transmission).days for c in transmis
                                     if c.date_reception and c.date_transmission]),
        "delai_decision": _moyenne([(c.date_decision - c.date_reception).days for c in decides
                                    if c.date_decision and c.date_reception]),
        "sante": {"contrats": sum(1 for c in etablis if c.nature == 'SANTE'),
                  "favorables": sum(1 for c in etablis if c.avis_medical == 'FAVORABLE'),
                  "defavorables": sum(1 for c in etablis if c.avis_medical == 'DEFAVORABLE')},
        "transport": _repartition([c.decision_transport for c in decides if c.decision_transport],
                                  dict(C.DECISIONS_TRANSPORT)),
        "prescriptions": len(prescrites), "par_action": list(par_action.values()),
        "freins": _repartition([f for p in prescrites for f in p.freins], dict(FREINS)),
        "sorties": _repartition([p.statut for p in sorties], dict(P.STATUTS)),
        "nb_sorties": len(sorties),
        "reorientations": len(reo_decidees), "ajournements": ajournements,
        "reo_decisions": _repartition([r.statut for r in reo_decidees], dict(R.STATUTS)),
        "reo_vers": _repartition([r.organisme_retenu.categorie for r in reo_decidees if r.organisme_retenu],
                                 dict(OrganismeOrientation.CATEGORIES)),
        "aujourd_hui": aujourd_hui,
    }


def tableaux_csv(stats):
    """Toutes les statistiques en un seul tableau « section ; libellé ; valeur ; part » (facile à retravailler)."""
    yield ["Section", "Libellé", "Nombre", "Part (%)"]
    yield ["File active", "Personnes dans la file active", stats["file_active"], ""]
    yield ["File active", "Avec un contrat en vigueur", stats["en_vigueur"], stats["taux_contractualisation"] or ""]
    for a in stats["alertes"]:
        yield ["Alertes", a["libelle"], a["nombre"], ""]
    for m in stats["par_mds"]:
        yield ["Par MDS", f"{m['mds']} : file active", m["file_active"], ""]
        yield ["Par MDS", f"{m['mds']} : contrat en vigueur", m["en_vigueur"], m["taux"]]
    yield ["Contrats", "Contrats établis sur la période", stats["contrats_etablis"], ""]
    for section, cle in (("Type des contrats établis", "types"), ("Nature des contrats en vigueur", "natures_en_vigueur"),
                         ("Décisions de la commission", "decisions"), ("Aide aux transports", "transport"),
                         ("Freins (prescriptions)", "freins"), ("Sorties d'action", "sorties"),
                         ("Réorientations décidées", "reo_decisions"), ("Réorientations vers", "reo_vers")):
        for r in stats[cle]:
            yield [section, r["libelle"], r["nombre"], r["part"]]
    yield ["Délais", "Transmission → réception (jours, moyenne)", stats["delai_reception"] or "", ""]
    yield ["Délais", "Réception → décision (jours, moyenne)", stats["delai_decision"] or "", ""]
    yield ["Contrats santé", "Établis", stats["sante"]["contrats"], ""]
    yield ["Contrats santé", "Avis favorables", stats["sante"]["favorables"], ""]
    yield ["Contrats santé", "Avis défavorables", stats["sante"]["defavorables"], ""]
    for a in stats["par_action"]:
        yield ["Prescriptions par action", f"{a['libelle']} ({a['code']}) : prescrites", a["prescrites"], ""]
        yield ["Prescriptions par action", f"{a['libelle']} ({a['code']}) : intégrées", a["integrees"],
               a["taux"] if a["taux"] is not None else ""]
    yield ["Réorientations", "Ajournements", stats["ajournements"], ""]
