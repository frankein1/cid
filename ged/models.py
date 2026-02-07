"""
ged/models.py - CORE-DITAS

GED V1 CONSERVÉE + GED V2 VERSIONNÉE (EMPILÉE)

GED V2 ACTIVE
-------------
DocumentVersion est la source physique.
DocumentGED est un cache + métadonnées + sécurité.
La dernière version est toujours la version active.
"""

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone

from .storage import SeaweedFSStorage

import os
import hashlib
import uuid


def get_default_extensions():
    return ["pdf", "jpg", "jpeg", "png"]


class DocumentCategorie(models.TextChoices):
    IDENTITE = "identite", "Identité"
    ADMINISTRATIF = "administratif", "Administratif"
    FINANCES = "finances", "Finances"
    SANTE = "sante", "Santé"
    SOCIAL = "social", "Social"
    CER = "contrat RSA", "Contrat RSA"
    LOGEMENT = "logement", "Logement"
    DIVERS = "divers", "Divers"


class DocumentType(models.Model):
    code = models.CharField(max_length=15, unique=True)
    nom = models.CharField(max_length=200)
    categorie = models.CharField(max_length=50, choices=DocumentCategorie.choices)
    extensions_autorisees = models.JSONField(default=get_default_extensions)
    taille_max_mb = models.IntegerField(default=10)
    est_sensible = models.BooleanField(default=False)
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Type de document"
        ordering = ["categorie", "nom"]

    def __str__(self):
        return f"{self.get_categorie_display()} - {self.nom}"


class DocumentGED(models.Model):
    # -------------------------------
    # Liaison métier
    # -------------------------------
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    type_document = models.ForeignKey(DocumentType, on_delete=models.PROTECT)
    titre = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    date_expiration = models.DateField(null=True, blank=True)
    notification_envoyee = models.BooleanField(default=False)
    alerte_active = models.BooleanField(default=True)

    # -------------------------------
    # Cache GED V1
    # -------------------------------
    seaweedfs_id = models.CharField(max_length=100, null=True, blank=True)
    hash_md5 = models.CharField(max_length=32, blank=True, db_index=True)
    taille_octets = models.BigIntegerField(default=0)
    extension = models.CharField(max_length=10, blank=True)

    # -------------------------------
    # Sécurité
    # -------------------------------
    CONF_CHOICES = [
        ("PUBLIC", "Public DITAS"),
        ("RESTREINT", "MDS Uniquement"),
        ("CONFIDENTIEL", "Nominatif (Agents autorisés)"),
        ("TRES_CONFIDENTIEL", "Direction / Cadres uniquement"),
    ]

    confidentialite = models.CharField(
        max_length=20, choices=CONF_CHOICES, default="RESTREINT"
    )

    agents_autorises = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="documents_speciaux",
        blank=True,
    )

    # -------------------------------
    # Statut / audit
    # -------------------------------
    statut = models.CharField(max_length=20, default="VALIDE")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="ged_uploads",
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Document GED"
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def __str__(self):
        return f"{self.titre} ({self.extension})"

    # -------------------------------
    # Création initiale (V1)
    # -------------------------------
    @classmethod
    def create_from_buffer(
        cls,
        *,
        buffer,
        filename,
        content_object,
        type_document,
        user=None,
        confidentialite="RESTREINT",
        raison="Génération automatique",
        request=None,
    ):
        if not buffer:
            raise ValueError("Buffer vide")

        buffer.seek(0)
        raw = buffer.read()

        storage = SeaweedFSStorage()
        fid = storage.save(filename, ContentFile(raw, name=filename))

        content_type = ContentType.objects.get_for_model(content_object)

        doc = cls.objects.create(
            content_type=content_type,
            object_id=content_object.pk,
            type_document=type_document,
            titre=filename,
            description=raison,
            seaweedfs_id=fid,
            extension=os.path.splitext(filename)[1].lower().replace(".", ""),
            confidentialite=confidentialite,
            uploaded_by=user,
        )

        doc._uploaded_file = ContentFile(raw, name=filename)
        doc.save()

        doc.log_action("GENERATION", user, raison, request)
        return doc

    # -------------------------------
    # GED V2 – versionnement
    # -------------------------------
    def add_new_version(
        self,
        *,
        buffer,
        filename,
        user=None,
        raison="Nouvelle version",
        request=None,
    ):
        if not buffer:
            raise ValueError("Buffer vide")

        buffer.seek(0)
        raw = buffer.read()

        storage = SeaweedFSStorage()
        fid = storage.save(filename, ContentFile(raw, name=filename))

        last = self.versions.first()
        numero = last.numero + 1 if last else 1

        version = DocumentVersion.objects.create(
            document=self,
            numero=numero,
            seaweedfs_id=fid,
            extension=os.path.splitext(filename)[1].lower().replace(".", ""),
            taille_octets=len(raw),
            hash_md5=hashlib.md5(raw).hexdigest(),
            cree_par=user,
        )

        # cache V1
        self.extension = version.extension
        self.taille_octets = version.taille_octets
        self.hash_md5 = version.hash_md5
        self.save(update_fields=["extension", "taille_octets", "hash_md5"])

        self.log_action("NOUVELLE_VERSION", user, raison, request)
        return version

    def generate_hash(self, file_content):
        md5 = hashlib.md5()
        for chunk in file_content.chunks():
            md5.update(chunk)
        return md5.hexdigest()

    def save(self, *args, **kwargs):
        if hasattr(self, "_uploaded_file") and self._uploaded_file:
            self.hash_md5 = self.generate_hash(self._uploaded_file)
            self.taille_octets = self._uploaded_file.size
        super().save(*args, **kwargs)

    # -------------------------------
    # Sécurité
    # -------------------------------
    def peut_etre_vu_par(self, user):
        """
        Contrôle d'accès pour la consultation.
        - Vérifie la territorialité (MDS)
        - Vérifie la confidentialité
        - Vérifie les capacités CORE
        """
        if user.is_superuser:
            return True
        
        # 1. Vérification territoriale (via le bénéficiaire)
        if not user.peut_agir_sur_objet(self.content_object, "peut_voir"):
            return False
        
        # 2. Vérification de la confidentialité
        if self.confidentialite == "TRES_CONFIDENTIEL":
            return user.a_la_capacite("peut_valider")
        
        if self.confidentialite == "CONFIDENTIEL":
            return (
                self.agents_autorises.filter(pk=user.pk).exists()
                or user.a_la_capacite("peut_valider")
            )
        
        # PUBLIC ou RESTREINT : accessible si territorialité OK
        return True

    def peut_etre_modifie_par(self, user):
        """
        Contrôle pour la modification.
        - L'uploader d'origine peut modifier
        - Les cadres peuvent modifier
        """
        if user.a_la_capacite("peut_valider"):
            return True
        return self.uploaded_by == user

    def log_action(self, action, user, commentaire="", request=None):
        HistoriqueDocument.objects.create(
            document=self,
            document_titre_archive=self.titre,
            action=action,
            utilisateur=user,
            commentaire=commentaire,
            ip_address=request.META.get("REMOTE_ADDR") if request else None,
        )


class DocumentVersion(models.Model):
    document = models.ForeignKey(
        DocumentGED,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    numero = models.PositiveIntegerField()
    seaweedfs_id = models.CharField(max_length=100, unique=True)
    extension = models.CharField(max_length=10)
    taille_octets = models.BigIntegerField()
    hash_md5 = models.CharField(max_length=32, db_index=True)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-numero"]
        unique_together = ("document", "numero")

    def __str__(self):
        return f"{self.document.titre} v{self.numero}"


class HistoriqueDocument(models.Model):
    document = models.ForeignKey(
        DocumentGED,
        on_delete=models.SET_NULL,
        null=True,
        related_name="historique",
    )
    document_titre_archive = models.CharField(max_length=255)
    action = models.CharField(max_length=50)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    date_action = models.DateTimeField(auto_now_add=True)
    commentaire = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-date_action"]


class PartageDocument(models.Model):
    document = models.ForeignKey(
        DocumentGED,
        on_delete=models.CASCADE,
        related_name="partages",
    )
    token = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    email_destinataire = models.EmailField()
    date_creation = models.DateTimeField(auto_now_add=True)
    date_expiration = models.DateTimeField()
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    utilise = models.BooleanField(default=False)

    def est_valide(self):
        return not self.utilise and timezone.now() < self.date_expiration
