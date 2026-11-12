# 📁 Emplacement : core/management/commands/init_capacites.py
# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

# core/management/commands/init_capacites.py
from django.core.management.base import BaseCommand
from core.models.capacite import Capacite

# Liste unique et centralisée de TOUTES les capacités du système
# (Core + AidFi + Autres modules)
CAPACITES = [
    # --- Lecture & Liste ---
    ('peut_voir', 'Voir'),
    ('peut_voir_stats', 'Voir statistiques'),
    ('stats_departement', "Statistiques de l'accompagnement de tout le département (comparaison des MDS, sans détail par agent)"),
    ('peut_lister', 'Lister'),
    ('peut_consulter_tous_usagers', 'Rechercher un usager dans toutes les MDS (identité, coordonnées, référent, famille)'),

    # --- CRUD Standard ---
    ('peut_creer', 'Créer'),
    ('peut_modifier', 'Modifier'),
    ('peut_supprimer', 'Supprimer'),

    # --- Instruction / Décision (Core) ---
    ('peut_instruire', 'Instruire'),
    ('peut_valider', 'Valider'),
    ('peut_decider', 'Décider'),
    ('peut_gerer_finance', 'Gérer finance'),
    ('peut_verser', 'Verser des aides'),
    ('ru_gerer_sas', 'Relation Usager – gérer les saisines et finalisations SAS'),

    # --- Administration ---
    ('peut_administrer', 'Administrer'),
    ('peut_configurer', 'Configurer'),
    ('peut_gerer_utilisateurs', 'Gérer les utilisateurs'),
    ('peut_gerer_acces', 'Gérer les comptes et les droits (toutes structures, sans accès aux dossiers)'),

    # --- GED ---
    ('ged_televerser', 'GED – Téléverser'),
    ('ged_valider', 'GED – Valider'),
    ('ged_supprimer', 'GED – Supprimer'),

    # --- RGPD ---
    ('rgpd_archiver', "RGPD – Archiver les dossiers inactifs de sa MDS (consulter et désarchiver les dossiers archivés)"),

    # --- Planning ---
    ('planning_generer', 'Planning – Générer'),
    ('planning_bloquer', 'Planning – Bloquer'),
    ('planning_exporter', 'Planning – Exporter'),
    ('planning_convoquer', 'Planning – Convoquer une réunion (voir les disponibilités, bloquer les agendas)'),

    # --- SPÉCIFIQUES AIDFI (Ajoutés ici pour centralisation) ---
    ('peut_gestion_aides_aidfi', 'Gestion des aides AidFi'),
    ('peut_valider_cheque_aidfi', 'CAP – Décider et remettre les chèques service (MDS)'),
    ('cap_regie_centrale', "Régie centrale : CAP remis en paierie et régies d'urgence"),
    ('ip_crip', "IP – CRIP : réception des informations préoccupantes et transmission aux MDS (toutes les IP)"),
    ('ip_pief', "IP – Inspecteur enfance famille : visa des rapports, validation des saisines du procureur"),
    ('ip_piloter', "IP – Piloter les IP de sa MDS (réunions, binôme, visas, saisines)"),
    ('ip_evaluer', "IP – Peut faire partie d'un binôme d'évaluation"),
    ('afase_controle', 'AFASE – UAGAF, unité administrative de gestion des aides financières (dossiers transmis par les MDS, demande de paiement au logiciel comptable)'),
    # --- RSA – INSERTION ---
    ('voir_journal_activite', "Consulter le journal d'activité des dossiers de sa MDS (consultations, modifications, exports)"),
    ('rsa_referentiel', "RSA – Gérer le référentiel départemental des actions d'insertion (saisie, import CSV)"),
    ('rsa_actions_locales', "RSA – Gérer les actions d'insertion locales de sa MDS"),
    ('rsa_pole_admin', "RSA – Administratif du pôle insertion (réception des contrats, délais)"),
    ('rsa_pole_cadre', "RSA – Cadre du pôle insertion (commissions de validation et de réorientation)"),
    ('rsa_pole_medecin', "RSA – Médecin du pôle insertion (contrats santé : certificat reçu, avis)"),
    # --- LOGEMENT – PRÉVENTION DES EXPULSIONS (Service Logement du Département) ---
    ('expulsion_sl_gestion', "Expulsions – Service Logement : saisie et suivi des dossiers de tous les territoires"),
    ('expulsion_sl_pilotage', "Expulsions – Service Logement : encadrement (supervision, suppression d'un dossier saisi par erreur)"),
    ('expulsion_sl_stats', "Expulsions – Statistiques départementales de la prévention des expulsions (lecture)"),
    ('peut_inscrire_aidfi', 'Inscription AidFi'),
    ('peut_consulter_dossiers_aidfi', 'Consulter dossiers AidFi'),
]

class Command(BaseCommand):
    help = "Initialise les capacités CORE et modules associés (AidFi inclus)"

    def handle(self, *args, **options):
        self.stdout.write("🔄 Initialisation des capacités métier...")
        created_count = 0
        updated_count = 0

        for code, nom in CAPACITES:
            cap, created = Capacite.objects.get_or_create(
                code=code,
                defaults={'nom': nom, 'actif': True}
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f"✓ Créé : {code}"))
                created_count += 1
            else:
                # Mise à jour si le nom a changé ou si actif était faux
                if cap.nom != nom or not cap.actif:
                    cap.nom = nom
                    cap.actif = True
                    cap.save()
                    self.stdout.write(self.style.WARNING(f"↻ Mis à jour : {code}"))
                    updated_count += 1
                else:
                    self.stdout.write(f"• Existe déjà : {code}")

        self.stdout.write(self.style.SUCCESS(f"\n✅ Terminé : {created_count} créées, {updated_count} mises à jour."))
