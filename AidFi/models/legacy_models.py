"""
FICHIER pour anciennes migrations AidFi (0005 spécifiquement)
Migration 0005 référence EXACTEMENT ces fonctions
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid, os

MAX_FILE_MB = getattr(settings, 'AIDFI_MAX_FILE_MB', 5)

def validate_file_size(file):
    """Migration 0005 référence cette fonction."""
    if file.size > MAX_FILE_MB * 1024 * 1024:
        raise ValidationError(f"File > {MAX_FILE_MB}MB")

def aide_piece_upload_path(instance, filename):
    """Migration 0005 référence CETTE fonction EXACTE."""
    ext = filename.split('.')[-1].lower()
    date_str = timezone.now().strftime('%Y_%m_%d')
    random_str = uuid.uuid4().hex[:8]
    base_name = f"{date_str}_{random_str}.{ext}"
    return os.path.join('pieces_aidfi', 'legacy', base_name)
