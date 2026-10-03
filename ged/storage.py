# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

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

def pcloud_configure():
    """pCloud est actif dès que ses identifiants sont dans l'environnement."""
    return bool(os.environ.get('PCLOUD_USER') and os.environ.get('PCLOUD_PASSWORD'))


PCLOUD_PREFIX = "pc_"   # tous les identifiants de fichiers pCloud commencent ainsi


@deconstructible
class SeaweedFSStorage(Storage):
    """
    Stockage UNIQUE de la GED. Trois modes, par ordre de priorité :
      1. pCloud (WebDAV)  : si PCLOUD_USER et PCLOUD_PASSWORD sont définis
      2. temporaire /tmp  : sur Render sans pCloud (fichiers perdus au redémarrage)
      3. SeaweedFS        : en local
    """

    _pcloud_dossier_pret = False   # le dossier n'est créé qu'une fois par processus

    def __init__(self, master_url=None, filer_url=None, volume_url=None):
        self.master_url = master_url or getattr(settings, 'SEAWEEDFS_MASTER_URL', 'http://localhost:9333')
        self.filer_url = filer_url or getattr(settings, 'SEAWEEDFS_FILER_URL', 'http://localhost:8888')
        self.volume_url = volume_url or getattr(settings, 'SEAWEEDFS_VOLUME_URL', 'http://localhost:8080')

        # Toujours prêt pour relire d'anciens fichiers temporaires
        self.temp_dir = '/tmp/ged_docs'

        # --- MODE pCloud (prioritaire) ---
        self.use_pcloud = pcloud_configure()
        if self.use_pcloud:
            self.pcloud_url = os.environ.get('PCLOUD_WEBDAV_URL', 'https://ewebdav.pcloud.com').rstrip('/')
            self.pcloud_dossier = os.environ.get('PCLOUD_FOLDER', 'CID_GED').strip('/')
            self.pcloud_auth = (os.environ['PCLOUD_USER'], os.environ['PCLOUD_PASSWORD'])
            self.use_temporary = False
            return

        # --- MODE temporaire sur Render ---
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
        if self.use_pcloud:
            return self._save_pcloud(name, content)
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

        if fid.startswith(PCLOUD_PREFIX):
            return self._open_pcloud(fid)
        if self.use_temporary or self.use_pcloud:
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
        if fid.startswith(PCLOUD_PREFIX):
            return self._exists_pcloud(fid)
        if self.use_pcloud:
            return False   # nom de fichier brut : l'identifiant pCloud sera de toute façon unique
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
        if fid.startswith(PCLOUD_PREFIX):
            return self._delete_pcloud(fid)
        if self.use_temporary or self.use_pcloud:
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
        if fid.startswith(PCLOUD_PREFIX):
            return f"/media/ged/{fid}"   # le téléchargement passe toujours par la vue GED (droits vérifiés)
        if self.use_temporary:
            return f"/media/ged/{fid}"  # URL factice pour l'affichage
        else:
            return f"{self.filer_url}/{fid}"
    
    # ==================== INFO POUR DEBUG ====================
    
    def get_mode(self):
        if self.use_pcloud:
            return "pcloud"
        return "temporaire" if self.use_temporary else "seaweedfs"
    
    def get_info(self):
        """Pour debug dans l'admin"""
        if self.use_pcloud:
            return {'mode': 'pcloud', 'url': self.pcloud_url, 'dossier': self.pcloud_dossier}
        if self.use_temporary:
            import glob
            files = glob.glob(os.path.join(self.temp_dir, "*"))
            return {
                'mode': 'temporaire',
                'dossier': self.temp_dir,
                'fichiers': len(files)
            }
        return {'mode': 'seaweedfs', 'url': self.master_url}

    # ==================== MODE pCloud (WebDAV) ====================

    def _pcloud_chemin(self, fid):
        return f"{self.pcloud_url}/{self.pcloud_dossier}/{fid}"

    def _pcloud_preparer_dossier(self):
        """Crée le dossier de la GED sur pCloud s'il n'existe pas (une fois par processus)."""
        if SeaweedFSStorage._pcloud_dossier_pret:
            return
        r = requests.request(
            "MKCOL", f"{self.pcloud_url}/{self.pcloud_dossier}",
            auth=self.pcloud_auth, timeout=30,
        )
        # 201 = créé, 405 = existe déjà
        if r.status_code not in (201, 405):
            r.raise_for_status()
        SeaweedFSStorage._pcloud_dossier_pret = True

    def _save_pcloud(self, name, content):
        """Envoie le fichier sur pCloud, retourne l'identifiant (FID) à conserver en base."""
        self._pcloud_preparer_dossier()

        base = os.path.basename(name).replace(' ', '_')
        fid = f"{PCLOUD_PREFIX}{uuid.uuid4().hex[:16]}_{base}"[:100]

        if hasattr(content, 'seek'):
            content.seek(0)
        if hasattr(content, 'chunks'):
            data = b''.join(content.chunks())
        elif hasattr(content, 'read'):
            data = content.read()
        else:
            data = content

        r = requests.put(self._pcloud_chemin(fid), data=data, auth=self.pcloud_auth, timeout=120)
        r.raise_for_status()
        logger.info(f"☁️ [pCloud] {name} → {fid}")
        return fid

    def _open_pcloud(self, fid):
        r = requests.get(self._pcloud_chemin(fid), auth=self.pcloud_auth, timeout=120)
        if r.status_code == 404:
            raise FileNotFoundError(f"Fichier {fid} absent de pCloud")
        r.raise_for_status()
        return ContentFile(r.content, name=fid)

    def _exists_pcloud(self, fid):
        try:
            r = requests.head(self._pcloud_chemin(fid), auth=self.pcloud_auth, timeout=30)
            return r.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def _delete_pcloud(self, fid):
        try:
            r = requests.delete(self._pcloud_chemin(fid), auth=self.pcloud_auth, timeout=30)
            return r.status_code in (200, 204)
        except requests.exceptions.RequestException:
            return False
