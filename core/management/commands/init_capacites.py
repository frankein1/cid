# core/management/commands/init_capacites.py
from django.core.management.base import BaseCommand
from core.models.capacite import Capacite

# Liste unique et centralisée de TOUTES les capacités du système
# (Core + AidFi + Autres modules)
CAPACITES = [
    # --- Lecture & Liste ---
    ('peut_voir', 'Voir'),
    ('peut_voir_stats', 'Voir statistiques'),
    ('peut_lister', 'Lister'),

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

    # --- Administration ---
    ('peut_administrer', 'Administrer'),
    ('peut_configurer', 'Configurer'),
    ('peut_gerer_utilisateurs', 'Gérer les utilisateurs'),

    # --- GED ---
    ('ged_televerser', 'GED – Téléverser'),
    ('ged_valider', 'GED – Valider'),
    ('ged_supprimer', 'GED – Supprimer'),

    # --- Planning ---
    ('planning_generer', 'Planning – Générer'),
    ('planning_bloquer', 'Planning – Bloquer'),
    ('planning_exporter', 'Planning – Exporter'),

    # --- SPÉCIFIQUES AIDFI (Ajoutés ici pour centralisation) ---
    ('peut_gestion_aides_aidfi', 'Gestion des aides AidFi'),
    ('peut_valider_cheque_aidfi', 'Valider chèques AidFi'),
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
