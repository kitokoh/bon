import os
import shutil

# Remplacez 'env1' par le chemin de votre environnement virtuel
venv_path = "env1"

# Extensions ou dossiers à supprimer
patterns_to_delete = ["__pycache__", ".pyc", ".pyo"]

def clean_venv(directory):
    for root, dirs, files in os.walk(directory):
        for name in dirs:
            if name in patterns_to_delete:
                dir_path = os.path.join(root, name)
                print(f"Suppression du dossier : {dir_path}")
                shutil.rmtree(dir_path)
        for name in files:
            if any(name.endswith(ext) for ext in patterns_to_delete):
                file_path = os.path.join(root, name)
                print(f"Suppression du fichier : {file_path}")
                os.remove(file_path)

clean_venv(venv_path)
print("Nettoyage terminé.")