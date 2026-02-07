# mds/permissions.py
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_migrate

def create_mds_permissions(sender, **kwargs):
    """
    Crée les permissions personnalisées pour l'application MDS.
    Ces codenames doivent correspondre aux tests effectués dans views.py et les modèles.
    """
    # On évite les problèmes d'import circulaire en important à l'intérieur
    from django.apps import apps
    try:
        MDS = apps.get_model('mds', 'MDS')
        UserMDSProfile = apps.get_model('mds', 'UserMDSProfile')
        
        mds_ct = ContentType.objects.get_for_model(MDS)
        profile_ct = ContentType.objects.get_for_model(UserMDSProfile)

        # Liste des permissions à créer/vérifier
        # Le format est : (codename, nom_lisible, content_type)
        perms = [
            # Permissions liées à la MDS (Gestion globale et stats)
            ('gestion_utilisateurs_mds', 'Peut gérer les utilisateurs rattachés à la MDS', mds_ct),
            ('gestion_salles_mds', 'Peut gérer le paramétrage des salles de la MDS', mds_ct),
            ('voir_statistiques_mds', 'Peut accéder aux tableaux de bord statistiques', mds_ct),
            
            # Capacités métier (utilisées par a_la_capacite dans CORE)
            ('peut_voir_stats', 'Capacité : Consulter les statistiques métier', mds_ct),
            ('peut_creer', 'Capacité : Créer des dossiers/fiches dans la MDS', mds_ct),
            ('peut_valider', 'Capacité : Valider des actions métier', mds_ct),
            
            # Permissions liées aux profils
            ('affecter_profil_core', 'Peut modifier les profils CORE des agents', profile_ct),
        ]

        for codename, name, ct in perms:
            Permission.objects.get_or_create(
                codename=codename,
                content_type=ct,
                defaults={'name': name}
            )
        
        # Note: Pas de print ici en prod, mais utile en dev
        # print("✅ Permissions MDS alignées avec succès")
        
    except Exception as e:
        # Important : en phase de migration initiale, les tables peuvent ne pas exister
        pass

# Note : Dans les versions récentes de Django, on évite sender=None 
# et on préfère connecter le signal dans le apps.py
