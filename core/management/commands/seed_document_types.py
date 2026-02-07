# core/management/commands/seed_document_types.py
from django.core.management.base import BaseCommand
from ged.models import DocumentType, DocumentCategorie

class Command(BaseCommand):
    help = 'Crée les types de documents par défaut pour la GED'
    
    def handle(self, *args, **options):
        # Liste complète des types de documents
        TYPES_DOCUMENTS = [
            {
                'code': 'CI',
                'nom': "Carte d'identité",
                'categorie': DocumentCategorie.IDENTITE,
                'extensions': ['jpg', 'jpeg', 'png', 'pdf'],
                'taille_max': 5,
                'sensible': True
            },
            {
                'code': 'PASSEPORT',
                'nom': "Passeport",
                'categorie': DocumentCategorie.IDENTITE,
                'extensions': ['jpg', 'jpeg', 'png', 'pdf'],
                'taille_max': 5,
                'sensible': True
            },
            {
                'code': 'TITRE_SEJOUR',
                'nom': "Titre de séjour",
                'categorie': DocumentCategorie.IDENTITE,
                'extensions': ['jpg', 'jpeg', 'png', 'pdf'],
                'taille_max': 5,
                'sensible': True
            },
            {
                'code': 'JUSTIF_DOM',
                'nom': "Justificatif de domicile",
                'categorie': DocumentCategorie.ADMINISTRATIF,
                'extensions': ['pdf', 'jpg', 'jpeg', 'png'],
                'taille_max': 5,
                'sensible': False
            },
            {
                'code': 'RIB',
                'nom': "Relevé d'identité bancaire",
                'categorie': DocumentCategorie.FINANCES,
                'extensions': ['pdf', 'jpg', 'jpeg', 'png'],
                'taille_max': 5,
                'sensible': True
            },
            {
                'code': 'AVIS_IMPOT',
                'nom': "Avis d'imposition",
                'categorie': DocumentCategorie.FINANCES,
                'extensions': ['pdf', 'jpg', 'jpeg', 'png'],
                'taille_max': 5,
                'sensible': True
            },
            {
                'code': 'ATTEST_SECU',
                'nom': "Attestation de sécurité sociale",
                'categorie': DocumentCategorie.SANTE,
                'extensions': ['pdf', 'jpg', 'jpeg', 'png'],
                'taille_max': 5,
                'sensible': False
            },
            {
                'code': 'CER_RSA',
                'nom': "Contrat d'Engagement Réciproque",
                'categorie': DocumentCategorie.CER,
                'extensions': ['pdf', 'doc', 'docx'],
                'taille_max': 10,
                'sensible': False
            },
            {
                'code': 'DECISION_RSA',
                'nom': "Décision RSA",
                'categorie': DocumentCategorie.FINANCES,
                'extensions': ['pdf', 'jpg', 'jpeg', 'png'],
                'taille_max': 5,
                'sensible': False
            },
            {
                'code': 'QUITTANCE',
                'nom': "Quittance de loyer",
                'categorie': DocumentCategorie.LOGEMENT,
                'extensions': ['pdf', 'jpg', 'jpeg', 'png'],
                'taille_max': 5,
                'sensible': False
            },
            {
                'code': 'BAIL',
                'nom': "Contrat de bail",
                'categorie': DocumentCategorie.LOGEMENT,
                'extensions': ['pdf', 'jpg', 'jpeg', 'png'],
                'taille_max': 10,
                'sensible': False
            },
            {
                'code': 'CV',
                'nom': "Curriculum Vitae",
                'categorie': DocumentCategorie.SOCIAL,
                'extensions': ['pdf', 'doc', 'docx'],
                'taille_max': 5,
                'sensible': False
            },
            {
                'code': 'PHOTO',
                'nom': "Photo d'identité",
                'categorie': DocumentCategorie.IDENTITE,
                'extensions': ['jpg', 'jpeg', 'png'],
                'taille_max': 2,
                'sensible': False
            },
            {
                'code': 'CERTIF_MED',
                'nom': "Certificat médical",
                'categorie': DocumentCategorie.SANTE,
                'extensions': ['pdf', 'jpg', 'jpeg', 'png'],
                'taille_max': 5,
                'sensible': True
            },
            {
                'code': 'AUTRE',
                'nom': "Autre document",
                'categorie': DocumentCategorie.DIVERS,
                'extensions': ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'xls', 'xlsx'],
                'taille_max': 10,
                'sensible': False
            }
        ]
        
        created_count = 0
        existing_count = 0
        
        for type_data in TYPES_DOCUMENTS:
            obj, created = DocumentType.objects.get_or_create(
                code=type_data['code'],
                defaults={
                    'nom': type_data['nom'],
                    'categorie': type_data['categorie'],
                    'extensions_autorisees': type_data['extensions'],
                    'taille_max_mb': type_data['taille_max'],
                    'est_sensible': type_data['sensible'],
                    'actif': True
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Créé: {obj.code} - {obj.nom}')
                )
                created_count += 1
            else:
                # Mise à jour si déjà existant
                obj.nom = type_data['nom']
                obj.categorie = type_data['categorie']
                obj.extensions_autorisees = type_data['extensions']
                obj.taille_max_mb = type_data['taille_max']
                obj.est_sensible = type_data['sensible']
                obj.actif = True
                obj.save()
                self.stdout.write(
                    self.style.WARNING(f'↻ Mis à jour: {obj.code} - {obj.nom}')
                )
                existing_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'\nRésumé:')
        )
        self.stdout.write(
            self.style.SUCCESS(f'- {created_count} nouveaux types créés')
        )
        self.stdout.write(
            self.style.SUCCESS(f'- {existing_count} types mis à jour')
        )
        self.stdout.write(
            self.style.SUCCESS(f'- Total en base: {DocumentType.objects.count()} types')
        )
