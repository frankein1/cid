#!/usr/bin/env python3
import os

HEADER = '''# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

'''

def main():
    for root, dirs, files in os.walk('.'):
        # Ignorer les dossiers inutiles
        if '.git' in dirs:
            dirs.remove('.git')
        if '__pycache__' in dirs:
            dirs.remove('__pycache__')
        if 'migrations' in dirs:
            dirs.remove('migrations')
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Éviter de dupliquer
                if '© AGPL3' in content[:500]:
                    print(f"⏩ Déjà présent: {filepath}")
                    continue
                
                new_content = HEADER + content
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"✅ Ajouté: {filepath}")

if __name__ == '__main__':
    main()
