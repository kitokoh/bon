"""
test.py — Exemple moderne avec Playwright (remplace l'ancienne version Selenium)
Ce fichier montre comment utiliser directement les composants Playwright du projet BON.
Pour une utilisation en production, préférez la CLI : python -m bon post --session <nom>
"""
import os
import json
import random
import logging
from datetime import datetime
from time import sleep
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from libs.playwright_engine import PlaywrightEngine
from libs.selector_registry import SelectorRegistry
from libs.timing_humanizer import human_delay
import emoji  # Bibliothèque pour gérer les émojis

# Charger les variables d'environnement
load_dotenv()
WAIT_MIN = int(os.getenv("WAIT_MIN", 1))  # Temps d'attente par défaut
PROFILE = os.getenv("PROFILE")
PUBLISH_LABEL = os.getenv("PUBLISH_LABEL", "Post")

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="scraper.log"
)
logger = logging.getLogger(__name__)


class ModernScraper:
    """
    Scraper moderne utilisant Playwright au lieu de Selenium.
    Version refactorisée et alignée sur l'architecture BON v4.0.
    """
    
    def __init__(self, headless: bool = False):
        """Initialise le scraper avec Playwright."""
        current_folder = Path(__file__).parent
        
        # Chemins des fichiers JSON
        self.data_path = current_folder / "data.json"
        self.data_pathx = current_folder / "data1.json"
        self.selectors_path = current_folder / "config" / "selectors.json"
        
        # Charger les données JSON
        self.json_data = self.load_json(self.data_path)
        self.json_datax = self.load_json(self.data_pathx)
        
        # Initialiser Playwright
        self.engine = PlaywrightEngine(headless=headless, slow_mo=50)
        self.selectors = None
        self.page = None
        self.context = None
        
    def load_json(self, path):
        """Charge un fichier JSON."""
        try:
            with open(path, encoding="UTF-8") as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Erreur lors du chargement du fichier {path} : {e}")
            return {"groups": [], "posts": [], "images": []}
    
    def start(self):
        """Démarre le navigateur et charge les sélecteurs."""
        self.engine.start()
        self.selectors = SelectorRegistry(self.selectors_path)
        self.context, self.page = self.engine.new_context()
        logger.info("Navigateur démarré avec Playwright")
        
    def stop(self):
        """Arrête proprement le navigateur."""
        try:
            if self.context:
                self.context.close()
            self.engine.stop()
            logger.info("Navigateur arrêté")
        except Exception as e:
            logger.error(f"Erreur à l'arrêt : {e}")
    
    def get_absolute_path(self, relative_path):
        """Convertit un chemin relatif en chemin absolu."""
        if not relative_path:
            return ""
        current_folder = Path(__file__).parent
        return str(current_folder / relative_path)
    
    def is_image(self, file_path):
        """Vérifie si le fichier est une image."""
        if not file_path or not Path(file_path).exists():
            return False
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        return Path(file_path).suffix.lower() in valid_extensions
    
    def navigate(self, url):
        """Navigue vers une URL."""
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            human_delay(2, 1)
            return True
        except Exception as e:
            logger.error(f"Erreur de navigation vers {url} : {e}")
            return False
    
    def upload_image(self, image_path):
        """Télécharge une image sur Facebook avec Playwright."""
        abs_path = self.get_absolute_path(image_path)
        if not self.is_image(abs_path):
            logger.error(f"Le fichier {image_path} n'est pas une image valide.")
            return False
        
        try:
            print(f"Tentative de téléchargement de l'image : {abs_path}")
            
            # Ouvrir le sélecteur d'images
            show_btn = self.selectors.find(self.page, "show_image_input", timeout=6000)
            show_btn.click()
            human_delay(1, 0.5)
            
            # Upload du fichier avec Playwright (API native)
            add_selector = self.selectors.get_candidates("add_image")
            if add_selector:
                self.page.set_input_files(add_selector[0], abs_path)
                human_delay(2, 1)
                print(f"Image téléchargée avec succès : {image_path}")
                return True
            else:
                logger.error("Sélecteur add_image non trouvé")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors du téléchargement de l'image {image_path} : {e}")
            return False
    
    def post_in_groupsx(self):
        """Publie un post aléatoire dans un groupe avec plusieurs images (mode multi)."""
        if not self.json_datax.get("groups"):
            logger.error("Aucun groupe configuré dans data1.json")
            return
        
        # Choisir un groupe aléatoire
        group = random.choice(self.json_datax["groups"])
        logger.info(f"Navigating to group: {group}")
        print(f"Navigation vers le groupe : {group}")
        
        if not self.navigate(group):
            return
        
        # Choisir un post aléatoire
        post_text = random.choice(self.json_datax["posts"])
        logger.info(f"Selected post text: {post_text}")
        print(f"Texte du post sélectionné : {post_text}")
        
        # Choisir jusqu'à 30 images aléatoires
        available_images = self.json_datax.get("images", [])
        post_images = random.sample(available_images, min(30, len(available_images))) if available_images else []
        logger.info(f"Selected images: {post_images}")
        print(f"Images sélectionnées : {len(post_images)} images")
        
        # Ouvrir la zone de texte pour le post
        try:
            logger.info("Opening text input...")
            print("Ouverture de la zone de texte...")
            btn = self.selectors.find(self.page, "display_input", timeout=10000)
            btn.click()
        except Exception as e:
            logger.error(f'Erreur en ouvrant la zone de texte : {e}')
            return
        
        human_delay(1, 0.5)
        
        # Écrire le texte du post
        try:
            logger.info("Writing post text...")
            print("Écriture du texte du post...")
            # Utiliser la bibliothèque emoji pour garantir une gestion correcte des émojis
            cleaned_text = emoji.emojize(emoji.demojize(post_text))  # Normaliser les émojis
            
            input_field = self.selectors.find(self.page, "input", timeout=8000)
            input_field.click()
            input_field.press_sequentially(cleaned_text, delay=random.randint(40, 120))
        except Exception as e:
            logger.error(f'Erreur en écrivant le texte : {e}')
            return
        
        # Télécharger les images
        for img in post_images:
            self.upload_image(img)
            human_delay(1, 0.5)
        
        # Soumettre le post
        try:
            logger.info("Submitting post...")
            print("Soumission du post...")
            submit_btn = self.selectors.find(self.page, "submit", timeout=10000)
            submit_btn.click()
            
            # Attendre que le post soit envoyé
            human_delay(5, 2)
            logger.info("Post envoyé avec succès.")
            print(f'Post réussi : "{post_text[:50]}..." ({group[:50]}...)')
            
        except Exception as e:
            logger.error(f'Erreur en soumettant le post : {e}')
            return
        
        # Attendre avant de poster dans un autre groupe
        sleep(WAIT_MIN * 60)
    
    def post_in_groups(self):
        """Publie un post aléatoire dans chaque groupe avec une seule image."""
        if not self.json_data.get("groups"):
            logger.error("Aucun groupe configuré dans data.json")
            return
        
        posts_done = []
        
        for idx, group in enumerate(self.json_data["groups"], 1):
            print(f"\n[{idx}/{len(self.json_data['groups'])}] Navigation vers : {group}")
            
            if not self.navigate(group):
                continue
            
            # Choisir un post aléatoire
            post = random.choice(self.json_data["posts"])
            post_text = post.get("text", "")
            post_image = post.get("image", "")
            
            # Ouvrir la zone de texte pour le post
            try:
                logger.info("Opening text input...")
                print("Ouverture de la zone de texte...")
                btn = self.selectors.find(self.page, "display_input", timeout=10000)
                btn.click()
            except Exception as e:
                logger.error(f'Erreur en ouvrant la zone de texte : "{post_text}" ({group}) : {e}')
                continue
            
            human_delay(2, 1)
            
            # Écrire le texte du post
            try:
                logger.info("Writing post text...")
                print("Écriture du texte du post...")
                cleaned_text = emoji.emojize(emoji.demojize(post_text))
                
                input_field = self.selectors.find(self.page, "input", timeout=8000)
                input_field.click()
                input_field.press_sequentially(cleaned_text, delay=random.randint(40, 120))
            except Exception as e:
                logger.error(f'Erreur en écrivant le texte : "{post_text}" ({group}) : {e}')
                continue
            
            # Télécharger l'image (si elle existe)
            if post_image:
                logger.info(f"Processing image: {post_image}")
                print(f"Traitement de l'image : {post_image}")
                if self.upload_image(post_image):
                    print("✓ Image uploadée")
                else:
                    print("✗ Échec upload image")
            
            # Soumettre le post
            try:
                logger.info("Submitting post...")
                print("Soumission du post...")
                submit_btn = self.selectors.find(self.page, "submit", timeout=10000)
                submit_btn.click()
                
                human_delay(5, 2)
                logger.info("Post envoyé avec succès.")
            except Exception as e:
                logger.error(f'Erreur en soumettant le post : "{post_text}" ({group}) : {e}')
                continue
            
            # Logs
            logger.info(f'Post réussi : "{post_text}" ({group})')
            print(f'✓ Post réussi : "{post_text[:50]}..."')
            posts_done.append([group, post_text])
            
            # Attendre avant de poster dans un autre groupe
            sleep(WAIT_MIN * 11)
        
        print(f"\n=== Résumé : {len(posts_done)} posts publiés ===")
    
    def save_groups(self, keyword):
        """Recherche et enregistre les groupes correspondant à un mot-clé."""
        logger.info(f"Searching groups for: {keyword}")
        search_url = f"https://www.facebook.com/groups/search/groups/?q={keyword}"
        
        if not self.navigate(search_url):
            return []
        
        # Scroll pour charger les résultats
        for _ in range(5):
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            human_delay(2, 1)
        
        # Extraire les URLs
        links = []
        try:
            elements = self.selectors.find_all(self.page, "group_link")
            for el in elements:
                href = el.get_attribute("href")
                if href and "facebook.com/groups/" in href:
                    clean = href.split("?")[0].rstrip("/") + "/"
                    if clean not in links:
                        links.append(clean)
        except Exception as e:
            logger.error(f"Erreur extraction liens : {e}")
        
        logger.info(f"{len(links)} groupes trouvés")
        print(f"{len(links)} groupes trouvés et enregistrés")
        
        # Mettre à jour le JSON
        if links:
            self.json_data["groups"] = links
            with open(self.data_path, "w", encoding="UTF-8") as file:
                json.dump(self.json_data, file, indent=4, ensure_ascii=False)
        
        return links


# Exemple d'utilisation
if __name__ == "__main__":
    print("=" * 60)
    print("BON — Test Moderne avec Playwright (v4.0)")
    print("Selenium est obsolète — Utilisation de Playwright")
    print("=" * 60)
    
    scraper = ModernScraper(headless=False)
    
    try:
        scraper.start()
        
        # Choisir le mode de test
        print("\nOptions:")
        print("1) Poster dans les groupes (1 image)")
        print("2) Poster multi-images")
        print("3) Sauvegarder des groupes")
        choice = input("Choix (1/2/3) : ").strip()
        
        if choice == "1":
            scraper.post_in_groups()
        elif choice == "2":
            scraper.post_in_groupsx()
        elif choice == "3":
            keyword = input("Mot-clé : ").strip()
            scraper.save_groups(keyword)
        else:
            print("Choix invalide")
    
    except KeyboardInterrupt:
        print("\n⚠ Interrupt par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur majeure : {e}")
        print(f"✗ Erreur : {e}")
    finally:
        scraper.stop()
        print("\n✓ Terminé")