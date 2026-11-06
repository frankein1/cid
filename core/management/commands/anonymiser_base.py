# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/management/commands/anonymiser_base.py
"""
Anonymise LA BASE COURANTE pour en faire une copie de test réaliste (volumes, structure des dossiers),
sans aucune donnée nominative. Inspiré de l'anonymiseur de Mon Suivi Social.

⚠️ À lancer UNIQUEMENT sur une COPIE restaurée de la base, jamais sur la production : l'opération est
irréversible. Trois verrous :
  1. variable d'environnement CID_ANONYMISATION_AUTORISEE=1 sur le serveur de la copie ;
  2. --base <nom de la base> : doit être exactement le nom de la base à laquelle CID est connecté ;
  3. --confirmer.

    CID_ANONYMISATION_AUTORISEE=1 python manage.py anonymiser_base --base cid_copie --confirmer

Ce qui est fait :
- usagers : noms et prénoms fictifs (une même famille garde un même nom), date de naissance décalée de
  quelques semaines (l'âge reste réaliste), adresse fictive dans la même commune, téléphones, courriels et
  numéros (NIR, CAF, France Travail, fiscal, GENESIS, PMI) effacés ;
- partout ailleurs (sauf le paramétrage) : textes libres remplacés, noms / téléphones / courriels effacés,
  données reçues des API vidées ;
- agents (hors super-administrateurs) : identifiants et noms fictifs, mots de passe rendus inutilisables ;
- documents de la GED : métadonnées anonymisées et DÉTACHÉS de leurs fichiers, sans rien supprimer dans le
  stockage (une copie de base pointe souvent vers le même stockage que la production) ;
- journal d'activité, sessions, jetons RDV-Solidarités : supprimés.
"""
import hashlib
import os
import random
from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction

APPS = ["core", "beneficiaire", "ged", "messagerie", "planning", "AidFi", "connecteurs", "protection_enfance",
        "insertion"]
# Paramétrage et référentiels (pas de données personnelles) : jamais modifiés
EXCLUS = {"core.Configuration", "core.ModeleCourrier", "core.Profil", "core.Capacite", "ged.DocumentType",
          "AidFi.ParametresAides", "AidFi.ReferentielMotifAFASE", "AidFi.MontantIndicatifAFASE",
          "AidFi.MotifRefusAFASE", "protection_enfance.TypeDanger", "insertion.TypeActionInsertion",
          "insertion.ActionInsertion", "insertion.QuestionAction", "insertion.ParametresRSA",
          "insertion.OrganismeOrientation", "insertion.PoleInsertion", "beneficiaire.ValeurListe", "beneficiaire.TypeAccompagnement",
          "connecteurs.MotifRDVSP", "connecteurs.ParametresRDVSP", "connecteurs.MdsRDVSP",
          "connecteurs.LieuExterneRDVSP", "connecteurs.ServiceInclusion",
          "connecteurs.ImportInclusion", "core.User"}
# Champs courts qui portent une donnée personnelle, où qu'ils soient
CHAMPS_EFFACES = {"telephone", "telephone_mobile", "telephone_fixe", "nir", "numero_caf", "numero_france_travail",
                  "numero_fiscal", "numero_genesis", "numero_dossier_pmi", "code_insee_naissance",
                  "identifiant_france_travail", "lieu_naissance", "nom_naissance", "iban", "bic",
                  "contact_telephone", "telephone_professionnel", "signalant_nom", "tiers_nom", "conjoint_referent",
                  "lieu_precis", "numero_lrar", "reference_parquet", "signature_manuscrite", "ldap_dn",
                  "dernier_emploi", "logement_precision", "precision", "situation_particuliere",
                  "reorientation_precision", "precision_notification", "famille_libelle"}
CHAMPS_NOM = {"nom", "nom_usage", "nom_famille"}
CHAMPS_PRENOM = {"prenom"}
CHAMPS_TEXTE_COURT = {"objet", "commentaire", "objet_libelle", "utilisateur_nom", "titre", "adresse", "resume",
                      "conclusion", "motif_non_retenue", "motif_non_integration", "preconisation",
                      "suite_a_donner", "orientation_precision"}

NOMS = ["ARNAUD", "BARRE", "BLANC", "BONNET", "BRUN", "CARON", "CHEVALIER", "CLÉMENT", "COLIN", "DAVID", "DUMAS",
        "FAURE", "FONTAINE", "GAUTIER", "GIRARD", "GUÉRIN", "HENRY", "JOLY", "LACROIX", "LAMBERT", "LEGRAND",
        "LEMAIRE", "MARCHAND", "MARTIN", "MASSON", "MERCIER", "MEYER", "MOREL", "NOËL", "PERRIN", "PICARD",
        "RENARD", "ROCHE", "ROUSSEL", "ROY", "SIMON", "VIDAL", "VINCENT"]
PRENOMS = ["Adèle", "Alice", "Amina", "Camille", "Chloé", "Clara", "Élise", "Emma", "Inès", "Jade", "Léa", "Lina",
           "Lucie", "Manon", "Nora", "Rose", "Sarah", "Yasmine", "Adam", "Bastien", "Clément", "Enzo", "Gabriel",
           "Hugo", "Karim", "Lucas", "Mathis", "Nathan", "Noé", "Paul", "Raphaël", "Samir", "Théo", "Tom",
           "Yanis", "Zacharie"]
TEXTE = "[texte anonymisé]"


def _choix(liste, graine):
    h = int(hashlib.sha256(str(graine).encode()).hexdigest(), 16)
    return liste[h % len(liste)]


class Command(BaseCommand):
    help = "Anonymise la base courante (copie de test uniquement, irréversible)."

    def add_arguments(self, parser):
        parser.add_argument("--base", required=True, help="Nom exact de la base à anonymiser (contrôle)")
        parser.add_argument("--confirmer", action="store_true")

    def handle(self, *args, **opts):
        nom_base = settings.DATABASES["default"]["NAME"]
        if os.environ.get("CID_ANONYMISATION_AUTORISEE") != "1":
            raise CommandError("Refusé : CID_ANONYMISATION_AUTORISEE=1 n'est pas défini sur ce serveur.")
        if opts["base"] != nom_base:
            raise CommandError(f"Refusé : CID est connecté à la base « {nom_base} », pas à « {opts['base']} ».")
        if not opts["confirmer"]:
            raise CommandError("Refusé : ajoutez --confirmer (opération irréversible).")
        self.sel = os.urandom(16).hex()     # même nom d'origine → même nom fictif, dans cette exécution seulement
        bilan = {}
        with transaction.atomic():
            bilan["usagers"] = self.usagers()
            bilan["agents"] = self.agents()
            bilan["documents"] = self.documents()
            bilan.update(self.suppressions())
            bilan["autres lignes"] = self.reste()
        for k, v in bilan.items():
            self.stdout.write(f"  {k} : {v}")
        self.stdout.write(self.style.SUCCESS(f"Base « {nom_base} » anonymisée."))

    # --------------------------------------------------------------- usagers
    def usagers(self):
        B = apps.get_model("beneficiaire", "Beneficiaire")
        lot, n = [], 0
        champs = ["nom", "prenom", "nom_naissance", "date_naissance", "lieu_naissance", "code_insee_naissance",
                  "nir", "numero_caf", "numero_france_travail", "numero_fiscal", "numero_genesis",
                  "numero_dossier_pmi", "adresse", "telephone_mobile", "telephone_fixe", "email", "detail_sortie"]
        champs = [c for c in champs if any(f.name == c for f in B._meta.concrete_fields)]
        for b in B._base_manager.all().iterator():
            b.nom = _choix(NOMS, self.sel + (b.nom or "").upper())
            b.prenom = _choix(PRENOMS, self.sel + str(b.pk))
            if b.date_naissance:
                b.date_naissance = b.date_naissance + timedelta(days=random.randint(-45, 45))
            b.adresse = f"{(b.pk % 90) + 1} rue de l'Essai"
            for c in champs:
                if c in ("nom", "prenom", "date_naissance", "adresse"):
                    continue
                f = B._meta.get_field(c)
                setattr(b, c, None if f.null else "")
            lot.append(b)
            n += 1
            if len(lot) >= 500:
                B._base_manager.bulk_update(lot, champs)
                lot = []
        if lot:
            B._base_manager.bulk_update(lot, champs)
        return n

    # --------------------------------------------------------------- agents
    def agents(self):
        User = apps.get_model("core", "User")
        n = 0
        for u in User.objects.filter(is_superuser=False).iterator():
            u.username = f"agent{u.pk}"
            u.first_name = _choix(PRENOMS, self.sel + f"agent{u.pk}")
            u.last_name = f"AGENT{u.pk}"
            u.email = f"agent{u.pk}@cid.invalid"
            u.set_unusable_password()
            extra = [c for c in ("matricule", "telephone") if any(f.name == c for f in User._meta.concrete_fields)]
            for c in extra:
                setattr(u, c, f"A{u.pk}" if c == "matricule" else "")
            u.save(update_fields=["username", "first_name", "last_name", "email", "password", *extra])
            n += 1
        return n

    # --------------------------------------------------------------- GED
    def documents(self):
        """Métadonnées anonymisées et lien vers le fichier coupé : update(), donc AUCUN signal de suppression."""
        from django.db.models import F, Value
        from django.db.models.functions import Concat
        D = apps.get_model("ged", "DocumentGED")
        V = apps.get_model("ged", "DocumentVersion")
        n = D.objects.update(titre=Concat(Value("Document "), F("pk"), output_field=models.CharField()),
                             description="", seaweedfs_id=Concat(Value("anonymise-"), F("pk"),
                                                                 output_field=models.CharField()))
        V.objects.update(seaweedfs_id=Concat(Value("anonymise-v"), F("pk"), output_field=models.CharField()))
        for nom in ("DocumentArchive", "ArchiveDocument"):
            try:
                A = apps.get_model("ged", nom)
            except LookupError:
                continue
            if any(f.name == "document_titre_archive" for f in A._meta.concrete_fields):
                A.objects.update(document_titre_archive="Document archivé")
        return n

    # --------------------------------------------------------------- suppressions
    def suppressions(self):
        res = {}
        for label in ("core.AuditLog", "sessions.Session", "connecteurs.CompteRDVSP"):
            try:
                M = apps.get_model(label)
            except LookupError:
                continue
            res[f"supprimés ({label})"] = M._base_manager.all().delete()[0]
        return res

    # --------------------------------------------------------------- tout le reste
    def reste(self):
        n = 0
        for app in APPS:
            for M in apps.get_app_config(app).get_models():
                label = f"{M._meta.app_label}.{M.__name__}"
                if label in EXCLUS or label == "beneficiaire.Beneficiaire" or M._meta.proxy:
                    continue
                maj = {}
                for f in M._meta.concrete_fields:
                    if f.primary_key or f.is_relation or f.choices:
                        continue
                    if isinstance(f, models.EmailField):
                        maj[f.name] = "" if not f.null else None
                    elif isinstance(f, models.TextField):
                        maj[f.name] = TEXTE if not f.null else None
                    elif isinstance(f, models.JSONField) and label not in ("insertion.ContratInsertion",
                                                                          "insertion.PrescriptionInsertion"):
                        maj[f.name] = f.get_default()
                    elif isinstance(f, models.CharField):
                        if f.name in CHAMPS_EFFACES:
                            maj[f.name] = "" if not f.null else None
                        elif f.name in CHAMPS_NOM:
                            maj[f.name] = "ANONYME"
                        elif f.name in CHAMPS_PRENOM:
                            maj[f.name] = "Anonyme"
                        elif f.name in CHAMPS_TEXTE_COURT and not f.unique:
                            maj[f.name] = TEXTE[:f.max_length]
                if maj:
                    n += M._base_manager.update(**maj)
        return n
