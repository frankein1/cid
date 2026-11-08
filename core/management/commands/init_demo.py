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
    ("chef_mds2", "Cadre", "MDS 2", "MDS_RESPONSABLE", "MDSTEST2"),
    ("as1_mds2", "Agent Social", "MDS 2", "MDS_AGENTS_SOCIAUX", "MDSTEST2"),
    ("uagaf_u1", "Agent", "UAGAF 1", "SERVICE_CONTROLE_AFASE", None),
    ("regie_r1", "Régisseur", "Central 1", "REGISSEUR_CENTRAL", None),
    ("admin_pi1", "Agent", "Pôle insertion", "POLE_INSERTION_ADMINISTRATIF", None),
    ("cadre_pi1", "Cadre", "Pôle insertion", "POLE_INSERTION_CADRE", None),
    ("medecin_pi1", "Médecin", "Pôle insertion", "POLE_INSERTION_MEDECIN", None),
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
# Archivage RGPD : dossiers fictifs sans activité depuis longtemps (code, civilité, nom, prénom, âge,
# inactif depuis N mois, archivé depuis N mois ou None)
RGPD_DEMO = [("RGPD1-HUG", "M.", "FERRAND", "Hugo", 44, 40, None),
             ("RGPD2-YAS", "MME", "OUALI", "Yasmine", 31, 52, None),
             ("RGPD3-ODI", "MME", "MARCHETTI", "Odile", 67, 60, 14)]
CODES_DEMO = ["FAM1-JEA", "FAM2-SOP", "FAM2-PAU", "FAM3-CLA", "FAM3-MAR", "API-JUL", "API-FRA"] + \
             [f"{f}-{p[0]}" for f, ps in FAMILLES.items() for p in ps] + [r[0] for r in RGPD_DEMO]


def type_aide(code):
    from AidFi.models.m_generique import TypeAide
    noms = {"AFASE": "Aide Financière ASE", "CAP": "Chèque d'Accompagnement Personnalisé", "REGIE": "Régie d'urgence"}
    return TypeAide.objects.get_or_create(code=code, defaults={"nom": noms[code], "actif": True})[0]


def mot_de_passe():
    return os.environ.get("DEMO_PASSWORD") or "demo123&"


# Comptes de démonstration (init2 et init_demo) : mot de passe remis à mot_de_passe() à chaque création ou
# réinitialisation du jeu. Jamais un super-administrateur.
# Anciens identifiants des comptes de démonstration → identifiants explicites (rôle_structure). Un compte existant
# est renommé (ses dossiers, messages, rendez-vous le suivent) au lieu d'être recréé : pas de doublon.
RENOMMAGES = {"kchef": "chef_mds1", "jcadre1": "cadre_mds1", "asmith": "as1_mds1", "bjones": "as2_mds1",
              "cdubois": "as3_mds1", "MarioB": "aa1_mds1", "LuigiB": "aa2_mds1", "pmi1": "pmi_mds1",
              "cadre2": "chef_mds2", "ts2": "as1_mds2", "crip1": "crip_c1", "pief1": "ief_p1", "uagaf1": "uagaf_u1",
              "regie1": "regie_r1", "pi_admin": "admin_pi1", "pi_cadre": "cadre_pi1", "pi_medecin": "medecin_pi1"}


def renommer_comptes_demo():
    for ancien, nouveau in RENOMMAGES.items():
        u = User.objects.filter(username=ancien, is_superuser=False).first()
        if u and not User.objects.filter(username=nouveau).exists():
            u.username = nouveau
            u.save(update_fields=["username"])


def _effacer_envois(qs):
    """Supprime des dossiers de démonstration avec leurs envois (le compteur de papier ne garde pas de doublons)."""
    from django.contrib.contenttypes.models import ContentType
    from logement.models import EnvoiDossier
    EnvoiDossier.objects.filter(content_type=ContentType.objects.get_for_model(qs.model),
                                object_id__in=list(qs.values_list('pk', flat=True))).delete()
    qs.delete()


def organiser_mds_demo():
    """MDS TEST 01 = MDS de territoire (directeur : chef_mds1, adjoint prévention : cadre_mds1) ;
    MDS TEST 02 = MDS de proximité rattachée à MDS TEST 01 (cadre de proximité : chef_mds2).
    Rejouable : corrige aussi un jeu déjà en place (ancien libellé « Chef de service (propriétaire) »)."""
    from mds.models import MDS, UserMDSProfile
    mds1 = MDS.objects.filter(code_mds="MDSTEST1").first()
    mds2 = MDS.objects.filter(code_mds="MDSTEST2").first()
    if not mds1:
        return
    if mds1.type_mds != MDS.TERRITOIRE or mds1.mds_territoire_id:
        mds1.type_mds, mds1.mds_territoire = MDS.TERRITOIRE, None
        mds1.save()
    if mds2 and (mds2.type_mds != MDS.PROXIMITE or mds2.mds_territoire_id != mds1.pk):
        mds2.type_mds, mds2.mds_territoire = MDS.PROXIMITE, mds1
        mds2.save()
    User.objects.filter(username="chef_mds1", last_name__contains="propriétaire").update(
        first_name="Responsable", last_name="MDS 1")
    for username, mds, fonction in (("chef_mds1", mds1, UserMDSProfile.DIRECTEUR),
                                    ("cadre_mds1", mds1, UserMDSProfile.ADJOINT_PREVENTION),
                                    ("chef_mds2", mds2, UserMDSProfile.CADRE_PROXIMITE)):
        ump = UserMDSProfile.objects.filter(user__username=username, mds=mds, herite_de__isnull=True).first() if mds else None
        if ump and (ump.fonction != fonction or ump.role_specifique in ("", "Chef de service")):
            ump.fonction, ump.role_specifique = fonction, ""
            ump.save()   # l'intitulé est proposé d'après la fonction ; les accès du CODIR suivent
    # équipe IP de MDS TEST 01 (fictive), désignée par le cadre : as2_mds1 et l'agent PMI
    UserMDSProfile.objects.filter(mds=mds1, herite_de__isnull=True,
                                  user__username__in=["as2_mds1", "pmi_mds1"]).update(equipe_ip=True)


COMPTES_INIT2 = ["as1_mds1", "as2_mds1", "as3_mds1", "aa1_mds1", "aa2_mds1", "cadre_mds1", "chef_mds1", "pmi_mds1", "crip_c1", "ief_p1"]


class Command(BaseCommand):
    help = "Crée le jeu de données fictives de démonstration et de test (voir docs/DONNEES_FICTIVES.md)."

    def add_arguments(self, parser):
        parser.add_argument("--reinitialiser", action="store_true",
                            help="Supprime les dossiers de démonstration (aides, IP, rendez-vous) puis les recrée.")

    def handle(self, *args, **opts):
        from beneficiaire.models import Beneficiaire
        renommer_comptes_demo()
        if not Beneficiaire.tous.filter(code_interne="FAM1-JEA").exists():
            call_command("init2")
        organiser_mds_demo()
        if opts["reinitialiser"]:
            self.supprimer()
        elif Beneficiaire.tous.filter(code_interne=MARQUEUR).exists():
            self.stdout.write("📌 Jeu de démonstration déjà présent (--reinitialiser pour le recréer).")
            return
        with transaction.atomic():
            self.j = timezone.localdate()
            self.structures()
            self.familles()
            self.referents()
            self.parametres()
            self.afase()
            self.cap_regie()
            self.ip()
            self.planning()
            self.ateliers()
            self.budgets()
            self.logement()
            self.journal()
            from core.demo_presentation import creer as presentation
            presentation(self)
            self.insertion()
            self.rgpd()
        self.stdout.write(self.style.SUCCESS("🎉 Jeu de données fictives créé (voir docs/DONNEES_FICTIVES.md)."))

    # ------------------------------------------------------------------ archivage RGPD
    def rgpd(self):
        """Deux dossiers inactifs (proposés à l'archivage) et un dossier archivé depuis 14 mois (effaçable)."""
        from beneficiaire.models import Beneficiaire, OperationRGPD
        maintenant = timezone.now()
        for code, civ, nom, prenom, age, inactif_mois, archive_mois in RGPD_DEMO:
            ancien = maintenant - relativedelta(months=inactif_mois)
            b, _ = Beneficiaire.tous.get_or_create(code_interne=code, defaults={
                "civilite": civ, "nom": nom, "prenom": prenom, "date_naissance": self.j - relativedelta(years=age),
                "adresse": "5 rue des Mimosas", "code_postal": "13110", "ville": "Port-de-Bouc", "mds": self.mds1,
                "statut": "ACTIF", "cree_par": self.ts})
            champs = {"date_creation": ancien, "date_modification": ancien}   # update() : sans auto_now
            if archive_mois:
                champs.update(statut="ARCHIVE", statut_avant_archivage="ACTIF", motif_archivage="SANS_NOUVELLES",
                              date_archivage=maintenant - relativedelta(months=archive_mois), archive_par=self.cadre)
            Beneficiaire.tous.filter(pk=b.pk).update(**champs)
            if archive_mois and not b.operations_rgpd.exists():
                op = OperationRGPD.objects.create(beneficiaire=b, action=OperationRGPD.ARCHIVAGE,
                                                  motif="SANS_NOUVELLES", mds=self.mds1, par=self.cadre,
                                                  derniere_activite=ancien.date())
                OperationRGPD.objects.filter(pk=op.pk).update(date=maintenant - relativedelta(months=archive_mois))
        self.stdout.write("✅ Archivage RGPD : 2 dossiers inactifs, 1 dossier archivé (fictifs)")

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
        benefs = Beneficiaire.tous.filter(code_interne__in=CODES_DEMO)
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
        from insertion.models import ContratInsertion
        contrats = list(ContratInsertion.objects.filter(beneficiaire__in=benefs).values_list("pk", flat=True))
        Message.objects.filter(content_type=ContentType.objects.get_for_model(ContratInsertion),
                               object_id__in=contrats).delete()
        from insertion.models import DemandeReorientation
        reorientations = list(DemandeReorientation.objects.filter(beneficiaire__in=benefs).values_list("pk", flat=True))
        Message.objects.filter(content_type=ContentType.objects.get_for_model(DemandeReorientation),
                               object_id__in=reorientations).delete()
        DemandeReorientation.objects.filter(pk__in=reorientations).delete()
        from insertion.models import PrescriptionInsertion
        prescriptions = list(PrescriptionInsertion.objects.filter(beneficiaire__in=benefs).values_list("pk", flat=True))
        Message.objects.filter(content_type=ContentType.objects.get_for_model(PrescriptionInsertion),
                               object_id__in=prescriptions).delete()
        PrescriptionInsertion.objects.filter(pk__in=prescriptions).delete()
        ContratInsertion.objects.filter(pk__in=contrats).delete()
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
            self.mds2.responsable = self.u("chef_mds2")
            self.mds2.save(update_fields=["responsable"])
        organiser_mds_demo()
        self.ts, self.ts_b, self.cadre, self.cadre2 = self.u("as1_mds1"), self.u("as2_mds1"), self.u("chef_mds1"), self.u("chef_mds2")
        self.ts2, self.uagaf, self.regie = self.u("as1_mds2"), self.u("uagaf_u1"), self.u("regie_r1")
        self.pief, self.crip, self.pmi = self.u("ief_p1"), self.u("crip_c1"), self.u("pmi_mds1")
        self.stdout.write("✅ Comptes et MDS de démonstration")

    # ------------------------------------------------------------------ familles
    def familles(self):
        from beneficiaire.models import Beneficiaire, LienFamilial
        self.b = {c: Beneficiaire.tous.get(code_interne=c) for c in
                  ["FAM1-JEA", "FAM2-SOP", "FAM2-PAU", "FAM3-CLA", "FAM3-MAR", "API-JUL", "API-FRA"]}
        rues = iter(["8 rue des Oliviers", "14 boulevard de la Mer", "3 impasse des Pins", "27 avenue du Port",
                     "9 rue Jean Moulin", "2 allée des Tamaris", "41 chemin des Salins", "6 place de la Liberté",
                     "18 rue des Écoles"])
        for fam, personnes in FAMILLES.items():
            adresse = next(rues)
            for suffixe, civ, nom, prenom, age, n_mds, cp, ville, statut_marital in personnes:
                code = f"{fam}-{suffixe}"
                naissance = self.j - relativedelta(years=age, days=37 * (len(prenom) + age % 7))
                self.b[code], _ = Beneficiaire.tous.get_or_create(code_interne=code, defaults={
                    "civilite": civ, "nom": nom, "prenom": prenom, "date_naissance": naissance,
                    "adresse": "12 rue du Rhône" if cp == "84000" else (adresse if n_mds == 1 else "11 rue des Lices"),
                    "code_postal": cp, "ville": ville, "mds": self.mds1 if n_mds == 1 else self.mds2,
                    "statut": "ACTIF", "marital_status": statut_marital, "cree_par": self.ts})
        # Enfants de moins de 6 ans suivis par la PMI : numéro de dossier fictif (le suivi médical reste hors de CID)
        for code, numero in [("FAM8-MIL", "PMI-DEMO-0001"), ("FAM10-ADA", "PMI-DEMO-0002")]:
            Beneficiaire.tous.filter(code_interne=code).update(numero_dossier_pmi=numero)
        # Points d'attention (bandeau en haut de la fiche)
        Beneficiaire.tous.filter(code_interne="FAM12-AUR").update(vff=True)
        Beneficiaire.tous.filter(code_interne="FAM4-NOL").update(rupture_familiale=True)
        Beneficiaire.tous.filter(code_interne="FAM9-CEL").update(personne_vulnerable=True)
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
            self.mds1.regisseur = self.u("aa1_mds1")
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

    # ------------------------------------------------------------------ référents
    def referents(self):
        """Chaque famille a son AS référente. FAM8 et FAM12 (IP en cours) sont suivies par Agent Social 3, FAM11 (IP
        reçue, binôme à désigner) par Agent Social 1 : la proposition de binôme ne les propose pas."""
        from beneficiaire.models import Beneficiaire
        as_mds1 = [self.u(f"as{i}_mds1") for i in (1, 2, 3)]
        particuliers = {"FAM8": self.u("as3_mds1"), "FAM12": self.u("as3_mds1"), "FAM11": self.u("as1_mds1")}
        n = 0
        for b in Beneficiaire.tous.filter(code_interne__in=CODES_DEMO).order_by("code_interne"):
            famille = b.code_interne.split("-")[0]
            if b.mds_id == self.mds1.pk:
                chiffres = "".join(c for c in famille if c.isdigit())
                b.referent_mds = particuliers.get(famille) or as_mds1[int(chiffres or 0) % 3]
            elif b.mds_id == self.mds2.pk:
                b.referent_mds = self.u("as1_mds2")
            else:
                continue
            b.save(update_fields=["referent_mds"])
            n += 1
        self.stdout.write(f"✅ Référents MDS attribués ({n} personnes)")

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
        # Agent Social 1 a instruit l'AFASE de la famille (non recommandé) : le cadre confirme, faute de personnel
        ip_circuit.designer_binome(ip, self.ts, self.pmi, self.cadre, forcer=True,
                                   motif="Sous-effectif de l'équipe IP ce mois-ci (fictif).")
        parents = list(ip.adultes.all())
        if parents:
            ip_convocations.programmer_audition(ip, self.ts, "AUDITION_PARENTS", timezone.now() + timedelta(days=6), 60,
                                                adultes=parents, agenda=True)
        ip = creer("FAM12-AUR", 75, "EDUCATION", "Absences répétées de Gabriel signalées par l'école (fictif).",
                   ["FAM12-GAB", "FAM12-LIN"])
        ip_circuit.transmettre_mds(ip, self.crip)
        # Agent Social 1 (aide d'urgence) et Agent Social 3 (référente) suivent la famille : binôme sans eux
        ip_circuit.designer_binome(ip, self.ts_b, self.pmi, self.cadre)
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
        ip_circuit.soumettre_rapport(ip, self.ts_b)
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
        pole.membres.add(*[self.u(c) for c in ("admin_pi1", "cadre_pi1", "medecin_pi1")])
        for code, libelle, type_code, niveau, mds, porteur, duree, rythme in ACTIONS_DEMO:
            a, _ = ActionInsertion.objects.update_or_create(code=code, mds=self.mds1 if mds else None, defaults={
                "libelle": libelle, "type_action": TypeActionInsertion.objects.get(code=type_code), "niveau": niveau,
                "porteur": porteur, "duree": duree, "comite_suivi": bool(rythme), "rythme_comite": rythme,
                "public_vise": "Bénéficiaires du RSA (fictif)", "destinataires": "prescription@exemple.fr",
                "pieces_a_joindre": "Attestation CAF de moins d'un mois", "aussi_logement": type_code == "logement",
                "description": "Action fictive du jeu de démonstration."})
            if niveau == "DEPARTEMENTAL" and code == "DEMO-MOBIL":
                a.poles.set([pole])
        self.questions_actions()
        self.stdout.write(f"✅ Insertion : pôle de démonstration (admin_pi1, cadre_pi1, medecin_pi1), {len(ACTIONS_DEMO)} actions fictives")
        self.contrats(pole)

    def contrats(self, pole):
        """Contrats fictifs à chaque étape du circuit (référente : Agent Social 1). Voir docs/INSERTION.md."""
        from insertion.models import ActionInsertion, ContratInsertion as C, LigneActionContrat
        from insertion.services import contrat_circuit as circuit
        j = self.j
        actions = {a.code: a for a in ActionInsertion.objects.filter(code__startswith="DEMO-")}
        cadre, admin, medecin = self.u("cadre_pi1"), self.u("admin_pi1"), self.u("medecin_pi1")

        def contrat(code, nature, il_y_a, objectifs, codes_actions, **champs):
            c = circuit.creer(self.b[code], self.ts)
            c.nature, c.date_etablissement = nature, j - timedelta(days=il_y_a)
            c.date_signature, c.accord_allocataire, c.engagement_renouvellement = c.date_etablissement, True, True
            c.parole_situation = "Situation décrite avec le bénéficiaire (fictif)."
            c.parole_souhaits = "Souhaits exprimés par le bénéficiaire (fictif)."
            c.objectifs, c.etapes = objectifs, "1. Premier rendez-vous avec le porteur.\n2. Point d'étape à mi-parcours."
            for k, v in champs.items():
                setattr(c, k, v)
            c.save()
            for code_action in codes_actions:
                LigneActionContrat.objects.create(contrat=c, action=actions[code_action], date_entree=c.date_etablissement)
            return c

        def valider(c, il_y_a, mois, decision=C.VALIDE, non_retenues=None):
            circuit.transmettre(c, self.ts)
            circuit.receptionner(c, admin)
            debut = j - timedelta(days=il_y_a)
            circuit.decider(c, cadre, decision=decision, date_decision=debut, date_debut=debut, duree_mois=mois,
                            decision_transport='OUI' if c.aide_transport_urbain else '',
                            non_retenues=non_retenues)
            C.objects.filter(pk=c.pk).update(date_transmission=debut - timedelta(days=12),
                                            date_reception=debut - timedelta(days=10))

        # Validé, échéance dans 20 jours : à renouveler
        sarah = contrat("FAM5-SAR", "EMPLOI", 200, "Retrouver un emploi dans la vente (fictif).", ["DEMO-ACCGLO"],
                        niveau_etudes="N4", emploi_recherche="Vendeuse (fictif)", permis_b=True,
                        aide_transport_urbain=True, inscrit_france_travail=True)
        valider(sarah, 163, 6)   # fin = début + 6 mois - 1 jour, soit environ dans 20 jours
        # Validé, échu depuis une dizaine de jours, sans contrat suivant
        kevin = contrat("FAM6-KEV", "SOCIAL", 200, "Stabiliser la situation administrative (fictif).", ["DEMO-MOBIL"])
        valider(kevin, 193, 6)
        # Validé sauf action, en vigueur
        thomas = contrat("FAM11-THO", "SOCIAL", 45, "Reprendre confiance et préparer un projet (fictif).",
                         ["DEMO-CISF", "DEMO-BRICO"])
        ligne = thomas.lignes.get(action__code="DEMO-BRICO")
        valider(thomas, 30, 3, C.VALIDE_SAUF_ACTION, {ligne.pk: "Action réservée au public logement (fictif)"})
        # Ajourné : de nouveau modifiable par la référente
        aurelie = contrat("FAM12-AUR", "LOGEMENT", 25, "Accéder à un logement adapté (fictif).", ["DEMO-BRICO"],
                          logement="HEBERGE")
        circuit.transmettre(aurelie, self.ts)
        circuit.receptionner(aurelie, admin)
        circuit.decider(aurelie, cadre, decision=C.AJOURNE, date_decision=j - timedelta(days=5),
                        motif="Objectifs à préciser avec la bénéficiaire (fictif).")
        # Reçu au pôle, en attente de la commission
        nadia = contrat("FAM7-NAD", "SOCIAL", 12, "Organiser la garde d'enfants pour suivre une formation (fictif).",
                        ["DEMO-ACCGLO", "DEMO-CISF"], incidence_formation=True)
        circuit.transmettre(nadia, self.ts)
        circuit.receptionner(nadia, admin)
        # Contrat santé transmis : à réceptionner, puis avis du médecin du pôle
        celine = contrat("FAM9-CEL", "SANTE", 6, "Engager un parcours de soins avant un retour à l'emploi (fictif).",
                         ["DEMO-SANTE"], certificat_mode="PLI", certificat_demande_le=j - timedelta(days=6))
        circuit.transmettre(celine, self.ts)
        # En préparation
        contrat("FAM8-LAU", "EMPLOI", 2, "", [], date_signature=None, accord_allocataire=False)
        self.stdout.write("✅ Contrats RSA : en préparation, transmis (santé), reçu, ajourné, validé sauf action, "
                          "à renouveler, échu")
        self.prescriptions()
        self.reorientations(pole)

    def questions_actions(self):
        """Questions propres aux actions fictives, validation par le pôle, pièces à joindre."""
        from insertion.models import ActionInsertion, QuestionAction as Q
        a = {x.code: x for x in ActionInsertion.objects.filter(code__startswith="DEMO-")}
        ActionInsertion.objects.filter(pk=a["DEMO-ACCGLO"].pk).update(
            pieces_a_joindre="Attestation CAF de moins d'un mois\nCV")
        ActionInsertion.objects.filter(pk=a["DEMO-SANTE"].pk).update(validation_pole=True)
        Q.objects.filter(action__in=a.values()).delete()
        Q.objects.create(action=a["DEMO-MOBIL"], ordre=1, libelle="Permis de conduire", type_reponse=Q.CHOIX,
                         choix="Aucun\nCode en cours\nPermis B\nPermis suspendu ou annulé", obligatoire=True)
        Q.objects.create(action=a["DEMO-MOBIL"], ordre=2, libelle="Besoins de mobilité", type_reponse=Q.CHOIX_MULTIPLE,
                         choix="Aide au permis\nLocation de véhicule\nDeux-roues\nTransports en commun")
        Q.objects.create(action=a["DEMO-SANTE"], ordre=1, type_reponse=Q.OUI_NON, obligatoire=True, restreinte=True,
                         libelle="Grille d'aide à la décision santé remplie avec la personne",
                         aide="La grille reste dans le dossier papier ; aucun détail médical ici.")
        Q.objects.create(action=a["DEMO-CISF"], ordre=1, libelle="Besoin d'un mode de garde pendant l'atelier",
                         type_reponse=Q.OUI_NON, obligatoire=True)
        Q.objects.create(action=a["DEMO-CISF"], ordre=2, libelle="Nombre d'enfants à faire garder",
                         type_reponse=Q.NOMBRE)

    def prescriptions(self):
        """Prescriptions fictives à chaque étape, rattachées aux contrats de démonstration."""
        from insertion.models import ActionInsertion, PrescriptionInsertion as P
        from insertion.services import prescription_circuit as circuit
        j = self.j
        a = {x.code: x for x in ActionInsertion.objects.filter(code__startswith="DEMO-")}
        admin = self.u("admin_pi1")

        def presc(code, action, il_y_a, reponses=None, **champs):
            p = circuit.creer(self.b[code], self.ts, a[action])
            p.consentement, p.date_signature = True, j - timedelta(days=il_y_a)
            p.objectifs = p.objectifs or "Objectifs travaillés avec la personne (fictif)."
            p.diagnostic = "Diagnostic partagé avec la personne (fictif)."
            p.avis_motive = "Action adaptée au projet de la personne (fictif)."
            p.situation_rsa = "SOCLE"
            for k, v in champs.items():
                setattr(p, k, v)
            p.save()
            if reponses:
                questions = {q.libelle: q.pk for q in a[action].questions.all()}
                circuit.enregistrer_reponses(p, {questions[k]: v for k, v in reponses.items()})
            return p

        def dater(p, il_y_a):
            P.objects.filter(pk=p.pk).update(date_prescription=j - timedelta(days=il_y_a),
                                             date_envoi=j - timedelta(days=il_y_a - 1))

        # Intégrée, en cours (Sarah, accompagnement global) : la ligne du contrat suit
        sarah = presc("FAM5-SAR", "DEMO-ACCGLO", 160, freins=["GARDE", "RECHERCHE_EMPLOI"],
                      pieces_fournies=["Attestation CAF de moins d'un mois", "CV"], inscrit_france_travail=True)
        circuit.adresser(sarah, self.ts)
        circuit.noter_retour(sarah, admin, issue=P.INTEGREE, premier_rdv_le=j - timedelta(days=150),
                             premier_rdv_issue="PRESENT", diagnostic_finalise=True, date_entree=j - timedelta(days=145))
        dater(sarah, 160)
        # Terminée (Kevin, plateforme mobilité)
        kevin = presc("FAM6-KEV", "DEMO-MOBIL", 190, {"Permis de conduire": "Code en cours",
                                                     "Besoins de mobilité": "Aide au permis"}, freins=["MOBILITE"])
        circuit.adresser(kevin, self.ts)
        circuit.noter_retour(kevin, self.ts, issue=P.INTEGREE, premier_rdv_le=j - timedelta(days=180),
                             premier_rdv_issue="PRESENT", date_entree=j - timedelta(days=175))
        circuit.noter_retour(kevin, self.ts, issue=P.TERMINEE, date_sortie=j - timedelta(days=20),
                             motif_sortie="Permis obtenu (fictif)")
        dater(kevin, 190)
        # Intégrée, en cours (Thomas, atelier ; son autre action n'a pas été retenue par la commission)
        thomas = presc("FAM11-THO", "DEMO-CISF", 40, {"Besoin d'un mode de garde pendant l'atelier": "non"},
                       freins=["ISOLEMENT"])
        circuit.adresser(thomas, self.ts)
        circuit.noter_retour(thomas, self.ts, issue=P.INTEGREE, premier_rdv_le=j - timedelta(days=30),
                             premier_rdv_issue="PRESENT", date_entree=j - timedelta(days=28))
        dater(thomas, 40)
        # Adressée au porteur, en attente d'intégration (Nadia, atelier, garde d'enfants)
        nadia = presc("FAM7-NAD", "DEMO-CISF", 10, {"Besoin d'un mode de garde pendant l'atelier": "oui",
                                                    "Nombre d'enfants à faire garder": "1"}, freins=["GARDE", "ISOLEMENT"])
        circuit.adresser(nadia, self.ts)
        dater(nadia, 10)
        # À valider par le pôle (Céline, parcours santé ; réponse à accès restreint)
        celine = presc("FAM9-CEL", "DEMO-SANTE", 6, {"Grille d'aide à la décision santé remplie avec la personne": "oui"},
                       freins=["SANTE"])
        circuit.adresser(celine, self.ts)
        dater(celine, 6)
        # Refusée par le pôle (Aurélie, parcours santé)
        aurelie = presc("FAM12-AUR", "DEMO-SANTE", 20,
                        {"Grille d'aide à la décision santé remplie avec la personne": "oui"}, freins=["LOGEMENT"])
        circuit.adresser(aurelie, self.ts)
        circuit.valider(aurelie, admin, False, "Action complète jusqu'à la prochaine session (fictif).")
        dater(aurelie, 20)
        # En préparation (Laura, plateforme mobilité) : la ligne s'ajoutera au contrat en préparation à l'envoi
        presc("FAM8-LAU", "DEMO-MOBIL", 1, consentement=False, freins=["MOBILITE", "GARDE"])
        self.stdout.write("✅ Prescriptions : en préparation, à valider par le pôle, refusée, en attente du porteur, "
                          "intégrées, terminée")

    def reorientations(self, pole):
        """Organismes, une commission passée (clôturée) et la prochaine (en préparation), demandes fictives."""
        from insertion.models import CommissionReorientation, DemandeReorientation as D, OrganismeOrientation as O
        from insertion.services import reorientation_circuit as circuit
        j = self.j
        admin, cadre = self.u("admin_pi1"), self.u("cadre_pi1")
        call_command("init_insertion", stdout=StringIO())   # France Travail et CAF
        ft = O.objects.filter(categorie=O.FRANCE_TRAVAIL).first()
        caf = O.objects.filter(categorie=O.CAF).first()
        asso, _ = O.objects.get_or_create(nom="Association d'accompagnement Exemple (fictif)",
                                         defaults={"categorie": O.ASSOCIATION, "ville": "Martigues",
                                                   "email": "accueil@exemple.org"})
        CommissionReorientation.objects.filter(pole=pole).delete()

        def demande(code, referent, orientation, motif, organisme=None, freins=(), avis="ACCORD"):
            d = circuit.creer(self.b[code], referent)
            d.motif, d.orientation_proposee, d.organisme_propose = motif, orientation, organisme
            d.situation = "Situation résumée avec la personne (fictif)."
            d.freins, d.avis_personne = list(freins) or d.freins, avis
            d.save()
            return d

        # Commission passée, clôturée : une acceptée (MDS 2), une refusée, une ajournée
        passee, _ = circuit.creer_commission(pole, admin, date=j - timedelta(days=70), lieu="Salle du pôle (fictif)")
        karim = demande("FAM7-KAR", self.u("as1_mds2"), O.FRANCE_TRAVAIL,
                        "Projet professionnel défini, prêt pour un accompagnement vers l'emploi (fictif).", ft,
                        ["RECHERCHE_EMPLOI"])
        celine = demande("FAM9-CEL", self.ts, O.ASSOCIATION, "Besoin d'un accompagnement santé renforcé (fictif).",
                         asso, ["SANTE"], avis="DESACCORD")
        thomas = demande("FAM11-THO", self.ts, O.FRANCE_TRAVAIL, "Souhaite reprendre un emploi rapidement (fictif).", ft)
        for d in (karim, celine, thomas):
            circuit.inscrire(d, d.referent)
            d.refresh_from_db()
            d.commission = passee
            d.save()
        circuit.decider(karim, cadre, decision=D.ACCEPTEE, organisme_retenu=ft, date_effet=j - timedelta(days=60))
        circuit.decider(celine, cadre, decision=D.REFUSEE, motif="Parcours santé en cours avec la MDS (fictif).")
        circuit.decider(thomas, cadre, decision=D.AJOURNEE, motif="Attendre la fin de l'atelier en cours (fictif).")
        passee.participants.set([admin, cadre, self.ts, self.u("as1_mds2")])
        circuit.cloturer(passee, cadre)
        # Prochaine commission, en préparation : Thomas (ajourné) la rejoint, deux nouvelles demandes inscrites
        prochaine, _ = circuit.creer_commission(pole, admin, date=j + timedelta(days=21), lieu="Salle du pôle (fictif)")
        for code, orientation, motif, organisme in [
                ("FAM5-SAR", O.FRANCE_TRAVAIL, "Accompagnement global mené à son terme, recherche d'emploi active (fictif).", ft),
                ("FAM7-NAD", O.CAF, "Naissance à venir : accompagnement proposé par la CAF (fictif).", caf)]:
            d = demande(code, self.ts, orientation, motif, organisme)
            circuit.inscrire(d, self.ts)
        # En préparation (référente)
        demande("FAM12-AUR", self.ts, O.ASSOCIATION, "", asso, avis="NON_INFORMEE")
        self.stdout.write("✅ Réorientation : commission passée (acceptée, refusée, ajournée), prochaine commission "
                          f"le {prochaine.date:%d/%m/%Y} (3 dossiers), une demande en préparation")

    # ------------------------------------------------------------------ planning
    def journal(self):
        """Entretiens fictifs : une suite à donner, une synthèse privée (visible du seul auteur), un accompagnement légal."""
        from beneficiaire.models import EntretienSocial as E, TypeAccompagnement as T
        E.objects.filter(beneficiaire__code_interne__in=CODES_DEMO).delete()
        t = {x.code: x for x in T.objects.all()}

        def entretien(code, il_y_a, mode, objet, types, synthese, prive="", suite="", echeance=None, faite=False):
            e = E.objects.create(beneficiaire=self.b[code], date=self.j - timedelta(days=il_y_a), heure=time(10),
                                 mode=mode, duree_minutes=45, auteur=self.ts, cree_par=self.ts, objet=objet,
                                 synthese=synthese, synthese_privee=prive, suite_a_donner=suite,
                                 echeance=self.j + timedelta(days=echeance) if echeance is not None else None,
                                 suite_faite=faite)
            e.types.set([t[c] for c in types if c in t])
        entretien("FAM5-SAR", 40, E.RDV, "Premier entretien", ["acces-droits", "rsa"],
                  "Point sur la situation et les droits. Contrat RSA à préparer.", suite="Préparer le contrat RSA",
                  echeance=-20, faite=True)
        entretien("FAM5-SAR", 9, E.TELEPHONE, "Facture d'électricité", ["budget"],
                  "Facture de régularisation reçue. Budget du foyer mis à jour. Demande d'échéancier à faire auprès du "
                  "fournisseur.", prive="Penser à vérifier le chèque énergie à la prochaine rencontre.",
                  suite="Rappeler pour savoir si l'échéancier est accordé", echeance=5)
        entretien("FAM2-SOP", 25, E.VAD, "Visite à domicile", ["logement", "parentalite"],
                  "Logement trop petit pour la famille. Demande de logement social à renouveler.",
                  suite="Vérifier le renouvellement de la demande de logement social", echeance=-2)
        self.stdout.write("✅ Journal de l'accompagnement fictif ajouté")

    def budgets(self):
        """Budgets du foyer fictifs : deux budgets successifs (historique) et un budget partagé par un couple."""
        from beneficiaire.models import BudgetFoyer
        BudgetFoyer.objects.filter(beneficiaire__code_interne__in=CODES_DEMO).delete()

        def budget(code, il_y_a, nb, r, c, dettes=(), commentaire=""):
            BudgetFoyer.objects.create(
                beneficiaire=self.b[code], date_etabli=self.j - timedelta(days=il_y_a), nb_personnes_foyer=nb,
                cree_par=self.ts, commentaire=commentaire,
                ressources={"v": 2, "lignes": {k: {"demandeur": str(v[0]), "conjoint": str(v[1]), "autres": "0"}
                                               for k, v in r.items()}, "precisions": {}},
                charges={"v": 2, "lignes": {k: {"payee": str(v[0]), "non_payee": str(v[1])} for k, v in c.items()},
                         "precisions": {}},
                dettes=[{"creancier": n, "montant": str(m)} for n, m in dettes])
        budget("FAM5-SAR", 200, 1, {"rsa": (635, 0), "logement": (290, 0)},
               {"loyer": (520, 0), "electricite": (60, 0), "telephone": (35, 0)})
        budget("FAM5-SAR", 10, 1, {"rsa": (635, 0), "logement": (290, 0)},
               {"loyer": (540, 0), "electricite": (85, 170), "telephone": (35, 0), "assurances": (20, 0)},
               dettes=[("Fournisseur d'énergie (fictif)", 170)],
               commentaire="Facture d'électricité de régularisation en attente d'échéancier.")
        budget("FAM2-SOP", 30, 4, {"salaire": (1350, 980), "familiales": (150, 0), "logement": (180, 0)},
               {"loyer": (850, 0), "electricite": (110, 0), "assurance_habitation": (25, 0), "credits": (210, 0),
                "garde_scolarite": (120, 0), "telephone": (60, 0)})
        self.stdout.write("✅ Budgets du foyer fictifs ajoutés")

    def logement(self):
        """FSL accès fictif : gestionnaires de démonstration (sans formulaire officiel : trame CID), une demande en
        attente de l'avis du cadre (bail manquant) et une demande accordée."""
        from logement.models import DemandeFSL, GestionnaireFSL
        from logement.services import circuit, envoi, fsl
        metro, _ = GestionnaireFSL.objects.get_or_create(
            nom="FSL – gestionnaire métropolitain (démo)",
            defaults={"adresse": "1 place de l'Exemple, 13000 Ville-Exemple (fictif)", "codes_postaux": "13110, 13500",
                      "transmission": "par le service du logement du Département (démo)",
                      "parametres": {"plafond_acces": 1500, "plafond_equipement_seul": 400,
                                     "plafond_equipement_famille": 700}})
        GestionnaireFSL.objects.get_or_create(
            nom="FSL – Département (démo)", defaults={"par_defaut": True, "adresse": "Adresse fictive"})
        _effacer_envois(DemandeFSL.objects.filter(beneficiaire__code_interne__in=["FAM5-SAR", "FAM2-SOP", "FAM3-CLA"]))

        def creer(code, maj, type_aide="ACCES", auteur=None):
            b, auteur = self.b[code], auteur or self.ts
            d = DemandeFSL.objects.create(beneficiaire=b, mds=b.mds, gestionnaire=metro, cree_par=auteur,
                                          type_aide=type_aide, donnees=fsl.preremplir(b, auteur, type_aide),
                                          pieces={c: "FOURNIE" for c, _, fac in fsl.liste_pieces(type_aide) if not fac})
            d.donnees.update(maj)
            d.tracer(self.ts, "Demande créée", "préremplie")
            d.save()
            return d
        d = creer("FAM5-SAR", {
            "bailleur_type": "PRIVE", "adresse_objet": "8 impasse des Tests, 1er étage", "cp_commune": "13110 Port-de-Bouc",
            "nouveau_bailleur": "M. Bailleur EXEMPLE\n4 rue Fictive 13110 Port-de-Bouc", "contact_bailleur": "04 00 00 00 99",
            "logement_anterieur": {"bailleur": "Bailleur privé (fictif)", "nature": "Logement du secteur privé",
                                   "typologie": "T1", "statut": "Locataire", "loyer": "540", "al": "290",
                                   "loyer_residuel": "250", "motif": "Trop petit", "caution_restituee": "NON"},
            "logement_nouveau": {"bailleur": "M. Bailleur EXEMPLE", "typologie": "T2", "classe_energetique": "D",
                                 "loyer": "480", "charges": "40", "chauffage_collectif": "NON", "montant_caution": "480",
                                 "al_previsionnel": "260", "loyer_residuel": "260"},
            "proposition": {"caution": "480", "premier_loyer": "520", "compteurs": "60", "equipements": "330"},
            "equipements": ["refrigerateur", "table_cuisson"]})
        d.avis, d.proposition_subvention, d.proposition_pret = "FAVORABLE", 1090, 300
        d.avis_motive = ("Madame quitte un hébergement chez un tiers devenu trop petit. Le loyer résiduel est compatible "
                         "avec ses ressources (fictif).")
        d.pieces.update({"bail": "MANQUANTE", "ident_logement": "MANQUANTE", "garantie": "SANS_OBJET",
                         "situation_precedente": "FOURNIE"})
        d.save()
        circuit.demander_avis_cadre(d, self.ts)
        d = creer("FAM2-SOP", {
            "bailleur_type": "SOCIAL", "adresse_objet": "Résidence Exemple, bâtiment B", "cp_commune": "13500 Martigues",
            "nouveau_bailleur": "Bailleur social EXEMPLE", "garantie": "4_12",
            "logement_nouveau": {"bailleur": "Bailleur social EXEMPLE", "typologie": "T4", "loyer": "690", "charges": "90",
                                 "al_previsionnel": "180", "loyer_residuel": "600"},
            "proposition": {"caution": "690", "premier_loyer": "780"}})
        d.avis, d.proposition_subvention, d.avis_motive = "FAVORABLE", 1470, "Relogement dans un logement adapté (fictif)."
        d.save()
        circuit.demander_visa(d, self.ts)
        circuit.avis_cadre(d, self.cadre, True, "")
        circuit.envoyer(d, self.ts, self.j - timedelta(days=40), mode="MAIL")
        envoi.enregistrer(d, "FSL accès au logement", d.mds, "MAIL", 18)
        circuit.enregistrer_reponse(d, self.ts, DemandeFSL.ACCORDEE, self.j - timedelta(days=12), subvention=1470,
                                    garantie="4 mois sur 12", commentaire="Accord (fictif).")
        # Énergie : facture de régularisation de moins de 500 €, instruite par un agent administratif, envoyée
        admin = User.objects.get(username="aa1_mds1")
        d = creer("FAM5-SAR", {"distributeur": "Fournisseur d'énergie EXEMPLE", "participation": "OUI",
                               "surendettement": "NON", "commentaire_administratif": "Facture de régularisation (fictif)."},
                  "ENERGIE", admin)
        d.instruction_administrative = True
        d.save()
        circuit.demander_visa(d, admin)
        circuit.avis_cadre(d, self.cadre, True, "")
        circuit.envoyer(d, admin, self.j - timedelta(days=3), mode="MAIL")
        envoi.enregistrer(d, "FSL impayés d'électricité, de gaz", d.mds, "MAIL", 9)
        # Eau : en préparation par le travailleur social
        creer("FAM2-SOP", {"distributeur": "Distributeur d'eau EXEMPLE", "date_facture": (self.j - timedelta(days=20)).strftime("%d/%m/%Y"),
                           "montant_facture": "286", "surendettement": "NON"}, "EAU")
        # Maintien (concordat) : dette locative, remise du bailleur d'un tiers, CCAPEX saisie
        d = creer("FAM3-CLA", {"bailleur_type": "PRIVE", "variante": "CONCORDAT",
                               "nom_bailleur": "SCI EXEMPLE\n7 rue Fictive 13110 Port-de-Bouc", "montant_dette": "1950",
                               "reprise_paiement_depuis": "mai 2026", "remise_dette": "OUI", "montant_remise": "650",
                               "saisine_ccapex": "OUI", "saisine_surendettement": "NON", "chauffage_collectif": "NON",
                               "logement": {"typologie": "T3", "surface": "64", "loyer": "640", "charges": "60",
                                            "al": "210"}}, "MAINTIEN")
        d.avis, d.proposition_subvention, d.proposition_pret = "FAVORABLE", 850, 450
        d.avis_motive = "Paiement du loyer repris depuis six mois ; le bailleur accepte une remise d'un tiers (fictif)."
        d.save()
        self.logement_social_copp()
        self.stdout.write("✅ Demandes FSL fictives ajoutées")

    def logement_social_copp(self):
        """Demandes de logement social, séances fictives de la commission des publics prioritaires et deux saisines."""
        from logement.models import CommissionPublicsPrioritaires as C, DemandeLogementSocial, SaisineCOPP
        from logement.services import copp, envoi
        from mds.models import MDS
        DemandeLogementSocial.objects.filter(beneficiaire__code_interne__in=["FAM2-SOP", "FAM3-CLA"]).delete()
        DemandeLogementSocial.objects.create(
            beneficiaire=self.b["FAM2-SOP"], nud="DEMO-NUD-0002", date_creation=self.j - timedelta(days=4 * 365 + 40),
            date_renouvellement=self.j - timedelta(days=345), dalo_depose=True, dalo_date=self.j - timedelta(days=500),
            dalo_etat="EN_COURS", alin_inscrit=True, alin_date=self.j - timedelta(days=200), alin_etat="EN_COURS",
            communes_souhaitees=["Port-de-Bouc", "Martigues", "Fos-sur-Mer"], typologie_souhaitee="T4",
            precisions="Rez-de-chaussée ou ascenseur souhaité (fictif).")
        DemandeLogementSocial.objects.create(
            beneficiaire=self.b["FAM3-CLA"], nud="DEMO-NUD-0003", date_creation=self.j - timedelta(days=2 * 365 + 90),
            dalo_depose=True, dalo_date=self.j - timedelta(days=300), dalo_etat="REFUSE",
            communes_souhaitees=["Martigues", "Port-de-Bouc"], typologie_souhaitee="T3")
        C.objects.filter(territoire="Territoire de démonstration").delete()
        mds = list(MDS.objects.filter(code_mds__in=["MDSTEST1", "MDSTEST2"]))
        seances = []
        for jours, lieu in ((-60, "Salle du conseil (fictif)"), (25, "Maison des services (fictif)"),
                            (115, "Salle du conseil (fictif)"), (205, "Maison des services (fictif)")):
            c = C.objects.create(territoire="Territoire de démonstration", date=self.j + timedelta(days=jours),
                                 date_limite_depot=self.j + timedelta(days=jours - 15), lieu=lieu, horaire="14 h")
            c.mds.set(mds)
            seances.append(c)
        _effacer_envois(SaisineCOPP.objects.filter(beneficiaire__code_interne__in=["FAM2-SOP", "FAM3-CLA"]))
        s = SaisineCOPP.objects.create(beneficiaire=self.b["FAM2-SOP"], mds=self.b["FAM2-SOP"].mds,
                                       donnees=copp.preremplir(self.b["FAM2-SOP"], self.ts), commission=seances[1],
                                       cree_par=self.ts, motifs=["DALO_ANCIEN", "SURNOMBRE"],
                                       rapport_social="Couple avec deux enfants dans un T2 devenu trop petit ; demande de "
                                                      "logement social depuis plus de quatre ans, DALO sans décision (fictif).")
        s.donnees.update({"logement_actuel": "PARC_PRIVE", "typologie": "T2", "endettement": "NON",
                          "plafonds_ressources": "PLUS", "rfr_n1_demandeur": "18500", "rfr_n2_demandeur": "17900"})
        s.tracer(self.ts, "Saisine créée", "préremplie")
        s.save()
        s = SaisineCOPP.objects.create(beneficiaire=self.b["FAM3-CLA"], mds=self.b["FAM3-CLA"].mds,
                                       donnees=copp.preremplir(self.b["FAM3-CLA"], self.ts), commission=seances[0],
                                       cree_par=self.ts, motifs=["DALO_REFUSE", "EXPULSION"], statut=SaisineCOPP.EXAMINEE,
                                       rapport_social="Procédure d'expulsion en cours, concordat déposé (fictif).",
                                       decision="Dossier retenu : proposition prioritaire auprès des bailleurs (fictif).",
                                       date_decision=seances[0].date)
        s.tracer(self.ts, "Envoyée à la commission par mail", str(seances[0]))
        s.save()
        envoi.enregistrer(s, "COPP", s.mds, "MAIL", 7)
        self.stdout.write("✅ Demandes de logement et commission des publics prioritaires fictives ajoutées")

    def ateliers(self):
        """Ateliers collectifs fictifs : une séance passée (présences notées), deux à venir dont une complète."""
        from planning import ateliers as regles
        from planning.models import Atelier, ParticipantAtelier as P, SeanceAtelier
        budget, _ = Atelier.objects.get_or_create(nom="Gérer son budget au quotidien", mds=None,
                                                  defaults={"description": "Atelier fictif de démonstration."})
        cuisine, _ = Atelier.objects.get_or_create(nom="Cuisine à petit prix", mds=self.mds1,
                                                   defaults={"description": "Atelier fictif de démonstration."})
        numerique, _ = Atelier.objects.get_or_create(nom="Premiers pas numériques", mds=self.mds1)
        SeanceAtelier.objects.filter(atelier__in=[budget, cuisine, numerique]).delete()

        def seance(atelier, jours, h, **champs):
            jour = self.j + timedelta(days=jours)
            while jour.weekday() >= 5:                     # jamais le week-end
                jour += timedelta(days=1)
            return SeanceAtelier.objects.create(atelier=atelier, mds=self.mds1, date=jour,
                                                heure_debut=time(h), heure_fin=time(h + 2), cree_par=self.ts,
                                                lieu="Salle polyvalente de la MDS", **champs)
        passee = seance(budget, -12, 9, animateur="Conseillère ESF de la MDS", places=8)
        for code in ("FAM2-SOP", "FAM5-SAR", "FAM4-NOL"):
            regles.inscrire(passee, self.ts, beneficiaire=self.b[code], forcer_age=True)
        regles.inscrire(passee, self.ts, prenom="Inès", nom="BARRE", ville="Commune fictive")
        regles.noter_presences(passee, {str(p.pk): v for p, v in zip(passee.inscrits(), [P.VENU, P.VENU, P.ABSENT, P.VENU])})
        cuis = seance(cuisine, 9, 14, places=3, payant=True, tarif=2, description="Participation aux courses : 2 €.")
        for code in ("FAM9-CEL", "FAM3-CLA", "FAM1-JEA", "FAM5-SAR"):          # la 4e personne part en liste d'attente
            regles.inscrire(cuis, self.ts, beneficiaire=self.b[code], forcer_age=True)
        seance(numerique, 16, 10, places=10, condition_age=SeanceAtelier.PLUS_DE, age_limite=18,
               description="Créer une adresse de courriel, se repérer sur les sites des administrations.")
        self.stdout.write("✅ Ateliers collectifs fictifs ajoutés")

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
                    "cree_par": self.ts, "reserve_par": self.u("aa1_mds1") if code else None,
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
