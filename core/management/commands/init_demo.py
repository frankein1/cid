# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/management/commands/init_demo.py
"""
Jeu de données FICTIVES pour tester toutes les fonctions de CID (voir docs/DONNEES_FICTIVES.md).

À lancer après init2 (comptes et familles de base) :
    python manage.py init_demo                  # crée le jeu s'il n'existe pas encore
    python manage.py init_demo --reinitialiser  # supprime les dossiers de démonstration et les recrée
                                                 # (les dates sont recalculées à partir d'aujourd'hui)

Toutes les personnes, adresses et numéros sont inventés. Les dates sont calculées par rapport au jour
de création : une demande « à décider sous 10 jours » le devient réellement, puis dépasse son délai.
Les montants sont des exemples : ils ne reprennent pas la note de service.
"""
import os
from io import StringIO
from datetime import time, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

User = get_user_model()
MARQUEUR = "FAM4-NOL"   # présent = jeu déjà créé

# Comptes ajoutés à ceux d'init2 : (identifiant, prénom, nom, profil, code MDS ou None)
COMPTES = [
    ("cadre2", "Cadre", "MDS 2", "MDS_RESPONSABLE", "MDSTEST2"),
    ("ts2", "Agent Social", "MDS 2", "MDS_AGENTS_SOCIAUX", "MDSTEST2"),
    ("uagaf1", "Agent", "UAGAF 1", "SERVICE_CONTROLE_AFASE", None),
    ("regie1", "Régisseur", "Central 1", "REGISSEUR_CENTRAL", None),
    ("pi_admin", "Agent", "Pôle insertion", "POLE_INSERTION_ADMINISTRATIF", None),
    ("pi_cadre", "Cadre", "Pôle insertion", "POLE_INSERTION_CADRE", None),
    ("pi_medecin", "Médecin", "Pôle insertion", "POLE_INSERTION_MEDECIN", None),
]

# Actions d'insertion fictives : code, libellé, type, niveau, MDS locale (1 ou None), porteur, durée, comité
ACTIONS_DEMO = [
    ("DEMO-ACCGLO", "Accompagnement global (fictif)", "accompagnement-global", "DEPARTEMENTAL", None,
     "Opérateur emploi (fictif)", "12 mois", "trimestriel"),
    ("DEMO-MOBIL", "Plateforme mobilité (fictif)", "mobilite", "DEPARTEMENTAL", None,
     "Association Mobilité Exemple (fictif)", "6 mois", ""),
    ("DEMO-SANTE", "Parcours santé et insertion (fictif)", "sante", "DEPARTEMENTAL", None,
     "Association Santé Exemple (fictif)", "12 mois, 1 rendez-vous par mois", "semestriel"),
    ("DEMO-CISF", "Atelier insertion des femmes (fictif)", "remobilisation", "LOCAL", 1,
     "Association de quartier (fictif)", "12 mois", "semestriel"),
    ("DEMO-BRICO", "Atelier bricolage et logement (fictif)", "logement", "LOCAL", 1,
     "Association de développement local (fictif)", "", ""),
]

# Familles ajoutées : code, civilité, nom, prénom, âge, MDS (1 ou 2), code postal, ville, situation familiale
FAMILLES = {
    "FAM4": [("NOL", "M.", "VIDAL", "Nolan", 19, 1, "13110", "Port-de-Bouc", "CELIBATAIRE")],
    "FAM5": [("SAR", "MME", "AMRANI", "Sarah", 27, 1, "13110", "Port-de-Bouc", "CONCUBINAGE")],
    "FAM6": [("KEV", "M.", "ROUX", "Kevin", 35, 1, "84000", "Avignon", "DIVORCE"),
             ("ROM", "M.", "ROUX", "Romain", 7, 1, "84000", "Avignon", None)],
    "FAM7": [("NAD", "MME", "BENSALEM", "Nadia", 36, 1, "13110", "Port-de-Bouc", "DIVORCE"),
             ("ILY", "M.", "BENSALEM", "Ilyes", 11, 1, "13110", "Port-de-Bouc", None),
             ("KAR", "M.", "BENSALEM", "Karim", 39, 2, "13500", "Martigues", "DIVORCE"),
             ("ANI", "MME", "BENSALEM", "Anissa", 6, 2, "13500", "Martigues", None)],
    "FAM8": [("LAU", "MME", "PEREZ", "Laura", 33, 1, "13110", "Port-de-Bouc", "CELIBATAIRE"),
             ("NOE", "M.", "PEREZ", "Noé", 9, 1, "13110", "Port-de-Bouc", None),
             ("MIL", "MME", "PEREZ", "Mila", 4, 1, "13110", "Port-de-Bouc", None)],
    "FAM9": [("CEL", "MME", "GARNIER", "Céline", 41, 1, "13110", "Port-de-Bouc", "CELIBATAIRE"),
             ("ETH", "M.", "GARNIER", "Ethan", 13, 1, "13110", "Port-de-Bouc", None),
             ("ROS", "MME", "GARNIER", "Rose", 10, 1, "13110", "Port-de-Bouc", None)],
    "FAM10": [("YAS", "MME", "CHERIF", "Yasmine", 30, 1, "13110", "Port-de-Bouc", "CELIBATAIRE"),
              ("ADA", "M.", "CHERIF", "Adam", 3, 1, "13110", "Port-de-Bouc", None)],
    "FAM11": [("THO", "M.", "LEGRAND", "Thomas", 45, 1, "13110", "Port-de-Bouc", "VEUF"),
              ("JUS", "MME", "LEGRAND", "Justine", 16, 1, "13110", "Port-de-Bouc", None)],
    "FAM12": [("AUR", "MME", "AUBERT", "Aurélie", 34, 1, "13110", "Port-de-Bouc", "MARIE"),
              ("DAV", "M.", "AUBERT", "David", 37, 1, "13110", "Port-de-Bouc", "MARIE"),
              ("GAB", "M.", "AUBERT", "Gabriel", 8, 1, "13110", "Port-de-Bouc", None),
              ("LIN", "MME", "AUBERT", "Lina", 5, 1, "13110", "Port-de-Bouc", None)],
}
# Liens familiaux : (parent ou conjoint, autre, type, vit au foyer)
LIENS = [
    ("FAM6-KEV", "FAM6-ROM", "ENFANT", True),
    ("FAM7-NAD", "FAM7-ILY", "ENFANT", True), ("FAM7-KAR", "FAM7-ANI", "ENFANT", True),
    ("FAM7-NAD", "FAM7-ANI", "ENFANT", False), ("FAM7-KAR", "FAM7-ILY", "ENFANT", False),
    ("FAM8-LAU", "FAM8-NOE", "ENFANT", False), ("FAM8-LAU", "FAM8-MIL", "ENFANT", True),
    ("FAM9-CEL", "FAM9-ETH", "ENFANT", True), ("FAM9-CEL", "FAM9-ROS", "ENFANT", True),
    ("FAM10-YAS", "FAM10-ADA", "ENFANT", True),
    ("FAM11-THO", "FAM11-JUS", "ENFANT", True),
    ("FAM12-AUR", "FAM12-DAV", "CONJOINT", True),
    ("FAM12-AUR", "FAM12-GAB", "ENFANT", True), ("FAM12-AUR", "FAM12-LIN", "ENFANT", True),
    ("FAM12-DAV", "FAM12-GAB", "ENFANT", True), ("FAM12-DAV", "FAM12-LIN", "ENFANT", True),
]
CODES_DEMO = ["FAM1-JEA", "FAM2-SOP", "FAM2-PAU", "FAM3-CLA", "FAM3-MAR", "API-JUL", "API-FRA"] + \
             [f"{f}-{p[0]}" for f, ps in FAMILLES.items() for p in ps]


def type_aide(code):
    from AidFi.models.m_generique import TypeAide
    noms = {"AFASE": "Aide Financière ASE", "CAP": "Chèque d'Accompagnement Personnalisé", "REGIE": "Régie d'urgence"}
    return TypeAide.objects.get_or_create(code=code, defaults={"nom": noms[code], "actif": True})[0]


def mot_de_passe():
    return os.environ.get("DEMO_PASSWORD") or "demo123&"


# Comptes de démonstration (init2 et init_demo) : mot de passe remis à mot_de_passe() à chaque création ou
# réinitialisation du jeu. Jamais un super-administrateur.
COMPTES_INIT2 = ["asmith", "bjones", "cdubois", "MarioB", "LuigiB", "jcadre1", "kchef", "pmi1", "crip1", "pief1"]


class Command(BaseCommand):
    help = "Crée le jeu de données fictives de démonstration et de test (voir docs/DONNEES_FICTIVES.md)."

    def add_arguments(self, parser):
        parser.add_argument("--reinitialiser", action="store_true",
                            help="Supprime les dossiers de démonstration (aides, IP, rendez-vous) puis les recrée.")

    def handle(self, *args, **opts):
        from beneficiaire.models import Beneficiaire
        if not Beneficiaire.objects.filter(code_interne="FAM1-JEA").exists():
            call_command("init2")
        if opts["reinitialiser"]:
            self.supprimer()
        elif Beneficiaire.objects.filter(code_interne=MARQUEUR).exists():
            self.stdout.write("📌 Jeu de démonstration déjà présent (--reinitialiser pour le recréer).")
            return
        with transaction.atomic():
            self.j = timezone.localdate()
            self.structures()
            self.familles()
            self.parametres()
            self.afase()
            self.cap_regie()
            self.ip()
            self.planning()
            self.insertion()
        self.stdout.write(self.style.SUCCESS("🎉 Jeu de données fictives créé (voir docs/DONNEES_FICTIVES.md)."))

    # ------------------------------------------------------------------ remise à zéro
    @transaction.atomic
    def supprimer(self):
        from AidFi.models.m_generique import DemandeAide
        from AidFi.models.m_recours import RecoursAFASE
        from beneficiaire.models import Beneficiaire
        from planning.models import CreneauRdv
        from protection_enfance.models import InformationPreoccupante
        from django.contrib.contenttypes.models import ContentType
        from messagerie.models import Message
        from protection_enfance.models import ActionIP
        benefs = Beneficiaire.objects.filter(code_interne__in=CODES_DEMO)
        aides = list(DemandeAide.objects.filter(beneficiaire__in=benefs).values_list("pk", flat=True))
        ips = InformationPreoccupante.objects.filter(famille__in=benefs).exclude(   # l'IP d'init2 est gardée
            historique_actions__action__startswith="IP de démonstration créée (init2)")
        creneaux = list(ActionIP.objects.filter(ip__in=ips, creneau__isnull=False).values_list("creneau_id", flat=True))
        # Messages automatiques liés aux dossiers supprimés (sinon leurs liens mèneraient à une page introuvable)
        types_aides = [ContentType.objects.get_for_model(m) for m in DemandeAide.__subclasses__()] + \
                      [ContentType.objects.get_for_model(DemandeAide)]
        Message.objects.filter(content_type__in=types_aides, object_id__in=aides).delete()
        Message.objects.filter(content_type=ContentType.objects.get_for_model(InformationPreoccupante),
                               object_id__in=list(ips.values_list("pk", flat=True))).delete()
        # Anciens messages des usagers fictifs dont le dossier n'existe déjà plus (remises à zéro antérieures)
        type_ip = ContentType.objects.get_for_model(InformationPreoccupante)
        orphelins = [m.pk for m in Message.objects.filter(beneficiaire__in=benefs, content_type__in=types_aides + [type_ip])
                     if not m.content_type.model_class().objects.filter(pk=m.object_id).exists()]
        Message.objects.filter(pk__in=orphelins).delete()
        # Documents GED des usagers fictifs et de leurs IP (déposés pendant les essais) : la suppression d'un
        # document supprime ses versions, et chaque version son fichier dans le stockage (pCloud sur Render).
        from ged.models import DocumentGED
        type_benef = ContentType.objects.get_for_model(Beneficiaire)
        docs = DocumentGED.objects.filter(content_type=type_benef, object_id__in=list(benefs.values_list("pk", flat=True))) | \
            DocumentGED.objects.filter(content_type=type_ip, object_id__in=list(ips.values_list("pk", flat=True)))
        nb_docs = docs.count()
        for doc in docs:
            doc.delete()
        RecoursAFASE.objects.filter(demande__beneficiaire__in=benefs).delete()
        DemandeAide.objects.filter(pk__in=aides).delete()
        ips.delete()
        CreneauRdv.objects.filter(pk__in=creneaux).delete()
        CreneauRdv.objects.filter(notes_internes__startswith="[démo]").delete()
        from AidFi.models.m_cap import ReceptionCAP, TitreCAP
        TitreCAP.objects.filter(reception__reference="BORD-DEMO").delete()
        ReceptionCAP.objects.filter(reference="BORD-DEMO").delete()
        self.stdout.write(f"🧹 Dossiers de démonstration supprimés ({len(aides)} demandes d'aide, {nb_docs} documents).")

    # ------------------------------------------------------------------ comptes et MDS
    def u(self, username):
        return User.objects.get(username=username)

    def structures(self):
        from core.models import Profil
        from mds.models import MDS, MDSReception, UserMDSProfile
        self.mds1 = MDS.objects.get(code_mds="MDSTEST1")
        self.mds2, _ = MDS.objects.get_or_create(code_mds="MDSTEST2", defaults={
            "nom": "MDS TEST 02", "adresse": "5 avenue des Platanes", "code_postal": "13500", "ville": "Martigues",
            "telephone": "0442000000", "email": "mds.test2@example.com", "active": True, "date_ouverture": self.j})
        MDSReception.objects.get_or_create(mds=self.mds2, nom="Bureau 1", defaults={
            "capacite": 3, "type_salle": "BUREAU", "actif": True, "horaire_debut": time(9), "horaire_fin": time(17),
            "disponible_lundi": True, "disponible_mardi": True, "disponible_mercredi": True,
            "disponible_jeudi": True, "disponible_vendredi": True})
        for username, prenom, nom, code, code_mds in COMPTES:
            user, cree = User.objects.get_or_create(username=username, defaults={
                "first_name": prenom, "last_name": nom, "email": f"{username}@exemple.fr", "is_active": True,
                "matricule": username.upper()})
            if cree:
                user.set_password(mot_de_passe())
                user.save()
            profil = Profil.objects.get(code=code)
            user.profils.add(profil)
            if code_mds:
                ump, _ = UserMDSProfile.objects.get_or_create(
                    user=user, mds=MDS.objects.get(code_mds=code_mds), defaults={"principale": True, "actif": True})
                ump.save()
        mdp = mot_de_passe()
        for user in User.objects.filter(username__in=COMPTES_INIT2 + [c[0] for c in COMPTES], is_superuser=False):
            user.set_password(mdp)
            user.force_change_password = False
            user.save(update_fields=["password", "force_change_password"])
        if not self.mds2.responsable:
            self.mds2.responsable = self.u("cadre2")
            self.mds2.save(update_fields=["responsable"])
        self.ts, self.ts_b, self.cadre, self.cadre2 = self.u("asmith"), self.u("bjones"), self.u("kchef"), self.u("cadre2")
        self.ts2, self.uagaf, self.regie = self.u("ts2"), self.u("uagaf1"), self.u("regie1")
        self.pief, self.crip, self.pmi = self.u("pief1"), self.u("crip1"), self.u("pmi1")
        self.stdout.write("✅ Comptes et MDS de démonstration")

    # ------------------------------------------------------------------ familles
    def familles(self):
        from beneficiaire.models import Beneficiaire, LienFamilial
        self.b = {c: Beneficiaire.objects.get(code_interne=c) for c in
                  ["FAM1-JEA", "FAM2-SOP", "FAM2-PAU", "FAM3-CLA", "FAM3-MAR", "API-JUL", "API-FRA"]}
        rues = iter(["8 rue des Oliviers", "14 boulevard de la Mer", "3 impasse des Pins", "27 avenue du Port",
                     "9 rue Jean Moulin", "2 allée des Tamaris", "41 chemin des Salins", "6 place de la Liberté",
                     "18 rue des Écoles"])
        for fam, personnes in FAMILLES.items():
            adresse = next(rues)
            for suffixe, civ, nom, prenom, age, n_mds, cp, ville, statut_marital in personnes:
                code = f"{fam}-{suffixe}"
                naissance = self.j - relativedelta(years=age, days=37 * (len(prenom) + age % 7))
                self.b[code], _ = Beneficiaire.objects.get_or_create(code_interne=code, defaults={
                    "civilite": civ, "nom": nom, "prenom": prenom, "date_naissance": naissance,
                    "adresse": "12 rue du Rhône" if cp == "84000" else (adresse if n_mds == 1 else "11 rue des Lices"),
                    "code_postal": cp, "ville": ville, "mds": self.mds1 if n_mds == 1 else self.mds2,
                    "statut": "ACTIF", "marital_status": statut_marital, "cree_par": self.ts})
        inverse = {"ENFANT": "PARENT", "CONJOINT": "CONJOINT"}
        for a, c, type_lien, foyer in LIENS:
            LienFamilial.objects.get_or_create(personne_a=self.b[a], personne_b=self.b[c], type_lien=type_lien,
                                               defaults={"vit_au_foyer": foyer, "est_responsable_legal": type_lien == "ENFANT",
                                                         "date_debut": self.j})
            LienFamilial.objects.get_or_create(personne_a=self.b[c], personne_b=self.b[a], type_lien=inverse[type_lien],
                                               defaults={"vit_au_foyer": foyer, "date_debut": self.j})
        self.stdout.write(f"✅ {len(FAMILLES)} familles fictives ajoutées")

    def parametres(self):
        """Textes de refus d'exemple si l'administration ne les a pas encore saisis (jamais écrasés)."""
        from AidFi.models.m_referentiel import MotifRefusAFASE
        exemples = {
            "1": "Votre demande ne comporte pas les justificatifs permettant d'évaluer vos ressources et vos charges.",
            "2": "Votre budget ne fait pas apparaître de difficulté justifiant une aide de l'aide sociale à l'enfance.",
            "3": "Votre demande relève d'un autre dispositif : je vous invite à solliciter {precision}.",
        }
        for code, texte in exemples.items():
            MotifRefusAFASE.objects.filter(code=code, texte_notification="").update(
                texte_notification=texte + " [texte d'exemple – à remplacer par celui de la note de service]")

    # ------------------------------------------------------------------ AFASE
    def _afase(self, code, statut, *, il_y_a=0, signature=None, ts=None, montant="150", duree=1, motif="1",
               lien="MERE", mesure="", avis="FAVORABLE", budget=None, nb=None, enfants_a_naitre=0, tiers_paiement=False):
        from AidFi.models import DemandeAFASE
        from AidFi.models.m_afase import BudgetAFASE, EnfantAFASE, EvaluationSocialeAFASE, nb_personnes_au_foyer
        from AidFi.services import budget_afase
        b = self.b[code]
        ts = ts or (self.ts2 if b.mds_id == self.mds2.pk else self.ts)
        cree = timezone.now() - timedelta(days=il_y_a)
        d = DemandeAFASE(beneficiaire=b, demandeur=b, type_aide=type_aide("AFASE"), type_aide_code="AFASE",
                         montant_sollicite=Decimal(montant), duree_demande=duree, statut="BROUILLON", cree_par=ts,
                         avis_ts=avis, lien_demandeur=lien, motif_envisage=motif, mesure_ase=mesure, qualite_ts="AS",
                         date_signature_demandeur=signature or (cree.date() if statut != "BROUILLON" else None),
                         allocataire_caf=True, situation_pro_demandeur="Sans emploi (fictif)",
                         aides_prealables_sollicitees=["CAF", "CCAS"] if motif == "1" else [],
                         premiere_demande=True)
        d._acteur = ts
        d.save()
        for e in [x for x in b.reseau_familial() if x["personne"].date_naissance and
                  (self.j - x["personne"].date_naissance).days < 21 * 365]:
            p = e["personne"]
            EnfantAFASE.objects.create(demande=d, beneficiaire=p, nom=p.nom, prenom=p.prenom,
                                       date_naissance=p.date_naissance, sexe="M" if p.civilite == "M." else "F",
                                       situation="Scolarisé(e)", concerne=True)
        for _ in range(enfants_a_naitre):
            EnfantAFASE.objects.create(demande=d, nom="XXX", date_naissance=self.j + timedelta(days=75), a_naitre=True)
        if statut != "BROUILLON":
            post = budget or {"r__rsa__demandeur": "650", "r__familiales__demandeur": "290", "r__logement__demandeur": "310",
                              "c__loyer__payee": "620", "c__electricite__payee": "85", "c__telephone__payee": "35",
                              "c__assurances__payee": "25", "c__electricite__non_payee": "160",
                              "d__0__creancier": "Fournisseur d'énergie (fictif)", "d__0__montant": "160"}
            r, c, dettes = budget_afase.depuis_post(post)
            BudgetAFASE.objects.create(demande=d, ressources=r, charges=c, dettes=dettes,
                                       nb_personnes_foyer=nb or nb_personnes_au_foyer(b) + enfants_a_naitre)
            if statut != "EN_INSTRUCTION":
                EvaluationSocialeAFASE.objects.create(
                    demande=d, code_instruction="4", situation_sociale="Situation fictive de démonstration.",
                    analyse_problematique="Dépenses imprévues ce mois-ci (données fictives).",
                    justification_demande="Aide ponctuelle pour l'alimentation des enfants (fictif).",
                    plan_action="Rendez-vous budget dans un mois ; dossier CAF à mettre à jour.", adhesion_famille="FORTE")
            # Pas de pièces : elles seraient sans fichier (« document supprimé »), et des fichiers fictifs
            # iraient remplir le stockage GED réel (pCloud sur Render). Les pièces exigées restent à joindre.
        if statut not in ("BROUILLON",):
            d.statut = "EN_INSTRUCTION"
            d.save(update_fields=["statut"])
        if statut not in ("BROUILLON", "EN_INSTRUCTION"):
            d.statut = "DEPOSEE"
            d.save(update_fields=["statut"])
        DemandeAFASE.objects.filter(pk=d.pk).update(date_creation=cree)
        d.refresh_from_db()
        return d

    def _decider(self, d, type_decision, *, code="1", montant=None, duree=None, il_y_a=0, precision="",
                 motivation="Décision fictive de démonstration.", paiement="FAMILLE", organisme="", par=None):
        from AidFi.models.m_afase import DecisionAFASE
        par = par or (self.cadre2 if d.beneficiaire.mds_id == self.mds2.pk else self.cadre)
        quand = timezone.now() - timedelta(days=il_y_a)
        dec = DecisionAFASE.objects.create(
            demande=d, type_decision=type_decision, code_decision="" if type_decision == "AJO" else code,
            montant_accorde=Decimal(montant if montant is not None else d.montant_sollicite) if type_decision == "ACCORD" else Decimal(0),
            duree_accordee=duree or d.duree_demande, motivation=motivation, precision_notification=precision,
            date_decision=quand, decide_par=par, paiement_a=paiement if type_decision == "ACCORD" else "",
            organisme_paiement=organisme)
        d.statut = {"ACCORD": "ACCORDEE", "REFUS": "REFUSEE", "AJO": "AJO"}[type_decision]
        d.date_ajournement = quand if type_decision == "AJO" else None
        d._acteur = par
        d.save(update_fields=["statut", "date_ajournement"])
        return dec

    def afase(self):
        from AidFi.models.m_recours import RecoursAFASE
        from AidFi.services import afase_recours
        J = self.j
        a = {}
        a["brouillon"] = self._afase("FAM4-NOL", "BROUILLON", lien="JEUNE_MAJEUR", montant="120")
        a["instruction"] = self._afase("FAM5-SAR", "EN_INSTRUCTION", lien="FEMME_ENCEINTE", enfants_a_naitre=1, montant="180")
        a["deposee"] = self._afase("FAM3-CLA", "DEPOSEE", il_y_a=3, montant="200", duree=2)
        a["deposee_j10"] = self._afase("FAM2-SOP", "DEPOSEE", il_y_a=45, signature=J - relativedelta(months=2) + timedelta(days=10))
        a["reputee_refusee"] = self._afase("API-JUL", "DEPOSEE", il_y_a=65, signature=J - relativedelta(months=2) - timedelta(days=5), lien="PERE")
        d = self._afase("FAM6-KEV", "DEPOSEE", il_y_a=8, lien="PERE")
        self._decider(d, "AJO", il_y_a=5, motivation="Avis d'imposition manquant.")
        d = self._afase("FAM1-JEA", "DEPOSEE", il_y_a=25, lien="PERE")
        self._decider(d, "AJO", il_y_a=20, motivation="Justificatifs de charges manquants.")
        d = self._afase("FAM7-NAD", "DEPOSEE", il_y_a=12, montant="250", duree=2)
        self._decider(d, "ACCORD", il_y_a=10)
        d = self._afase("FAM3-MAR", "DEPOSEE", il_y_a=70, lien="PERE", montant="180")
        dec = self._decider(d, "ACCORD", il_y_a=65)
        dec.date_transmission_controle, dec.transmis_par = timezone.now() - timedelta(days=60), self.cadre
        dec.save()
        d.statut = "TRANSMISE_CONTROLE"; d.save(update_fields=["statut"])
        d = self._afase("FAM2-PAU", "DEPOSEE", il_y_a=100, lien="PERE", motif="2", montant="95")
        dec = self._decider(d, "ACCORD", code="2", il_y_a=95, paiement="ORGANISME", organisme="Cantine scolaire de Port-de-Bouc (fictif)")
        dec.date_transmission_controle, dec.transmis_par = timezone.now() - timedelta(days=90), self.cadre
        dec.date_demande_paiement, dec.reference_comptable, dec.controle_par = J - timedelta(days=85), "EJ-DEMO-0001", self.uagaf
        dec.save()
        d.statut = "PAIEMENT_DEMANDE"; d.save(update_fields=["statut"])
        d = self._afase("FAM1-JEA", "DEPOSEE", il_y_a=130, lien="PERE", montant="160")
        dec = self._decider(d, "ACCORD", il_y_a=125)
        dec.date_transmission_controle, dec.transmis_par = timezone.now() - timedelta(days=120), self.cadre
        dec.date_demande_paiement, dec.reference_comptable, dec.controle_par = J - timedelta(days=115), "EJ-DEMO-0002", self.uagaf
        dec.date_envoi_regie, dec.date_delivrance, dec.montant_delivre = J - timedelta(days=112), J - timedelta(days=105), Decimal("160")
        dec.save()
        d.statut = "CLOTUREE"; d.save(update_fields=["statut"])
        d = self._afase("FAM7-KAR", "DEPOSEE", il_y_a=30, lien="PERE", montant="140")
        dec = self._decider(d, "ACCORD", il_y_a=28)
        dec.motif_renvoi, dec.controle_par = "RIB illisible : merci de joindre un RIB lisible (fictif).", self.uagaf
        dec.save()
        d = self._afase("API-FRA", "DEPOSEE", il_y_a=40, lien="JEUNE_MAJEUR", montant="300", motif="3")
        self._decider(d, "REFUS", code="3", il_y_a=35, precision="le Fonds d'aide aux jeunes", motivation="Relève du FAJ.")
        d = self._afase("FAM9-CEL", "DEPOSEE", il_y_a=60, montant="220")
        self._decider(d, "REFUS", code="2", il_y_a=55, motivation="Reste à vivre suffisant (fictif).")
        RecoursAFASE.objects.create(demande=d, type_recours="GRACIEUX", date_recours=J - timedelta(days=40),
                                    commentaire="Courrier reçu par la direction (fictif).", enregistre_par=self.cadre)
        d = self._afase("FAM10-YAS", "DEPOSEE", il_y_a=80, montant="150")
        self._decider(d, "REFUS", code="2", il_y_a=75)
        rc = RecoursAFASE.objects.create(demande=d, type_recours="GRACIEUX", date_recours=J - timedelta(days=60),
                                         issue="ACCORD", date_issue=J - timedelta(days=4), enregistre_par=self.cadre)
        afase_recours.creer_nouvelle_demande(rc, self.cadre)
        d = self._afase("FAM11-THO", "DEPOSEE", il_y_a=90, lien="PERE", montant="400", duree=3)
        self._decider(d, "REFUS", code="2", il_y_a=85)
        RecoursAFASE.objects.create(demande=d, type_recours="CONTENTIEUX", date_recours=J - timedelta(days=70),
                                    issue="REJET", date_issue=J - timedelta(days=15), enregistre_par=self.cadre)
        self._afase("FAM8-LAU", "DEPOSEE", il_y_a=6, mesure="ASSISTANCE_EDUCATIVE", montant="130")
        self.stdout.write("✅ AFASE : 18 dossiers, à tous les stades du circuit")

    # ------------------------------------------------------------------ CAP et régie
    def cap_regie(self):
        from AidFi.models import DemandeCAP, DemandeRegie
        self.coffre_cap()
        def base(model, code, statut, il_y_a, montant, **extra):
            b = self.b[code]
            obj = model(beneficiaire=b, demandeur=b, type_aide=type_aide("CAP" if model is DemandeCAP else "REGIE"),
                type_aide_code="CAP" if model is DemandeCAP else "REGIE", montant_sollicite=Decimal(montant),
                statut="DEPOSEE", cree_par=self.ts, motivation="Besoin alimentaire immédiat (fictif).", **extra)
            obj._acteur = self.ts
            obj.save()
            model.objects.filter(pk=obj.pk).update(date_creation=timezone.now() - timedelta(days=il_y_a))
            obj.refresh_from_db()
            return obj
        base(DemandeCAP, "FAM12-AUR", "DEPOSEE", 1, "60")
        c = base(DemandeCAP, "FAM4-NOL", "ACCORDEE", 4, "40")
        c.statut, c.montant_accorde, c.decide_par, c.date_decision = "ACCORDEE", 40, self.cadre, timezone.now() - timedelta(days=3)
        c._acteur = self.cadre; c.save()
        c = base(DemandeCAP, "FAM11-THO", "REFUSEE", 20, "80")
        c.statut, c.decide_par, c.date_decision, c.motif_refus = "REFUSEE", self.cadre, timezone.now() - timedelta(days=19), "Aide déjà accordée ce mois-ci (fictif)."
        c._acteur = self.cadre; c.save()
        base(DemandeRegie, "FAM5-SAR", "DEPOSEE", 0, "50", mode_paiement="ESPECES")
        r = base(DemandeRegie, "FAM9-CEL", "TRANSMISE_PAIERIE", 2, "75", mode_paiement="TIERS",
                 tiers_nom="Pharmacie du Port (fictif)", tiers_reference="Facture F-DEMO-12")
        r.statut, r.montant_accorde, r.decide_par, r.date_decision = "TRANSMISE_PAIERIE", Decimal("75"), self.cadre, timezone.now() - timedelta(days=1)
        r._acteur = self.cadre; r.save()
        r = base(DemandeRegie, "FAM10-YAS", "CLOTUREE", 15, "40", mode_paiement="ESPECES")
        r.statut, r.montant_accorde, r.decide_par, r.date_decision = "CLOTUREE", Decimal("40"), self.cadre, timezone.now() - timedelta(days=14)
        r.date_versement, r.montant_verse, r.verse_par = timezone.now() - timedelta(days=13), Decimal("40"), self.regie
        r._acteur = self.regie; r.save()
        self.stdout.write("✅ Chèques service (3) et régie d'urgence (3)")

    def coffre_cap(self):
        """Régisseur (Agent Admin 1) et stock fictif de chèques au coffre de la MDS TEST 01 : 480 €."""
        from AidFi.models.m_cap import ReceptionCAP, TitreCAP
        if not self.mds1.regisseur_id:
            self.mds1.regisseur = self.u("MarioB")
            self.mds1.save(update_fields=["regisseur"])
        reception = ReceptionCAP.objects.create(
            mds=self.mds1, regisseur=self.mds1.regisseur, date_reception=self.j - timedelta(days=20),
            date_validite=self.j + relativedelta(years=1), reference="BORD-DEMO", saisie_terminee=True,
            commentaire="Réception fictive de démonstration (init_demo).")
        for valeur, nombre in ((10, 10), (20, 10), (30, 6)):
            for i in range(1, nombre + 1):
                TitreCAP.objects.create(numero=f"DEMO-{valeur}-{i:04d}", valeur=valeur, reception=reception,
                                        mds=self.mds1, date_validite=reception.date_validite)
        self.stdout.write("✅ Coffre CAP : régisseur Agent Admin 1, 26 chèques fictifs (480 €)")

    # ------------------------------------------------------------------ IP
    def ip(self):
        from protection_enfance.models import EnfantIP, InformationPreoccupante, TypeDanger
        from protection_enfance.services import ip_circuit, ip_convocations
        from protection_enfance.services.ip_famille import completer_depuis_dossier
        def creer(code, il_y_a, origine, description, enfants, urgence="COURANTE"):
            famille = self.b[code]
            ip = InformationPreoccupante.objects.create(
                date_reception_crip=self.j - timedelta(days=il_y_a), recue_par=self.crip, cree_par=self.crip,
                origine=origine, niveau_urgence=urgence, famille=famille, mds=famille.mds, description=description,
                signalant_qualite="Professionnel (fictif)", signalant_nom="Exemple")
            for c in enfants:
                e = self.b[c]
                EnfantIP.objects.create(ip=ip, beneficiaire=e, nom=e.nom, prenom=e.prenom, date_naissance=e.date_naissance)
            completer_depuis_dossier(ip)
            return ip
        creer("FAM11-THO", 1, "NUM_119", "Appel au 119 : adolescente souvent seule le soir (fictif).", ["FAM11-JUS"])
        ip = creer("FAM8-LAU", 30, "MDS", "Inquiétudes de l'équipe sur le suivi médical de Mila (fictif).",
                   ["FAM8-MIL", "FAM8-NOE"], urgence="RAPIDE")
        ip_circuit.transmettre_mds(ip, self.crip)
        ip_circuit.designer_binome(ip, self.ts, self.pmi, self.cadre)
        parents = list(ip.adultes.all())
        if parents:
            ip_convocations.programmer_audition(ip, self.ts, "AUDITION_PARENTS", timezone.now() + timedelta(days=6), 60,
                                                adultes=parents, agenda=True)
        ip = creer("FAM12-AUR", 75, "EDUCATION", "Absences répétées de Gabriel signalées par l'école (fictif).",
                   ["FAM12-GAB", "FAM12-LIN"])
        ip_circuit.transmettre_mds(ip, self.crip)
        ip_circuit.designer_binome(ip, self.ts, self.ts_b, self.cadre)
        rapport = ip_circuit.rapport_de(ip)
        rapport.composition_familiale = "Couple et deux enfants (fictif)."
        rapport.analyse = "Fatigue scolaire liée à des difficultés d'organisation familiale (fictif)."
        rapport.preconisation = "DROIT_COMMUN"
        rapport.preconisation_detail = "Accompagnement social de droit commun et lien avec l'école."
        rapport.save()
        danger = TypeDanger.objects.filter(code="scolarite").first()
        for e in ip.enfants.all():
            e.conclusion = "RISQUE" if e.prenom == "Gabriel" else "PAS_DANGER"
            e.save()
            if e.conclusion == "RISQUE" and danger:
                e.dangers_constates.add(danger)
        ip_circuit.soumettre_rapport(ip, self.ts)
        self.stdout.write("✅ IP : reçue à la CRIP, en évaluation (convocation prévue), en synthèse "
                          "(+ l'IP d'init2 transmise à la MDS)")

    # ------------------------------------------------------------------ RSA – insertion
    def insertion(self):
        from django.core.management import call_command
        from insertion.models import ActionInsertion, PoleInsertion, TypeActionInsertion
        call_command("init_insertion", stdout=StringIO())
        pole, _ = PoleInsertion.objects.get_or_create(code="PI-DEMO", defaults={
            "nom": "Pôle insertion de démonstration", "adresse": "1 rue de l'Exemple", "code_postal": "13000",
            "ville": "Exemple", "telephone": "0400000000", "email": "pole.insertion@exemple.fr"})
        pole.mds.add(self.mds1, self.mds2)
        pole.membres.add(*[self.u(c) for c in ("pi_admin", "pi_cadre", "pi_medecin")])
        for code, libelle, type_code, niveau, mds, porteur, duree, rythme in ACTIONS_DEMO:
            a, _ = ActionInsertion.objects.update_or_create(code=code, mds=self.mds1 if mds else None, defaults={
                "libelle": libelle, "type_action": TypeActionInsertion.objects.get(code=type_code), "niveau": niveau,
                "porteur": porteur, "duree": duree, "comite_suivi": bool(rythme), "rythme_comite": rythme,
                "public_vise": "Bénéficiaires du RSA (fictif)", "destinataires": "prescription@exemple.fr",
                "pieces_a_joindre": "Attestation CAF de moins d'un mois", "aussi_logement": type_code == "logement",
                "description": "Action fictive du jeu de démonstration."})
            if niveau == "DEPARTEMENTAL" and code == "DEMO-MOBIL":
                a.poles.set([pole])
        self.stdout.write(f"✅ Insertion : pôle de démonstration (pi_admin, pi_cadre, pi_medecin), {len(ACTIONS_DEMO)} actions fictives")

    # ------------------------------------------------------------------ planning
    def planning(self):
        from mds.models import MDSReception
        from planning.models import CreneauRdv
        salle = MDSReception.objects.filter(mds=self.mds1, type_salle="BUREAU").first()
        jour = self.j
        while jour.weekday() >= 5:
            jour += timedelta(days=1)
        for h, code, statut in [(9, "FAM9-CEL", "RESERVE"), (10, "FAM5-SAR", "RESERVE"), (11, None, "DISPONIBLE"),
                                (14, "FAM4-NOL", "RESERVE"), (15, None, "DISPONIBLE")]:
            CreneauRdv.objects.get_or_create(
                date=jour, heure_debut=time(h), agent=self.ts, defaults={
                    "heure_fin": time(h, 45), "duree_minutes": 45, "salle": salle, "mds": self.mds1,
                    "beneficiaire": self.b.get(code) if code else None, "statut": statut, "type_rdv": "PERMANENCE",
                    "nature": "PERMANENCE", "domaine": "SOCIAL", "notes_internes": "[démo] rendez-vous fictif",
                    "cree_par": self.ts, "reserve_par": self.u("MarioB") if code else None,
                    "date_reservation": timezone.now() if code else None})
        # Une semaine plus tard : créneaux libres pour « Prendre rendez-vous » (recherche de J+2 à J+17)
        semaine = jour + timedelta(days=7)
        for h in (9, 10, 11, 14, 15):
            CreneauRdv.objects.get_or_create(
                date=semaine, heure_debut=time(h), agent=self.ts, defaults={
                    "heure_fin": time(h, 45), "duree_minutes": 45, "salle": salle, "mds": self.mds1,
                    "statut": "DISPONIBLE", "type_rdv": "PERMANENCE", "nature": "PERMANENCE", "domaine": "SOCIAL",
                    "notes_internes": "[démo] créneau fictif", "cree_par": self.ts})
        self.stdout.write(f"✅ Planning : permanences d'Agent Social 1 le {jour:%d/%m/%Y} et le {semaine:%d/%m/%Y}")
