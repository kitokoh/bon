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
            print(f"Erreur lors du chargement du fichier {path} : {e}")
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
            print(f"Erreur lors de la détection de la langue : {e}")
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
            print(f"Erreur lors de la récupération du libellé pour {selector_key} : {e}")
            return None

    def upload_image(self, image_path):
        """Télécharge une image sur Facebook."""
        if not self.is_image(image_path):
            logger.error(f"Le fichier {image_path} n'est pas une image valide.")
            print(f"Le fichier {image_path} n'est pas une image valide.")
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
            print(f"Erreur lors du téléchargement de l'image {image_path} : {e}")
            return False

    def upload_images_parallel(self, image_paths):
        """Télécharge plusieurs images en parallèle."""
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self.upload_image, path) for path in image_paths]
            for future in futures:
                future.result()  # Attendre que chaque tâche soit terminée


    def post_in_groups(self):
        """Publie un post aléatoire dans chaque groupe avec une seule image."""
        for group in self.json_data["groups"]:
            post = random.choice(self.json_data["posts"])
            post_text = post["text"]
            post_image = post.get("image", "")
            post_images = [post_image] if post_image else []
            print(f"Publication dans le groupe : {group}")
            print(f"Texte du post : {post_text}")
            print(f"Image du post : {post_images}")
            self._post_in_group(group, post_text, post_images)

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

    def handle_captcha(self):
        """Gère les captchas en demandant à l'utilisateur de les résoudre manuellement."""
        try:
            WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors["captcha"]))
            )
            print("Veuillez résoudre le captcha manuellement.")
            WebDriverWait(self.driver, 300).until_not(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors["captcha"]))
            )
            print("Captcha résolu.")
        except TimeoutException:
            logger.error("Captcha non résolu à temps.")
            print("Captcha non résolu à temps.")
            raise

    def bypass_cloudflare(self, url):
        """Bypass Cloudflare protection."""
        self.set_page(url)
        sleep(10)  # Wait for Cloudflare challenge to complete
        self.driver.execute_script("window.stop();")

    def clear_browser_cache(self):
        """Clear browser cache."""
        self.driver.execute_script("window.localStorage.clear();")
        self.driver.execute_script("window.sessionStorage.clear();")
        self.driver.execute_cdp_cmd('Network.clearBrowserCache', {})

    def capture_network_traffic(self):
        """Capture network traffic."""
        logs = self.driver.get_log("performance")
        return logs

    def get_alert_text(self):
        """Get the text from an alert box."""
        try:
            WebDriverWait(self.driver, 10).until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            print(f"Texte de l'alerte : {alert_text}")
            return alert_text
        except TimeoutException:
            return None

    def dismiss_alert(self):
        """Dismiss an alert box."""
        try:
            WebDriverWait(self.driver, 10).until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            alert.dismiss()
            print("Alerte rejetée.")
        except TimeoutException:
            pass

    def accept_alert(self):
        """Accept an alert box."""
        try:
            WebDriverWait(self.driver, 10).until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            alert.accept()
            print("Alerte acceptée.")
        except TimeoutException:
            pass

    def restart_browser(self, time_out=0):
        """Restart the browser."""
        self.close_browser()
        self.__set_browser_instance__()
        if time_out > 0:
            self.driver.set_page_load_timeout(time_out)

    def refresh_page(self):
        """Refresh the current page."""
        self.driver.refresh()
        print("Page rafraîchie.")

    def close_browser(self):
        """Close the browser."""
        self.driver.quit()
        print("Navigateur fermé.")

    def execute_script(self, script, *args):
        """Execute a JavaScript script."""
        result = self.driver.execute_script(script, *args)
        print(f"Script exécuté avec succès : {script}")
        return result

    def wait_for_element(self, selector, time_out=10):
        """Wait for an element to be present."""
        try:
            WebDriverWait(self.driver, time_out).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            print(f"Élément trouvé avec le sélecteur : {selector}")
        except TimeoutException:
            print(f"Element with selector {selector} not found within {time_out} seconds")
            raise Exception(f"Element with selector {selector} not found within {time_out} seconds")

    def wait_for_element_to_be_clickable(self, selector, time_out=10):
        """Wait for an element to be clickable."""
        try:
            WebDriverWait(self.driver, time_out).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            print(f"Élément cliquable trouvé avec le sélecteur : {selector}")
        except TimeoutException:
            print(f"Element with selector {selector} not clickable within {time_out} seconds")
            raise Exception(f"Element with selector {selector} not clickable within {time_out} seconds")

    def wait_for_element_to_disappear(self, selector, time_out=10):
        """Wait for an element to disappear."""
        try:
            WebDriverWait(self.driver, time_out).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, selector)))
            print(f"Élément disparu avec le sélecteur : {selector}")
        except TimeoutException:
            print(f"Element with selector {selector} did not disappear within {time_out} seconds")
            raise Exception(f"Element with selector {selector} did not disappear within {time_out} seconds")
    
    def wait_for_text_to_be_present(self, selector, text, time_out=10):
        """Wait for specific text to be present in an element."""
        try:
            WebDriverWait(self.driver, time_out).until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, selector), text))
            print(f"Texte '{text}' trouvé dans l'élément avec le sélecteur : {selector}")
        except TimeoutException:
            print(f"Text '{text}' not present in element with selector {selector} within {time_out} seconds")
            raise Exception(f"Text '{text}' not present in element with selector {selector} within {time_out} seconds")
    
    def wait_for_title(self, title, time_out=10):
        """Wait for the page title to be a specific value."""
        try:
            WebDriverWait(self.driver, time_out).until(EC.title_is(title))
            print(f"Titre de la page trouvé : {title}")
        except TimeoutException:
            print(f"Title '{title}' not present within {time_out} seconds")
            raise Exception(f"Title '{title}' not present within {time_out} seconds")




    def wait_for_title_contains(self, title, time_out=10):
        """Wait for the page title to contain a specific value."""
        try:
            WebDriverWait(self.driver, time_out).until(EC.title_contains(title))
            print(f"Titre de la page contenant '{title}' trouvé")
        except TimeoutException:
            print(f"Title containing '{title}' not present within {time_out} seconds")
            raise Exception(f"Title containing '{title}' not present within {time_out} seconds")

    def add_comments(self):
        """Ajouter des commentaires au post publié."""
        comments = [
            "Super post !",
            "Merci pour le partage !",
            "Très intéressant !",
            "Top !",
            "J'aime beaucoup ce contenu."
        ]

        # Sélecteurs possibles pour le champ de commentaire
        possible_selectors = [
            "div.xdj266r.x11i5rnm.xat24cr.x1mh8g0r",
            "div.xi81zsa.xo1l8bm.xlyipyv.xuxw1ft.x49crj4.x1ed109x.xdl72j9.x1iyjqo2.xs83m0k.x6prxxf.x6ikm8r.x10wlt62.x1y1aw1k.xn6708d.xwib8y2.x1ye3gou"
        ]

        try:
            for selector in possible_selectors:
                try:
                    comment_inputs = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if comment_inputs:
                        comment_input = comment_inputs[0]
                        comment_button = self.driver.find_element(By.CSS_SELECTOR, "div[aria-label='Comment']")
                        comment_button.click()
                        for comment in random.sample(comments, k=random.randint(1, 2)):
                            try:
                                comment_input.click()
                                comment_input.send_keys(comment)
                                self.random_sleep()
                                self.click_js(self.selectors["submit_comment"])
                                self.random_sleep()
                                logger.info(f'Commentaire ajouté : "{comment}"')
                                print(f'Commentaire ajouté : "{comment}"')
                                break
                            except Exception as e:
                                logger.error(f'Erreur en ajoutant le commentaire : "{comment}" : {e}')
                                print(f'Erreur en ajoutant le commentaire : "{comment}" : {e}')
                        break
                except Exception as e:
                    continue
            else:
                logger.warning("Champ de commentaire non trouvé.")
                print("Champ de commentaire non trouvé.")
        except Exception as e:    
            pass

    def post_in_marketplace(self):
        """Publie un post dans la section Marketplace de Facebook."""
        try:
            self.set_page("https://www.facebook.com/marketplace/create/item")
            self.random_sleep(3, 5)

            # Titre de l'annonce
            title = random.choice(self.json_datax["titles"])
            self.send_data(self.selectors["marketplace_title"], title)

            # Prix de l'annonce
            price = "1"
            self.send_data(self.selectors["marketplace_price"], price)

            # Catégorie de l'annonce
            category = random.choice(self.json_datax["categories"])
            self.select_drop_down_text(self.selectors["marketplace_category"], category)

            # Description de l'annonce
            description = random.choice(self.json_datax["descriptions"])
            self.send_data(self.selectors["marketplace_description"], description)

            # Télécharger les images
            post_images = random.sample(self.json_datax["images"], min(10, len(self.json_datax["images"])))
            self.upload_images_parallel([self.get_absolute_path(img) for img in post_images])

            # Soumettre l'annonce
            self.click_js(self.selectors["marketplace_submit"])
            logger.info(f'Annonce publiée : "{title}" - "{price}" - "{description}"')
            print(f'Annonce publiée : "{title}" - "{price}" - "{description}"')

        except Exception as e:
            logger.error(f'Erreur lors de la publication dans le Marketplace : {e}')
            print(f'Erreur lors de la publication dans le Marketplace : {e}')





    def _post_in_group(self, group, post_text, post_images):
        """Méthode interne pour publier un post dans un groupe."""
        self.set_page(group)
        self.random_sleep(5, 7)

        # Rafraîchir la page
        try:
            self.refresh_selenium()
        except Exception as e:
            self._log_error(f'Erreur lors du rafraîchissement de la page : {e}')
            return

        # Ouvrir la zone de texte
        if not self._click_element(self.selectors["display_input"], "display_input"):
            return

        self.random_sleep()

        # Remplir le champ de texte
        if not self._fill_input(self.selectors["input"], post_text, "input"):
            return

        # Télécharger les images si elles sont fournies
        if post_images:
            try:
                self.upload_images_parallel([self.get_absolute_path(img) for img in post_images])
            except Exception as e:
                self._log_error(f"Erreur lors du téléchargement des images, publication du texte avec un thème : {e}")
                self._apply_theme()

        # Soumettre le post
        if not self._click_element(self.selectors["submit"], "submit"):
            return

        self._log_success(f'Post réussi : "{post_text}" ({group})')
        self.random_sleep(15, 20)
        self.add_comments()
        self.random_sleep(WAIT_MIN * 60, WAIT_MIN * 70)

    def _click_element(self, selector, element_name):
        """Tente de cliquer sur un élément et retourne True si réussi, False sinon."""
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            ).click()
            return True
        except TimeoutException:
            self._log_error(f"L'élément '{element_name}' n'est pas devenu interactif après 10 secondes.")
        except Exception as e:
            self._log_error(f'Erreur en cliquant sur l\'élément "{element_name}" : {e}')
        return False

    def _fill_input(self, selector, text, element_name):
        """Tente de remplir un champ de texte et retourne True si réussi, False sinon."""
        try:
            input_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            input_element.clear()
            input_element.send_keys(text)
            return True
        except TimeoutException:
            self._log_error(f"L'élément '{element_name}' n'est pas devenu interactif après 10 secondes.")
        except NoSuchElementException:
            self._log_error(f"Sélecteur '{element_name}' introuvable.")
        except ElementNotInteractableException:
            self._log_error(f"L'élément '{element_name}' n'est pas interactif.")
        except Exception as e:
            self._log_error(f'Erreur en écrivant le texte dans l\'élément "{element_name}" : {e}')
        return False

    def _apply_theme(self):
        """Applique un thème aléatoire au post."""
        try:
            self.click_js(self.selectors["display_themes"])
            self.random_sleep()
            self.click_js(self.selectors["theme"].replace("index", str(random.randint(1, 5))))
        except Exception as e:
            self._log_error(f'Erreur en appliquant le thème : {e}')

    def _log_error(self, message):
        """Log et affiche un message d'erreur."""
        logger.error(message)
        print(message)

    def _log_success(self, message):
        """Log et affiche un message de succès."""
        logger.info(message)
        print(message)
# Exemple d'utilisation
if __name__ == "__main__":
    scraper = Scraper()
    scraper.post_in_groupsx()
    scraper.post_in_marketplace()