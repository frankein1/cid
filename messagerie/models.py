# messagerie/models.py - VERSION CORRIGÉE

from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from core.models import User
from core.mixins import AuditedMixin  # ← Seulement celui-ci
from ged.models import DocumentGED


class Message(AuditedMixin):  # ✅ Seulement AuditedMixin
    """Message 1-à-1 avec copie optionnelle et pièces jointes GED"""
    
    # Participants
    expediteur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='messages_envoyes'
    )
    
    destinataire = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='messages_recus'
    )
    
    copie = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages_en_copie',
        help_text="Cadre ou autre personne en copie"
    )
    
    # Liaison directe au bénéficiaire
    beneficiaire = models.ForeignKey(
        'beneficiaire.Beneficiaire',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages',
        help_text="Bénéficiaire concerné par ce message"
    )
    
    # Contenu
    objet = models.CharField(max_length=255)
    contenu = models.TextField()
    
    # Pièces jointes via GED
    pieces_jointes = models.ManyToManyField(
        DocumentGED,
        blank=True,
        related_name='messages_lies',
        help_text="Documents GED attachés au message"
    )
    
    # Lien générique vers un objet métier (optionnel)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    objet_lie = GenericForeignKey('content_type', 'object_id')
    
    reference = models.CharField(max_length=100, blank=True)
    
    # Fil de conversation
    reponse_a = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reponses'
    )
    
    # Métadonnées
    PRIORITE_CHOICES = [
        ('normale', 'Normale'),
        ('importante', 'Importante'),
        ('urgente', 'Urgente'),
    ]
    priorite = models.CharField(
        max_length=20,
        choices=PRIORITE_CHOICES,
        default='normale'
    )
    
    # Motifs approfondis
    MOTIF_CHOICES = [
        # Dossier et suivi
        ('suivi_dossier', 'Suivi de dossier'),
        ('piece_manquante', 'Pièce manquante'),
        ('validation_document', 'Validation de document'),
        ('mise_a_jour_situation', 'Mise à jour situation'),
        
        # Rendez-vous et planning
        ('demande_rdv', 'Demande de rendez-vous'),
        ('modification_rdv', 'Modification de rendez-vous'),
        ('annulation_rdv', 'Annulation de rendez-vous'),
        ('compte_rendu_rdv', 'Compte-rendu de rendez-vous'),
        
        # Bénéficiaire
        ('demande_beneficiaire', 'Demande du bénéficiaire'),
        ('information_beneficiaire', 'Information sur le bénéficiaire'),
        ('changement_situation', 'Changement de situation'),
        ('urgence_sociale', 'Urgence sociale'),
        
        # Financier
        ('question_aide', 'Question sur aide financière'),
        ('justificatif_paiement', 'Justificatif de paiement'),
        ('reclamation_paiement', 'Réclamation de paiement'),
        
        # Coordination
        ('coordination_equipe', 'Coordination équipe'),
        ('transmission_info', 'Transmission d\'information'),
        ('demande_avis', 'Demande d\'avis'),
        ('validation_cadre', 'Validation cadre'),
        
        # Administratif
        ('question_procedure', 'Question sur procédure'),
        ('demande_support', 'Demande de support'),
        ('signalement', 'Signalement'),
        
        # Autre
        ('autre', 'Autre motif'),
    ]
    motif = models.CharField(
        max_length=30,
        choices=MOTIF_CHOICES,
        default='autre',
        help_text="Motif du message"
    )
    
   
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['expediteur', '-created_at']),
            models.Index(fields=['destinataire', '-created_at']),
            models.Index(fields=['copie', '-created_at']),
            models.Index(fields=['beneficiaire', '-created_at']),
            models.Index(fields=['motif']),
        ]
    
    def __str__(self):
        beneficiaire_info = f" - {self.beneficiaire}" if self.beneficiaire else ""
        return f"{self.objet}{beneficiaire_info} - {self.expediteur.username} → {self.destinataire.username}"
    
    @property
    def fil_conversation(self):
        """Retourne le fil complet de conversation"""
        if self.reponse_a:
            racine = self.reponse_a
            while racine.reponse_a:
                racine = racine.reponse_a
            return Message.objects.filter(
                models.Q(id=racine.id) | models.Q(reponse_a=racine)
            ).order_by('created_at')
        return Message.objects.filter(
            models.Q(id=self.id) | models.Q(reponse_a=self)
        ).order_by('created_at')
    
    def nb_non_lus_pour(self, user):
        """Compte les messages non lus dans le fil pour cet utilisateur"""
        messages = self.fil_conversation.filter(
            models.Q(destinataire=user) | models.Q(copie=user)
        )
        return messages.exclude(
            statuts_lecture__utilisateur=user,
            statuts_lecture__lu=True
        ).count()


class StatutLecture(models.Model):
    """Statut de lecture par utilisateur"""
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='statuts_lecture'
    )
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE)
    lu = models.BooleanField(default=False)
    date_lecture = models.DateTimeField(null=True, blank=True)
    
    TYPE_RECEPTION_CHOICES = [
        ('destinataire', 'Destinataire'),
        ('copie', 'Copie'),
    ]
    type_reception = models.CharField(
        max_length=20,
        choices=TYPE_RECEPTION_CHOICES,
        default='destinataire'
    )
    
    class Meta:
        unique_together = ('message', 'utilisateur')
        indexes = [
            models.Index(fields=['utilisateur', 'lu']),
        ]
