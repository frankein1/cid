# ged/storage.py - Version 100% compatible Render
# NE nécessite PAS seaweedfs-bin, SEULEMENT requests

import os
import uuid
import requests
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from django.conf import settings
from django.core.files.base import ContentFile
import logging

logger = logging.getLogger(__name__)

def is_render_environment():
    """Détecte Render sans ambiguïté"""
    return os.environ.get('RENDER') is not None

@deconstructible
class SeaweedFSStorage(Storage):
    """
    Stockage UNIQUE qui sur Render utilise /tmp/, 
    sinon tente l'API REST SeaweedFS
    """
    
    def __init__(self, master_url=None, filer_url=None, volume_url=None):
        self.master_url = master_url or getattr(settings, 'SEAWEEDFS_MASTER_URL', 'http://localhost:9333')
        self.filer_url = filer_url or getattr(settings, 'SEAWEEDFS_FILER_URL', 'http://localhost:8888')
        self.volume_url = volume_url or getattr(settings, 'SEAWEEDFS_VOLUME_URL', 'http://localhost:8080')
        
        # DÉTECTION SIMPLE : sur Render → mode temporaire
        self.use_temporary = is_render_environment()
        
        if self.use_temporary:
            self.temp_dir = '/tmp/ged_docs'
            os.makedirs(self.temp_dir, exist_ok=True)
            logger.info(f"📁 Stockage TEMPORAIRE activé: {self.temp_dir}")
        else:
            logger.info(f"🌿 Tentative SeaweedFS: {self.master_url}")
    
    # ==================== CŒUR DU STOCKAGE ====================
    
    def _save(self, name, content):
        """Sauvegarde un fichier, retourne un FID"""
        if self.use_temporary:
            return self._save_temporary(name, content)
        else:
            # Essayer le vrai SeaweedFS, fallback temporaire si échec
            try:
                return self._save_seaweedfs(name, content)
            except Exception as e:
                logger.warning(f"SeaweedFS échoué, fallback temporaire: {e}")
                self.use_temporary = True
                self.temp_dir = '/tmp/ged_docs'
                os.makedirs(self.temp_dir, exist_ok=True)
                return self._save_temporary(name, content)
    
    def _save_temporary(self, name, content):
        """Sauvegarde temporaire (pour Render)"""
        fid = f"{uuid.uuid4().hex[:8]},{uuid.uuid4().hex[:8]}"
        safe_name = f"{fid.replace(',', '_')}_{name.replace('/', '_')}"
        path = os.path.join(self.temp_dir, safe_name)
        
        # Écrire le fichier
        if hasattr(content, 'chunks'):
            with open(path, 'wb') as f:
                for chunk in content.chunks():
                    f.write(chunk)
        elif hasattr(content, 'read'):
            with open(path, 'wb') as f:
                f.write(content.read())
        else:
            with open(path, 'wb') as f:
                f.write(content)
        
        logger.info(f"📄 [TEMP] {name} → {fid}")
        return fid
    
    def _save_seaweedfs(self, name, content):
        """Votre code REST API original (pour local)"""
        try:
            response = requests.get(f"{self.master_url}/dir/assign", timeout=5)
            response.raise_for_status()
            assignment = response.json()
            
            files = {'file': content}
            upload_response = requests.post(
                f"{self.volume_url}/{assignment['fid']}", 
                files=files, 
                timeout=10
            )
            upload_response.raise_for_status()
            
            logger.info(f"✅ [SeaweedFS] {name} → {assignment['fid']}")
            return assignment['fid']
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erreur SeaweedFS: {e}")
            raise
    
    def open(self, name, mode='rb'):
        """Ouvre un fichier par son FID"""
        fid = name
        
        if self.use_temporary:
            return self._open_temporary(fid)
        else:
            return self._open_seaweedfs(fid)
    
    def _open_temporary(self, fid):
        """Ouvre depuis le stockage temporaire"""
        import glob
        pattern = f"*{fid.replace(',', '_')}*"
        matches = glob.glob(os.path.join(self.temp_dir, pattern))
        
        if matches:
            with open(matches[0], 'rb') as f:
                return ContentFile(f.read(), name=fid)
        raise FileNotFoundError(f"Fichier {fid} non trouvé")
    
    def _open_seaweedfs(self, fid):
        """Votre code REST original"""
        try:
            response = requests.get(f"{self.volume_url}/{fid}", stream=True, timeout=5)
            response.raise_for_status()
            return ContentFile(response.content, name=fid)
        except requests.exceptions.RequestException as e:
            logger.error(f"Fichier {fid} introuvable: {e}")
            raise Exception("Erreur de lecture.")
    
    def exists(self, name):
        fid = name
        if self.use_temporary:
            import glob
            pattern = f"*{fid.replace(',', '_')}*"
            matches = glob.glob(os.path.join(self.temp_dir, pattern))
            return len(matches) > 0
        else:
            try:
                response = requests.head(f"{self.volume_url}/{fid}", timeout=3)
                return response.status_code == 200
            except:
                return False
    
    def delete(self, name):
        fid = name
        if self.use_temporary:
            import glob
            pattern = f"*{fid.replace(',', '_')}*"
            matches = glob.glob(os.path.join(self.temp_dir, pattern))
            for path in matches:
                os.remove(path)
            return bool(matches)
        else:
            try:
                response = requests.delete(f"{self.volume_url}/{fid}", timeout=5)
                return response.status_code == 200
            except:
                return False
    
    def url(self, name):
        fid = name
        if self.use_temporary:
            return f"/media/ged/{fid}"  # URL factice pour l'affichage
        else:
            return f"{self.filer_url}/{fid}"
    
    # ==================== INFO POUR DEBUG ====================
    
    def get_mode(self):
        return "temporaire" if self.use_temporary else "seaweedfs"
    
    def get_info(self):
        """Pour debug dans l'admin"""
        if self.use_temporary:
            import glob
            files = glob.glob(os.path.join(self.temp_dir, "*"))
            return {
                'mode': 'temporaire',
                'dossier': self.temp_dir,
                'fichiers': len(files)
            }
        return {'mode': 'seaweedfs', 'url': self.master_url}
