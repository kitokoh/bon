import os
import shutil

def clean_venv(venv_path):
    for root, dirs, files in os.walk(venv_path):
        for file in files:
            if file.endswith(('.pyd', '.so', '.dll', '.pyc')):
                file_path = os.path.join(root, file)
                print(f"Deleting: {file_path}")
                os.remove(file_path)
        for dir in dirs:
            if dir == '__pycache__':
                dir_path = os.path.join(root, dir)
                print(f"Deleting: {dir_path}")
                shutil.rmtree(dir_path)

if __name__ == "__main__":
    venv_path = "env1"  # Chemin vers votre dossier venv
    clean_venv(venv_path)