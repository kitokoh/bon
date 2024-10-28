import sys
from libs.scraper import Scraper
from check_license import is_license_valid

def force_utf8_encoding(filepath):
    """
    Force l'encodage UTF-8 du fichier donné si ce n'est pas déjà le cas.
    """
    try:
        # Tentative de lire le fichier en UTF-8
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
    except UnicodeDecodeError:
        # Si l'encodage n'est pas UTF-8, on le convertit en UTF-8
        print(f"Le fichier {filepath} n'est pas encodé en UTF-8. Conversion en cours...")
        with open(filepath, 'r', encoding='latin-1') as file:
            content = file.read()
        # On réécrit le fichier en UTF-8
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Le fichier {filepath} a été converti en UTF-8 avec succès.")
    except Exception as e:
        print(f"Erreur lors de la gestion du fichier {filepath}: {e}")
        sys.exit(1)

# Exemple : forcer l'encodage UTF-8 pour le fichier de licence
#license_file = 'chemin/vers/ton/fichier_de_licence.txt'
#  force_utf8_encoding(license_file)

# Vérification de la licence avant de démarrer
try:
    if is_license_valid():
        print("Licence valide. Démarrage du script principal...")
        scraper = Scraper()

        keyword = input("Enter keyword: ")
        scraper.save_groups(keyword)
    else:
        print("Licence invalide ou expirée. Fermeture de l'application.")
except Exception as e:
    print(f"Une erreur inattendue est survenue : {e}")
    sys.exit(1)
