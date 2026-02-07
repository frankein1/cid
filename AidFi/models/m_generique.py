"""
# AidFi/models/m_generique.py
Modèles GÉNÉRIQUES AidFi
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, FileExtensionValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
import os
import uuid

# --- CONSTANTES ---
STATUT_DEMANDE = [
    ('BROUILLON', 'Draft'), ('DEPOSEE', 'Submitted'), ('EN_INSTRUCTION', 'In progress'),
    ('VALIDE', 'Validated'), ('ACCORDEE', 'Granted'), ('AJO', 'Postponed'), ('ANNULEE', 'Cancelled'),
]

TYPE_PIECE_CHOICES = [
    ('IDENTITE', 'ID document'), ('LIVRET_FAMILLE', 'Family record book'), 
    ('RIB', 'Bank account details'), ('DOMICILE', 'Proof of address'),
    ('RESSOURCES', 'Income proof'), ('CHARGES', 'Expense proof'), ('AUTRE', 'Other document'),
]

MAX_FILE_MB = getattr(settings, 'AIDFI_MAX_FILE_MB', 5)

# --- FONCTIONS UTILITAIRES ---
def validate_file_size(file):
    if file.size > MAX_FILE_MB * 1024 * 1024:
        raise ValidationError(f"File cannot exceed {MAX_FILE_MB} MB.")

def aide_piece_upload_path(instance, filename):
    ext = filename.split('.')[-1].lower()
    date_str = timezone.now().strftime('%Y_%m_%d')
    random_str = uuid.uuid4().hex[:8]
    base_name = f"{date_str}_{random_str}.{ext}"

    beneficiaire_code = getattr(instance.demande.beneficiaire, 'code_interne', 'UNKNOWN')
    type_aide = (instance.demande.type_aide_code or 'type').lower()
    dossier = f"{type_aide}_{instance.demande.id or 'new'}"

    return os.path.join(
        'pieces_aidfi', type_aide, beneficiaire_code, dossier,
        instance.type_piece.lower(), base_name
    )

# MODÈLES GÉNÉRIQUES
class TypeAide(models.Model):
    code = models.CharField(max_length=50, unique=True)
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['code']
    def __str__(self): return f"{self.code} - {self.nom}"

class MotifDemande(models.Model):
    code = models.CharField(max_length=20)
    libelle = models.CharField(max_length=300)
    type_aide = models.ForeignKey(TypeAide, on_delete=models.CASCADE, related_name='motifs_demande')
    def __str__(self): return f"{self.type_aide.code} - {self.libelle}"

class DemandeAide(models.Model):
    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.CASCADE, related_name='demandes_aide')
    type_aide = models.ForeignKey(TypeAide, on_delete=models.PROTECT, related_name='demandes')
    type_aide_code = models.CharField(max_length=50, blank=True)
    motif_demande = models.ForeignKey(MotifDemande, on_delete=models.PROTECT, null=True, blank=True)
    demandeur = models.ForeignKey('beneficiaire.Beneficiaire',on_delete=models.PROTECT,related_name='demandes_formulees',help_text="Personne ayant formulé la demande (parent, jeune majeur, tuteur, etc.)")
    montant_sollicite = models.DecimalField(max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    statut = models.CharField(max_length=20, choices=STATUT_DEMANDE, default='BROUILLON')
    date_creation = models.DateTimeField(auto_now_add=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    evaluation_sociale = models.TextField(blank=True)
    numero_dossier = models.CharField(max_length=100, blank=True)
    
    def statut_badge_classes(self):
        return {"BROUILLON": "bg-gray-200 text-gray-700", "DEPOSEE": "bg-blue-100 text-blue-800",
                "EN_INSTRUCTION": "bg-yellow-100 text-yellow-800", "ACCORDEE": "bg-emerald-100 text-emerald-800"}.get(self.statut)
    
    def save(self, *args, **kwargs):
        if self.type_aide and not self.type_aide_code: self.type_aide_code = self.type_aide.code
        super().save(*args, **kwargs)

class SuiviDemande(models.Model):
    demande = models.ForeignKey(DemandeAide, on_delete=models.CASCADE, related_name='suivis')
    statut_precedent = models.CharField(max_length=50)
    statut_nouveau = models.CharField(max_length=50)
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    date_action = models.DateTimeField(auto_now_add=True)
    
class PieceJustificative(models.Model):
    demande = models.ForeignKey(DemandeAide, on_delete=models.CASCADE, related_name='pieces_justificatives')
    type_piece = models.CharField(max_length=50, choices=TYPE_PIECE_CHOICES)
    document_ged = models.ForeignKey('ged.DocumentGED', on_delete=models.SET_NULL, null=True, blank=True)
    statut = models.CharField(max_length=15, choices=[('EN_ATTENTE','Pending'), ('VALIDE','OK')], default='EN_ATTENTE')
