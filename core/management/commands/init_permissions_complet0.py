# core/management/commands/init_permissions_complet.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

try:
    from core.models.profil import Profil
    from core.models.configuration import Configuration
except ImportError:
    from core.models import Profil, Configuration

from mds.models import MDS
from beneficiaire.models import Beneficiaire
from planning.models import CreneauRdv
from ged.models import DocumentGED, DocumentType

try:
    from AidFi.models import (
        DemandeAide, TypeAide, PieceJustificative,
        CAPCheque, RegieUrgence, PieceObligatoire
    )
    AIDFI_INSTALLED = True
except ImportError:
    AIDFI_INSTALLED = False


PROTECTION_ENFANCE_INSTALLED = False


def get_perms_for_model(model_class, actions):
    """
    Retourne la liste des Permission pour un modèle donné et une liste d'actions
    (view, add, change, delete).
    """
    perms = []
    ct = ContentType.objects.get_for_model(model_class)
    for action in actions:
        try:
            perm = Permission.objects.get(
                content_type=ct,
                codename=f"{action}_{model_class._meta.model_name}",
            )
            perms.append(perm)
        except Permission.DoesNotExist:
            continue
    return perms


def get_custom_permissions(app_label, codenames):
    """Récupère les permissions custom (déclarées dans Meta.permissions)."""
    perms = []
    for codename in codenames:
        try:
            perm = Permission.objects.get(
                codename=codename, content_type__app_label=app_label
            )
            perms.append(perm)
        except Permission.DoesNotExist:
            continue
    return perms


class Command(BaseCommand):
    help = (
        "Initialise TOUTES les permissions pour tous les profils métier "
        "(CORE-COMPATIBLE) – script unique et central."
    )

    def handle(self, *args, **options):
        self.stdout.write("🚀 Initialisation COMPLÈTE des permissions CORE...")

        # ------------------------------------------------------------------
        # 0. Configuration par défaut pour les Profils
        # ------------------------------------------------------------------
        try:
            config_defaut, _ = Configuration.objects.get_or_create(
                cle="PROFILS_CONFIG_DEFAUT",
                defaults={
                    "valeur": '{"notifications": true, "theme": "clair", "langue": "fr"}',
                    "type_valeur": "JSON",
                    "categorie": "SYSTEME",
                    "description": "Configuration par défaut pour les Profils métiers",
                    "modifiable": True,
                },
            )
            self.stdout.write(f"  ✓ Configuration par défaut des Profils: {config_defaut.cle}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erreur Configuration Profils: {e}"))
            return

        # ------------------------------------------------------------------
        # 1. Définition des groupes/profils métiers et de leurs droits
        # ------------------------------------------------------------------
        groupes_config = {
            "MDS_Administratifs": {
                "permissions": {
                    "beneficiaire": ["view", "add", "change", "delete"],
                    "planning": ["view", "add", "change", "delete"],
                    "ged": ["view", "add", "change"],
                    "mds": ["view"],
                    # pas de clé 'aidfi' ici : lecture seule via additional_models
                },
                "beneficiaire_custom": [
                    "can_view_beneficiaire",
                    "can_create_beneficiaire",
                    "can_edit_beneficiaire",
                    # pas de delete / export / anonymisation
                ],
                "flags": {"peut_creer_dossier": True},
                "description": "Accueil et secrétariat des MDS",
            },
            "MDS_Agents_Sociaux": {
                "permissions": {
                    "beneficiaire": ["view", "add", "change"],
                    "planning": ["view", "add", "change", "delete"],
                    "ged": ["view", "add", "change"],
                    "mds": ["view"],
                    "aidfi": ["view", "add", "change"],
                },
                "beneficiaire_custom": [
                    "can_view_beneficiaire",
                    "can_create_beneficiaire",
                    "can_edit_beneficiaire",
                    "view_confidential_beneficiary",
                ],
                "custom_permissions": {
                    "AidFi": [
                        "creer_demande",
                        "instruire_demande",
                        "valider_piece",
                    ],
                    "planning": ["reserver_rdv", "annuler_rdv"],
                    "ged": ["upload_document", "valider_document"],
                },
                "flags": {
                    "peut_creer_dossier": True,
                    "peut_instruire_dossier": True,
                },
                "description": "Travailleurs sociaux - Droits complets sur leurs dossiers",
            },
            "MDS_Cadres": {
                "permissions": {
                    "beneficiaire": ["view", "add", "change", "delete"],
                    "planning": ["view", "add", "change", "delete"],
                    "ged": ["view", "add", "change", "delete"],
                    "mds": ["view", "change"],
                    "aidfi": ["view", "add", "change", "delete"],
                },
                "beneficiaire_custom": [
                    "can_view_beneficiaire",
                    "can_create_beneficiaire",
                    "can_edit_beneficiaire",
                    "can_delete_beneficiaire",
                    "view_confidential_beneficiary",
                    "export_beneficiary",
                ],
                "custom_permissions": {
                    "AidFi": [
                        "creer_demande",
                        "instruire_demande",
                        "decider_demande_aide",
                        "gestion_catalogue_aides",
                        "gestion_regies",
                        "gestion_cap",
                        "configurer_aides",
                    ],
                    "planning": [
                        "generer_creneaux",
                        "gerer_jours_bloques",
                        "voir_notes_internes",
                    ],
                    "ged": [
                        "gestion_types_documents",
                        "gerer_acces_document",
                        "supprimer_document",
                    ],
                },
                "flags": {
                    "peut_creer_dossier": True,
                    "peut_instruire_dossier": True,
                    "peut_valider_dossier": True,
                    "peut_decider_aide": True,
                    "peut_acceder_finance": True,
                },
                "description": "Chefs de service MDS - Validation et gestion",
            },
            "DGAS_Direction": {
                "permissions": {
                    "beneficiaire": ["view"],
                    "planning": ["view"],
                    "ged": ["view"],
                    "mds": ["view"],
                    "aidfi": ["view"],
                },
                "beneficiaire_custom": [
                    "can_view_beneficiaire",
                    "view_confidential_beneficiary",
                    "export_beneficiary",
                ],
                "custom_permissions": {
                    "ged": ["view_document_confidentiel"],
                },
                "flags": {
                    "peut_acceder_finance": True,
                    "acces_donnees_sensibles": True,
                },
                "description": "Direction DGAS - Lecture tous dossiers",
            },
            "DITAS_Direction": {
                "permissions": {
                    "beneficiaire": ["view"],
                    "planning": ["view"],
                    "ged": ["view"],
                    "mds": ["view"],
                    "aidfi": ["view"],
                },
                "beneficiaire_custom": [
                    "can_view_beneficiaire",
                    "view_confidential_beneficiary",
                    "export_beneficiary",
                    "anonymize_beneficiary",
                ],
                "custom_permissions": {
                    # éventuellement: 'AidFi': ['export_aid_requests'],
                },
                "flags": {
                    "acces_donnees_sensibles": True,
                },
                "description": "Direction DITAS - Lecture seule étendue",
            },
            "SUPER_ADMIN": {
                "permissions": "all",
                "beneficiaire_custom": [
                    "can_view_beneficiaire",
                    "can_create_beneficiaire",
                    "can_edit_beneficiaire",
                    "can_delete_beneficiaire",
                    "view_confidential_beneficiary",
                    "export_beneficiary",
                    "anonymize_beneficiary",
                ],
                "flags": {
                    "peut_creer_dossier": True,
                    "peut_instruire_dossier": True,
                    "peut_valider_dossier": True,
                    "peut_decider_aide": True,
                    "peut_acceder_finance": True,
                    "peut_administrer": True,
                    "acces_donnees_sensibles": True,
                },
                "description": "Super Administrateur - Tous les droits",
            },
        }

        # ------------------------------------------------------------------
        # 2. Mapping des apps vers les modèles principaux
        # ------------------------------------------------------------------
        models_mapping = {
            "beneficiaire": Beneficiaire,
            "planning": CreneauRdv,
            "ged": DocumentGED,
            "mds": MDS,
        }
        if AIDFI_INSTALLED:
            models_mapping["aidfi"] = DemandeAide

        # Modèles supplémentaires AidFi
        additional_models = {}
        if AIDFI_INSTALLED:
            additional_models.update(
                {
                    "TypeAide": TypeAide,
                    "PieceJustificative": PieceJustificative,
                    "CAPCheque": CAPCheque,
                    "RegieUrgence": RegieUrgence,
                    "PieceObligatoire": PieceObligatoire,
                }
            )

        # ------------------------------------------------------------------
        # 3. Création et configuration des groupes/profils
        # ------------------------------------------------------------------
        for code_profil, config in groupes_config.items():
            nom_groupe = code_profil  # 1 profil = 1 groupe du même nom

            # Créer / nettoyer le Group
            groupe, _ = Group.objects.get_or_create(name=nom_groupe)
            groupe.permissions.clear()

            # Créer / récupérer le Profil
            profil, _ = Profil.objects.get_or_create(
                code=code_profil,
                defaults={
                    "nom": code_profil.replace("_", " "),
                    "lecture_seule": False,
                    "configuration": config_defaut,
                },
            )

            # Nettoyer les permissions et flags du Profil
            profil.permissions.clear()
            for field in [
                "peut_creer_dossier",
                "peut_instruire_dossier",
                "peut_valider_dossier",
                "peut_decider_aide",
                "peut_acceder_finance",
                "peut_administrer",
                "lecture_seule",
                "acces_donnees_sensibles",
            ]:
                setattr(profil, field, False)

            # --- Appliquer les permissions ---
            if config["permissions"] == "all":
                all_perms = Permission.objects.all()
                profil.permissions.add(*all_perms)
            else:
                # Permissions standard (view/add/change/delete) sur les modèles principaux
                for app_name, actions in config["permissions"].items():
                    if not actions:
                        continue
                    model_class = models_mapping.get(app_name)
                    if model_class:
                        perms = get_perms_for_model(model_class, actions)
                        profil.permissions.add(*perms)

                # Permissions custom AidFi / planning / ged
                custom_perms_cfg = config.get("custom_permissions", {})
                for app_label, codenames in custom_perms_cfg.items():
                    perms = get_custom_permissions(app_label, codenames)
                    profil.permissions.add(*perms)

                # Permissions custom bénéficiaire (Meta.permissions)
                benef_custom = config.get("beneficiaire_custom", [])
                if benef_custom:
                    perms = get_custom_permissions("beneficiaire", benef_custom)
                    profil.permissions.add(*perms)

                # Permissions standard sur les modèles supplémentaires AidFi
                for _, model_class in additional_models.items():
                    if code_profil == "MDS_Administratifs":
                        actions = ["view"]
                    elif code_profil == "MDS_Agents_Sociaux":
                        actions = ["view", "add", "change"]
                    elif code_profil == "MDS_Cadres":
                        actions = ["view", "add", "change", "delete"]
                    elif code_profil == "DGAS_Direction":
                        actions = ["view"]
                    elif code_profil == "DITAS_Direction":
                        actions = ["view"]
                    elif code_profil == "SUPER_ADMIN":
                        actions = ["view", "add", "change", "delete"]
                    else:
                        actions = []

                    if actions:
                        perms = get_perms_for_model(model_class, actions)
                        profil.permissions.add(*perms)

            # --- Appliquer les flags métier ---
            for flag, value in config.get("flags", {}).items():
                setattr(profil, flag, value)

            profil.save()

            # Lier Profil ↔ Group (1-n) et synchroniser les permissions au niveau du Group
            profil.groupes.clear()
            profil.groupes.add(groupe)

            groupe.permissions.add(*profil.permissions.all())

            desc = config.get("description", "")
            self.stdout.write(
                f"  ✓ {code_profil}: {profil.permissions.count()} permissions - {desc}"
            )

        self.stdout.write(self.style.SUCCESS("\n✅ Initialisation CORE-COMPATIBLE terminée !"))
        self.stdout.write("")
        self.stdout.write("📌 Profils / Groupes disponibles (1:1) :")
        for nom in groupes_config.keys():
            self.stdout.write(f"   - {nom}")
        self.stdout.write("")
        self.stdout.write(
            "ℹ️  L'affectation des profils aux utilisateurs doit désormais "
            "automatiquement les placer dans le Group portant le même code "
            "(ex: profil MDS_Administratifs → groupe MDS_Administratifs)."
        )
