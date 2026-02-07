# ged/storage.py

import requests
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from django.conf import settings
from django.core.files.base import ContentFile
import logging


logger = logging.getLogger(__name__)

@deconstructible
class SeaweedFSStorage(Storage):
    def __init__(self, master_url=None, filer_url=None, volume_url=None):
        self.master_url = master_url or getattr(settings, 'SEAWEEDFS_MASTER_URL', 'http://localhost:9333')
        self.filer_url = filer_url or getattr(settings, 'SEAWEEDFS_FILER_URL', 'http://localhost:8888')
        self.volume_url = volume_url or getattr(settings, 'SEAWEEDFS_VOLUME_URL', 'http://localhost:8080')

    def _save(self, name, content):
        try:
            response = requests.get(f"{self.master_url}/dir/assign")
            response.raise_for_status()
            assignment = response.json()
            files = {'file': content}
            upload_response = requests.post(f"{self.volume_url}/{assignment['fid']}", files=files)
            upload_response.raise_for_status()
            return assignment['fid']
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de l'upload vers SeaweedFS: {e}")
            raise Exception(f"Échec de l'upload vers SeaweedFS: {e}")

    def url(self, name):
        return f"{self.filer_url}/{name}"

    def open(self, name, mode='rb'):
        try:
            # On tape directement sur le volume server pour la performance
            response = requests.get(f"{self.volume_url}/{name}", stream=True)
            response.raise_for_status()
            # On retourne un ContentFile pour que Django sache quoi en faire
            return ContentFile(response.content, name=name)
        except requests.exceptions.RequestException as e:
            logger.error(f"Fichier {name} introuvable sur SeaweedFS: {e}")
            raise Exception("Erreur de lecture sur le cluster de stockage.")

    def exists(self, name):
        try:
            response = requests.head(f"{self.volume_url}/{name}")
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def delete(self, name):
        try:
            response = requests.delete(f"{self.volume_url}/{name}")
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la suppression du fichier {name}: {e}")
            return False
    
    def list_all_file_ids(self):
        raise NotImplementedError(
            "À implémenter selon l’API SeaweedFS (scan filer / index)"
        )
