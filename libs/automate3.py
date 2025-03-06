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
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="web_scraping.log"
)
logger = logging.getLogger(__name__)

class WebScraping:
    service = None
    options = None

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

        if start_killing:
            logger.info("Trying to kill chrome...")
            command = 'taskkill /IM "chrome.exe" /F'
            os.system(command)
            logger.info("Chrome killed successfully.")

        if self.__start_openning__:
            self.__set_browser_instance__()

        if time_out > 0:
            self.driver.set_page_load_timeout(time_out)

    def __set_browser_instance__(self):
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

    def __create_proxy_extesion__(self):
        """Create a proxy extension for authenticated proxies."""
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
        """ % (self.__proxy_server__, self.__proxy_port__, self.__proxy_user__, self.__proxy_pass__)

        with zipfile.ZipFile(self.__pluginfile__, 'w') as zp:
            zp.writestr("manifest.json", manifest_json)
            zp.writestr("background.js", background_js)

    def set_cookies(self, cookies: list):
        """Set cookies in the browser."""
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
    # def send_data(self, selector, data):
    #     """
    #     Envoie des données (texte) dans un champ de saisie.
    #     Attend que l'élément soit présent et interactif avant d'envoyer les données.
    #     Gère les erreurs et les logs pour chaque étape.
    #     """
    #     try:
    #         # Attend que l'élément soit présent et interactif
    #         elem = WebDriverWait(self.driver, 10).until(
    #             EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
    #         )
    #         elem.clear()  # Nettoie le champ avant d'envoyer les données (optionnel)
    #         elem.send_keys(data)  # Envoie les données
    #         logger.info(f"Données envoyées avec succès à l'élément avec le sélecteur : {selector}")
    #         return True
    #     except TimeoutException:
    #         logger.error(f"L'élément avec le sélecteur {selector} n'est pas devenu interactif après 10 secondes.")
    #         return False
    #     except Exception as e:
    #         logger.error(f"Échec de l'envoi des données à l'élément avec le sélecteur {selector} : {e}")
    #         return False

    # def click(self, selector):
    #     """Click on an element."""
    #     try:
    #         element = WebDriverWait(self.driver, 10).until(
    #             EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
    #         )
    #         element.click()
    #         logger.info(f"Clicked on element with selector: {selector}")
    #     except Exception as e:
    #         logger.error(f"Failed to click on element with selector {selector}: {e}")
    #         raise

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
        try:
            elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return elem.text
        except NoSuchElementException:
            logger.error(f"Element with selector {selector} not found.")
            return None
        except TimeoutException:
            logger.error(f"Timeout while waiting for element with selector {selector}.")
            return None

    def get_texts(self, selector):
        """Get the texts of multiple elements."""
        texts = []
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
        try:
            elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return elem.get_attribute(attrib_name)
        except Exception as e:
            logger.error(f"Failed to get attribute {attrib_name} from element with selector {selector}: {e}")
            return None

    def get_attribs(self, selector, attrib_name, allow_duplicates=True, allow_empty=True):
        """Get attributes of multiple elements."""
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
                logger.warning(f"Page load stopped due to timeout: {web_page}")
        except Exception as e:
            logger.error(f"Failed to set page to {web_page}: {e}")
            raise



    # def click_js(self, selector: str, timeout: int = 10):
    #     """
    #     Click on an element using JavaScript.
        
    #     Args:
    #         selector (str): The CSS selector of the element to click.
    #         timeout (int): Maximum time to wait for the element to be clickable (default: 10 seconds).
        
    #     Raises:
    #         NoSuchElementException: If the element is not found.
    #         ElementNotInteractableException: If the element is not interactable.
    #         TimeoutException: If the element does not become clickable within the timeout.
    #         Exception: For any other unexpected error.
    #     """
    #     try:
    #         # Wait until the element is present and clickable
    #         element = WebDriverWait(self.driver, timeout).until(
    #             EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
    #         )
    #         # Use JavaScript to click the element
    #         self.driver.execute_script("arguments[0].click();", element)
    #         logger.info(f"Successfully clicked on element with selector: {selector}")
    #     except NoSuchElementException:
    #         logger.error(f"Element not found with selector: {selector}")
    #         raise NoSuchElementException(f"Element with selector '{selector}' not found.")
    #     except ElementNotInteractableException:
    #         logger.error(f"Element with selector {selector} is not interactable.")
    #         raise ElementNotInteractableException(f"Element with selector '{selector}' is not interactable.")
    #     except TimeoutException:
    #         logger.error(f"Timeout: Element with selector {selector} did not become clickable within {timeout} seconds.")
    #         raise TimeoutException(f"Timeout: Element with selector '{selector}' did not become clickable.")
    #     except Exception as e:
    #         logger.error(f"Unexpected error while clicking on element with selector {selector}: {e}")
    #         raise Exception(f"Unexpected error: {e}")


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
        try:
            self.driver.close()
            logger.info("Current tab closed.")
        except Exception as e:
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








    def click(self, selector: str, timeout: int = 10):
        """
        Click on an element using Selenium's native click or JavaScript as a fallback.
        
        Args:
            selector (str): The CSS selector of the element to click.
            timeout (int): Maximum time to wait for the element to be clickable (default: 10 seconds).
        
        Returns:
            bool: True if the click was successful, False otherwise.
        
        Raises:
            Exception: If both native and JavaScript clicks fail.
        """
        try:
            # Wait until the element is present and clickable
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            # Try to click using Selenium's native click
            element.click()
            logger.info(f"Successfully clicked on element with selector: {selector} using native click.")
            return True
        except (TimeoutException, ElementNotInteractableException) as e:
            logger.warning(f"Native click failed for selector {selector}. Trying JavaScript click...")
            try:
                # Fallback to JavaScript click
                self.driver.execute_script("arguments[0].click();", element)
                logger.info(f"Successfully clicked on element with selector: {selector} using JavaScript.")
                return True
            except Exception as js_error:
                logger.error(f"JavaScript click failed for selector {selector}: {js_error}")
                raise Exception(f"Failed to click on element with selector {selector}: {js_error}")
        except NoSuchElementException as e:
            logger.error(f"Element not found with selector: {selector}")
            raise NoSuchElementException(f"Element with selector '{selector}' not found.")
        except Exception as e:
            logger.error(f"Unexpected error while clicking on element with selector {selector}: {e}")
            raise Exception(f"Unexpected error: {e}")

    def click_js(self, selector: str, timeout: int = 10):
        """
        Click on an element using JavaScript.
        
        Args:
            selector (str): The CSS selector of the element to click.
            timeout (int): Maximum time to wait for the element to be clickable (default: 10 seconds).
        
        Raises:
            NoSuchElementException: If the element is not found.
            ElementNotInteractableException: If the element is not interactable.
            TimeoutException: If the element does not become clickable within the timeout.
            Exception: For any other unexpected error.
        """
        try:
            # Wait until the element is present and clickable
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            # Use JavaScript to click the element
            self.driver.execute_script("arguments[0].click();", element)
            logger.info(f"Successfully clicked on element with selector: {selector}")
        except NoSuchElementException:
            logger.error(f"Element not found with selector: {selector}")
            raise NoSuchElementException(f"Element with selector '{selector}' not found.")
        except ElementNotInteractableException:
            logger.error(f"Element with selector {selector} is not interactable.")
            raise ElementNotInteractableException(f"Element with selector '{selector}' is not interactable.")
        except TimeoutException:
            logger.error(f"Timeout: Element with selector {selector} did not become clickable within {timeout} seconds.")
            raise TimeoutException(f"Timeout: Element with selector '{selector}' did not become clickable.")
        except Exception as e:
            logger.error(f"Unexpected error while clicking on element with selector {selector}: {e}")
            raise Exception(f"Unexpected error: {e}")

    def send_data(self, selector: str, data: str, timeout: int = 10):
        """
        Send data (text) to an input field.
        
        Args:
            selector (str): The CSS selector of the input field.
            data (str): The text to send to the input field.
            timeout (int): Maximum time to wait for the element to be interactable (default: 10 seconds).
        
        Returns:
            bool: True if the data was sent successfully, False otherwise.
        
        Raises:
            Exception: If the input field is not found or not interactable.
        """
        try:
            # Wait until the element is present and interactable
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            element.clear()  # Clear the input field (optional)
            element.send_keys(data)  # Send the data
            logger.info(f"Data sent successfully to element with selector: {selector}")
            return True
        except TimeoutException:
            logger.error(f"Element with selector {selector} did not become interactable within {timeout} seconds.")
            raise TimeoutException(f"Timeout: Element with selector '{selector}' did not become interactable.")
        except NoSuchElementException:
            logger.error(f"Element not found with selector: {selector}")
            raise NoSuchElementException(f"Element with selector '{selector}' not found.")
        except Exception as e:
            logger.error(f"Failed to send data to element with selector {selector}: {e}")
            raise Exception(f"Failed to send data: {e}")

# Exemple d'utilisation
# driver = webdriver.Chrome()
# poster = FacebookPoster(driver)
# poster.click('button.submit')
# poster.click_js('button.submit')
# poster.send_data('input.text-field', 'Hello, World!')