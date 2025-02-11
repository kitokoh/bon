import os
import time
import zipfile
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
<<<<<<< HEAD
import json
import threading
from typing import List, Dict, Optional, Union
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import random
import string
import re
from datetime import datetime
import requests
from urllib.parse import urljoin
=======
>>>>>>> c9ba7d302208764d82a1218f7368eb37bb590766
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.remote.webelement import WebElement  # Ajoutez cette ligne
class WebScraping:
    """Classe principale pour le scraping web avec Selenium Chrome."""
    
    service = None
    options = None
<<<<<<< HEAD
    
    def __init__(
        self,
        headless: bool = False,
        timeout: int = 0,
        proxy_server: str = "",
        proxy_port: str = "",
        proxy_user: str = "",
        proxy_pass: str = "",
        chrome_folder: str = "",
        user_agent: bool = False,
        download_folder: str = "",
        extensions: List[str] = [],
        incognito: bool = False,
        experimentals: bool = True,
        start_killing: bool = False,
        start_openning: bool = True,
        width: int = 1280,
        height: int = 720,
        mute: bool = True,
        *args,
        **kwargs
    ):
        """Initialise le navigateur avec les paramètres configurés."""
        
        # Configuration du logging
        self._setup_logging()
        
        # Variables d'instance
=======

    def __init__(self, headless=False, time_out=0,
                 proxy_server="", proxy_port="", proxy_user="", proxy_pass="",
                 proxy_type="http", chrome_folder="", user_agent=False, 
                 download_folder="", extensions=[], incognito=False, experimentals=True,
                 start_killing=False, start_openning: bool = True, width: int = 1280, height: int = 720,
                 mute: bool = True):
        """ Constructor of the class
        Args:
            headless (bool, optional): Hide (True) or Show (False) the google chrome window. Defaults to False.
            time_out (int, optional): Wait time to load each page. Defaults to 0.
            proxy_server (str, optional): Proxy server or host to use in the window. Defaults to "".
            proxy_port (str, optional): Proxy post to use in the window. Defaults to "".
            proxy_user (str, optional): Proxy user to use in the window. Defaults to "".
            proxy_pass (str, optional): Proxy password to use in the window. Defaults to "".
            proxy_type (str, optional): Type of proxy (http, socks). Defaults to "http".
            chrome_folder (str, optional): folder with user google chrome data. Defaults to "".
            user_agent (bool, optional): user agent to setup to chrome. Defaults to False.
            download_folder (str, optional): Default download folder. Defaults to "".
            extensions (list, optional): Paths of extensions in format .crx, to install. Defaults to [].
            incognito (bool, optional): Open chrome in incognito mode. Defaults to False.
            experimentals (bool, optional): Activate the experimentals options. Defaults to True.
            start_killing (bool, optional): Kill chrome process before start. Defaults to False.
            start_openning (bool, optional): Open chrome window before start. Defaults to True.
            width (int, optional): Width of the window. Defaults to 1280.
            height (int, optional): Height of the window. Defaults to 720.
            mute (bool, optional): Mute the audio of the window. Defaults to True.
        """
>>>>>>> c9ba7d302208764d82a1218f7368eb37bb590766
        self.basetime = 1
        self.current_folder = os.path.dirname(__file__)
        self.__headless__ = headless
        self.__proxy_server__ = proxy_server
        self.__proxy_port__ = proxy_port
        self.__proxy_user__ = proxy_user
        self.__proxy_pass__ = proxy_pass
        self.__proxy_type__ = proxy_type
        self.__pluginfile__ = os.path.join(self.current_folder, 'proxy_auth_plugin.zip')
        self.__chrome_folder__ = chrome_folder
        self.__user_agent__ = user_agent
        self.__download_folder__ = download_folder
        self.__extensions__ = extensions
        self.__incognito__ = incognito
        self.__experimentals__ = experimentals
        self.__start_openning__ = start_openning
        self.__width__ = width
        self.__height__ = height
        self.__mute__ = mute
        self.__web_page__ = None
        
        # Gestion des processus Chrome existants
        if start_killing:
<<<<<<< HEAD
            self._kill_chrome_processes()
            
        # Initialisation du navigateur si demandé
=======
            logger.info("Trying to kill chrome...")
            command = 'taskkill /IM "chrome.exe" /F'
            os.system(command)
            logger.info("Chrome killed successfully.")

>>>>>>> c9ba7d302208764d82a1218f7368eb37bb590766
        if self.__start_openning__:
            self.__set_browser_instance__()
            
        # Configuration du timeout de chargement de page
        if timeout > 0:
            self.driver.set_page_load_timeout(timeout)
            
        # Initialisation des variables supplémentaires
        self._setup_additional_variables()
    
    def _setup_logging(self):
        """Configure le système de logging."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            filename="web_scraping.log"
        )
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Ajouter un handler pour la console
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(ch)
    
    def _kill_chrome_processes(self):
        """Arrête tous les processus Chrome existants."""
        try:
            command = 'taskkill /IM "chrome.exe" /F'
            os.system(command)
            self.logger.info("Chrome killed successfully.")
        except Exception as e:
            self.logger.error(f"Failed to kill Chrome processes: {e}")
    
    def _setup_additional_variables(self):
        """Initialise les variables supplémentaires pour les fonctionnalités avancées."""
        self.script_directory = os.path.join(self.current_folder, 'scripts')
        self.data_directory = os.path.join(self.current_folder, 'data')
        self.screenshot_directory = os.path.join(self.current_folder, 'screenshots')
        
        # Création des répertoires si ils n'existent pas
        for directory in [self.script_directory, self.data_directory, self.screenshot_directory]:
            os.makedirs(directory, exist_ok=True)
    
    def __set_browser_instance__(self):
<<<<<<< HEAD
        """Configure et initialise l'instance du navigateur."""
        os.environ['WDM_LOG_LEVEL'] = '0'
        os.environ['WDM_PRINT_FIRST_LINE'] = 'False'
        
        if not WebScraping.options:
            WebScraping.options = webdriver.ChromeOptions()
            
            # Options de base
            WebScraping.options.add_argument('--no-sandbox')
            WebScraping.options.add_argument('--start-maximized')
            WebScraping.options.add_argument('--output=/dev/null')
            WebScraping.options.add_argument('--log-level=3')
            WebScraping.options.add_argument("--disable-notifications")
            WebScraping.options.add_argument("--disable-infobars")
            WebScraping.options.add_argument("--safebrowsing-disable-download-protection")
            WebScraping.options.add_argument("--disable-dev-shm-usage")
            WebScraping.options.add_argument("--disable-renderer-backgrounding")
            WebScraping.options.add_argument("--disable-background-timer-throttling")
            WebScraping.options.add_argument("--disable-backgrounding-occluded-windows")
            WebScraping.options.add_argument("--disable-client-side-phishing-detection")
            WebScraping.options.add_argument("--disable-crash-reporter")
            WebScraping.options.add_argument("--disable-oopr-debug-crash-dump")
            WebScraping.options.add_argument("--no-crash-upload")
            WebScraping.options.add_argument("--disable-gpu")
            WebScraping.options.add_argument("--disable-extensions")
            WebScraping.options.add_argument("--disable-low-res-tiling")
            WebScraping.options.add_argument("--log-level=3")
            WebScraping.options.add_argument("--silent")
            
            # Options expérimentales
            if self.__experimentals__:
                WebScraping.options.add_experimental_option('excludeSwitches', ['enable-logging', "enable-automation"])
                WebScraping.options.add_experimental_option('useAutomationExtension', False)
            
            # Configuration de la fenêtre
            WebScraping.options.add_experimental_option('window-size', f"{self.__width__},{self.__height__}")
            
            # Mode headless
            if self.__headless__:
                WebScraping.options.add_argument("--headless=new")
                
            # Contrôle audio
            if self.__mute__:
                WebScraping.options.add_argument("--mute-audio")
                
            # Dossier Chrome personnalisé
            if self.__chrome_folder__:
                WebScraping.options.add_argument(f"--user-data-dir={self.__chrome_folder__}")
                
            # User Agent personnalisé
            if self.__user_agent__:
                WebScraping.options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36')
                
            # Configuration des téléchargements
            if self.__download_folder__:
                prefs = {
                    "download.default_directory": f"{self.__download_folder__}",
                    "download.prompt_for_download": "false",
                    'profile.default_content_setting_values.automatic_downloads': 1,
                    'profile.default_content_settings.popups': 0,
                    "download.directory_upgrade": True,
                    "plugins.always_open_pdf_externally": True,
                    "plugins.plugins_list": [{"enabled": False, "name": "Chrome PDF Viewer"}],
                    'download.extensions_to_open': 'xml',
                    'safebrowsing.enabled': True
                }
                WebScraping.options.add_experimental_option("prefs", prefs)
                
            # Extensions
            if self.__extensions__:
                for extension in self.__extensions__:
                    WebScraping.options.add_extension(extension)
                    
            # Mode navigation privée
            if self.__incognito__:
                WebScraping.options.add_argument("--incognito")
                
            # Options anti-détection
            if self.__experimentals__:
                WebScraping.options.add_argument("--disable-blink-features=AutomationControlled")
                
            # Configuration proxy
            if self.__proxy_server__ and self.__proxy_port__:
                if not self.__proxy_user__ and not self.__proxy_pass__:
                    proxy = f"{self.__proxy_server__}:{self.__proxy_port__}"
                    WebScraping.options.add_argument(f"--proxy-server={proxy}")
                else:
                    self.__create_proxy_extesion__()
                    WebScraping.options.add_extension(self.__pluginfile__)
        
        if not WebScraping.service:
            WebScraping.service = Service()
            
        self.driver = webdriver.Chrome(service=WebScraping.service, options=WebScraping.options)
    
=======
        """Configure and start the browser instance."""
        try:
            os.environ['WDM_LOG_LEVEL'] = '0'
            os.environ['WDM_PRINT_FIRST_LINE'] = 'False'

            if not WebScraping.options:
                WebScraping.options = webdriver.ChromeOptions()
                WebScraping.options.add_argument('--no-sandbox')
                WebScraping.options.add_argument('--start-maximized')
                WebScraping.options.add_argument('--output=/dev/null')
                WebScraping.options.add_argument('--log-level=3')
                WebScraping.options.add_argument("--disable-notifications")
                WebScraping.options.add_argument("--disable-infobars")
                WebScraping.options.add_argument("--safebrowsing-disable-download-protection")
                WebScraping.options.add_argument("--disable-dev-shm-usage")
                WebScraping.options.add_argument("--disable-renderer-backgrounding")
                WebScraping.options.add_argument("--disable-background-timer-throttling")
                WebScraping.options.add_argument("--disable-backgrounding-occluded-windows")
                WebScraping.options.add_argument("--disable-client-side-phishing-detection")
                WebScraping.options.add_argument("--disable-crash-reporter")
                WebScraping.options.add_argument("--disable-oopr-debug-crash-dump")
                WebScraping.options.add_argument("--no-crash-upload")
                WebScraping.options.add_argument("--disable-gpu")
                WebScraping.options.add_argument("--disable-extensions")
                WebScraping.options.add_argument("--disable-low-res-tiling")
                WebScraping.options.add_argument("--log-level=3")
                WebScraping.options.add_argument("--silent")

                if self.__experimentals__:
                    WebScraping.options.add_experimental_option('excludeSwitches', ['enable-logging', "enable-automation"])
                    WebScraping.options.add_experimental_option('useAutomationExtension', False)

                WebScraping.options.add_argument(f"--window-size={self.__width__},{self.__height__}")

                if self.__headless__:
                    WebScraping.options.add_argument("--headless=new")

                if self.__mute__:
                    WebScraping.options.add_argument("--mute-audio")

                if self.__chrome_folder__:
                    WebScraping.options.add_argument(f"--user-data-dir={self.__chrome_folder__}")

                if self.__user_agent__:
                    WebScraping.options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36')

                if self.__download_folder__:
                    prefs = {
                        "download.default_directory": f"{self.__download_folder__}",
                        "download.prompt_for_download": "false",
                        'profile.default_content_setting_values.automatic_downloads': 1,
                        'profile.default_content_settings.popups': 0,
                        "download.directory_upgrade": True,
                        "plugins.always_open_pdf_externally": True,
                        "plugins.plugins_list": [{"enabled": False, "name": "Chrome PDF Viewer"}],
                        'download.extensions_to_open': 'xml',
                        'safebrowsing.enabled': True
                    }
                    WebScraping.options.add_experimental_option("prefs", prefs)

                if self.__extensions__:
                    for extension in self.__extensions__:
                        WebScraping.options.add_extension(extension)

                if self.__incognito__:
                    WebScraping.options.add_argument("--incognito")

                if self.__experimentals__:
                    WebScraping.options.add_argument("--disable-blink-features=AutomationControlled")

            if self.__proxy_server__ and self.__proxy_port__ and not self.__proxy_user__ and not self.__proxy_pass__:
                proxy = f"{self.__proxy_server__}:{self.__proxy_port__}"
                WebScraping.options.add_argument(f"--proxy-server={proxy}")

            if self.__proxy_server__ and self.__proxy_port__ and self.__proxy_user__ and self.__proxy_pass__:
                self.__create_proxy_extesion__()
                WebScraping.options.add_extension(self.__pluginfile__)

            if not WebScraping.service:
                WebScraping.service = Service()

            self.driver = webdriver.Chrome(service=WebScraping.service, options=WebScraping.options)
            logger.info("Browser instance created successfully.")
        except Exception as e:
            logger.error(f"Failed to create browser instance: {e}")
            raise

>>>>>>> c9ba7d302208764d82a1218f7368eb37bb590766
    def __create_proxy_extesion__(self):
        """Crée une extension pour les proxys authentifiés."""
        manifest_json = """
        {
            "version": "1.0.0",
            "manifest_version": 2,
            "name": "Chrome Proxy",
            "permissions": [
                "proxy",
                "tabs",
                "unlimitedStorage",
                "storage",
                "<all_urls>",
                "webRequest",
                "webRequestBlocking"
            ],
            "background": {
                "scripts": ["background.js"]
            },
            "minimum_chrome_version":"22.0.0"
        }
        """
        background_js = """
        var config = {
            mode: "fixed_servers",
            rules: {
                singleProxy: {
                    scheme: "http",
                    host: "%s",
                    port: parseInt(%s)
                },
                bypassList: ["localhost"]
            }
        };
        chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});
        function callbackFn(details) {
            return {
                authCredentials: {
                    username: "%s",
                    password: "%s"
                }
            };
        }
        chrome.webRequest.onAuthRequired.addListener(
            callbackFn,
            {urls: ["<all_urls>"]},
            ['blocking']
        );
        """ % (self.__proxy_server__, self.__proxy_port__, 
               self.__proxy_user__, self.__proxy_pass__)
        
        with zipfile.ZipFile(self.__pluginfile__, 'w') as zp:
            zp.writestr("manifest.json", manifest_json)
            zp.writestr("background.js", background_js)
    
    def set_cookies(self, cookies: List[Dict]) -> None:
        """Définit les cookies dans le navigateur."""
        cookies_formatted = []
        for cookie in cookies:
            if "expirationDate" in cookie:
                cookie["expiry"] = int(cookie["expirationDate"])
                del cookie["expirationDate"]
            cookies_formatted.append(cookie)
        
        for cookie in cookies_formatted:
            try:
                self.driver.add_cookie(cookie)
            except Exception as e:
<<<<<<< HEAD
                self.logger.error(f"Failed to add cookie: {e}")
    
    def screenshot(self, base_name: str) -> None:
        """Prend une capture d'écran de la page actuelle."""
        if not base_name.endswith(".png"):
            base_name = f"{base_name}.png"
        screenshot_path = os.path.join(self.screenshot_directory, base_name)
        self.driver.save_screenshot(screenshot_path)
    
    def full_screenshot(self, path: str) -> None:
        """Prend une capture d'écran complète de la page."""
        original_size = self.driver.get_window_size()
        required_width = self.driver.execute_script('return document.body.parentNode.scrollWidth')
        required_height = self.driver.execute_script('return document.body.parentNode.scrollHeight')
        self.driver.set_window_size(required_width, required_height)
        self.screenshot(path)
        self.driver.set_window_size(original_size['width'], original_size['height'])
    
    def get_browser(self) -> webdriver.Chrome:
        """Retourne l'instance du navigateur."""
        return self.driver
    
    def end_browser(self) -> None:
        """Ferme l'instance du navigateur."""
        self.driver.quit()
    
    def __reload_browser__(self) -> None:
        """Recharge l'instance du navigateur."""
        self.end_browser()
        self.driver = self.get_browser()
        if self.__web_page__:
            self.driver.get(self.__web_page__)
    
    def send_data(self, selector: str, data: str) -> None:
        """Envoie des données dans un champ de formulaire."""
        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
        elem.send_keys(data)
    
    def click(self, selector: str) -> None:
        """Clique sur un élément."""
        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
        elem.click()
    
    def wait_load(self, selector: str, time_out: int = 1, refresh_back_tab: int = -1) -> None:
        """Attend que l'élément soit chargé."""
        total_time = 0
        while total_time < time_out:
            total_time += 1
            try:
                elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                elem.text
                break
            except Exception as e:
                if refresh_back_tab != -1:
                    self.refresh_selenium(back_tab=refresh_back_tab)
                else:
                    time.sleep(self.basetime)
                continue
        else:
            raise Exception(f"Time out exceeded. The element {selector} is not in the page.")
    
    def wait_die(self, selector: str, time_out: int = 10) -> None:
        """Attend que l'élément disparaisse."""
        total_time = 0
        while total_time < time_out:
            total_time += 1
            try:
                elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                elem.text
                time.sleep(self.basetime)
                continue
            except:
                break
        else:
            raise Exception(f"Time out exceeded. The element {selector} is still in the page.")
    
    def get_text(self, selector: str) -> Optional[str]:
        """Retourne le texte d'un élément."""
=======
                logger.error(f"Failed to add cookie: {e}")

    def clear_cookies(self, name=None):
        """Clear specific or all cookies."""
        try:
            if name:
                self.driver.delete_cookie(name)
                logger.info(f"Cookie {name} deleted.")
            else:
                self.driver.delete_all_cookies()
                logger.info("All cookies deleted.")
        except Exception as e:
            logger.error(f"Failed to clear cookies: {e}")

    def screenshot(self, base_name):
        """Take a screenshot of the current page."""
        try:
            if str(base_name).endswith(".png"):
                file_name = base_name
            else:
                file_name = f"{base_name}.png"
            self.driver.save_screenshot(file_name)
            logger.info(f"Screenshot saved as {file_name}.")
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")

    def full_screenshot(self, path: str):
        """Take a full screenshot of the current page."""
        try:
            original_size = self.driver.get_window_size()
            required_width = self.driver.execute_script('return document.body.parentNode.scrollWidth')
            required_height = self.driver.execute_script('return document.body.parentNode.scrollHeight')
            self.driver.set_window_size(required_width, required_height)
            self.screenshot(path)  # avoids scrollbar
            self.driver.set_window_size(original_size['width'], original_size['height'])
            logger.info(f"Full screenshot saved as {path}.")
        except Exception as e:
            logger.error(f"Failed to take full screenshot: {e}")

    def get_browser(self):
        """Get the current browser instance."""
        return self.driver

    def end_browser(self):
        """Close the browser instance."""
        try:
            self.driver.quit()
            logger.info("Browser instance closed successfully.")
        except Exception as e:
            logger.error(f"Failed to close browser instance: {e}")

    def send_data(self, selector, data):
        """Send data to an input field."""
        try:
            elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            elem.send_keys(data)
            logger.info(f"Data sent to element with selector: {selector}")
        except Exception as e:
            logger.error(f"Failed to send data to element with selector {selector}: {e}")
            raise

    def click(self, selector):
        """Click on an element."""
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            element.click()
            logger.info(f"Clicked on element with selector: {selector}")
        except Exception as e:
            logger.error(f"Failed to click on element with selector {selector}: {e}")
            raise

    def wait_load(self, selector, time_out=10, refresh_back_tab=-1):
        """Wait for an element to load."""
        try:
            total_time = 0
            while total_time < time_out:
                total_time += 1
                try:
                    WebDriverWait(self.driver, 1).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    if refresh_back_tab != -1:
                        self.refresh_selenium(back_tab=refresh_back_tab)
                    else:
                        time.sleep(self.basetime)
            else:
                raise TimeoutException(f"Time out exceeded. The element {selector} is not in the page.")
        except TimeoutException as e:
            logger.error(f"Timeout while waiting for element with selector {selector}: {e}")
            raise

    def wait_die(self, selector, time_out=10):
        """Wait for an element to disappear."""
        try:
            WebDriverWait(self.driver, time_out).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, selector))
            )
            logger.info(f"Element with selector {selector} has disappeared.")
        except TimeoutException as e:
            logger.error(f"Timeout while waiting for element with selector {selector} to disappear: {e}")
            raise

    def get_text(self, selector):
        """Get the text of an element."""
>>>>>>> c9ba7d302208764d82a1218f7368eb37bb590766
        try:
            elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return elem.text
<<<<<<< HEAD
        except Exception as e:
            self.logger.error(f"Failed to get text: {e}")
=======
        except NoSuchElementException:
            logger.error(f"Element with selector {selector} not found.")
            return None
        except TimeoutException:
            logger.error(f"Timeout while waiting for element with selector {selector}.")
>>>>>>> c9ba7d302208764d82a1218f7368eb37bb590766
            return None
    
    def get_texts(self, selector: str) -> List[str]:
        """Retourne les textes de plusieurs éléments."""
        texts = []
<<<<<<< HEAD
        elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
        for elem in elems:
            try:
                texts.append(elem.text)
            except Exception as e:
                self.logger.error(f"Failed to get text: {e}")
                continue
        return texts
    
    def set_attrib(self, selector: str, attrib_name: str, attrib_value: str) -> None:
        """Définit un attribut d'un élément."""
        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
        self.driver.execute_script(f"arguments[0].setAttribute('{attrib_name}', '{attrib_value}');", elem)
    
    def get_attrib(self, selector: str, attrib_name: str) -> Optional[str]:
        """Retourne la valeur d'un attribut d'un élément."""
=======
        try:
            elems = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
            )
            for elem in elems:
                try:
                    texts.append(elem.text)
                except Exception as e:
                    logger.error(f"Failed to get text from element: {e}")
                    continue
            return texts
        except Exception as e:
            logger.error(f"Failed to get texts from elements with selector {selector}: {e}")
            return texts

    def set_attrib(self, selector, attrib_name, attrib_value):
        """Set an attribute of an element."""
        try:
            elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            self.driver.execute_script(f"arguments[0].setAttribute('{attrib_name}', '{attrib_value}');", elem)
            logger.info(f"Set attribute {attrib_name} to {attrib_value} on element with selector: {selector}")
        except Exception as e:
            logger.error(f"Failed to set attribute {attrib_name} on element with selector {selector}: {e}")
            raise

    def get_attrib(self, selector, attrib_name):
        """Get an attribute of an element."""
>>>>>>> c9ba7d302208764d82a1218f7368eb37bb590766
        try:
            elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return elem.get_attribute(attrib_name)
        except Exception as e:
<<<<<<< HEAD
            self.logger.error(f"Failed to get attribute: {e}")
=======
            logger.error(f"Failed to get attribute {attrib_name} from element with selector {selector}: {e}")
>>>>>>> c9ba7d302208764d82a1218f7368eb37bb590766
            return None
    
    def get_attribs(self, selector: str, attrib_name: str, allow_duplicates: bool = True, allow_empty: bool = True) -> List[str]:
        """Retourne les attributs de plusieurs éléments."""
        attributes = []
        try:
            elems = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
            )
            for elem in elems:
                try:
                    attribute = elem.get_attribute(attrib_name)
                    if not allow_duplicates and attribute in attributes:
                        continue
                    if not allow_empty and attribute.strip() == "":
                        continue
                    attributes.append(attribute)
                except Exception as e:
                    logger.error(f"Failed to get attribute {attrib_name} from element: {e}")
                    continue
<<<<<<< HEAD
                if not allow_empty and attribute.strip() == "":
                    continue
                attributes.append(attribute)
            except Exception as e:
                self.logger.error(f"Failed to get attribute: {e}")
                continue
        return attributes
    
    def get_elem(self, selector: str) -> webdriver.WebElement:
        """Retourne un élément unique."""
        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
        return elem
    
    def get_elems(self, selector: str) -> List[webdriver.WebElement]:
        """Retourne plusieurs éléments."""
        elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
        return elems
    
    def set_page_js(self, web_page: str, new_tab: bool = False) -> None:
        """Définit la page actuelle en utilisant JavaScript."""
        self.__web_page__ = web_page
        if new_tab:
            script = f'window.open("{web_page}");'
        else:
            script = f'window.open("{web_page}").focus();'
        self.driver.execute_script(script)
    
    def set_page(self, web_page: str, time_out: int = 0, break_time_out: bool = False) -> None:
        """Définit la page actuelle."""
=======
            return attributes
        except Exception as e:
            logger.error(f"Failed to get attributes {attrib_name} from elements with selector {selector}: {e}")
            return attributes

    def get_elem(self, selector):
        """Get a single element."""
        try:
            elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return elem
        except NoSuchElementException:
            logger.error(f"Element with selector {selector} not found.")
            return None
        except TimeoutException:
            logger.error(f"Timeout while waiting for element with selector {selector}.")
            return None

    def get_elems(self, selector):
        """Get multiple elements."""
        try:
            elems = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
            )
            return elems
        except NoSuchElementException:
            logger.error(f"Elements with selector {selector} not found.")
            return []
        except TimeoutException:
            logger.error(f"Timeout while waiting for elements with selector {selector}.")
            return []

    def set_page_js(self, web_page, new_tab=False):
        """Set the current page using JavaScript."""
        self.__web_page__ = web_page
        try:
            if new_tab:
                script = f'window.open("{web_page}");'
            else:
                script = f'window.open("{web_page}.focus();'
            self.driver.execute_script(script)
            logger.info(f"Page set to {web_page} using JavaScript.")
        except Exception as e:
            logger.error(f"Failed to set page using JavaScript: {e}")
            raise

    def set_page(self, web_page, time_out=0, break_time_out=False):
        """Set the current page."""
>>>>>>> c9ba7d302208764d82a1218f7368eb37bb590766
        try:
            self.__web_page__ = web_page
            if time_out > 0:
                self.driver.set_page_load_timeout(time_out)
            self.driver.get(self.__web_page__)
            logger.info(f"Page set to {web_page}.")
        except TimeoutException as e:
            if break_time_out:
                logger.error(f"Time out to load page: {web_page}")
                raise
            else:
                self.driver.execute_script("window.stop();")
<<<<<<< HEAD
    
    def click_js(self, selector: str) -> None:
        """Clique sur un élément en utilisant JavaScript."""
        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
        self.driver.execute_script("arguments[0].click();", elem)
    
    def select_drop_down_index(self, selector: str, index: int) -> None:
        """Sélectionne une option dans un dropdown par son index."""
        select_elem = Select(self.get_elem(selector))
        select_elem.select_by_index(index)
    
    def select_drop_down_text(self, selector: str, text: str) -> None:
        """Sélectionne une option dans un dropdown par son texte."""
        select_elem = Select(self.get_elem(selector))
        select_elem.select_by_visible_text(text)
    
    def go_bottom(self, selector: str = "body") -> None:
        """Fait défiler jusqu'en bas de la page."""
        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
        elem.send_keys(Keys.CONTROL + Keys.END)
    
    def go_top(self, selector: str = "body") -> None:
        """Fait défiler jusqu'en haut de la page."""
        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
        elem.send_keys(Keys.CONTROL + Keys.UP)
    
    def go_down(self, selector: str = "body") -> None:
        """Fait défiler vers le bas."""
        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
        elem.send_keys(Keys.PAGE_DOWN)
    
    def go_up(self, selector: str = "body") -> None:
        """Fait défiler vers le haut."""
        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
        elem.send_keys(Keys.PAGE_UP)
    
    def switch_to_main_frame(self) -> None:
        """Basculer vers le frame principal."""
        self.driver.switch_to.default_content()
    
    def switch_to_frame(self, frame_selector: str) -> None:
        """Basculer vers un frame spécifique."""
        frame = self.get_elem(frame_selector)
        self.driver.switch_to.frame(frame)
    
    def open_tab(self) -> None:
        """Ouvre un nouvel onglet."""
        self.driver.execute_script("window.open('');")
    
    def close_tab(self) -> None:
        """Ferme l'onglet actuel."""
=======
                logger.warning(f"Page load stopped due to timeout: {web_page}")
        except Exception as e:
            logger.error(f"Failed to set page to {web_page}: {e}")
            raise

    def click_js(self, selector: str):
        """Click on an element using JavaScript."""
        try:
            elem = self.driver.find_element(By.CSS_SELECTOR, selector)
            self.driver.execute_script("arguments[0].click();", elem)
            logger.info(f"Clicked on element with selector {selector} using JavaScript.")
        except Exception as e:
            logger.error(f"Failed to click on element with selector {selector} using JavaScript: {e}")
            raise

    def select_drop_down_index(self, selector, index):
        """Select an option from a dropdown by index."""
        try:
            select_elem = Select(self.get_elem(selector))
            select_elem.select_by_index(index)
            logger.info(f"Selected index {index} from dropdown with selector {selector}.")
        except Exception as e:
            logger.error(f"Failed to select index {index} from dropdown with selector {selector}: {e}")
            raise

    def select_drop_down_text(self, selector, text):
        """Select an option from a dropdown by visible text."""
        try:
            select_elem = Select(self.get_elem(selector))
            select_elem.select_by_visible_text(text)
            logger.info(f"Selected text '{text}' from dropdown with selector {selector}.")
        except Exception as e:
            logger.error(f"Failed to select text '{text}' from dropdown with selector {selector}: {e}")
            raise

    def go_bottom(self, selector: str = "body"):
        """Scroll to the bottom of the page."""
        try:
            elem = self.driver.find_element(By.CSS_SELECTOR, selector)
            elem.send_keys(Keys.CONTROL + Keys.END)
            logger.info("Scrolled to the bottom of the page.")
        except Exception as e:
            logger.error(f"Failed to scroll to the bottom of the page: {e}")
            raise

    def go_top(self, selector: str = "body"):
        """Scroll to the top of the page."""
        try:
            elem = self.driver.find_element(By.CSS_SELECTOR, selector)
            elem.send_keys(Keys.CONTROL + Keys.UP)
            logger.info("Scrolled to the top of the page.")
        except Exception as e:
            logger.error(f"Failed to scroll to the top of the page: {e}")
            raise

    def go_down(self, selector: str = "body"):
        """Scroll down the page."""
        try:
            elem = self.driver.find_element(By.CSS_SELECTOR, selector)
            elem.send_keys(Keys.PAGE_DOWN)
            logger.info("Scrolled down the page.")
        except Exception as e:
            logger.error(f"Failed to scroll down the page: {e}")
            raise

    def go_up(self, selector: str = "body"):
        """Scroll up the page."""
        try:
            elem = self.driver.find_element(By.CSS_SELECTOR, selector)
            elem.send_keys(Keys.PAGE_UP)
            logger.info("Scrolled up the page.")
        except Exception as e:
            logger.error(f"Failed to scroll up the page: {e}")
            raise

    def switch_to_main_frame(self):
        """Switch to the main frame."""
        try:
            self.driver.switch_to.default_content()
            logger.info("Switched to the main frame.")
        except Exception as e:
            logger.error(f"Failed to switch to the main frame: {e}")
            raise

    def switch_to_frame(self, frame_selector):
        """Switch to a specific frame."""
        try:
            frame = self.get_elem(frame_selector)
            self.driver.switch_to.frame(frame)
            logger.info(f"Switched to frame with selector {frame_selector}.")
        except Exception as e:
            logger.error(f"Failed to switch to frame with selector {frame_selector}: {e}")
            raise

    def open_tab(self):
        """Open a new tab."""
        try:
            self.driver.execute_script("window.open('');")
            logger.info("New tab opened.")
        except Exception as e:
            logger.error(f"Failed to open new tab: {e}")
            raise

    def close_tab(self):
        """Close the current tab."""
>>>>>>> c9ba7d302208764d82a1218f7368eb37bb590766
        try:
            self.driver.close()
            logger.info("Current tab closed.")
        except Exception as e:
<<<<<<< HEAD
            self.logger.error(f"Failed to close tab: {e}")
    
    def switch_to_tab(self, number: int) -> None:
        """Basculer vers un onglet spécifique."""
        windows = self.driver.window_handles
        self.driver.switch_to.window(windows[number])
    
    def refresh_selenium(self, time_units: int = 1, back_tab: int = 0) -> None:
        """Rafraîchit le navigateur."""
        self.open_tab()
        self.switch_to_tab(len(self.driver.window_handles) - 1)
        time.sleep(self.basetime * time_units)
        self.close_tab()
        self.switch_to_tab(back_tab)
        time.sleep(self.basetime * time_units)
    
    def save_page(self, file_html: str) -> None:
        """Sauvegarde la page actuelle en HTML."""
        page_html = self.driver.page_source
        page_file = open(os.path.join(self.current_folder, file_html), "w", encoding='utf-8')
        page_file.write(page_html)
        page_file.close()
    
    def zoom(self, percentage: int = 50) -> None:
        """Modifie le zoom de la page."""
        script = f"document.body.style.zoom='{percentage}%'"
        self.driver.execute_script(script)
    
    def kill(self) -> None:
        """Tue toutes les instances du navigateur."""
        tabs = self.driver.window_handles
        for _ in tabs:
            self.switch_to_tab(0)
            self.end_browser()
    
    def scroll(self, selector: str, scroll_x: int, scroll_y: int) -> None:
        """Fait défiler jusqu'à une position spécifique."""
        elem = self.get_elem(selector)
        self.driver.execute_script("arguments[0].scrollTo(arguments[1], arguments[2])", elem, scroll_x, scroll_y)
    
    def set_local_storage(self, key: str, value: str) -> None:
        """Définit une valeur dans le localStorage."""
        script = f"window.localStorage.setItem('{key}', '{value}')"
        self.driver.execute_script(script)
    
    def wait_element(self, selector: str, timeout: int = 10, by: By = By.CSS_SELECTOR) -> webdriver.WebElement:
        """Attend qu'un élément soit présent et cliquable."""
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, selector))
        )
    
    def wait_disappear(self, selector: str, timeout: int = 10, by: By = By.CSS_SELECTOR) -> None:
        """Attend que l'élément disparaisse."""
        return WebDriverWait(self.driver, timeout).until_not(
            lambda d: d.find_element(by, selector)
        )
    
    def navigate_with_retry(self, url: str, max_retries: int = 3, retry_delay: int = 2) -> bool:
        """Navigue vers une URL avec gestion des erreurs."""
        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                return True
            except Exception as e:
                self.logger.warning(f"Tentative {attempt + 1}/{max_retries} échouée: {e}")
                time.sleep(retry_delay)
        raise Exception(f"Echec après {max_retries} tentatives")
    
    def refresh_page(self) -> None:
        """Rafraîchit la page en gardant le contexte des frames."""
        current_frame = self.driver.current_frame
        self.driver.refresh()
        if current_frame:
            self.driver.switch_to.frame(current_frame)
    
    def save_cookies(self) -> None:
        """Sauvegarde les cookies dans un fichier."""
        cookies = self.driver.get_cookies()
        with open('cookies.json', 'w') as f:
            json.dump(cookies, f)
    
    def load_cookies(self) -> None:
        """Charge les cookies depuis un fichier."""
        try:
            with open('cookies.json', 'r') as f:
                cookies = json.load(f)
                for cookie in cookies:
                    self.driver.add_cookie(cookie)
        except FileNotFoundError:
            self.logger.warning("Fichier de cookies non trouvé")
    
    def execute_script_optimized(self, script: str, *args) -> any:
        """Exécute un script JavaScript avec timeout personnalisable."""
        try:
            return self.driver.execute_async_script(script, *args)
        except Exception as e:
            self.logger.error(f"Erreur d'exécution du script: {e}")
            raise
    
    def screenshot_with_retry(self, filename: str, max_retries: int = 3) -> bool:
        """Prend une capture d'écran avec plusieurs tentatives."""
        for attempt in range(max_retries):
            try:
                self.driver.save_screenshot(filename)
                return True
            except Exception as e:
                self.logger.warning(f"Tentative {attempt + 1}/{max_retries}: {e}")
                time.sleep(1)
        raise Exception(f"Echec après {max_retries} tentatives")
    
    def switch_to_newest_window(self) -> bool:
        """Basculer vers la fenêtre la plus récente."""
        windows = self.driver.window_handles
        if len(windows) > 1:
            self.driver.switch_to.window(windows[-1])
            return True
        return False
    
    def close_all_but_main(self) -> None:
        """Ferme toutes les fenêtres sauf la principale."""
        main_window = self.driver.current_window_handle
        for window in self.driver.window_handles:
            if window != main_window:
                self.driver.switch_to.window(window)
                self.driver.close()
        self.driver.switch_to.window(main_window)
    
    def get_window_handles_info(self) -> Dict:
        """Obtient des informations sur toutes les fenêtres ouvertes."""
        windows = {}
        current_handle = self.driver.current_window_handle
        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            windows[handle] = {
                'title': self.driver.title,
                'url': self.driver.current_url
            }
        self.driver.switch_to.window(current_handle)
        return windows
    
    def verify_element_state(self, selector: str, expected_state: str, timeout: int = 10) -> bool:
        """Vérifie l'état d'un élément."""
        element = self.wait_element(selector, timeout)
        states = {
            'visible': lambda e: e.is_visible(),
            'enabled': lambda e: e.is_enabled(),
            'selected': lambda e: e.is_selected(),
            'contains_text': lambda e: expected_state in e.text
        }
        return states[expected_state](element)
    
    def validate_form(self, form_selector: str, expected_fields: Dict[str, str]) -> None:
        """Valide que tous les champs d'un formulaire sont présents."""
        form = self.wait_element(form_selector)
        for field_name, field_type in expected_fields.items():
            selector = f"{form_selector} {field_type}"
            if not self.wait_element(selector, timeout=5):
                raise ValueError(f"Champ '{field_name}' manquant")
    
    def check_page_loaded(self, expected_title: Optional[str] = None, expected_url: Optional[str] = None) -> bool:
        """Vérifie que la page est complètement chargée."""
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                if expected_title and expected_title not in self.driver.title:
                    raise Exception("Titre incorrect")
                if expected_url and expected_url not in self.driver.current_url:
                    raise Exception("URL incorrect")
                return True
            except:
                time.sleep(1)
        raise Exception(f"Page non chargée après {max_attempts} tentatives")
    
    def save_screenshot_with_context(self, filename: str, extra_info: Optional[Dict] = None) -> None:
        
        pass 






    def execute_custom_script(self, script_name: str, *args) -> any:
        """Exécute des scripts personnalisés avec gestion d'erreurs."""
        script_path = os.path.join(self.script_directory, f"{script_name}.js")
        with open(script_path, 'r') as f:
            script_content = f.read()
        try:
            return self.driver.execute_script(script_content, *args)
        except Exception as e:
            self.logger.error(f"Erreur d'exécution du script {script_name}: {e}")
            raise

    def screenshot_with_elements(self, filename: str, elements: Optional[List[webdriver.WebElement]] = None) -> None:
        """Prend une capture d'écran avec mise en évidence des éléments."""
        self.driver.save_screenshot(filename)
        if elements:
            for element in elements:
                element.screenshot(f"{filename}_highlight_{elements.index(element)}.png")

    def get_element_dimensions(self, selector: str) -> tuple:
        """Retourne les dimensions et la position d'un élément."""
        element = self.wait_element(selector)
        return element.size, element.location

    def retry_on_failure(self, func, max_attempts: int = 3, delay: int = 1):
        """Décorateur pour les réessais automatiques."""
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    self.logger.warning(
                        f"Tentative {attempt + 1} échouée: {e}. "
                        f"Réessai dans {delay} secondes..."
                    )
                    time.sleep(delay)
            return wrapper

    def safe_execute(self, func) -> any:
        """Exécute une fonction de manière sécurisée."""
        try:
            return func()
        except Exception as e:
            self.logger.error(f"Erreur d'exécution: {e}")
            self.screenshot_with_context("error_screenshot.png", {"error": str(e)})
            raise

    def setup_proxy_rotation(self, proxy_list: List[Dict], rotation_interval: int = 300):
        """Configure une rotation automatique des proxy."""
        self.proxy_list = proxy_list
        self.current_proxy_index = 0
        self.proxy_rotation_interval = rotation_interval
        self.last_proxy_rotation = time.time()
        
        def rotate_proxy():
            current_time = time.time()
            if current_time - self.last_proxy_rotation >= self.proxy_rotation_interval:
                self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
                self.update_proxy(self.proxy_list[self.current_proxy_index])
                self.last_proxy_rotation = current_time
        
        self.proxy_rotation_thread = threading.Thread(target=self._proxy_rotation_monitor, args=(rotate_proxy,))
        self.proxy_rotation_thread.daemon = True
        self.proxy_rotation_thread.start()

    def update_proxy(self, proxy_config: Dict) -> None:
        """Met à jour la configuration proxy en cours."""
        proxy = f"{proxy_config['host']}:{proxy_config['port']}"
        self.driver.quit()
        options = webdriver.ChromeOptions()
        options.add_argument(f"--proxy-server={proxy}")
        if proxy_config.get('username') and proxy_config.get('password'):
            self._create_proxy_auth_extension(proxy_config)
            options.add_extension(self.proxy_auth_plugin)
        self.driver = webdriver.Chrome(options=options)

    def _proxy_rotation_monitor(self, rotation_func):
        """Surveille et gère la rotation des proxy."""
        while True:
            rotation_func()
            time.sleep(60)  # Vérification toutes les minutes

    def handle_ssl_certificates(self, ignore: bool = False) -> None:
        """Gère les certificats SSL avec options configurables."""
        options = webdriver.ChromeOptions()
        if ignore:
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--ignore-ssl-errors')
            options.add_experimental_option('excludeSwitches', ['ignore-certificate-errors'])
        self.driver.quit()
        self.driver = webdriver.Chrome(options=options)

    def install_certificate(self, cert_path: str) -> None:
        """Installe un certificat SSL personnalisé."""
        options = webdriver.ChromeOptions()
        options.add_argument(f"--ssl-key={cert_path}")
        self.driver.quit()
        self.driver = webdriver.Chrome(options=options)

    def monitor_performance(self, interval: int = 60) -> None:
        """Surveille les performances du navigateur."""
        def monitor():
            while True:
                performance_data = self.get_performance_metrics()
                self.logger.info(f"Performances: {performance_data}")
                time.sleep(interval)
        
        self.performance_thread = threading.Thread(target=monitor)
        self.performance_thread.daemon = True
        self.performance_thread.start()

    def get_performance_metrics(self) -> Dict:
        """Obtient les métriques de performance du navigateur."""
        performance_data = self.driver.execute_script("""
        return {
            memory: performance.memory,
            navigation: performance.navigation,
            timing: performance.timing,
            cpu: navigator.hardwareConcurrency,
            jsHeap: window.performance.memory?.usedJSHeapSize,
            totalHeap: window.performance.memory?.totalJSHeapSize
        };
        """)
        return performance_data

    def manage_storage(self, storage_type: str = 'local', data: Optional[Dict] = None) -> Optional[Dict]:
        """Gère le stockage local/session avec des options avancées."""
        if data:
            if storage_type == 'local':
                self.driver.execute_script(
                    f"localStorage.setItem(arguments[0], arguments[1]);",
                    json.dumps(data), json.dumps(data)
                )
            else:
                self.driver.execute_script(
                    f"sessionStorage.setItem(arguments[0], arguments[1]);",
                    json.dumps(data), json.dumps(data)
                )
        else:
            if storage_type == 'local':
                return json.loads(self.driver.execute_script("localStorage.getItem(arguments[0]);"))
            else:
                return json.loads(self.driver.execute_script("sessionStorage.getItem(arguments[0]);"))

    def clear_browser_data(self, types: Optional[List[str]] = None) -> None:
        """Nettoie les données du navigateur de manière sélective."""
        if types is None:
            types = ['cookies', 'cache', 'localStorage', 'sessionStorage']
        
        for type_ in types:
            self.driver.execute_script(f"""
            if (typeof {type_} !== 'undefined') {{
                {type_}.clear();
            }}
            """)

    def download_file(self, url: str, download_folder: Optional[str] = None) -> str:
        """Télécharge un fichier avec gestion des répertoires."""
        if download_folder:
            os.makedirs(download_folder, exist_ok=True)
            self.driver.command_executor._commands["send_command"] = (
                "POST", '/session/$sessionId/chromium/send_command'
            )
            params = {
                'cmd': 'Page.setDownloadBehavior',
                'params': {
                    'behavior': 'allow',
                    'downloadPath': download_folder
                }
            }
            self.driver.execute_command(params)
        
        try:
            self.navigate_with_retry(url)
            filename = os.path.basename(url)
            if download_folder:
                return os.path.join(download_folder, filename)
            return filename
        except Exception as e:
            self.logger.error(f"Erreur de téléchargement: {e}")
            raise

    def execute_javascript_dialog(self, dialog_type: str, text: Optional[str] = None) -> None:
        """Gère les dialogues JavaScript (alert, confirm, prompt)."""
        self.driver.switch_to.alert
        if dialog_type == "prompt" and text:
            self.driver.switch_to.alert.send_keys(text)
        self.driver.switch_to.alert.accept()

    def scroll_to_element_with_offset(self, selector: str, offset_x: int = 0, offset_y: int = 0) -> None:
        """Fait défiler jusqu'à un élément avec décalage."""
        element = self.wait_element(selector)
        self.driver.execute_script(
            f"arguments[0].scrollIntoView();"
            f"window.scrollBy({offset_x}, {offset_y});",
            element
        )

    def get_element_dimensions(self, selector: str) -> tuple:
        """Retourne les dimensions et la position d'un élément."""
        element = self.wait_element(selector)
        return element.size, element.location

    def retry_on_failure(self, func, max_attempts: int = 3, delay: int = 1):
        """Décorateur pour les réessais automatiques."""
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    self.logger.warning(
                        f"Tentative {attempt + 1} échouée: {e}. "
                        f"Réessai dans {delay} secondes..."
                    )
                    time.sleep(delay)
            return wrapper

    def safe_execute(self, func) -> any:
        """Exécute une fonction de manière sécurisée."""
        try:
            return func()
        except Exception as e:
            self.logger.error(f"Erreur d'exécution: {e}")
            self.screenshot_with_context("error_screenshot.png", {"error": str(e)})
            raise

    def setup_proxy_rotation(self, proxy_list: List[Dict], rotation_interval: int = 300):
        """Configure une rotation automatique des proxy."""
        self.proxy_list = proxy_list
        self.current_proxy_index = 0
        self.proxy_rotation_interval = rotation_interval
        self.last_proxy_rotation = time.time()
        
        def rotate_proxy():
            current_time = time.time()
            if current_time - self.last_proxy_rotation >= self.proxy_rotation_interval:
                self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
                self.update_proxy(self.proxy_list[self.current_proxy_index])
                self.last_proxy_rotation = current_time
        
        self.proxy_rotation_thread = threading.Thread(target=self._proxy_rotation_monitor, args=(rotate_proxy,))
        self.proxy_rotation_thread.daemon = True
        self.proxy_rotation_thread.start()

    def update_proxy(self, proxy_config: Dict) -> None:
        """Met à jour la configuration proxy en cours."""
        proxy = f"{proxy_config['host']}:{proxy_config['port']}"
        self.driver.quit()
        options = webdriver.ChromeOptions()
        options.add_argument(f"--proxy-server={proxy}")
        if proxy_config.get('username') and proxy_config.get('password'):
            self._create_proxy_auth_extension(proxy_config)
            options.add_extension(self.proxy_auth_plugin)
        self.driver = webdriver.Chrome(options=options)

    def _proxy_rotation_monitor(self, rotation_func):
        """Surveille et gère la rotation des proxy."""
        while True:
            rotation_func()
            time.sleep(60)  # Vérification toutes les minutes

    def handle_ssl_certificates(self, ignore: bool = False) -> None:
        """Gère les certificats SSL avec options configurables."""
        options = webdriver.ChromeOptions()
        if ignore:
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--ignore-ssl-errors')
            options.add_experimental_option('excludeSwitches', ['ignore-certificate-errors'])
        self.driver.quit()
        self.driver = webdriver.Chrome(options=options)

    def install_certificate(self, cert_path: str) -> None:
        """Installe un certificat SSL personnalisé."""
        options = webdriver.ChromeOptions()
        options.add_argument(f"--ssl-key={cert_path}")
        self.driver.quit()
        self.driver = webdriver.Chrome(options=options)

    def monitor_performance(self, interval: int = 60) -> None:
        """Surveille les performances du navigateur."""
        def monitor():
            while True:
                performance_data = self.get_performance_metrics()
                self.logger.info(f"Performances: {performance_data}")
                time.sleep(interval)
        
        self.performance_thread = threading.Thread(target=monitor)
        self.performance_thread.daemon = True
        self.performance_thread.start()

    def get_performance_metrics(self) -> Dict:
        """Obtient les métriques de performance du navigateur."""
        performance_data = self.driver.execute_script("""
        return {
            memory: performance.memory,
            navigation: performance.navigation,
            timing: performance.timing,
            cpu: navigator.hardwareConcurrency,
            jsHeap: window.performance.memory?.usedJSHeapSize,
            totalHeap: window.performance.memory?.totalJSHeapSize
        };
        """)
        return performance_data

    def manage_storage(self, storage_type: str = 'local', data: Optional[Dict] = None) -> Optional[Dict]:
        """Gère le stockage local/session avec des options avancées."""
        if data:
            if storage_type == 'local':
                self.driver.execute_script(
                    f"localStorage.setItem(arguments[0], arguments[1]);",
                    json.dumps(data), json.dumps(data)
                )
            else:
                self.driver.execute_script(
                    f"sessionStorage.setItem(arguments[0], arguments[1]);",
                    json.dumps(data), json.dumps(data)
                )
        else:
            if storage_type == 'local':
                return json.loads(self.driver.execute_script("localStorage.getItem(arguments[0]);"))
            else:
                return json.loads(self.driver.execute_script("sessionStorage.getItem(arguments[0]);"))

    def clear_browser_data(self, types: Optional[List[str]] = None) -> None:
        """Nettoie les données du navigateur de manière sélective."""
        if types is None:
            types = ['cookies', 'cache', 'localStorage', 'sessionStorage']
        
        for type_ in types:
            self.driver.execute_script(f"""
            if (typeof {type_} !== 'undefined') {{
                {type_}.clear();
            }}
            """)

    def execute_custom_script(self, script_name: str, *args) -> any:
        """Exécute des scripts personnalisés avec gestion d'erreurs."""
        script_path = os.path.join(self.script_directory, f"{script_name}.js")
        with open(script_path, 'r') as f:
            script_content = f.read()
        try:
            return self.driver.execute_script(script_content, *args)
        except Exception as e:
            self.logger.error(f"Erreur d'exécution du script {script_name}: {e}")
            raise

    def screenshot_with_elements(self, filename: str, elements: Optional[List[webdriver.WebElement]] = None) -> None:
        """Prend une capture d'écran avec mise en évidence des éléments."""
        self.driver.save_screenshot(filename)
        if elements:
            for element in elements:
                element.screenshot(f"{filename}_highlight_{elements.index(element)}.png")

    def get_element_dimensions(self, selector: str) -> tuple:
        """Retourne les dimensions et la position d'un élément."""
        element = self.wait_element(selector)
        return element.size, element.location

    def retry_on_failure(self, func, max_attempts: int = 3, delay: int = 1):
        """Décorateur pour les réessais automatiques."""
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    self.logger.warning(
                        f"Tentative {attempt + 1} échouée: {e}. "
                        f"Réessai dans {delay} secondes..."
                    )
                    time.sleep(delay)
            return wrapper

    def safe_execute(self, func) -> any:
        """Exécute une fonction de manière sécurisée."""
        try:
            return func()
        except Exception as e:
            self.logger.error(f"Erreur d'exécution: {e}")
            self.screenshot_with_context("error_screenshot.png", {"error": str(e)})
            raise

    def setup_proxy_rotation(self, proxy_list: List[Dict], rotation_interval: int = 300):
        """Configure une rotation automatique des proxy."""
        self.proxy_list = proxy_list
        self.current_proxy_index = 0
        self.proxy_rotation_interval = rotation_interval
        self.last_proxy_rotation = time.time()
        
        def rotate_proxy():
            current_time = time.time()
            if current_time - self.last_proxy_rotation >= self.proxy_rotation_interval:
                self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
                self.update_proxy(self.proxy_list[self.current_proxy_index])
                self.last_proxy_rotation = current_time
        
        self.proxy_rotation_thread = threading.Thread(target=self._proxy_rotation_monitor, args=(rotate_proxy,))
        self.proxy_rotation_thread.daemon = True
        self.proxy_rotation_thread.start()

    def update_proxy(self, proxy_config: Dict) -> None:
        """Met à jour la configuration proxy en cours."""
        proxy = f"{proxy_config['host']}:{proxy_config['port']}"
        self.driver.quit()
        options = webdriver.ChromeOptions()
        options.add_argument(f"--proxy-server={proxy}")
        if proxy_config.get('username') and proxy_config.get('password'):
            self._create_proxy_auth_extension(proxy_config)
            options.add_extension(self.proxy_auth_plugin)
        self.driver = webdriver.Chrome(options=options)

    def _proxy_rotation_monitor(self, rotation_func):
        """Surveille et gère la rotation des proxy."""
        while True:
            rotation_func()
            time.sleep(60)  # Vérification toutes les minutes

    def handle_ssl_certificates(self, ignore: bool = False) -> None:
        """Gère les certificats SSL avec options configurables."""
        options = webdriver.ChromeOptions()
        if ignore:
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--ignore-ssl-errors')
            options.add_experimental_option('excludeSwitches', ['ignore-certificate-errors'])
        self.driver.quit()
        self.driver = webdriver.Chrome(options=options)

    def install_certificate(self, cert_path: str) -> None:
        """Installe un certificat SSL personnalisé."""
        options = webdriver.ChromeOptions()
        options.add_argument(f"--ssl-key={cert_path}")
        self.driver.quit()
        self.driver = webdriver.Chrome(options=options)

    def monitor_performance(self, interval: int = 60) -> None:
        """Surveille les performances du navigateur."""
        def monitor():
            while True:
                performance_data = self.get_performance_metrics()
                self.logger.info(f"Performances: {performance_data}")
                time.sleep(interval)
        
        self.performance_thread = threading.Thread(target=monitor)
        self.performance_thread.daemon = True
        self.performance_thread.start()

    def get_performance_metrics(self) -> Dict:
        """Obtient les métriques de performance du navigateur."""
        performance_data = self.driver.execute_script("""
        return {
            memory: performance.memory,
            navigation: performance.navigation,
            timing: performance.timing,
            cpu: navigator.hardwareConcurrency,
            jsHeap: window.performance.memory?.usedJSHeapSize,
            totalHeap: window.performance.memory?.totalJSHeapSize
        };
        """)
        return performance_data

    def manage_storage(self, storage_type: str = 'local', data: Optional[Dict] = None) -> Optional[Dict]:
        """Gère le stockage local/session avec des options avancées."""
        if data:
            if storage_type == 'local':
                self.driver.execute_script(
                    f"localStorage.setItem(arguments[0], arguments[1]);",
                    json.dumps(data), json.dumps(data)
                )
            else:
                self.driver.execute_script(
                    f"sessionStorage.setItem(arguments[0], arguments[1]);",
                    json.dumps(data), json.dumps(data)
                )
        else:
            if storage_type == 'local':
                return json.loads(self.driver.execute_script("localStorage.getItem(arguments[0]);"))
            else:
                return json.loads(self.driver.execute_script("sessionStorage.getItem(arguments[0]);"))

    def clear_browser_data(self, types: Optional[List[str]] = None) -> None:
        """Nettoie les données du navigateur de manière sélective."""
        if types is None:
            types = ['cookies', 'cache', 'localStorage', 'sessionStorage']
        
        for type_ in types:
            self.driver.execute_script(f"""
            if (typeof {type_} !== 'undefined') {{
                {type_}.clear();
            }}
            """)

    def execute_custom_script(self, script_name: str, *args) -> any:
        """Exécute des scripts personnalisés avec gestion d'erreurs."""
        script_path = os.path.join(self.script_directory, f"{script_name}.js")
        with open(script_path, 'r') as f:
            script_content = f.read()
        try:
            return self.driver.execute_script(script_content, *args)
        except Exception as e:
            self.logger.error(f"Erreur d'exécution du script {script_name}: {e}")
            raise

    def screenshot_with_elements(self, filename: str, elements: Optional[List[webdriver.WebElement]] = None) -> None:
        """Prend une capture d'écran avec mise en évidence des éléments."""
        self.driver.save_screenshot(filename)
        if elements:
            for element in elements:
                element.screenshot(f"{filename}_highlight_{elements.index(element)}.png")

    def get_element_dimensions(self, selector: str) -> tuple:
        """Retourne les dimensions et la position d'un élément."""
        element = self.wait_element(selector)
        return element.size, element.location

    def retry_on_failure(self, func, max_attempts: int = 3, delay: int = 1):
        """Décorateur pour les réessais automatiques."""
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    self.logger.warning(
                        f"Tentative {attempt + 1} échouée: {e}. "
                        f"Réessai dans {delay} secondes..."
                    )
                    time.sleep(delay)
            return wrapper

    def safe_execute(self, func) -> any:
        """Exécute une fonction de manière sécurisée."""
        try:
            return func()
        except Exception as e:
            self.logger.error(f"Erreur d'exécution: {e}")
            self.screenshot_with_context("error_screenshot.png", {"error": str(e)})
            raise

    def setup_proxy_rotation(self, proxy_list: List[Dict], rotation_interval: int = 300):
        """Configure une rotation automatique des proxy."""
        self.proxy_list = proxy_list
        self.current_proxy_index = 0
        self.proxy_rotation_interval = rotation_interval
        self.last_proxy_rotation = time.time()
        
        def rotate_proxy():
            current_time = time.time()
            if current_time - self.last_proxy_rotation >= self.proxy_rotation_interval:
                self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
                self.update_proxy(self.proxy_list[self.current_proxy_index])
                self.last_proxy_rotation = current_time
        
        self.proxy_rotation_thread = threading.Thread(target=self._proxy_rotation_monitor, args=(rotate_proxy,))
        self.proxy_rotation_thread.daemon = True
        self.proxy_rotation_thread.start()

    def update_proxy(self, proxy_config: Dict) -> None:
        """Met à jour la configuration proxy en cours."""
        proxy = f"{proxy_config['host']}:{proxy_config['port']}"
        self.driver.quit()
        options = webdriver.ChromeOptions()
        options.add_argument(f"--proxy-server={proxy}")
        if proxy_config.get('username') and proxy_config.get('password'):
            self._create_proxy_auth_extension(proxy_config)
            options.add_extension(self.proxy_auth_plugin)
        self.driver = webdriver.Chrome(options=options)

    def _proxy_rotation_monitor(self, rotation_func):
        """Surveille et gère la rotation des proxy."""
        while True:
            rotation_func()
            time.sleep(60)  # Vérification toutes les minutes

    def handle_ssl_certificates(self, ignore: bool = False) -> None:
        """Gère les certificats SSL avec options configurables."""
        options = webdriver.ChromeOptions()
        if ignore:
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--ignore-ssl-errors')
            options.add_experimental_option('excludeSwitches', ['ignore-certificate-errors'])
        self.driver.quit()
        self.driver = webdriver.Chrome(options=options)

    def install_certificate(self, cert_path: str) -> None:
        """Installe un certificat SSL personnalisé."""
        options = webdriver.ChromeOptions()
        options.add_argument(f"--ssl-key={cert_path}")
        self.driver.quit()
        self.driver = webdriver.Chrome(options=options)

    def monitor_performance(self, interval: int = 60) -> None:
        """Surveille les performances du navigateur."""
        def monitor():
            while True:
                performance_data = self.get_performance_metrics()
                self.logger.info(f"Performances: {performance_data}")
                time.sleep(interval)
        
        self.performance_thread = threading.Thread(target=monitor)
        self.performance_thread.daemon = True
        self.performance_thread.start()

    def get_performance_metrics(self) -> Dict:
        """Obtient les métriques de performance du navigateur."""
        performance_data = self.driver.execute_script("""
        return {
            memory: performance.memory,
            navigation: performance.navigation,
            timing: performance.timing,
            cpu: navigator.hardwareConcurrency,
            jsHeap: window.performance.memory?.usedJSHeapSize,
            totalHeap: window.performance.memory?.totalJSHeapSize
        };
        """)
        return performance_data

    def manage_storage(self, storage_type: str = 'local', data: Optional[Dict] = None) -> Optional[Dict]:
        """Gère le stockage local/session avec des options avancées."""
        if data:
            if storage_type == 'local':
                self.driver.execute_script(
                    f"localStorage.setItem(arguments[0], arguments[1]);",
                    json.dumps(data), json.dumps(data)
                )
            else:
                self.driver.execute_script(
                    f"sessionStorage.setItem(arguments[0], arguments[1]);",
                    json.dumps(data), json.dumps(data)
                )
        else:
            if storage_type == 'local':
                return json.loads(self.driver.execute_script("localStorage.getItem(arguments[0]);"))
            else:
                return json.loads(self.driver.execute_script("sessionStorage.getItem(arguments[0]);"))

    def clear_browser_data(self, types: Optional[List[str]] = None) -> None:
        """Nettoie les données du navigateur de manière sélective."""
        if types is None:
            types = ['cookies', 'cache', 'localStorage', 'sessionStorage']
        
        for type_ in types:
            self.driver.execute_script(f"""
            if (typeof {type_} !== 'undefined') {{
                {type_}.clear();
            }}
            """)

    def execute_custom_script(self, script_name: str, *args) -> any:
        """Exécute des scripts personnalisés avec gestion d'erreurs."""
        script_path = os.path.join(self.script_directory, f"{script_name}.js")
        with open(script_path, 'r') as f:
            script_content = f.read()
        try:
            return self.driver.execute_script(script_content, *args)
        except Exception as e:
            self.logger.error(f"Erreur d'exécution du script {script_name}: {e}")
            raise

    def screenshot_with_elements(self, filename: str, elements: Optional[List[webdriver.WebElement]] = None) -> None:
        """Prend une capture d'écran avec mise en évidence des éléments."""
        self.driver.save_screenshot(filename)
        if elements:
            for element in elements:
                element.screenshot(f"{filename}_highlight_{elements.index(element)}.png")

    def get_element_dimensions(self, selector: str) -> tuple:
        """Retourne les dimensions et la position d'un élément."""
        element = self.wait_element(selector)
        return element.size, element.location

    def retry_on_failure(self, func, max_attempts: int = 3, delay: int = 1):
        """Décorateur pour les réessais automatiques."""
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                   pass

















# import os
# import time
# import zipfile
# import logging
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.support.ui import Select
# from selenium.webdriver.chrome.service import Service

# # Configuration du logging
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(levelname)s - %(message)s",
#     filename="web_scraping.log"
# )
# logger = logging.getLogger(__name__)

# class WebScraping:
#     service = None
#     options = None

#     def __init__(self, headless=False, time_out=0,
#                  proxy_server="", proxy_port="", proxy_user="", proxy_pass="",
#                  chrome_folder="", user_agent=False, 
#                  download_folder="", extensions=[], incognito=False, experimentals=True,
#                  start_killing=False, start_openning: bool = True, width: int = 1280, height: int = 720,
#                  mute: bool = True, *args, **kwargs,):
#         """ Constructor of the class
#         Args:
#             headless (bool, optional): Hide (True) or Show (False) the google chrome window. Defaults to False.
#             time_out (int, optional): Wait time to load each page. Defaults to 0.
#             proxy_server (str, optional): Proxy server or host to use in the window. Defaults to "".
#             proxy_port (str, optional): Proxy post to use in the window. Defaults to "".
#             proxy_user (str, optional): Proxy user to use in the window. Defaults to "".
#             proxy_pass (str, optional): Proxy password to use in the window. Defaults to "".
#             chrome_folder (str, optional): folder with user google chrome data. Defaults to "".
#             user_agent (bool, optional): user agent to setup to chrome. Defaults to False.
#             download_folder (str, optional): Default download folder. Defaults to "".
#             extensions (list, optional): Paths of extensions in format .crx, to install. Defaults to [].
#             incognito (bool, optional): Open chrome in incognito mode. Defaults to False.
#             experimentals (bool, optional): Activate the experimentals options. Defaults to True.
#             start_killing (bool, optional): Kill chrome process before start. Defaults to False.
#             start_openning (bool, optional): Open chrome window before start. Defaults to True.
#             width (int, optional): Width of the window. Defaults to 1280.
#             height (int, optional): Height of the window. Defaults to 720.
#             mute (bool, optional): Mute the audio of the window. Defaults to True.
#         """
#         self.basetime = 1
#         self.current_folder = os.path.dirname(__file__)
#         self.__headless__ = headless
#         self.__proxy_server__ = proxy_server
#         self.__proxy_port__ = proxy_port
#         self.__proxy_user__ = proxy_user
#         self.__proxy_pass__ = proxy_pass
#         self.__pluginfile__ = os.path.join(self.current_folder, 'proxy_auth_plugin.zip')
#         self.__chrome_folder__ = chrome_folder
#         self.__user_agent__ = user_agent
#         self.__download_folder__ = download_folder
#         self.__extensions__ = extensions
#         self.__incognito__ = incognito
#         self.__experimentals__ = experimentals
#         self.__start_openning__ = start_openning
#         self.__width__ = width
#         self.__height__ = height
#         self.__mute__ = mute
#         self.__web_page__ = None

#         if start_killing:
#             logger.info("Trying to kill chrome...")
#             command = 'taskkill /IM "chrome.eexe" /F'
#             os.system(command)
#             logger.info("Chrome killed successfully.")

#         if self.__start_openning__:
#             self.__set_browser_instance__()

#         if time_out > 0:
#             self.driver.set_page_load_timeout(time_out)


#         # ... votre code existant ...
#         self.logger = logging.getLogger(__name__)
#         self.logger.setLevel(logging.INFO)
        
#         # Ajouter un handler pour la console
#         ch = logging.StreamHandler()
#         ch.setFormatter(logging.Formatter(
#             '%(asctime)s - %(levelname)s - %(message)s'
#         ))
#         self.logger.addHandler(ch)

#     def __set_browser_instance__(self):
#         """Configure and start the browser instance."""
#         os.environ['WDM_LOG_LEVEL'] = '0'
#         os.environ['WDM_PRINT_FIRST_LINE'] = 'False'

#         if not WebScraping.options:
#             WebScraping.options = webdriver.ChromeOptions()
#             WebScraping.options.add_argument('--no-sandbox')
#             WebScraping.options.add_argument('--start-maximized')
#             WebScraping.options.add_argument('--output=/dev/null')
#             WebScraping.options.add_argument('--log-level=3')
#             WebScraping.options.add_argument("--disable-notifications")
#             WebScraping.options.add_argument("--disable-infobars")
#             WebScraping.options.add_argument("--safebrowsing-disable-download-protection")
#             WebScraping.options.add_argument("--disable-dev-shm-usage")
#             WebScraping.options.add_argument("--disable-renderer-backgrounding")
#             WebScraping.options.add_argument("--disable-background-timer-throttling")
#             WebScraping.options.add_argument("--disable-backgrounding-occluded-windows")
#             WebScraping.options.add_argument("--disable-client-side-phishing-detection")
#             WebScraping.options.add_argument("--disable-crash-reporter")
#             WebScraping.options.add_argument("--disable-oopr-debug-crash-dump")
#             WebScraping.options.add_argument("--no-crash-upload")
#             WebScraping.options.add_argument("--disable-gpu")
#             WebScraping.options.add_argument("--disable-extensions")
#             WebScraping.options.add_argument("--disable-low-res-tiling")
#             WebScraping.options.add_argument("--log-level=3")
#             WebScraping.options.add_argument("--silent")

#             if self.__experimentals__:
#                 WebScraping.options.add_experimental_option('excludeSwitches', ['enable-logging', "enable-automation"])
#                 WebScraping.options.add_experimental_option('useAutomationExtension', False)

#             WebScraping.options.add_argument(f"--window-size={self.__width__},{self.__height__}")

#             if self.__headless__:
#                 WebScraping.options.add_argument("--headless=new")

#             if self.__mute__:
#                 WebScraping.options.add_argument("--mute-audio")

#             if self.__chrome_folder__:
#                 WebScraping.options.add_argument(f"--user-data-dir={self.__chrome_folder__}")

#             if self.__user_agent__:
#                 WebScraping.options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36')

#             if self.__download_folder__:
#                 prefs = {
#                     "download.default_directory": f"{self.__download_folder__}",
#                     "download.prompt_for_download": "false",
#                     'profile.default_content_setting_values.automatic_downloads': 1,
#                     'profile.default_content_settings.popups': 0,
#                     "download.directory_upgrade": True,
#                     "plugins.always_open_pdf_externally": True,
#                     "plugins.plugins_list": [{"enabled": False, "name": "Chrome PDF Viewer"}],
#                     'download.extensions_to_open': 'xml',
#                     'safebrowsing.enabled': True
#                 }
#                 WebScraping.options.add_experimental_option("prefs", prefs)

#             if self.__extensions__:
#                 for extension in self.__extensions__:
#                     WebScraping.options.add_extension(extension)

#             if self.__incognito__:
#                 WebScraping.options.add_argument("--incognito")

#             if self.__experimentals__:
#                 WebScraping.options.add_argument("--disable-blink-features=AutomationControlled")

#         if self.__proxy_server__ and self.__proxy_port__ and not self.__proxy_user__ and not self.__proxy_pass__:
#             proxy = f"{self.__proxy_server__}:{self.__proxy_port__}"
#             WebScraping.options.add_argument(f"--proxy-server={proxy}")

#         if self.__proxy_server__ and self.__proxy_port__ and self.__proxy_user__ and self.__proxy_pass__:
#             self.__create_proxy_extesion__()
#             WebScraping.options.add_extension(self.__pluginfile__)

#         if not WebScraping.service:
#             WebScraping.service = Service()

#         self.driver = webdriver.Chrome(service=WebScraping.service, options=WebScraping.options)

#     def __create_proxy_extesion__(self):
#         """Create a proxy extension for authenticated proxies."""
#         manifest_json = """
#         {
#             "version": "1.0.0",
#             "manifest_version": 2,
#             "name": "Chrome Proxy",
#             "permissions": [
#                 "proxy",
#                 "tabs",
#                 "unlimitedStorage",
#                 "storage",
#                 "<all_urls>",
#                 "webRequest",
#                 "webRequestBlocking"
#             ],
#             "background": {
#                 "scripts": ["background.js"]
#             },
#             "minimum_chrome_version":"22.0.0"
#         }
#         """
#         background_js = """
#         var config = {
#                 mode: "fixed_servers",
#                 rules: {
#                 singleProxy: {
#                     scheme: "http",
#                     host: "%s",
#                     port: parseInt(%s)
#                 },
#                 bypassList: ["localhost"]
#                 }
#             };
#         chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});
#         function callbackFn(details) {
#             return {
#                 authCredentials: {
#                     username: "%s",
#                     password: "%s"
#                 }
#             };
#         }
#         chrome.webRequest.onAuthRequired.addListener(
#                     callbackFn,
#                     {urls: ["<all_urls>"]},
#                     ['blocking']
#         );
#         """ % (self.__proxy_server__, self.__proxy_port__, self.__proxy_user__, self.__proxy_pass__)

#         with zipfile.ZipFile(self.__pluginfile__, 'w') as zp:
#             zp.writestr("manifest.json", manifest_json)
#             zp.writestr("background.js", background_js)

#     def set_cookies(self, cookies: list):
#         """Set cookies in the browser."""
#         cookies_formatted = []
#         for cookie in cookies:
#             if "expirationDate" in cookie:
#                 cookie["expiry"] = int(cookie["expirationDate"])
#                 del cookie["expirationDate"]
#             cookies_formatted.append(cookie)

#         for cookie in cookies_formatted:
#             try:
#                 self.driver.add_cookie(cookie)
#             except Exception as e:
#                 logger.error(f"Failed to add cookie: {e}")

#     def screenshot(self, base_name):
#         """Take a screenshot of the current page."""
#         if str(base_name).endswith(".png"):
#             file_name = base_name
#         else:
#             file_name = f"{base_name}.png"
#         self.driver.save_screenshot(file_name)

#     def full_screenshot(self, path: str):
#         """Take a full screenshot of the current page."""
#         original_size = self.driver.get_window_size()
#         required_width = self.driver.execute_script('return document.body.parentNode.scrollWidth')
#         required_height = self.driver.execute_script('return document.body.parentNode.scrollHeight')
#         self.driver.set_window_size(required_width, required_height)
#         self.screenshot(path)  # avoids scrollbar
#         self.driver.set_window_size(original_size['width'], original_size['height'])

#     def get_browser(self):
#         """Get the current browser instance."""
#         return self.driver

#     def end_browser(self):
#         """Close the browser instance."""
#         self.driver.quit()

#     def __reload_browser__(self):
#         """Reload the browser instance."""
#         self.end_browser()
#         self.driver = self.get_browser()
#         self.driver.get(self.__web_page__)

#     def send_data(self, selector, data):
#         """Send data to an input field."""
#         elem = self.driver.find_element(By.CSS_SELECTOR, selector)
#         elem.send_keys(data)

#     def click(self, selector):
#         """Click on an element."""
#         elem = self.driver.find_element(By.CSS_SELECTOR, selector)
#         elem.click()

#     def wait_load(self, selector, time_out=1, refresh_back_tab=-1):
#         """Wait for an element to load."""
#         total_time = 0
#         while True:
#             if total_time < time_out:
#                 total_time += 1
#                 try:
#                     elem = self.driver.find_element(By.CSS_SELECTOR, selector)
#                     elem.text
#                     break
#                 except Exception as e:
#                     if refresh_back_tab != -1:
#                         self.refresh_selenium(back_tab=refresh_back_tab)
#                     else:
#                         time.sleep(self.basetime)
#                     continue
#             else:
#                 raise Exception(f"Time out exceeded. The element {selector} is not in the page.")

#     def wait_die(self, selector, time_out=10):
#         """Wait for an element to disappear."""
#         total_time = 0
#         while True:
#             if total_time < time_out:
#                 total_time += 1
#                 try:
#                     elem = self.driver.find_element(By.CSS_SELECTOR, selector)
#                     elem.text
#                     time.sleep(self.basetime)
#                     continue
#                 except:
#                     break
#             else:
#                 raise Exception(f"Time out exceeded. The element {selector} is still in the page.")

#     def get_text(self, selector):
#         """Get the text of an element."""
#         try:
#             elem = self.driver.find_element(By.CSS_SELECTOR, selector)
#             return elem.text
#         except Exception as e:
#             logger.error(f"Failed to get text: {e}")
#             return None

#     def get_texts(self, selector):
#         """Get the texts of multiple elements."""
#         texts = []
#         elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
#         for elem in elems:
#             try:
#                 texts.append(elem.text)
#             except Exception as e:
#                 logger.error(f"Failed to get text: {e}")
#                 continue
#         return texts

#     def set_attrib(self, selector, attrib_name, attrib_value):
#         """Set an attribute of an element."""
#         elem = self.driver.find_element(By.CSS_SELECTOR, selector)
#         self.driver.execute_script(f"arguments[0].setAttribute('{attrib_name}', '{attrib_value}');", elem)

#     def get_attrib(self, selector, attrib_name):
#         """Get an attribute of an element."""
#         try:
#             elem = self.driver.find_element(By.CSS_SELECTOR, selector)
#             return elem.get_attribute(attrib_name)
#         except Exception as e:
#             logger.error(f"Failed to get attribute: {e}")
#             return None

#     def get_attribs(self, selector, attrib_name, allow_duplicates=True, allow_empty=True):
#         """Get attributes of multiple elements."""
#         attributes = []
#         elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
#         for elem in elems:
#             try:
#                 attribute = elem.get_attribute(attrib_name)
#                 if not allow_duplicates and attribute in attributes:
#                     continue
#                 if not allow_empty and attribute.strip() == "":
#                     continue
#                 attributes.append(attribute)
#             except Exception as e:
#                 logger.error(f"Failed to get attribute: {e}")
#                 continue
#         return attributes

#     def get_elem(self, selector):
#         """Get a single element."""
#         elem = self.driver.find_element(By.CSS_SELECTOR, selector)
#         return elem

#     def get_elems(self, selector):
#         """Get multiple elements."""
#         elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
#         return elems

#     def set_page_js(self, web_page, new_tab=False):
#         """Set the current page using JavaScript."""
#         self.__web_page__ = web_page
#         if new_tab:
#             script = f'window.open("{web_page}");'
#         else:
#             script = f'window.open("{web_page}").focus();'
#         self.driver.execute_script(script)

#     def set_page(self, web_page, time_out=0, break_time_out=False):
#         """Set the current page."""
#         try:
#             self.__web_page__ = web_page
#             if time_out > 0:
#                 self.driver.set_page_load_timeout(time_out)
#             self.driver.get(self.__web_page__)
#         except Exception as e:
#             if break_time_out:
#                 raise Exception(f"Time out to load page: {web_page}")
#             else:
#                 self.driver.execute_script("window.stop();")

#     def click_js(self, selector: str):
#         """Click on an element using JavaScript."""
#         elem = self.driver.find_element(By.CSS_SELECTOR, selector)
#         self.driver.execute_script("arguments[0].click();", elem)

#     def select_drop_down_index(self, selector, index):
#         """Select an option from a dropdown by index."""
#         select_elem = Select(self.get_elem(selector))
#         select_elem.select_by_index(index)

#     def select_drop_down_text(self, selector, text):
#         """Select an option from a dropdown by visible text."""
#         select_elem = Select(self.get_elem(selector))
#         select_elem.select_by_visible_text(text)

#     def go_bottom(self, selector: str = "body"):
#         """Scroll to the bottom of the page."""
#         elem = self.driver.find_element(By.CSS_SELECTOR, selector)
#         elem.send_keys(Keys.CONTROL + Keys.END)

#     def go_top(self, selector: str = "body"):
#         """Scroll to the top of the page."""
#         elem = self.driver.find_element(By.CSS_SELECTOR, selector)
#         elem.send_keys(Keys.CONTROL + Keys.UP)

#     def go_down(self, selector: str = "body"):
#         """Scroll down the page."""
#         elem = self.driver.find_element(By.CSS_SELECTOR, selector)
#         elem.send_keys(Keys.PAGE_DOWN)

#     def go_up(self, selector: str = "body"):
#         """Scroll up the page."""
#         elem = self.driver.find_element(By.CSS_SELECTOR, selector)
#         elem.send_keys(Keys.PAGE_UP)

#     def switch_to_main_frame(self):
#         """Switch to the main frame."""
#         self.driver.switch_to.default_content()

#     def switch_to_frame(self, frame_selector):
#         """Switch to a specific frame."""
#         frame = self.get_elem(frame_selector)
#         self.driver.switch_to.frame(frame)

#     def open_tab(self):
#         """Open a new tab."""
#         self.driver.execute_script("window.open('');")

#     def close_tab(self):
#         """Close the current tab."""
#         try:
#             self.driver.close()
#         except Exception as e:
#             logger.error(f"Failed to close tab: {e}")

#     def switch_to_tab(self, number):
#         """Switch to a specific tab."""
#         windows = self.driver.window_handles
#         self.driver.switch_to.window(windows[number])

#     def refresh_selenium(self, time_units=1, back_tab=0):
#         """Refresh the browser."""
#         self.open_tab()
#         self.switch_to_tab(len(self.driver.window_handles) - 1)
#         time.sleep(self.basetime * time_units)
#         self.close_tab()
#         self.switch_to_tab(back_tab)
#         time.sleep(self.basetime * time_units)

#     def save_page(self, file_html):
#         """Save the current page as HTML."""
#         page_html = self.driver.page_source
#         current_folder = os.path.dirname(__file__)
#         page_file = open(os.path.join(current_folder, file_html), "w", encoding='utf-8')
#         page_file.write(page_html)
#         page_file.close()

#     def zoom(self, percentage=50):
#         """Zoom the page."""
#         script = f"document.body.style.zoom='{percentage}%'"
#         self.driver.execute_script(script)

#     def kill(self):
#         """Kill all browser instances."""
#         tabs = self.driver.window_handles
#         for _ in tabs:
#             self.switch_to_tab(0)
#             self.end_browser()

#     def scroll(self, selector, scroll_x, scroll_y):
#         """Scroll to a specific position."""
#         elem = self.get_elem(selector)
#         self.driver.execute_script("arguments[0].scrollTo(arguments[1], arguments[2])", elem, scroll_x, scroll_y)

#     def set_local_storage(self, key: str, value: str):
#         """Set a value in the local storage."""
#         script = f"window.localStorage.setItem('{key}', '{value}')"
#         self.driver.execute_script(script)









# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC

# def wait_element(self, selector, timeout=10, by=By.CSS_SELECTOR):
#     """Attendre qu'un élément soit présent et cliquable."""
#     return WebDriverWait(self.driver, timeout).until(
#         EC.element_to_be_clickable((by, selector))
#     )

# def wait_disappear(self, selector, timeout=10, by=By.CSS_SELECTOR):
#     """Attendre que l'élément disparaisse."""
#     return WebDriverWait(self.driver, timeout).until_not(
#         lambda d: d.find_element(by, selector)
#     )


# def navigate_with_retry(self, url, max_retries=3, retry_delay=2):
#     """Naviguer vers une URL avec gestion des erreurs."""
#     for attempt in range(max_retries):
#         try:
#             self.driver.get(url)
#             return True
#         except Exception as e:
#             logger.warning(f"Tentative {attempt + 1}/{max_retries} échouée: {e}")
#             time.sleep(retry_delay)
#     raise Exception(f"Echec après {max_retries} tentatives")

# def refresh_page(self):
#     """Actualiser la page avec gestion des frames."""
#     current_frame = self.driver.current_frame
#     self.driver.refresh()
#     if current_frame:
#         self.driver.switch_to.frame(current_frame)


# def save_cookies(self):
#     """Sauvegarder les cookies dans un fichier."""
#     cookies = self.driver.get_cookies()
#     with open('cookies.json', 'w') as f:
#         json.dump(cookies, f)

# def load_cookies(self):
#     """Charger les cookies depuis un fichier."""
#     try:
#         with open('cookies.json', 'r') as f:
#             cookies = json.load(f)
#             for cookie in cookies:
#                 self.driver.add_cookie(cookie)
#     except FileNotFoundError:
#         logger.warning("Fichier de cookies non trouvé")



# def execute_script_optimized(self, script, *args):
#     """Exécuter un script JavaScript avec timeout personnalisable."""
#     try:
#         return self.driver.execute_async_script(script, *args)
#     except Exception as e:
#         self.logger.error(f"Erreur d'exécution du script: {e}")
#         raise

# def screenshot_with_retry(self, filename, max_retries=3):
#     """Prendre un screenshot avec plusieurs tentatives."""
#     for attempt in range(max_retries):
#         try:
#             self.driver.save_screenshot(filename)
#             return True
#         except Exception as e:
#             self.logger.warning(f"Tentative {attempt + 1}/{max_retries}: {e}")
#             time.sleep(1)
#     raise Exception(f"Echec après {max_retries} tentatives")





# def switch_to_newest_window(self):
#     """Basculer vers la fenêtre la plus récente."""
#     windows = self.driver.window_handles
#     if len(windows) > 1:
#         self.driver.switch_to.window(windows[-1])
#         return True
#     return False

# def close_all_but_main(self):
#     """Fermer toutes les fenêtres sauf la principale."""
#     main_window = self.driver.current_window_handle
#     for window in self.driver.window_handles:
#         if window != main_window:
#             self.driver.switch_to.window(window)
#             self.driver.close()
#     self.driver.switch_to.window(main_window)

# def get_window_handles_info(self):
#     """Obtenir des informations sur toutes les fenêtres ouvertes."""
#     windows = {}
#     current_handle = self.driver.current_window_handle
#     for handle in self.driver.window_handles:
#         self.driver.switch_to.window(handle)
#         windows[handle] = {
#             'title': self.driver.title,
#             'url': self.driver.current_url
#         }
#     self.driver.switch_to.window(current_handle)
#     return windows



# def verify_element_state(self, selector, expected_state, timeout=10):
#     """Vérifier l'état d'un élément (visible, cliquable, etc.)."""
#     element = self.wait_element(selector, timeout)
#     states = {
#         'visible': lambda e: e.is_visible(),
#         'enabled': lambda e: e.is_enabled(),
#         'selected': lambda e: e.is_selected(),
#         'contains_text': lambda e: expected_state in e.text
#     }
#     return states[expected_state](element)

# def validate_form(self, form_selector, expected_fields):
#     """Valider que tous les champs d'un formulaire sont présents."""
#     form = self.wait_element(form_selector)
#     for field_name, field_type in expected_fields.items():
#         selector = f"{form_selector} {field_type}"
#         if not self.wait_element(selector, timeout=5):
#             raise ValueError(f"Champ '{field_name}' manquant")

# def check_page_loaded(self, expected_title=None, expected_url=None):
#     """Vérifier que la page est complètement chargée."""
#     max_attempts = 5
#     for attempt in range(max_attempts):
#         try:
#             if expected_title and expected_title not in self.driver.title:
#                 raise Exception("Titre incorrect")
#             if expected_url and expected_url not in self.driver.current_url:
#                 raise Exception("URL incorrect")
#             return True
#         except:
#             time.sleep(1)
#     raise Exception(f"Page non chargée après {max_attempts} tentatives")




# def save_screenshot_with_context(self, filename, extra_info=None):
#     """Sauvegarder une capture d'écran avec des informations contextuelles."""
#     self.driver.save_screenshot(filename)
#     if extra_info:
#         with open(f"{filename}.log", "w") as f:
#             f.write(f"URL: {self.driver.current_url}\n")
#             f.write(f"Titre: {self.driver.title}\n")
#             f.write(f"Timestamp: {datetime.now()}\n")
#             if isinstance(extra_info, dict):
#                 for key, value in extra_info.items():
#                     f.write(f"{key}: {value}\n")

# def download_file(self, url, download_folder=None):
#     """Télécharger un fichier avec gestion des répertoires."""
#     if download_folder:
#         os.makedirs(download_folder, exist_ok=True)
#         self.driver.command_executor._commands["send_command"] = (
#             "POST", '/session/$sessionId/chromium/send_command'
#         )
#         params = {
#             'cmd': 'Page.setDownloadBehavior',
#             'params': {
#                 'behavior': 'allow',
#                 'downloadPath': download_folder
#             }
#         }
#         self.driver.execute_command(params)
    
#     try:
#         self.navigate_with_retry(url)
#         filename = os.path.basename(url)
#         if download_folder:
#             return os.path.join(download_folder, filename)
#         return filename
#     except Exception as e:
#         self.logger.error(f"Erreur de téléchargement: {e}")
#         raise





# def execute_javascript_dialog(self, dialog_type, text=None):
#     """Gérer les dialogues JavaScript (alert, confirm, prompt)."""
#     self.driver.switch_to.alert
#     if dialog_type == "prompt" and text:
#         self.driver.switch_to.alert.send_keys(text)
#     self.driver.switch_to.alert.accept()

# def scroll_to_element_with_offset(self, selector, offset_x=0, offset_y=0):
#     """Faire défiler jusqu'à un élément avec décalage."""
#     element = self.wait_element(selector)
#     self.driver.execute_script(
#         f"arguments[0].scrollIntoView();"
#         f"window.scrollBy({offset_x}, {offset_y});",
#         element
#     )

# def get_element_dimensions(self, selector):
#     """Obtenir les dimensions et la position d'un élément."""
#     element = self.wait_element(selector)
#     return element.size, element.location




# def retry_on_failure(self, func, max_attempts=3, delay=1):
#     """Décorateur pour les réessais automatiques."""
#     def wrapper(*args, **kwargs):
#         for attempt in range(max_attempts):
#             try:
#                 return func(*args, **kwargs)
#             except Exception as e:
#                 if attempt == max_attempts - 1:
#                     raise
#                 self.logger.warning(
#                     f"Tentative {attempt + 1} échouée: {e}. "
#                     f"Réessai dans {delay} secondes..."
#                 )
#                 time.sleep(delay)
#     return wrapper

# def safe_execute(self, func):
#     """Exécuter une fonction de manière sécurisée."""
#     try:
#         return func()
#     except Exception as e:
#         self.logger.error(f"Erreur d'exécution: {e}")
#         self.screenshot_with_context("error_screenshot.png", {"error": str(e)})
#         raise





# def setup_proxy_rotation(self, proxy_list, rotation_interval=300):
#     """Configurer une rotation automatique des proxy."""
#     self.proxy_list = proxy_list
#     self.current_proxy_index = 0
#     self.proxy_rotation_interval = rotation_interval
#     self.last_proxy_rotation = time.time()
    
#     def rotate_proxy():
#         current_time = time.time()
#         if current_time - self.last_proxy_rotation >= self.proxy_rotation_interval:
#             self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
#             self.update_proxy(self.proxy_list[self.current_proxy_index])
#             self.last_proxy_rotation = current_time
    
#     self.proxy_rotation_thread = threading.Thread(target=self._proxy_rotation_monitor, args=(rotate_proxy,))
#     self.proxy_rotation_thread.daemon = True
#     self.proxy_rotation_thread.start()

# def update_proxy(self, proxy_config):
#     """Mettre à jour la configuration proxy en cours."""
#     proxy = f"{proxy_config['host']}:{proxy_config['port']}"
#     self.driver.quit()
#     options = webdriver.ChromeOptions()
#     options.add_argument(f"--proxy-server={proxy}")
#     if proxy_config.get('username') and proxy_config.get('password'):
#         self._create_proxy_auth_extension(proxy_config)
#         options.add_extension(self.proxy_auth_plugin)
#     self.driver = webdriver.Chrome(options=options)

# def _proxy_rotation_monitor(self, rotation_func):
#     """Surveiller et gérer la rotation des proxy."""
#     while True:
#         rotation_func()
#         time.sleep(60)  # Vérification toutes les minutes





# def handle_ssl_certificates(self, ignore=False):
#     """Gérer les certificats SSL avec options configurables."""
#     options = webdriver.ChromeOptions()
#     if ignore:
#         options.add_argument('--ignore-certificate-errors')
#         options.add_argument('--ignore-ssl-errors')
#     options.add_experimental_option('excludeSwitches', ['ignore-certificate-errors'])
#     self.driver.quit()
#     self.driver = webdriver.Chrome(options=options)

# def install_certificate(self, cert_path):
#     """Installer un certificat SSL personnalisé."""
#     options = webdriver.ChromeOptions()
#     options.add_argument(f"--ssl-key={cert_path}")
#     self.driver.quit()
#     self.driver = webdriver.Chrome(options=options)





# def monitor_performance(self, interval=60):
#     """Surveiller les performances du navigateur."""
#     def monitor():
#         while True:
#             performance_data = self.get_performance_metrics()
#             self.logger.info(f"Performances: {performance_data}")
#             time.sleep(interval)
    
#     self.performance_thread = threading.Thread(target=monitor)
#     self.performance_thread.daemon = True
#     self.performance_thread.start()

# def get_performance_metrics(self):
#     """Obtenir les métriques de performance du navigateur."""
#     performance_data = self.driver.execute_script("""
#         return {
#             memory: performance.memory,
#             navigation: performance.navigation,
#             timing: performance.timing,
#             cpu: navigator.hardwareConcurrency,
#             jsHeap: window.performance.memory?.usedJSHeapSize,
#             totalHeap: window.performance.memory?.totalJSHeapSize
#         };
#     """)
#     return performance_data




# def manage_storage(self, storage_type='local', data=None):
#     """Gérer le stockage local/session avec des options avancées."""
#     if data:
#         if storage_type == 'local':
#             self.driver.execute_script(f"localStorage.setItem(arguments[0], arguments[1]);", 
#                                     json.dumps(data), json.dumps(data))
#         else:
#             self.driver.execute_script(f"sessionStorage.setItem(arguments[0], arguments[1]);", 
#                                     json.dumps(data), json.dumps(data))
#     else:
#         if storage_type == 'local':
#             return json.loads(self.driver.execute_script("localStorage.getItem(arguments[0]);"))
#         else:
#             return json.loads(self.driver.execute_script("sessionStorage.getItem(arguments[0]);"))

# def clear_browser_data(self, types=None):
#     """Nettoyer les données du navigateur de manière sélective."""
#     if types is None:
#         types = ['cookies', 'cache', 'localStorage', 'sessionStorage']
    
#     for type_ in types:
#         self.driver.execute_script(f"""
#             if (typeof {type_} !== 'undefined') {{
#                 {type_}.clear();
#             }}
#         """)

# def execute_custom_script(self, script_name, *args):
#     """Exécuter des scripts personnalisés avec gestion d'erreurs."""
#     script_path = os.path.join(self.script_directory, f"{script_name}.js")
#     with open(script_path, 'r') as f:
#         script_content = f.read()
    
#     try:
#         return self.driver.execute_script(script_content, *args)
#     except Exception as e:
#         self.logger.error(f"Erreur d'exécution du script {script_name}: {e}")
#         raise

# def screenshot_with_elements(self, filename, elements=None):
#     """Prendre une capture d'écran avec mise en évidence des éléments."""
#     self.driver.save_screenshot(filename)
#     if elements:
#         for element in elements:
#             element.screenshot(f"{filename}_highlight_{elements.index(element)}.png")



# # Configuration initiale
# scrapper = WebScraping(
#     proxy_rotation=True,
#     performance_monitoring=True,
#     ssl_ignore=True
# )

# # Rotation des proxy
# proxy_list = [
#     {'host': 'proxy1:8080', 'username': 'user1', 'password': 'pass1'},
#     {'host': 'proxy2:8080', 'username': 'user2', 'password': 'pass2'}
# ]
# scrapper.setup_proxy_rotation(proxy_list, rotation_interval=300)

# # Gestion du stockage
# scrapper.manage_storage('local', {'user_id': '123', 'session': 'abc'})
# data = scrapper.manage_storage('local')

# # Exécution de scripts personnalisés
# result = scrapper.execute_custom_script('custom_script', arg1, arg2)
=======
            logger.error(f"Failed to close tab: {e}")
            raise

    def switch_to_tab(self, number):
        """Switch to a specific tab."""
        try:
            windows = self.driver.window_handles
            self.driver.switch_to.window(windows[number])
            logger.info(f"Switched to tab number {number}.")
        except Exception as e:
            logger.error(f"Failed to switch to tab number {number}: {e}")
            raise

    def refresh_selenium(self, time_units=1, back_tab=0):
        """Refresh the browser."""
        try:
            self.open_tab()
            self.switch_to_tab(len(self.driver.window_handles) - 1)
            time.sleep(self.basetime * time_units)
            self.close_tab()
            self.switch_to_tab(back_tab)
            time.sleep(self.basetime * time_units)
            logger.info("Browser refreshed.")
        except Exception as e:
            logger.error(f"Failed to refresh browser: {e}")
            raise

    def save_page(self, file_html):
        """Save the current page as HTML."""
        try:
            page_html = self.driver.page_source
            current_folder = os.path.dirname(__file__)
            with open(os.path.join(current_folder, file_html), "w", encoding='utf-8') as page_file:
                page_file.write(page_html)
            logger.info(f"Page saved as {file_html}.")
        except Exception as e:
            logger.error(f"Failed to save page as {file_html}: {e}")
            raise

    def zoom(self, percentage=50):
        """Zoom the page."""
        try:
            script = f"document.body.style.zoom='{percentage}%'"
            self.driver.execute_script(script)
            logger.info(f"Page zoomed to {percentage}%.")
        except Exception as e:
            logger.error(f"Failed to zoom page: {e}")
            raise

    def kill(self):
        """Kill all browser instances."""
        try:
            tabs = self.driver.window_handles
            for _ in tabs:
                self.switch_to_tab(0)
                self.end_browser()
            logger.info("All browser instances killed.")
        except Exception as e:
            logger.error(f"Failed to kill all browser instances: {e}")
            raise

    def scroll(self, selector, scroll_x, scroll_y):
        """Scroll to a specific position."""
        try:
            elem = self.get_elem(selector)
            self.driver.execute_script("arguments[0].scrollTo(arguments[1], arguments[2])", elem, scroll_x, scroll_y)
            logger.info(f"Scrolled to position ({scroll_x}, {scroll_y}) in element with selector {selector}.")
        except Exception as e:
            logger.error(f"Failed to scroll in element with selector {selector}: {e}")
            raise

    def set_local_storage(self, key: str, value: str):
        """Set a value in the local storage."""
        try:
            script = f"window.localStorage.setItem('{key}', '{value}')"
            self.driver.execute_script(script)
            logger.info(f"Set localStorage key '{key}' to '{value}'.")
        except Exception as e:
            logger.error(f"Failed to set localStorage key '{key}' to '{value}': {e}")
            raise

    def get_alert_text(self):
        """Get the text from an alert box."""
        try:
            WebDriverWait(self.driver, 10).until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            logger.info("Alert text retrieved and accepted.")
            return alert_text
        except TimeoutException:
            logger.warning("No alert present.")
            return None
        except Exception as e:
            logger.error(f"Failed to get alert text: {e}")
            raise

    def dismiss_alert(self):
        """Dismiss an alert box."""
        try:
            WebDriverWait(self.driver, 10).until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            alert.dismiss()
            logger.info("Alert dismissed.")
        except TimeoutException:
            logger.warning("No alert present to dismiss.")
        except Exception as e:
            logger.error(f"Failed to dismiss alert: {e}")
            raise

    def accept_alert(self):
        """Accept an alert box."""
        try:
            WebDriverWait(self.driver, 10).until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            alert.accept()
            logger.info("Alert accepted.")
        except TimeoutException:
            logger.warning("No alert present to accept.")
        except Exception as e:
            logger.error(f"Failed to accept alert: {e}")
            raise

    def capture_network_traffic(self):
        """Capture network traffic."""
        try:
            logs = self.driver.get_log("performance")
            logger.info("Network traffic captured.")
            return logs
        except Exception as e:
            logger.error(f"Failed to capture network traffic: {e}")
            raise

    def clear_cache(self):
        """Clear browser cache."""
        try:
            self.driver.execute_script("window.localStorage.clear();")
            self.driver.execute_script("window.sessionStorage.clear();")
            self.driver.execute_cdp_cmd('Network.clearBrowserCache', {})
            logger.info("Browser cache cleared.")
        except Exception as e:
            logger.error(f"Failed to clear browser cache: {e}")
            raise

    def bypass_cloudflare(self, url):
        """Bypass Cloudflare protection."""
        try:
            self.set_page(url)
            time.sleep(10)  # Wait for Cloudflare challenge to complete
            self.driver.execute_script("window.stop();")
            logger.info("Bypassed Cloudflare protection.")
        except Exception as e:
            logger.error(f"Failed to bypass Cloudflare protection for URL {url}: {e}")
            raise

    def wait_for_element(self, selector, time_out=10):
        """Wait for an element to be present."""
        try:
            WebDriverWait(self.driver, time_out).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            logger.info(f"Element with selector {selector} is present.")
        except TimeoutException:
            logger.error(f"Element with selector {selector} not found within {time_out} seconds")
            raise

    def wait_for_element_to_be_clickable(self, selector, time_out=10):
        """Wait for an element to be clickable."""
        try:
            WebDriverWait(self.driver, time_out).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            logger.info(f"Element with selector {selector} is clickable.")
        except TimeoutException:
            logger.error(f"Element with selector {selector} not clickable within {time_out} seconds")
            raise

    def wait_for_element_to_disappear(self, selector, time_out=10):
        """Wait for an element to disappear."""
        try:
            WebDriverWait(self.driver, time_out).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, selector)))
            logger.info(f"Element with selector {selector} has disappeared.")
        except TimeoutException:
            logger.error(f"Element with selector {selector} did not disappear within {time_out} seconds")
            raise
    
    def wait_for_text_to_be_present(self, selector, text, time_out=10):
        """Wait for specific text to be present in an element."""
        try:
            WebDriverWait(self.driver, time_out).until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, selector), text))
            logger.info(f"Text '{text}' is present in element with selector {selector}.")
        except TimeoutException:
            logger.error(f"Text '{text}' not present in element with selector {selector} within {time_out} seconds")
            raise
    
    def wait_for_title(self, title, time_out=10):
        """Wait for the page title to be a specific value."""
        try:
            WebDriverWait(self.driver, time_out).until(EC.title_is(title))
            logger.info(f"Page title is '{title}'.")
        except TimeoutException:
            logger.error(f"Title '{title}' not present within {time_out} seconds")
            raise

    def wait_for_title_contains(self, title, time_out=10):
        """Wait for the page title to contain a specific value."""
        try:
            WebDriverWait(self.driver, time_out).until(EC.title_contains(title))
            logger.info(f"Page title contains '{title}'.")
        except TimeoutException:
            logger.error(f"Title containing '{title}' not present within {time_out} seconds")
            raise

    def refresh_page(self):
        """Refresh the current page."""
        try:
            self.driver.refresh()
            logger.info("Page refreshed.")
        except Exception as e:
            logger.error(f"Failed to refresh page: {e}")
            raise

    def execute_script(self, script, *args):
        """Execute a JavaScript script."""
        try:
            result = self.driver.execute_script(script, *args)
            logger.info("Script executed successfully.")
            return result
        except Exception as e:
            logger.error(f"Failed to execute script: {e}")
            raise

    def close_browser(self):
        """Close the browser."""
        try:
            self.driver.quit()
            logger.info("Browser closed.")
        except Exception as e:
            logger.error(f"Failed to close browser: {e}")
            raise

    def restart_browser(self, time_out=0):
        """Restart the browser."""
        try:
            self.close_browser()
            self.__set_browser_instance__()
            if time_out > 0:
                self.driver.set_page_load_timeout(time_out)
            logger.info("Browser restarted.")
        except Exception as e:
            logger.error(f"Failed to restart browser: {e}")
            raise

    def get_user_agent(self):
        """Get the user agent of the browser."""
        try:
            user_agent = self.driver.execute_script("return navigator.userAgent;")
            logger.info(f"User agent retrieved: {user_agent}")
            return user_agent
        except Exception as e:
            logger.error(f"Failed to get user agent: {e}")
            raise
>>>>>>> c9ba7d302208764d82a1218f7368eb37bb590766
