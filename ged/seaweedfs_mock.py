"""
SeaweedFS Mock intelligent - Simule une vraie GED pour les démos
CORRIGÉ : Utilisation de MEDIA_ROOT pour la persistance
"""
import uuid
import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile

class SeaweedFSMock:
    """Mock intelligent qui stocke réellement les fichiers temporairement"""
    
    def __init__(self):
        # Utilisation de MEDIA_ROOT au lieu de /tmp pour persistance
        storage_path = getattr(settings, 'MEDIA_ROOT', '/tmp/ged_mock')
        self.storage = FileSystemStorage(location=os.path.join(storage_path, 'ged_mock'))
        self.files = {}
        print(f"✅ GED Mock activé (stockage persistant : {storage_path}/ged_mock)")
    
    def upload_file(self, file_content, name=None, **kwargs):
        """Upload un fichier et retourne un ID réaliste"""
        if hasattr(file_content, 'read'):
            # C'est un fichier Django uploadé
            content = file_content.read()
            original_name = file_content.name
        else:
            # C'est du contenu brut
            content = file_content
            original_name = name or f"document_{uuid.uuid4()}"
        
        # Générer un ID SeaweedFS réaliste
        fid = f"{uuid.uuid4().hex[:8]},{uuid.uuid4().hex[:8]}"  # Format: 3,01637037d6
        
        # Sauvegarder le fichier temporairement
        filename = f"{fid.replace(',', '_')}_{original_name}"
        self.storage.save(filename, ContentFile(content))
        
        self.files[fid] = {
            'filename': filename,
            'original_name': original_name,
            'size': len(content)
        }
        
        print(f"📄 [GED Mock] Upload: {original_name} → {fid} ({len(content)} bytes)")
        
        return {
            'fid': fid,
            'name': original_name,
            'size': len(content),
            'url': f'/ged/mock/download/{fid}/'
        }
    
    def get_file(self, fid):
        """Récupère un fichier mocké"""
        if fid not in self.files:
            return None
            
        file_info = self.files[fid]
        path = self.storage.path(file_info['filename'])
        
        with open(path, 'rb') as f:
            content = f.read()
        
        print(f"📥 [GED Mock] Téléchargement: {fid} → {file_info['original_name']}")
        return content
    
    def delete_file(self, fid):
        """Supprime un fichier mocké"""
        if fid in self.files:
            file_info = self.files[fid]
            self.storage.delete(file_info['filename'])
            del self.files[fid]
            print(f"🗑️ [GED Mock] Suppression: {fid}")
            return True
        return False
    
    def list_files(self):
        """Liste tous les fichiers mockés"""
        return [
            {
                'fid': fid,
                'name': info['original_name'],
                'size': info['size'],
                'uploaded_at': '2024-02-15'  # Date fixe pour la démo
            }
            for fid, info in self.files.items()
        ]

# Instance globale
seaweedfs_client = SeaweedFSMock()
