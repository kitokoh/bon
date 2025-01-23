

import os
import json
import random
import logging
from datetime import datetime
from time import sleep
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from mimetypes import guess_type
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException
from libs.automate import WebScraping

# Charger les variables d'environnement
load_dotenv()
CHROME_FOLDER = os.getenv("CHROME_FOLDER")
WAIT_MIN = int(os.getenv("WAIT_MIN", 1))  # Temps d'attente par défaut
PROFILE = os.getenv("PROFILE")
PUBLISH_LABEL = os.getenv("PUBLISH_LABEL", "Post")
VISIT_LABEL = os.getenv("VISIT_LABEL", "Visit")

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="scraper.log"
)
logger = logging.getLogger(__name__)

class Scraper(WebScraping):
    def __init__(self):
        """Initialise le scraper en chargeant les données et les sélecteurs."""
        current_folder = os.path.dirname(__file__)
        parent_folder = os.path.dirname(current_folder)

        # Chemins des fichiers JSON
        self.data_path = os.path.join(parent_folder, "data.json")
        self.data_pathx = os.path.join(parent_folder, "data1.json")
        self.selectors_path = os.path.join(parent_folder, "config", "selectors.json")

        # Charger les données JSON
        self.json_data = self.load_json(self.data_path)
        self.json_datax = self.load_json(self.data_pathx)

        # Charger les sélecteurs
        self.selectors = self.load_json(self.selectors_path)

        # Démarrer le navigateur
        super().__init__(chrome_folder=CHROME_FOLDER, start_killing=True, user_agent=True)

    def load_json(self, path):
        """Charge un fichier JSON."""
        try:
            with open(path, encoding="UTF-8") as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Erreur lors du chargement du fichier {path} : {e}")
            return {}

    def get_absolute_path(self, relative_path):
        """Convertit un chemin relatif en chemin absolu."""
        current_folder = os.path.dirname(os.path.abspath(__file__))
        return os.path.normpath(os.path.join(current_folder, relative_path))

    def is_image(self, file_path):
        """Vérifie si le fichier est une image."""
        if not os.path.exists(file_path):
            return False
        file_type, _ = guess_type(file_path)
        return file_type and file_type.startswith("image")

    def random_sleep(self, min_seconds=1, max_seconds=5):
        """Attend un délai aléatoire."""
        sleep(random.uniform(min_seconds, max_seconds))

    def detect_language(self):
        """Détecte la langue de l'interface utilisateur."""
        try:
            # Détecter la langue à partir de l'attribut 'lang' de l'élément <html>
            language_element = self.driver.find_element(By.CSS_SELECTOR, "html")
            lang = language_element.get_attribute("lang")
            print(f"Langue détectée : {lang}")
            return lang.split("-")[0]  # Retourne uniquement le code de langue (ex: "fr")
        except Exception as e:
            logger.error(f"Erreur lors de la détection de la langue : {e}")
            return "en"  # Langue par défaut

    def get_dynamic_label(self, selector_key):
        """Récupère un libellé dynamiquement en fonction de la langue détectée."""
        try:
            # Extraire le libellé d'un élément spécifique
            element = self.driver.find_element(By.CSS_SELECTOR, self.selectors[selector_key])
            label = element.text.strip()
            print(f"Libellé récupéré pour {selector_key} : {label}")
            return label
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du libellé pour {selector_key} : {e}")
            return None

    def upload_image(self, image_path):
        """Télécharge une image sur Facebook."""
        if not self.is_image(image_path):
            logger.error(f"Le fichier {image_path} n'est pas une image valide.")
            return False

        try:
            print(f"Tentative de téléchargement de l'image : {image_path}")
            self.click_js(self.selectors["show_image_input"])
            self.random_sleep()
            file_input = self.driver.find_element(By.CSS_SELECTOR, self.selectors["add_image"])
            file_input.send_keys(image_path)
            self.random_sleep()
            print(f"Image téléchargée avec succès : {image_path}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors du téléchargement de l'image {image_path} : {e}")
            return False

    def upload_images_parallel(self, image_paths):
        """Télécharge plusieurs images en parallèle."""
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self.upload_image, path) for path in image_paths]
            for future in futures:
                future.result()  # Attendre que chaque tâche soit terminée

    def post_in_groupsx(self):
        """Publie un post aléatoire dans un groupe aléatoire avec plusieurs images."""
        posts_done = []

        # Choisir un groupe aléatoire
        group = random.choice(self.json_datax["groups"])
        logger.info(f"Navigating to group: {group}")
        print(f"Navigation vers le groupe : {group}")
        self.set_page(group)
        self.random_sleep(3, 5)

        try:
            logger.info("Refreshing the page...")
            print("Rafraîchissement de la page...")
            self.refresh_selenium()
        except Exception as e:
            logger.error(f'Erreur lors du rafraîchissement de la page : {e}')
            return

        # Choisir un post aléatoire
        post_text = random.choice(self.json_datax["posts"])
        logger.info(f"Selected post text: {post_text}")
        print(f"Texte du post sélectionné : {post_text}")

        # Choisir jusqu'à 30 images aléatoires
        post_images = random.sample(self.json_datax["images"], min(30, len(self.json_datax["images"])))
        logger.info(f"Selected images: {post_images}")
        print(f"Images sélectionnées : {post_images}")

        # Ouvrir la zone de texte pour le post
        try:
            logger.info("Opening text input...")
            print("Ouverture de la zone de texte...")
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.selectors["display_input"]))
            ).click()
        except TimeoutException:
            logger.error("L'élément 'display_input' n'est pas devenu interactif après 10 secondes.")
            return
        except Exception as e:
            logger.error(f'Erreur en ouvrant la zone de texte : {e}')
            return

        self.random_sleep()

        # Écrire le texte du post
        try:
            logger.info("Writing post text...")
            print("Écriture du texte du post...")
            self.send_data(self.selectors["input"], post_text)
        except Exception as e:
            logger.error(f'Erreur en écrivant le texte : {e}')
            return

        # Télécharger les images
        self.upload_images_parallel([self.get_absolute_path(img) for img in post_images])

        # Soumettre le post
        try:
            logger.info("Submitting post...")
            print("Soumission du post...")
            self.click_js(self.selectors["submit"])
        except Exception as e:
            logger.error(f'Erreur en soumettant le post : {e}')
            return

        # Logs
        logger.info(f'Post réussi : "{post_text}" ({group})')
        print(f'Post réussi : "{post_text}" ({group})')
        posts_done.append([group, post_text])

        # Attendre avant de poster dans un autre groupe
        sleep(WAIT_MIN * 60)

    def post_in_groups(self):
        """Publie un post aléatoire dans chaque groupe avec une seule image."""
        posts_done = []
        for group in self.json_data["groups"]:
            self.set_page(group)
            sleep(5)

            try:
                self.refresh_selenium()
            except Exception as e:
                logger.error(f'Erreur lors du rafraîchissement de la page : {e}')
                continue

            # Choisir un post aléatoire
            post = random.choice(self.json_data["posts"])
            post_text = post["text"]
            post_image = post.get("image", "")

            # Ouvrir la zone de texte pour le post
            try:
                logger.info("Opening text input...")
                print("Ouverture de la zone de texte...")
                self.click_js(self.selectors["display_input"])
            except Exception as e:
                logger.error(f'Erreur en ouvrant la zone de texte : "{post_text}" ({group}) : {e}')
                continue

            sleep(2)  # Attendre que la zone de texte soit chargée

            # Écrire le texte du post
            try:
                logger.info("Writing post text...")
                print("Écriture du texte du post...")
                self.send_data(self.selectors["input"], post_text)
            except Exception as e:
                logger.error(f'Erreur en écrivant le texte : "{post_text}" ({group}) : {e}')
                continue

            # Télécharger l'image (si elle existe)
            if post_image:
                absolute_image_path = self.get_absolute_path(post_image)
                logger.info(f"Processing image: {absolute_image_path}")
                print(f"Traitement de l'image : {absolute_image_path}")

                if not os.path.exists(absolute_image_path):
                    logger.error(f'Image non trouvée : {absolute_image_path}')
                    continue

                try:
                    logger.info("Clicking image input...")
                    print("Clic sur l'input d'image...")
                    self.click_js(self.selectors["show_image_input"])
                    sleep(2)  # Attendre que l'input d'image soit prêt

                    # Trouver l'élément <input type="file"> et envoyer le chemin du fichier
                    logger.info("Sending file path to input...")
                    print("Envoi du chemin du fichier à l'input...")
                    file_input = self.driver.find_element(By.CSS_SELECTOR, self.selectors["add_image"])
                    file_input.send_keys(absolute_image_path)
                    sleep(2)  # Attendre que l'image soit téléchargée
                except Exception as e:
                    logger.error(f'Erreur en téléchargeant l\'image : {absolute_image_path} : {e}')
                    continue

            # Soumettre le post
            try:
                logger.info("Submitting post...")
                print("Soumission du post...")
                self.click_js(self.selectors["submit"])
            except Exception as e:
                logger.error(f'Erreur en soumettant le post : "{post_text}" ({group}) : {e}')
                continue

            # Logs
            logger.info(f'Post réussi : "{post_text}" ({group})')
            print(f'Post réussi : "{post_text}" ({group})')
            posts_done.append([group, post_text])

            # Attendre avant de poster dans un autre groupe
            sleep(WAIT_MIN * 11)

    def save_groups(self, keyword):
        """Recherche et enregistre les groupes correspondant à un mot-clé."""
        logger.info("Searching groups...")
        print(f"Recherche des groupes pour le mot-clé : {keyword}")
        search_page = f"https://www.facebook.com/groups/search/groups/?q={keyword}"
        self.set_page(search_page)
        sleep(3)

        links_num = 0
        tries_count = 0

        # Faire défiler pour charger tous les groupes
        while True:
            self.go_bottom()
            new_links_num = len(self.get_elems(self.selectors["group_link"]))
            if new_links_num == links_num:
                tries_count += 1
            else:
                links_num = new_links_num
                self.refresh_selenium()

            if tries_count == 3:
                break

        # Récupérer tous les liens des groupes
        links = self.get_attribs(self.selectors["group_link"], "href")
        logger.info(f"{len(links)} groupes trouvés et enregistrés")
        print(f"{len(links)} groupes trouvés et enregistrés")

        # Enregistrer les liens dans le fichier JSON
        if links:
            self.json_data["groups"] = links
            with open(self.data_path, "w", encoding="UTF-8") as file:
                json.dump(self.json_data, file, indent=4)

# Exemple d'utilisation
if __name__ == "__main__":
    scraper = Scraper()
    scraper.post_in_groupsx()