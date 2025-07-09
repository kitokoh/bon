import os
import sys # Added for sys.exit
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
PROFILE = os.getenv("PROFILE") # Currently unused in Scraper from quick scan
PUBLISH_LABEL = os.getenv("PUBLISH_LABEL", "Post") # Currently unused
VISIT_LABEL = os.getenv("VISIT_LABEL", "Visit") # Currently unused

# Configuration du logging
# This basicConfig will only work if no other part of the application (e.g. __main__.py)
# has already configured the root logger. It's safer to configure logging at the application entry point.
# For now, assuming this is the primary logging setup.
logging.basicConfig(
    level=logging.INFO, # Consider making this configurable (e.g., from .env)
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", # Added logger name
    filename="scraper.log", # Consider making filename configurable
    filemode='a' # Append mode
)
logger = logging.getLogger(__name__)

class Scraper(WebScraping):
    def __init__(self):
        """Initialise le scraper en chargeant les données et les sélecteurs."""
        logger.info("[Scraper.__init__] Initializing Scraper instance.")

        # Validate essential environment variables
        if not CHROME_FOLDER:
            logger.critical("[Scraper.__init__] CRITICAL: CHROME_FOLDER environment variable is not set. This is required for browser operation. Exiting.")
            print("ERREUR CRITIQUE: La variable d'environnement CHROME_FOLDER n'est pas définie. Veuillez la configurer dans votre fichier .env ou système.")
            sys.exit(1)
        else:
            logger.info(f"[Scraper.__init__] CHROME_FOLDER is set to: {CHROME_FOLDER}")

        current_folder = os.path.dirname(__file__)
        parent_folder = os.path.dirname(current_folder)
        logger.debug(f"[Scraper.__init__] Script parent folder: {parent_folder}")

        # Define paths for configuration files
        self.data_path = os.path.join(parent_folder, "data.json")
        self.data_pathx = os.path.join(parent_folder, "data1.json") # For marketplace
        self.selectors_path = os.path.join(parent_folder, "config", "selectors.json")
        logger.debug(f"[Scraper.__init__] Core data path: {self.data_path}")
        logger.debug(f"[Scraper.__init__] Marketplace data path: {self.data_pathx}")
        logger.debug(f"[Scraper.__init__] Selectors config path: {self.selectors_path}")

        # Validate existence of critical configuration files
        critical_files = {
            "Core data file (data.json)": self.data_path,
            "Selectors file (selectors.json)": self.selectors_path
        }
        for name, path in critical_files.items():
            if not os.path.exists(path):
                logger.critical(f"[Scraper.__init__] CRITICAL: {name} not found at {path}. This file is required. Exiting.")
                print(f"ERREUR CRITIQUE: Le fichier {name} est introuvable à l'emplacement {path}. Ce fichier est nécessaire.")
                sys.exit(1)

        # Check for optional marketplace data file
        if not os.path.exists(self.data_pathx):
            logger.warning(f"[Scraper.__init__] WARNING: Marketplace data file (data1.json) not found at {self.data_pathx}. Marketplace functions may not work as expected.")
            # print(f"AVERTISSEMENT: Le fichier data1.json (pour Marketplace) est introuvable à {self.data_pathx}.")


        # Load JSON data (load_json method already logs success/failure)
        logger.info("[Scraper.__init__] Loading core data from data.json.")
        self.json_data = self.load_json(self.data_path)
        logger.info("[Scraper.__init__] Loading marketplace data from data1.json.")
        self.json_datax = self.load_json(self.data_pathx)

        # Charger les sélecteurs
        logger.info("[Scraper.__init__] Loading selectors from config/selectors.json.")
        self.selectors = self.load_json(self.selectors_path)

        if not self.json_data or not self.selectors:
            logger.critical("[Scraper.__init__] Core data (data.json) or selectors (selectors.json) failed to load. Scraper may not function correctly.")
            # Consider raising an exception or exiting if these are critical

        logger.info("[Scraper.__init__] Initializing WebScraping superclass.")
        # Démarrer le navigateur
        super().__init__(chrome_folder=CHROME_FOLDER, start_killing=True, user_agent=True)
        logger.info("[Scraper.__init__] Scraper instance initialized.")

    def load_json(self, path):
        """Charge un fichier JSON."""
        logger.info(f"[Scraper.load_json] Attempting to load JSON from: {path}")
        try:
            with open(path, encoding="UTF-8") as file:
                data = json.load(file)
                logger.info(f"[Scraper.load_json] Successfully loaded JSON from: {path}")
                return data
        except FileNotFoundError:
            logger.error(f"[Scraper.load_json] File not found: {path}")
            # print(f"Erreur: Le fichier {path} est introuvable.") # Keep print if user needs direct feedback
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"[Scraper.load_json] Error decoding JSON from file {path}: {e}")
            # print(f"Erreur: Impossible de décoder le JSON du fichier {path}. Vérifiez le format.")
            return {}
        except Exception as e:
            logger.error(f"[Scraper.load_json] An unexpected error occurred while loading {path}: {e}")
            # print(f"Erreur inattendue lors du chargement du fichier {path}: {e}")
            return {}

    def get_absolute_path(self, relative_path):
        """Convertit un chemin relatif en chemin absolu par rapport au dossier courant du script."""
        # This assumes relative_path is relative to the script's directory (libs)
        logger.debug(f"[Scraper.get_absolute_path] Converting relative path '{relative_path}' to absolute.")
        current_folder = os.path.dirname(os.path.abspath(__file__))
        abs_path = os.path.normpath(os.path.join(current_folder, relative_path))
        logger.debug(f"[Scraper.get_absolute_path] Absolute path: '{abs_path}'.")
        return abs_path

    def is_image(self, file_path):
        """Vérifie si le fichier est une image en se basant sur son type MIME."""
        logger.debug(f"[Scraper.is_image] Checking if '{file_path}' is an image.")
        if not os.path.exists(file_path):
            logger.warning(f"[Scraper.is_image] File does not exist: {file_path}")
            return False
        file_type, _ = guess_type(file_path)
        is_img = file_type and file_type.startswith("image")
        logger.debug(f"[Scraper.is_image] Path: '{file_path}', MIME type: {file_type}, Is image: {is_img}")
        return is_img

    def random_sleep(self, min_seconds=1, max_seconds=5):
        """Attend un délai aléatoire entre min_seconds et max_seconds."""
        sleep_duration = random.uniform(min_seconds, max_seconds)
        logger.info(f"[Scraper.random_sleep] Sleeping for {sleep_duration:.2f} seconds (range: {min_seconds}-{max_seconds}s).")
        sleep(sleep_duration)

    def detect_language(self):
        """Détecte la langue de l'interface utilisateur à partir de l'attribut lang de l'élément <html>."""
        logger.info("[Scraper.detect_language] Attempting to detect UI language.")
        try:
            language_element = self.driver.find_element(By.CSS_SELECTOR, "html")
            lang_attr = language_element.get_attribute("lang")
            if lang_attr:
                lang_code = lang_attr.split("-")[0]
                logger.info(f"[Scraper.detect_language] Detected language attribute 'lang={lang_attr}', using code: '{lang_code}'.")
                # print(f"Langue détectée : {lang_code}") # Keep for direct user feedback if needed
                return lang_code
            else:
                logger.warning("[Scraper.detect_language] 'lang' attribute not found on <html> tag. Defaulting to 'en'.")
                return "en"
        except Exception as e:
            logger.error(f"[Scraper.detect_language] Error detecting language: {e}. Defaulting to 'en'.")
            # print(f"Erreur lors de la détection de la langue : {e}") # Keep for direct user feedback
            return "en"

    def get_dynamic_label(self, selector_key):
        """Récupère un libellé dynamiquement en fonction de la langue détectée (non utilisé actuellement au profit de selectors.json exhaustif)."""
        # This method seems unused in favor of the comprehensive selectors.json.
        # If it were to be used, it would need robust error handling and clear logging.
        logger.info(f"[Scraper.get_dynamic_label] Attempting to get dynamic label for selector key: '{selector_key}'.")
        try:
            selector = self.selectors.get(selector_key)
            if not selector:
                logger.error(f"[Scraper.get_dynamic_label] Selector key '{selector_key}' not found in selectors config.")
                return None

            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            label = element.text.strip()
            logger.info(f"[Scraper.get_dynamic_label] Retrieved label for '{selector_key}' (selector: '{selector}'): '{label}'.")
            # print(f"Libellé récupéré pour {selector_key} : {label}") # Keep for direct user feedback
            return label
        except Exception as e:
            logger.error(f"[Scraper.get_dynamic_label] Error retrieving label for '{selector_key}': {e}")
            # print(f"Erreur lors de la récupération du libellé pour {selector_key} : {e}") # Keep for direct user feedback
            return None

    def upload_image(self, image_path):
        """Télécharge une image sur Facebook."""
        # is_image already logs
        if not self.is_image(image_path):
            # Error already logged by is_image if file doesn't exist, or it's not an image
            # Adding a specific log here might be redundant or provide more context
            logger.error(f"[Scraper.upload_image] Skipping upload for invalid image or non-existent file: {image_path}")
            # print(f"Le fichier {image_path} n'est pas une image valide.") # Keep for direct user feedback
            return False

        logger.info(f"[Scraper.upload_image] Attempting to upload image: {image_path}")
        try:
            # print(f"Tentative de téléchargement de l'image : {image_path}") # Replaced by logger
            logger.debug(f"[Scraper.upload_image] Clicking 'show_image_input' (selector: {self.selectors['show_image_input']})")
            self.click_js(self.selectors["show_image_input"]) # click_js has logging
            self.random_sleep() # Has logging

            logger.debug(f"[Scraper.upload_image] Finding file input element (selector: {self.selectors['add_image']})")
            file_input = self.driver.find_element(By.CSS_SELECTOR, self.selectors["add_image"])
            logger.debug(f"[Scraper.upload_image] Sending keys (image path) to file input: {image_path}")
            file_input.send_keys(image_path) # This needs to be an absolute path for send_keys to work reliably
            self.random_sleep()
            logger.info(f"[Scraper.upload_image] Image '{image_path}' uploaded successfully (file input sent).")
            # print(f"Image téléchargée avec succès : {image_path}") # Replaced by logger
            return True
        except Exception as e:
            logger.error(f"[Scraper.upload_image] Error during image upload for '{image_path}': {e}")
            # print(f"Erreur lors du téléchargement de l'image {image_path} : {e}") # Keep for direct user feedback
            return False

    def upload_images_parallel(self, image_paths):
        """Télécharge plusieurs images en parallèle en utilisant ThreadPoolExecutor."""
        # Note: Selenium WebDriver instances are generally not thread-safe.
        # Parallel execution of WebDriver commands (like find_element, click, send_keys) across threads
        # on the SAME driver instance can lead to unpredictable behavior and errors.
        # This method might be problematic if self.upload_image uses self.driver extensively.
        # For true parallel UI operations, multiple independent driver instances would be needed.
        # If upload_image is simple enough (e.g., just one send_keys after setup), it *might* work, but it's risky.
        logger.warning("[Scraper.upload_images_parallel] Attempting parallel image upload. Note: WebDriver is not inherently thread-safe. This may lead to issues.")
        num_images = len(image_paths)
        logger.info(f"[Scraper.upload_images_parallel] Starting parallel upload for {num_images} images.")

        results = []
        # Limiting max_workers as browser interactions might be the bottleneck, not I/O
        with ThreadPoolExecutor(max_workers=min(num_images, 3)) as executor:
            futures = [executor.submit(self.upload_image, path) for path in image_paths]
            for i, future in enumerate(futures):
                try:
                    result = future.result()  # Wait for each task to complete
                    results.append(result)
                    logger.info(f"[Scraper.upload_images_parallel] Upload task {i+1}/{num_images} (path: {image_paths[i]}) completed with result: {result}")
                except Exception as e:
                    logger.error(f"[Scraper.upload_images_parallel] Exception from parallel upload task for {image_paths[i]}: {e}")
                    results.append(False) # Assume failure on exception from future
        successful_uploads = sum(1 for r in results if r is True)
        logger.info(f"[Scraper.upload_images_parallel] Parallel upload process finished. {successful_uploads}/{num_images} images reported success.")


    def post_in_groups(self):
        """Publie un post aléatoire dans chaque groupe listé dans data.json avec une seule image."""
        logger.info(f"[Scraper.post_in_groups] Starting 'post_in_groups' process for {len(self.json_data.get('groups', []))} groups.")
        if not self.json_data.get("groups"):
            logger.warning("[Scraper.post_in_groups] No groups found in data.json. Aborting.")
            return
        if not self.json_data.get("posts"):
            logger.warning("[Scraper.post_in_groups] No post templates found in data.json. Aborting.")
            return

        for i, group_url in enumerate(self.json_data["groups"]):
            logger.info(f"[Scraper.post_in_groups] Processing group {i+1}/{len(self.json_data['groups'])}: {group_url}")
            try:
                post_template = random.choice(self.json_data["posts"])
                post_text = post_template["text"]
                post_image_rel_path = post_template.get("image", "")

                # Use get_absolute_path for the image
                post_image_abs_path = self.get_absolute_path(post_image_rel_path) if post_image_rel_path else ""

                post_images_to_upload = [post_image_abs_path] if post_image_abs_path else []

                logger.info(f"[Scraper.post_in_groups] Posting to group: {group_url}")
                logger.debug(f"[Scraper.post_in_groups] Post text: '{post_text[:100]}{'...' if len(post_text)>100 else ''}'")
                if post_images_to_upload:
                    logger.debug(f"[Scraper.post_in_groups] Post image: {post_images_to_upload[0]}")
                else:
                    logger.debug("[Scraper.post_in_groups] No image for this post.")

                # print(f"Publication dans le groupe : {group_url}") # Replaced by logger
                # print(f"Texte du post : {post_text}") # Replaced by logger
                # print(f"Image du post : {post_images_to_upload}") # Replaced by logger

                self._post_in_group(group_url, post_text, post_images_to_upload)
            except Exception as e:
                logger.error(f"[Scraper.post_in_groups] Unhandled error while processing group {group_url}: {e}")
                # Decide if to continue to the next group or stop
                logger.info(f"[Scraper.post_in_groups] Skipping to next group due to error.")
        logger.info("[Scraper.post_in_groups] Finished 'post_in_groups' process.")


    def save_groups(self, keyword):
        """Recherche et enregistre les groupes correspondant à un mot-clé."""
        logger.info(f"[Scraper.save_groups] Starting group search for keyword: '{keyword}'.")
        # print(f"Recherche des groupes pour le mot-clé : {keyword}") # Replaced by logger

        search_page = f"https://www.facebook.com/groups/search/groups/?q={keyword}"
        logger.debug(f"[Scraper.save_groups] Navigating to search page: {search_page}")
        self.set_page(search_page) # Has logging
        # Consider a more robust wait after page load, e.g., wait_for_element for a known element on search results
        logger.info(f"[Scraper.save_groups] Initial sleep for 3s after navigating to search page.")
        sleep(3)

        links_num = 0
        tries_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 10 # Prevent infinite loop if new links always appear or page is too long

        logger.info("[Scraper.save_groups] Starting scroll loop to load all groups.")
        # Faire défiler pour charger tous les groupes
        while tries_count < 3 and scroll_attempts < max_scroll_attempts:
            scroll_attempts += 1
            logger.debug(f"[Scraper.save_groups] Scroll attempt #{scroll_attempts}. Current links: {links_num}, Tries without new links: {tries_count}.")
            self.go_bottom() # Has logging
            self.random_sleep(1,2) # Short sleep after scroll to allow content to load

            # It's crucial that self.selectors["group_link"] is accurate
            # get_elems has its own logging
            current_elements = self.get_elems(self.selectors["group_link"])
            new_links_num = len(current_elements)

            if new_links_num == links_num:
                tries_count += 1
                logger.info(f"[Scraper.save_groups] No new group links found on scroll attempt {scroll_attempts}. Tries count incremented to {tries_count}.")
            else:
                logger.info(f"[Scraper.save_groups] Found {new_links_num - links_num} new group links. Total now: {new_links_num}.")
                links_num = new_links_num
                tries_count = 0 # Reset tries count as new links were found
                # self.refresh_selenium() # This seems disruptive; try without first or use a less disruptive wait/action.
                                        # If refresh_selenium is indeed needed, its internal logging is already improved.
                                        # Consider if this refresh is truly necessary or if waiting for a specific element change is better.
                logger.debug(f"[Scraper.save_groups] Resetting no-new-link tries count to 0.")

            if tries_count >= 3:
                logger.info("[Scraper.save_groups] Reached 3 consecutive scrolls with no new group links. Ending scroll loop.")
                break
            if scroll_attempts >= max_scroll_attempts:
                logger.warning(f"[Scraper.save_groups] Reached max scroll attempts ({max_scroll_attempts}). Ending scroll loop to prevent infinite scrolling.")
                break

        logger.info("[Scraper.save_groups] Scroll loop finished. Retrieving group links.")
        # Récupérer tous les liens des groupes
        # get_attribs has its own logging
        links = self.get_attribs(self.selectors["group_link"], "href", allow_duplicates=False)

        if links:
            logger.info(f"[Scraper.save_groups] Found {len(links)} unique group links. Saving to {self.data_path}.")
            # print(f"{len(links)} groupes trouvés et enregistrés") # Replaced by logger
            self.json_data["groups"] = links # Assuming self.json_data is already loaded and is a dict
            try:
                with open(self.data_path, "w", encoding="UTF-8") as file:
                    json.dump(self.json_data, file, indent=4)
                logger.info(f"[Scraper.save_groups] Successfully saved {len(links)} group links to {self.data_path}.")
            except Exception as e:
                logger.error(f"[Scraper.save_groups] Failed to write group links to {self.data_path}: {e}")
        else:
            logger.warning("[Scraper.save_groups] No group links found or retrieved after scrolling.")

        logger.info("[Scraper.save_groups] Finished 'save_groups' process.")

    def handle_captcha(self):
        """Gère les captchas en attendant que l'utilisateur les résolve manuellement."""
        captcha_selector = self.selectors.get("captcha") # Assuming "captcha" key exists in selectors
        if not captcha_selector:
            logger.error("[Scraper.handle_captcha] Captcha selector not found in config. Cannot handle CAPTCHA.")
            return

        logger.info(f"[Scraper.handle_captcha] Checking for CAPTCHA presence using selector: {captcha_selector}")
        try:
            WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, captcha_selector))
            )
            logger.warning("[Scraper.handle_captcha] CAPTCHA detected! Please solve it manually in the browser.")
            print("CAPTCHA DETECTED: Veuillez résoudre le captcha manuellement dans le navigateur.") # Direct user feedback

            # Wait for the CAPTCHA element to disappear
            WebDriverWait(self.driver, 300).until_not( # 5 minutes timeout for manual resolution
                EC.presence_of_element_located((By.CSS_SELECTOR, captcha_selector))
            )
            logger.info("[Scraper.handle_captcha] CAPTCHA element no longer present. Assuming resolved.")
            # print("Captcha résolu.") # Replaced by logger
        except TimeoutException:
            logger.error("[Scraper.handle_captcha] CAPTCHA was not resolved by user within the 5-minute timeout.")
            # print("Captcha non résolu à temps.") # Replaced by logger
            raise # Re-raise to indicate failure to proceed
        except Exception as e:
            logger.error(f"[Scraper.handle_captcha] An unexpected error occurred while handling CAPTCHA: {e}")
            raise


    # NOTE: The following methods (bypass_cloudflare, clear_browser_cache, etc.) are duplicates
    # of methods in WebScraping. They should ideally be called from the parent class (super().method_name())
    # or removed if they are identical. For now, adding specific Scraper logging.
    # If these are intended to override parent methods, they should use super() appropriately if needed.

    def bypass_cloudflare(self, url):
        """Bypass Cloudflare protection. (Uses parent method)"""
        logger.info(f"[Scraper.bypass_cloudflare] Calling parent bypass_cloudflare for URL: {url}")
        super().bypass_cloudflare(url)

    def clear_browser_cache(self):
        """Clear browser cache. (Uses parent method)"""
        logger.info(f"[Scraper.clear_browser_cache] Calling parent clear_cache.")
        super().clear_cache()

    def capture_network_traffic(self):
        """Capture network traffic. (Uses parent method)"""
        logger.info(f"[Scraper.capture_network_traffic] Calling parent capture_network_traffic.")
        return super().capture_network_traffic()

    def get_alert_text(self):
        """Get the text from an alert box. (Uses parent method)"""
        logger.info(f"[Scraper.get_alert_text] Calling parent get_alert_text.")
        # print(f"Texte de l'alerte : {alert_text}") # Parent method logs this
        return super().get_alert_text()

    def dismiss_alert(self):
        """Dismiss an alert box. (Uses parent method)"""
        logger.info(f"[Scraper.dismiss_alert] Calling parent dismiss_alert.")
        # print("Alerte rejetée.") # Parent method logs this
        super().dismiss_alert()

    def accept_alert(self):
        """Accept an alert box. (Uses parent method)"""
        logger.info(f"[Scraper.accept_alert] Calling parent accept_alert.")
        # print("Alerte acceptée.") # Parent method logs this
        super().accept_alert()

    def restart_browser(self, time_out=0):
        """Restart the browser. (Uses parent method)"""
        logger.info(f"[Scraper.restart_browser] Calling parent restart_browser with timeout {time_out}.")
        super().restart_browser(time_out=time_out)

    def refresh_page(self):
        """Refresh the current page. (Uses parent method)"""
        logger.info(f"[Scraper.refresh_page] Calling parent refresh_page.")
        # print("Page rafraîchie.") # Parent method logs this
        super().refresh_page()

    def close_browser(self):
        """Close the browser. (Uses parent method)"""
        logger.info(f"[Scraper.close_browser] Calling parent close_browser.")
        # print("Navigateur fermé.") # Parent method logs this
        super().close_browser()

    def execute_script(self, script, *args):
        """Execute a JavaScript script. (Uses parent method)"""
        # Parent method logs this
        # print(f"Script exécuté avec succès : {script}")
        return super().execute_script(script, *args)

    def wait_for_element(self, selector, time_out=10):
        """Wait for an element to be present. (Uses parent method)"""
        logger.info(f"[Scraper.wait_for_element] Calling parent wait_for_element for selector '{selector}'.")
        # print(f"Élément trouvé avec le sélecteur : {selector}") # Parent method logs this
        super().wait_for_element(selector, time_out=time_out)


    def wait_for_element_to_be_clickable(self, selector, time_out=10):
        """Wait for an element to be clickable. (Uses parent method)"""
        logger.info(f"[Scraper.wait_for_element_to_be_clickable] Calling parent for selector '{selector}'.")
        # print(f"Élément cliquable trouvé avec le sélecteur : {selector}") # Parent method logs this
        super().wait_for_element_to_be_clickable(selector, time_out=time_out)

    def wait_for_element_to_disappear(self, selector, time_out=10):
        """Wait for an element to disappear. (Uses parent method)"""
        logger.info(f"[Scraper.wait_for_element_to_disappear] Calling parent for selector '{selector}'.")
        # print(f"Élément disparu avec le sélecteur : {selector}") # Parent method logs this
        super().wait_for_element_to_disappear(selector, time_out=time_out)
    
    def wait_for_text_to_be_present(self, selector, text, time_out=10):
        """Wait for specific text to be present in an element. (Uses parent method)"""
        logger.info(f"[Scraper.wait_for_text_to_be_present] Calling parent for text '{text}' in '{selector}'.")
        # print(f"Texte '{text}' trouvé dans l'élément avec le sélecteur : {selector}") # Parent method logs this
        super().wait_for_text_to_be_present(selector, text, time_out=time_out)
    
    def wait_for_title(self, title, time_out=10):
        """Wait for the page title to be a specific value. (Uses parent method)"""
        logger.info(f"[Scraper.wait_for_title] Calling parent for title '{title}'.")
        # print(f"Titre de la page trouvé : {title}") # Parent method logs this
        super().wait_for_title(title, time_out=time_out)

    def wait_for_title_contains(self, title, time_out=10):
        """Wait for the page title to contain a specific value. (Uses parent method)"""
        logger.info(f"[Scraper.wait_for_title_contains] Calling parent for title containing '{title}'.")
        # print(f"Titre de la page contenant '{title}' trouvé") # Parent method logs this
        super().wait_for_title_contains(title, time_out=time_out)

    def add_comments(self):
        """Ajouter des commentaires aléatoires au post publié."""
        logger.info("[Scraper.add_comments] Attempting to add comments.")
        comments = [ # Consider moving to config or data.json if frequently changed
            "Super post !",
            "Merci pour le partage !",
            "Très intéressant !",
            "Top !",
            "J'aime beaucoup ce contenu."
        ]

        # Sélecteurs possibles pour le champ de commentaire. This strategy is fragile.
        # A more robust approach would be a single, reliable selector or a priority list.
        # These selectors look very generic and might match unintended elements.
        possible_comment_area_selectors = [
            "div.xdj266r.x11i5rnm.xat24cr.x1mh8g0r", # Very generic
            "div.xi81zsa.xo1l8bm.xlyipyv.xuxw1ft.x49crj4.x1ed109x.xdl72j9.x1iyjqo2.xs83m0k.x6prxxf.x6ikm8r.x10wlt62.x1y1aw1k.xn6708d.xwib8y2.x1ye3gou" # Also very generic
        ]
        # Assuming 'comment_button_selector' and 'submit_comment_selector' are more specific and defined in selectors.json
        comment_button_selector = "div[aria-label='Comment']" # This is an example, should be from self.selectors
        submit_comment_selector = self.selectors.get("submit_comment")

        if not submit_comment_selector:
            logger.error("[Scraper.add_comments] 'submit_comment' selector not found in config. Cannot add comments.")
            return

        found_comment_input = False
        try:
            for idx, area_selector in enumerate(possible_comment_area_selectors):
                logger.debug(f"[Scraper.add_comments] Trying comment area selector #{idx+1}: {area_selector}")
                try:
                    # It's better to find a specific comment input field, not just any div.
                    # This logic assumes the first div found is the comment input area.
                    comment_inputs = self.driver.find_elements(By.CSS_SELECTOR, area_selector)
                    if comment_inputs:
                        comment_input_element = comment_inputs[0] # Assuming the first one is correct
                        logger.info(f"[Scraper.add_comments] Found potential comment input area with selector: {area_selector}")

                        # Click a general "Comment" button to open the input field if necessary
                        # This logic might need adjustment based on actual FB UI flow.
                        # The 'comment_button' here seems to be a generic button to enable commenting,
                        # not the final submit button for a typed comment.
                        logger.debug(f"[Scraper.add_comments] Clicking generic comment button: {comment_button_selector}")
                        self.click(comment_button_selector) # Uses WebScraping.click with its logging
                        self.random_sleep(1,2)

                        selected_comments = random.sample(comments, k=random.randint(1, min(2, len(comments))))
                        for comment_text in selected_comments:
                            try:
                                logger.info(f"[Scraper.add_comments] Attempting to post comment: '{comment_text}'")
                                # The 'comment_input_element' found above might be a container.
                                # A more specific selector for the actual text input field is needed.
                                # For now, let's assume comment_input_element.click() and .send_keys() work.
                                comment_input_element.click()
                                self.random_sleep(0.5, 1)
                                comment_input_element.send_keys(comment_text)
                                self.random_sleep(1, 2)

                                logger.debug(f"[Scraper.add_comments] Clicking submit comment button: {submit_comment_selector}")
                                self.click_js(submit_comment_selector) # Using JS click for submit
                                self.random_sleep(2, 3)
                                logger.info(f'[Scraper.add_comments] Comment "{comment_text}" posted successfully.')
                                # print(f'Commentaire ajouté : "{comment_text}"') # Replaced
                                found_comment_input = True
                                break # Exit after one successful comment per found input area
                            except Exception as e_comment:
                                logger.error(f'[Scraper.add_comments] Error adding comment "{comment_text}": {e_comment}')
                                # print(f'Erreur en ajoutant le commentaire : "{comment_text}" : {e_comment}') # Replaced
                        if found_comment_input:
                            break # Exit outer loop if a comment was successfully posted
                except NoSuchElementException:
                    logger.debug(f"[Scraper.add_comments] Comment area selector '{area_selector}' not found or not interactable.")
                    continue # Try next selector
                except Exception as e_selector_area:
                    logger.error(f"[Scraper.add_comments] Error with comment area selector '{area_selector}': {e_selector_area}")
                    continue # Try next selector

            if not found_comment_input:
                logger.warning("[Scraper.add_comments] Could not find a usable comment input field after trying all selectors.")
                # print("Champ de commentaire non trouvé.") # Replaced
        except Exception as e_global:
            logger.error(f"[Scraper.add_comments] An unexpected error occurred during add_comments: {e_global}")
            # pass # Avoid silent pass

    def post_in_marketplace(self):
        """Publie un post dans la section Marketplace de Facebook."""
        logger.info("[Scraper.post_in_marketplace] Starting 'post_in_marketplace' process.")
        if not self.json_datax:
             logger.error("[Scraper.post_in_marketplace] Marketplace data (data1.json) is empty or not loaded. Aborting.")
             return

        try:
            marketplace_url = "https://www.facebook.com/marketplace/create/item"
            logger.info(f"[Scraper.post_in_marketplace] Navigating to: {marketplace_url}")
            self.set_page(marketplace_url) # Has logging
            self.random_sleep(3, 5) # Has logging

            # Titre de l'annonce
            title = random.choice(self.json_datax.get("titles", ["Default Title"]))
            logger.info(f"[Scraper.post_in_marketplace] Setting title: '{title}' using selector: {self.selectors.get('marketplace_title')}")
            self.send_data(self.selectors["marketplace_title"], title) # Has logging

            # Prix de l'annonce
            price = "1" # Consider making price configurable
            logger.info(f"[Scraper.post_in_marketplace] Setting price: '{price}' using selector: {self.selectors.get('marketplace_price')}")
            self.send_data(self.selectors["marketplace_price"], price) # Has logging

            # Catégorie de l'annonce
            category = random.choice(self.json_datax.get("categories", ["Default Category"]))
            logger.info(f"[Scraper.post_in_marketplace] Selecting category: '{category}' using selector: {self.selectors.get('marketplace_category')}")
            self.select_drop_down_text(self.selectors["marketplace_category"], category) # Has logging

            # Description de l'annonce
            description = random.choice(self.json_datax.get("descriptions", ["Default Description"]))
            logger.info(f"[Scraper.post_in_marketplace] Setting description (first 50 chars): '{description[:50]}...' using selector: {self.selectors.get('marketplace_description')}")
            self.send_data(self.selectors["marketplace_description"], description) # Has logging

            # Télécharger les images
            available_images = self.json_datax.get("images", [])
            if available_images:
                num_to_sample = min(10, len(available_images))
                post_images_relative = random.sample(available_images, num_to_sample)
                post_images_absolute = [self.get_absolute_path(img) for img in post_images_relative]
                logger.info(f"[Scraper.post_in_marketplace] Preparing to upload {len(post_images_absolute)} images for marketplace post.")
                self.upload_images_parallel(post_images_absolute) # Has logging
            else:
                logger.warning("[Scraper.post_in_marketplace] No images found in data1.json for marketplace post.")

            # Soumettre l'annonce
            logger.info(f"[Scraper.post_in_marketplace] Attempting to submit marketplace listing using selector: {self.selectors.get('marketplace_submit')}")
            self.click_js(self.selectors["marketplace_submit"]) # Has logging

            logger.info(f'[Scraper.post_in_marketplace] Marketplace ad submitted (or attempt made): "{title}" - "{price}" - "{description[:50]}..."')
            # print(f'Annonce publiée : "{title}" - "{price}" - "{description}"') # Replaced

        except KeyError as e:
            logger.error(f"[Scraper.post_in_marketplace] Missing selector key in config: {e}. Cannot proceed with marketplace post.")
        except Exception as e:
            logger.error(f'[Scraper.post_in_marketplace] Error during marketplace posting: {e}')
            # print(f'Erreur lors de la publication dans le Marketplace : {e}') # Replaced
        logger.info("[Scraper.post_in_marketplace] Finished 'post_in_marketplace' process.")


    def _post_in_group(self, group_url, post_text, post_images_abs_paths):
        """Méthode interne pour publier un post dans un groupe spécifique."""
        method_name = "_post_in_group" # For logging context
        logger.info(f"[Scraper.{method_name}] Attempting to post in group: {group_url}. Text: '{post_text[:50]}...', Images: {len(post_images_abs_paths)}")

        self.set_page(group_url) # Has logging
        self.random_sleep(5, 7) # Has logging

        # Rafraîchir la page - Consider if this is always needed or only on certain conditions
        try:
            logger.info(f"[Scraper.{method_name}] Refreshing page for group {group_url}.")
            self.refresh_selenium() # Has logging from parent
        except Exception as e:
            self._log_error(f'Error during page refresh for group {group_url}: {e}', method_name)
            return # Critical step failed

        # Ouvrir la zone de texte
        display_input_selector = self.selectors.get("display_input")
        if not display_input_selector:
            self._log_error("Selector 'display_input' not found in config.", method_name)
            return
        logger.info(f"[Scraper.{method_name}] Attempting to click display_input: {display_input_selector}")
        if not self._click_element(display_input_selector, "display_input_area", method_name=method_name):
            self._log_error("Failed to click display_input_area, cannot proceed with post.", method_name)
            return

        self.random_sleep() # Has logging

        # Remplir le champ de texte
        input_selector = self.selectors.get("input")
        if not input_selector:
            self._log_error("Selector 'input' (for text area) not found in config.", method_name)
            return
        logger.info(f"[Scraper.{method_name}] Attempting to fill text input: {input_selector}")
        if not self._fill_input(input_selector, post_text, "post_text_area", method_name=method_name):
            self._log_error("Failed to fill post text area, cannot proceed with post.", method_name)
            return

        self.random_sleep(1,2) # Pause after typing

        # Télécharger les images si elles sont fournies
        if post_images_abs_paths:
            logger.info(f"[Scraper.{method_name}] Attempting to upload {len(post_images_abs_paths)} image(s).")
            try:
                # Assuming upload_images_parallel handles paths correctly and has logging
                self.upload_images_parallel(post_images_abs_paths)
            except Exception as e:
                # If image upload fails, log it and try to apply a theme as a fallback for text posts
                self._log_error(f"Error during image upload for group {group_url}: {e}. Attempting to post text with theme.", method_name)
                self._apply_theme(method_name=method_name)

        self.random_sleep(1,2) # Pause after potential image upload

        # Soumettre le post
        submit_selector = self.selectors.get("submit")
        if not submit_selector:
            self._log_error("Selector 'submit' (for post button) not found in config.", method_name)
            return
        logger.info(f"[Scraper.{method_name}] Attempting to click submit button: {submit_selector}")
        if not self._click_element(submit_selector, "submit_post_button", method_name=method_name):
            self._log_error("Failed to click submit post button. Post may not have been submitted.", method_name)
            return # Post failed

        # Assuming post was successful if submit was clicked
        self._log_success(f'Post attempt in group "{group_url}" with text "{post_text[:50]}..." appears successful.', method_name)

        logger.info(f"[Scraper.{method_name}] Waiting 15-20s before attempting to add comments.")
        self.random_sleep(15, 20)
        self.add_comments() # Has its own logging

        wait_duration_min = WAIT_MIN * 60
        wait_duration_max = WAIT_MIN * 70
        logger.info(f"[Scraper.{method_name}] Post process for group {group_url} complete. Waiting for {wait_duration_min}-{wait_duration_max}s before next group.")
        self.random_sleep(wait_duration_min, wait_duration_max)


    def _click_element(self, selector, element_name, method_name=""):
        """Tente de cliquer sur un élément et retourne True si réussi, False sinon."""
        parent_method_name = f"{method_name}._click_element" if method_name else "_click_element"
        logger.info(f"[Scraper.{parent_method_name}] Attempting to click element '{element_name}' (selector: {selector})")
        try:
            # Using WebScraping's click method which has WebDriverWait and logging
            super().click(selector)
            # logger.info(f"[Scraper.{parent_method_name}] Successfully clicked '{element_name}'.") # Covered by parent log
            return True
        except TimeoutException: # WebDriverWait in parent click will raise this
            self._log_error(f"Timeout: Element '{element_name}' (selector: {selector}) not clickable after 10 seconds.", parent_method_name)
        except Exception as e: # Catch other potential errors from parent click
            self._log_error(f'Error clicking element "{element_name}" (selector: {selector}): {e}', parent_method_name)
        return False

    def _fill_input(self, selector, text, element_name, method_name=""):
        """Tente de remplir un champ de texte et retourne True si réussi, False sinon."""
        parent_method_name = f"{method_name}._fill_input" if method_name else "_fill_input"
        text_to_log = text[:100] + "..." if len(text) > 100 else text
        logger.info(f"[Scraper.{parent_method_name}] Attempting to fill input '{element_name}' (selector: {selector}) with text: '{text_to_log}'")
        try:
            input_element = super().get_elem(selector) # Uses parent get_elem with logging
            if not input_element:
                # Error already logged by get_elem
                self._log_error(f"Input element '{element_name}' (selector: {selector}) not found.", parent_method_name)
                return False

            input_element.clear()
            logger.debug(f"[Scraper.{parent_method_name}] Cleared input field '{element_name}'.")
            input_element.send_keys(text)
            logger.info(f"[Scraper.{parent_method_name}] Successfully sent keys to input '{element_name}'.")
            return True
        except TimeoutException: # Should be caught by get_elem if it uses WebDriverWait
            self._log_error(f"Timeout: Element '{element_name}' (selector: {selector}) not found or not interactable for filling.", parent_method_name)
        except NoSuchElementException: # Should be caught by get_elem
            self._log_error(f"NoSuchElement: Element '{element_name}' (selector: {selector}) not found for filling.", parent_method_name)
        except ElementNotInteractableException:
            self._log_error(f"ElementNotInteractable: Element '{element_name}' (selector: {selector}) is not interactable.", parent_method_name)
        except Exception as e:
            self._log_error(f'Error writing text to element "{element_name}" (selector: {selector}): {e}', parent_method_name)
        return False

    def _apply_theme(self, method_name=""):
        """Applique un thème aléatoire au post."""
        parent_method_name = f"{method_name}._apply_theme" if method_name else "_apply_theme"
        logger.info(f"[Scraper.{parent_method_name}] Attempting to apply a random theme.")
        try:
            display_themes_selector = self.selectors.get("display_themes")
            theme_selector_template = self.selectors.get("theme")

            if not display_themes_selector or not theme_selector_template:
                self._log_error("Theme selectors ('display_themes' or 'theme') not found in config.", parent_method_name)
                return

            logger.debug(f"[Scraper.{parent_method_name}] Clicking display_themes button: {display_themes_selector}")
            self.click_js(display_themes_selector) # Has logging
            self.random_sleep() # Has logging

            random_theme_index = random.randint(1, 5) # Assuming 5 themes
            theme_selector = theme_selector_template.replace("index", str(random_theme_index))
            logger.debug(f"[Scraper.{parent_method_name}] Clicking theme #{random_theme_index}: {theme_selector}")
            self.click_js(theme_selector) # Has logging
            logger.info(f"[Scraper.{parent_method_name}] Successfully applied theme #{random_theme_index}.")
        except Exception as e:
            self._log_error(f'Error applying theme: {e}', parent_method_name)

    def _log_error(self, message, method_name=""):
        """Log et affiche un message d'erreur, préfixé par la classe et la méthode."""
        context = f"[Scraper.{method_name}]" if method_name else "[Scraper]"
        full_message = f"{context} ERROR: {message}"
        logger.error(full_message)
        # print(full_message) # Consider removing print if logger is sufficient

    def _log_success(self, message, method_name=""):
        """Log et affiche un message de succès, préfixé par la classe et la méthode."""
        context = f"[Scraper.{method_name}]" if method_name else "[Scraper]"
        full_message = f"{context} SUCCESS: {message}"
        logger.info(full_message)
        # print(full_message) # Consider removing print if logger is sufficient
# Removed __main__ block as per instructions