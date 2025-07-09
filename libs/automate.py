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
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s", # Consider updating format to include logger name for consistency
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
            proxy_pass (str, optional): Proxy password to use in the window. Defaults to "". # Note: Consider security if logging this.
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
        logger.info(f"[WebScraping.__init__] Initializing WebScraping instance with headless={headless}, chrome_folder='{chrome_folder}', user_agent_enabled={user_agent}, proxy_enabled={bool(proxy_server)}")
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
            logger.info("[WebScraping.__init__] Attempting to kill existing chrome processes.")
            command = 'taskkill /IM "chrome.exe" /F' # Consider platform compatibility for this command
            os.system(command)
            logger.info("[WebScraping.__init__] Chrome process kill command executed.") # Note: os.system doesn't guarantee success

        if self.__start_openning__:
            logger.info("[WebScraping.__init__] Proceeding to set up browser instance.")
            self.__set_browser_instance__()
        else:
            logger.info("[WebScraping.__init__] Browser instance will not be started (start_openning=False).")

        if time_out > 0 and hasattr(self, 'driver'):
            logger.info(f"[WebScraping.__init__] Setting page load timeout to {time_out} seconds.")
            self.driver.set_page_load_timeout(time_out)

        logger.info(f"[WebScraping.__init__] WebScraping instance initialization complete.")

    def __set_browser_instance__(self):
        """Configure and start the browser instance."""
        logger.info("[WebScraping.__set_browser_instance__] Starting browser instance setup.")
        try:
            os.environ['WDM_LOG_LEVEL'] = '0' # Suppresses WDM logs
            os.environ['WDM_PRINT_FIRST_LINE'] = 'False' # Suppresses WDM logs
            logger.info("[WebScraping.__set_browser_instance__] Configuring Chrome options.")

            if not WebScraping.options:
                WebScraping.options = webdriver.ChromeOptions()
                logger.info("[WebScraping.__set_browser_instance__] Created new ChromeOptions object.")
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
            logger.info("[WebScraping.__set_browser_instance__] Chrome options configured.")

            if self.__proxy_server__ and self.__proxy_port__ and not self.__proxy_user__ and not self.__proxy_pass__:
                proxy = f"{self.__proxy_server__}:{self.__proxy_port__}"
                WebScraping.options.add_argument(f"--proxy-server={proxy}")
                logger.info(f"[WebScraping.__set_browser_instance__] Set unauthenticated proxy: {proxy}")

            if self.__proxy_server__ and self.__proxy_port__ and self.__proxy_user__ and self.__proxy_pass__:
                logger.info("[WebScraping.__set_browser_instance__] Creating authenticated proxy extension.")
                self.__create_proxy_extesion__()
                WebScraping.options.add_extension(self.__pluginfile__)
                logger.info("[WebScraping.__set_browser_instance__] Added authenticated proxy extension.")

            # Use ChromeDriverManager to automatically manage ChromeDriver
            logger.info("[WebScraping.__set_browser_instance__] Initializing WebDriver Service.")
            try:
                if not WebScraping.service:
                    # Ensure WDM logs are suppressed if not already set by environment variables
                    # by configuring the logger for 'webdriver_manager'
                    wdm_logger = logging.getLogger('webdriver_manager')
                    wdm_logger.setLevel(logging.ERROR) # Only show errors from WDM
                    WebScraping.service = Service(ChromeDriverManager().install())
                    logger.info("[WebScraping.__set_browser_instance__] ChromeDriver service initialized via ChromeDriverManager.")
            except Exception as e:
                logger.error(f"[WebScraping.__set_browser_instance__] Failed to download/install ChromeDriver using ChromeDriverManager: {e}")
                logger.info("[WebScraping.__set_browser_instance__] Falling back to default Service initialization.")
                # Fallback to default service if ChromeDriverManager fails (e.g. no internet)
                if not WebScraping.service: # Ensure service is initialized if previous attempt failed
                    WebScraping.service = Service()
                    logger.info("[WebScraping.__set_browser_instance__] ChromeDriver service initialized with default Service().")

            logger.info("[WebScraping.__set_browser_instance__] Creating Chrome WebDriver instance.")
            self.driver = webdriver.Chrome(service=WebScraping.service, options=WebScraping.options)
            logger.info("[WebScraping.__set_browser_instance__] Browser instance created successfully.")
        except Exception as e:
            logger.error(f"[WebScraping.__set_browser_instance__] Failed to create browser instance: {e}")
            raise

    def __create_proxy_extesion__(self):
        """Create a proxy extension for authenticated proxies."""
        logger.info(f"[WebScraping.__create_proxy_extesion__] Generating proxy extension for {self.__proxy_server__}:{self.__proxy_port__}")
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
        logger.info(f"[WebScraping.__create_proxy_extesion__] Proxy extension file created: {self.__pluginfile__}")

    def set_cookies(self, cookies: list):
        """Set cookies in the browser."""
        logger.info(f"[WebScraping.set_cookies] Attempting to set {len(cookies)} cookie(s).")
        cookies_formatted = []
        for cookie_orig in cookies:
            cookie = cookie_orig.copy() # Avoid modifying original cookie dict
            if "expirationDate" in cookie:
                cookie["expiry"] = int(cookie["expirationDate"])
                del cookie["expirationDate"]
            cookies_formatted.append(cookie)

        for i, cookie_to_set in enumerate(cookies_formatted):
            try:
                self.driver.add_cookie(cookie_to_set)
                # Avoid logging full cookie value for security if sensitive
                logger.debug(f"[WebScraping.set_cookies] Cookie #{i+1} (name: {cookie_to_set.get('name')}) added.")
            except Exception as e:
                logger.error(f"[WebScraping.set_cookies] Failed to add cookie #{i+1} (name: {cookie_to_set.get('name')}): {e}")
        logger.info(f"[WebScraping.set_cookies] Finished setting cookies.")

    def clear_cookies(self, name=None):
        """Clear specific or all cookies."""
        if name:
            logger.info(f"[WebScraping.clear_cookies] Attempting to delete cookie: {name}.")
        else:
            logger.info("[WebScraping.clear_cookies] Attempting to delete all cookies.")
        try:
            if name:
                self.driver.delete_cookie(name)
                logger.info(f"[WebScraping.clear_cookies] Cookie '{name}' deleted.")
            else:
                self.driver.delete_all_cookies()
                logger.info("[WebScraping.clear_cookies] All cookies deleted.")
        except Exception as e:
            logger.error(f"[WebScraping.clear_cookies] Failed to clear cookies (name: {name}): {e}")

    def screenshot(self, base_name):
        """Take a screenshot of the current page."""
        logger.info(f"[WebScraping.screenshot] Attempting to take screenshot: {base_name}")
        try:
            if str(base_name).endswith(".png"):
                file_name = base_name
            else:
                file_name = f"{base_name}.png"
            self.driver.save_screenshot(file_name)
            logger.info(f"[WebScraping.screenshot] Screenshot saved as '{file_name}'.")
        except Exception as e:
            logger.error(f"[WebScraping.screenshot] Failed to take screenshot '{base_name}': {e}")

    def full_screenshot(self, path: str):
        """Take a full screenshot of the current page."""
        logger.info(f"[WebScraping.full_screenshot] Attempting to take full page screenshot: {path}")
        try:
            original_size = self.driver.get_window_size()
            logger.debug(f"[WebScraping.full_screenshot] Original window size: {original_size}")
            required_width = self.driver.execute_script('return document.body.parentNode.scrollWidth')
            required_height = self.driver.execute_script('return document.body.parentNode.scrollHeight')
            self.driver.set_window_size(required_width, required_height)
            logger.debug(f"[WebScraping.full_screenshot] Resized window to {required_width}x{required_height} for screenshot.")
            self.screenshot(path)  # avoids scrollbar
            self.driver.set_window_size(original_size['width'], original_size['height'])
            logger.debug(f"[WebScraping.full_screenshot] Restored window size to {original_size}.")
            logger.info(f"[WebScraping.full_screenshot] Full screenshot saved as {path}.") # This is already logged by self.screenshot, consider removing duplicate
        except Exception as e:
            logger.error(f"[WebScraping.full_screenshot] Failed to take full screenshot '{path}': {e}")

    def get_browser(self):
        """Get the current browser instance."""
        logger.debug("[WebScraping.get_browser] Returning browser driver instance.")
        return self.driver

    def end_browser(self):
        """Close the browser instance."""
        logger.info("[WebScraping.end_browser] Attempting to close browser instance.")
        try:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
                logger.info("[WebScraping.end_browser] Browser instance closed successfully.")
            else:
                logger.info("[WebScraping.end_browser] No active driver instance to close.")
        except Exception as e:
            logger.error(f"[WebScraping.end_browser] Failed to close browser instance: {e}")

from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, StaleElementReferenceException

# ... (le reste des imports et le début de la classe) ...

    def send_data(self, selector, data):
        """Send data to an input field with StaleElementReferenceException handling."""
        logger.info(f"[WebScraping.send_data] Attempting to send data to element with selector: {selector}")
        for attempt in range(2): # Try twice
            try:
                elem = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                elem.clear() # Clear before sending keys, good practice
                elem.send_keys(data)
                logger.info(f"[WebScraping.send_data] Data successfully sent to element: {selector} on attempt {attempt + 1}")
                return
            except StaleElementReferenceException as e_stale:
                logger.warning(f"[WebScraping.send_data] StaleElementReferenceException on attempt {attempt + 1} for selector '{selector}': {e_stale}. Retrying...")
                if attempt == 1: # Last attempt
                    logger.error(f"[WebScraping.send_data] StaleElementReferenceException persisted after retries for selector '{selector}'.")
                    raise
                time.sleep(0.5) # Wait a bit before retrying
            except Exception as e:
                logger.error(f"[WebScraping.send_data] Failed to send data to element '{selector}' on attempt {attempt + 1}: {e}")
                raise
        # Should not be reached if successful or exception is raised
        logger.error(f"[WebScraping.send_data] send_data failed for '{selector}' after all attempts.")
        raise Exception(f"send_data failed for '{selector}' after all attempts.")


    def click(self, selector):
        """Click on an element with StaleElementReferenceException handling."""
        logger.info(f"[WebScraping.click] Attempting to click element with selector: {selector}")
        for attempt in range(2): # Try twice
            try:
                element = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                element.click()
                logger.info(f"[WebScraping.click] Successfully clicked element: {selector} on attempt {attempt + 1}")
                return
            except StaleElementReferenceException as e_stale:
                logger.warning(f"[WebScraping.click] StaleElementReferenceException on attempt {attempt + 1} for selector '{selector}': {e_stale}. Retrying...")
                if attempt == 1: # Last attempt
                    logger.error(f"[WebScraping.click] StaleElementReferenceException persisted after retries for selector '{selector}'.")
                    raise
                time.sleep(0.5) # Wait a bit before retrying
            except Exception as e:
                logger.error(f"[WebScraping.click] Failed to click element '{selector}' on attempt {attempt + 1}: {e}")
                raise
        # Should not be reached
        logger.error(f"[WebScraping.click] click failed for '{selector}' after all attempts.")
        raise Exception(f"click failed for '{selector}' after all attempts.")


    def wait_load(self, selector, time_out=10, refresh_back_tab=-1):
        """Wait for an element to load."""
        logger.info(f"[WebScraping.wait_load] Waiting for element '{selector}' to load (timeout: {time_out}s).")
        try:
            total_time = 0
            while total_time < time_out:
                total_time += 1
                try:
                    WebDriverWait(self.driver, 1).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"[WebScraping.wait_load] Element '{selector}' loaded successfully.")
                    return True # Indicate success
                except:
                    if refresh_back_tab != -1:
                        logger.debug(f"[WebScraping.wait_load] Element '{selector}' not found, refreshing tab {refresh_back_tab}.")
                        self.refresh_selenium(back_tab=refresh_back_tab)
                    else:
                        time.sleep(self.basetime)
            else: # Loop completed without break means timeout
                logger.error(f"[WebScraping.wait_load] Timeout exceeded. Element '{selector}' not found after {time_out}s.")
                raise TimeoutException(f"Time out exceeded. The element {selector} is not in the page.")
        except TimeoutException as e: # Catching the re-raised or a new TimeoutException
            # Already logged, re-raise to signal failure
            raise
        except Exception as e:
            logger.error(f"[WebScraping.wait_load] Error waiting for element '{selector}': {e}")
            raise
        return False # Should not be reached if exception is raised

    def wait_die(self, selector, time_out=10):
        """Wait for an element to disappear."""
        logger.info(f"[WebScraping.wait_die] Waiting for element '{selector}' to disappear (timeout: {time_out}s).")
        try:
            WebDriverWait(self.driver, time_out).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, selector))
            )
            logger.info(f"[WebScraping.wait_die] Element '{selector}' has disappeared.")
        except TimeoutException as e:
            logger.error(f"[WebScraping.wait_die] Timeout waiting for element '{selector}' to disappear: {e}")
            raise
        except Exception as e:
            logger.error(f"[WebScraping.wait_die] Error waiting for element '{selector}' to disappear: {e}")
            raise

    def get_text(self, selector):
        """Get the text of an element."""
        logger.info(f"[WebScraping.get_text] Attempting to get text from element: {selector}")
        for attempt in range(2):
            try:
                elem = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                text_content = elem.text
                logger.info(f"[WebScraping.get_text] Successfully retrieved text from '{selector}' on attempt {attempt + 1}. Length: {len(text_content)}.")
                logger.debug(f"[WebScraping.get_text] Text from '{selector}': '{text_content[:100]}{'...' if len(text_content)>100 else ''}'")
                return text_content
            except StaleElementReferenceException as e_stale:
                logger.warning(f"[WebScraping.get_text] StaleElementReferenceException on attempt {attempt + 1} for selector '{selector}': {e_stale}. Retrying...")
                if attempt == 1:
                    logger.error(f"[WebScraping.get_text] StaleElementReferenceException persisted for '{selector}'.")
                    raise
                time.sleep(0.5)
            except NoSuchElementException: # This might be redundant if WebDriverWait is used, but good for clarity
                logger.error(f"[WebScraping.get_text] Element '{selector}' not found (NoSuchElement).")
                return None # Or raise
            except TimeoutException:
                logger.error(f"[WebScraping.get_text] Timeout waiting for element '{selector}' to be present.")
                return None # Or raise
            except Exception as e:
                logger.error(f"[WebScraping.get_text] Error getting text from element '{selector}': {e}")
                # Decide if to raise or return None based on how critical this is
                if attempt == 1: raise # Raise on last attempt for general errors too
        return None # Should not be reached if successful or exception raised


    def get_texts(self, selector):
        """Get the texts of multiple elements. StaleElement checks for individual elements within the loop."""
        logger.info(f"[WebScraping.get_texts] Attempting to get texts from elements: {selector}")
        texts = []
        try:
            elems = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
            )
            logger.info(f"[WebScraping.get_texts] Found {len(elems)} elements for selector '{selector}'.")
            for i, elem_proxy in enumerate(elems): # elem_proxy is a WebElement, can go stale
                for attempt in range(2): # Retry for each element
                    try:
                        # Re-access the specific element in list by index if needed, or re-fetch the list if the whole list can go stale
                        # For simplicity, we'll try to use elem_proxy directly first.
                        # If the list itself can go stale, this needs a more complex retry for the list.
                        current_elem = WebDriverWait(self.driver, 2).until(
                            # Try to ensure the element is still present and interactable
                            # This re-fetches based on its initial finding, not a re-find by selector for *this specific element*
                            # A more robust way would be to re-evaluate the selector and get element at index i,
                            # but that's more complex if the number of elements changes.
                            # For now, just try to access .text
                            lambda d: elems[i] if elems[i].is_displayed() else False # Basic check
                        )
                        text_val = current_elem.text
                        texts.append(text_val)
                        logger.debug(f"[WebScraping.get_texts] Text from element #{i} ('{selector}'): '{text_val[:50]}...'")
                        break # Success for this element
                    except StaleElementReferenceException:
                        logger.warning(f"[WebScraping.get_texts] StaleElementReferenceException for element #{i} of '{selector}' on attempt {attempt+1}. Retrying list or element.")
                        if attempt == 1:
                            logger.error(f"[WebScraping.get_texts] StaleElementReferenceException persisted for element #{i} of '{selector}'. Skipping.")
                            break # Break inner retry loop, continue to next element
                        time.sleep(0.5)
                        # Potentially re-fetch the entire list of elements here if the list itself might have changed
                        elems = WebDriverWait(self.driver, 5).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
                        if i >= len(elems): # If element index is now out of bounds
                            logger.warning(f"[WebScraping.get_texts] Element #{i} no longer in list after re-fetch. Skipping.")
                            break
                    except Exception as e_inner:
                        logger.error(f"[WebScraping.get_texts] Failed to get text from sub-element #{i} of '{selector}': {e_inner}")
                        break # Break inner retry, continue to next element
            logger.info(f"[WebScraping.get_texts] Retrieved {len(texts)} texts successfully from '{selector}'.")
            return texts
        except TimeoutException:
            logger.error(f"[WebScraping.get_texts] Timeout waiting for elements with selector '{selector}'.")
            return [] # Return empty list on timeout
        except Exception as e:
            logger.error(f"[WebScraping.get_texts] Failed to get texts from elements with selector '{selector}': {e}")
            return texts # Return whatever was collected

    def set_attrib(self, selector, attrib_name, attrib_value):
        """Set an attribute of an element with StaleElementReferenceException handling."""
        logger.info(f"[WebScraping.set_attrib] Attempting to set attribute '{attrib_name}' to '{attrib_value}' for element: {selector}")
        for attempt in range(2):
            try:
                elem = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                self.driver.execute_script(f"arguments[0].setAttribute(arguments[1], arguments[2]);", elem, attrib_name, attrib_value)
                logger.info(f"[WebScraping.set_attrib] Successfully set attribute '{attrib_name}'='{attrib_value}' on element: {selector} on attempt {attempt+1}")
                return
            except StaleElementReferenceException as e_stale:
                logger.warning(f"[WebScraping.set_attrib] StaleElementReferenceException on attempt {attempt + 1} for '{selector}': {e_stale}. Retrying...")
                if attempt == 1:
                    logger.error(f"[WebScraping.set_attrib] StaleElementReferenceException persisted for '{selector}'.")
                    raise
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"[WebScraping.set_attrib] Failed to set attribute '{attrib_name}' on element '{selector}' on attempt {attempt+1}: {e}")
                raise
        logger.error(f"[WebScraping.set_attrib] set_attrib failed for '{selector}' after all attempts.")
        raise Exception(f"set_attrib failed for '{selector}' after all attempts.")


    def get_attrib(self, selector, attrib_name):
        """Get an attribute of an element with StaleElementReferenceException handling."""
        logger.info(f"[WebScraping.get_attrib] Attempting to get attribute '{attrib_name}' from element: {selector}")
        for attempt in range(2):
            try:
                elem = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                attr_value = elem.get_attribute(attrib_name)
                logger.info(f"[WebScraping.get_attrib] Successfully retrieved attribute '{attrib_name}' (value: '{attr_value}') from: {selector} on attempt {attempt+1}")
                return attr_value
            except StaleElementReferenceException as e_stale:
                logger.warning(f"[WebScraping.get_attrib] StaleElementReferenceException on attempt {attempt + 1} for '{selector}': {e_stale}. Retrying...")
                if attempt == 1:
                    logger.error(f"[WebScraping.get_attrib] StaleElementReferenceException persisted for '{selector}'.")
                    raise # Or return None depending on desired behavior
                time.sleep(0.5)
            except TimeoutException:
                logger.error(f"[WebScraping.get_attrib] Timeout waiting for element '{selector}' to get attribute '{attrib_name}'.")
                return None # Or raise
            except Exception as e:
                logger.error(f"[WebScraping.get_attrib] Failed to get attribute '{attrib_name}' from element '{selector}': {e}")
                # Decide if to raise or return None
                if attempt == 1: raise
        return None # Should not be reached if successful or exception raised

    def get_attribs(self, selector, attrib_name, allow_duplicates=True, allow_empty=True):
        """Get attributes of multiple elements. StaleElement handling for individual elements within the loop."""
        logger.info(f"[WebScraping.get_attribs] Attempting to get attribute '{attrib_name}' from elements: {selector}")
        attributes = []
        try:
            elems = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
            )
            logger.info(f"[WebScraping.get_attribs] Found {len(elems)} elements for selector '{selector}'.")
            for i, elem in enumerate(elems):
                try:
                    attribute = elem.get_attribute(attrib_name)
                    if not allow_duplicates and attribute in attributes:
                        logger.debug(f"[WebScraping.get_attribs] Duplicate attribute '{attribute}' from element #{i} ('{selector}') skipped.")
                        continue
                    if not allow_empty and (attribute is None or attribute.strip() == ""):
                        logger.debug(f"[WebScraping.get_attribs] Empty attribute from element #{i} ('{selector}') skipped.")
                        continue
                    attributes.append(attribute)
                    logger.debug(f"[WebScraping.get_attribs] Attribute from element #{i} ('{selector}'): '{attribute}'")
                except Exception as e:
                    logger.error(f"[WebScraping.get_attribs] Failed to get attribute '{attrib_name}' from sub-element #{i} of '{selector}': {e}")
                    continue
            logger.info(f"[WebScraping.get_attribs] Retrieved {len(attributes)} attributes ('{attrib_name}') successfully from '{selector}'.")
            return attributes
        except TimeoutException:
            logger.error(f"[WebScraping.get_attribs] Timeout waiting for elements with selector '{selector}' for attribute '{attrib_name}'.")
            return []
        except Exception as e:
            logger.error(f"[WebScraping.get_attribs] Failed to get attributes '{attrib_name}' from elements with selector '{selector}': {e}")
            return attributes # Return whatever was collected

    def get_elem(self, selector):
        """Get a single element."""
        logger.info(f"[WebScraping.get_elem] Attempting to get element: {selector}")
        try:
            elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            logger.info(f"[WebScraping.get_elem] Successfully retrieved element: {selector}")
            return elem
        except NoSuchElementException: # Might be redundant
            logger.error(f"[WebScraping.get_elem] Element '{selector}' not found (NoSuchElement).")
            return None
        except TimeoutException:
            logger.error(f"[WebScraping.get_elem] Timeout waiting for element '{selector}'.")
            return None
        except Exception as e:
            logger.error(f"[WebScraping.get_elem] Error getting element '{selector}': {e}")
            return None


    def get_elems(self, selector):
        """Get multiple elements."""
        logger.info(f"[WebScraping.get_elems] Attempting to get multiple elements: {selector}")
        try:
            elems = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
            )
            logger.info(f"[WebScraping.get_elems] Successfully retrieved {len(elems)} elements for selector: {selector}")
            return elems
        except NoSuchElementException: # Might be redundant
            logger.error(f"[WebScraping.get_elems] Elements with selector '{selector}' not found (NoSuchElement).")
            return []
        except TimeoutException:
            logger.error(f"[WebScraping.get_elems] Timeout waiting for elements with selector '{selector}'.")
            return []
        except Exception as e:
            logger.error(f"[WebScraping.get_elems] Error getting elements with selector '{selector}': {e}")
            return []

    def set_page_js(self, web_page, new_tab=False):
        """Set the current page using JavaScript."""
        logger.info(f"[WebScraping.set_page_js] Setting page to '{web_page}' using JavaScript (new_tab={new_tab}).")
        self.__web_page__ = web_page
        try:
            if new_tab:
                script = f'window.open("{web_page}");'
                logger.debug(f"[WebScraping.set_page_js] Executing script: {script}")
            else:
                script = f'window.location.href = "{web_page}";' # More reliable than window.open for same tab
                logger.debug(f"[WebScraping.set_page_js] Executing script: {script}")
            self.driver.execute_script(script)
            logger.info(f"[WebScraping.set_page_js] Page successfully set to '{web_page}' using JavaScript.")
        except Exception as e:
            logger.error(f"[WebScraping.set_page_js] Failed to set page to '{web_page}' using JavaScript: {e}")
            raise

    def set_page(self, web_page, time_out=0, break_time_out=False):
        """Set the current page."""
        logger.info(f"[WebScraping.set_page] Navigating to URL: {web_page} (timeout: {time_out}s, break_on_timeout: {break_time_out})")
        try:
            self.__web_page__ = web_page
            if time_out > 0:
                self.driver.set_page_load_timeout(time_out)
                logger.debug(f"[WebScraping.set_page] Page load timeout set to {time_out}s.")
            self.driver.get(self.__web_page__)
            logger.info(f"[WebScraping.set_page] Successfully navigated to {web_page}.")
        except TimeoutException as e:
            if break_time_out:
                logger.error(f"[WebScraping.set_page] Timeout loading page: {web_page}. Raising exception as break_time_out is True.")
                raise
            else:
                self.driver.execute_script("window.stop();") # Try to stop loading
                logger.warning(f"[WebScraping.set_page] Page load for {web_page} timed out, but script continued as break_time_out is False.")
        except Exception as e:
            logger.error(f"[WebScraping.set_page] Failed to navigate to {web_page}: {e}")
            raise

    def click_js(self, selector: str):
        """Click on an element using JavaScript."""
        logger.info(f"[WebScraping.click_js] Attempting to click element (via JS) with selector: {selector}")
        for attempt in range(2):
            try:
                # Find element just before clicking, as JS click doesn't wait for interactability like Selenium click
                elem = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                self.driver.execute_script("arguments[0].click();", elem)
                logger.info(f"[WebScraping.click_js] Successfully clicked (via JS) element: {selector} on attempt {attempt+1}")
                return
            except StaleElementReferenceException as e_stale:
                logger.warning(f"[WebScraping.click_js] StaleElementReferenceException on attempt {attempt + 1} for '{selector}': {e_stale}. Retrying...")
                if attempt == 1:
                    logger.error(f"[WebScraping.click_js] StaleElementReferenceException persisted for '{selector}'.")
                    raise
                time.sleep(0.5)
            except NoSuchElementException: # Could happen if element disappears before JS click
                 logger.error(f"[WebScraping.click_js] Element '{selector}' not found for JS click on attempt {attempt+1}.")
                 if attempt == 1: raise
                 time.sleep(0.5) # Wait before retrying find
            except TimeoutException: # From WebDriverWait
                 logger.error(f"[WebScraping.click_js] Timeout waiting for element '{selector}' for JS click on attempt {attempt+1}.")
                 if attempt == 1: raise
                 time.sleep(0.5)
            except Exception as e:
                logger.error(f"[WebScraping.click_js] Failed to click (via JS) element '{selector}' on attempt {attempt+1}: {e}")
                if attempt == 1: raise
        logger.error(f"[WebScraping.click_js] click_js failed for '{selector}' after all attempts.")
        raise Exception(f"click_js failed for '{selector}' after all attempts.")


    def select_drop_down_index(self, selector, index):
        """Select an option from a dropdown by index with StaleElementReferenceException handling."""
        logger.info(f"[WebScraping.select_drop_down_index] Attempting to select index {index} from dropdown '{selector}'.")
        for attempt in range(2):
            try:
                select_elem_wrapper = self.get_elem(selector) # get_elem has its own logging and wait
                if select_elem_wrapper:
                    select_obj = Select(select_elem_wrapper)
                    select_obj.select_by_index(index)
                    logger.info(f"[WebScraping.select_drop_down_index] Selected index {index} from dropdown '{selector}' on attempt {attempt+1}.")
                    return
                else:
                    # get_elem would have logged the error and returned None
                    logger.error(f"[WebScraping.select_drop_down_index] Dropdown element '{selector}' not found by get_elem.")
                    raise NoSuchElementException(f"Dropdown element '{selector}' not found for select_by_index.")
            except StaleElementReferenceException as e_stale:
                logger.warning(f"[WebScraping.select_drop_down_index] StaleElementReferenceException on attempt {attempt + 1} for '{selector}': {e_stale}. Retrying...")
                if attempt == 1:
                    logger.error(f"[WebScraping.select_drop_down_index] StaleElementReferenceException persisted for '{selector}'.")
                    raise
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"[WebScraping.select_drop_down_index] Failed to select index {index} from dropdown '{selector}' on attempt {attempt+1}: {e}")
                if attempt == 1: raise # Raise original error if retries fail
        logger.error(f"[WebScraping.select_drop_down_index] select_drop_down_index failed for '{selector}' after all attempts.")
        raise Exception(f"select_drop_down_index failed for '{selector}' after all attempts.")


    def select_drop_down_text(self, selector, text):
        """Select an option from a dropdown by visible text with StaleElementReferenceException handling."""
        logger.info(f"[WebScraping.select_drop_down_text] Attempting to select text '{text}' from dropdown '{selector}'.")
        for attempt in range(2):
            try:
                select_elem_wrapper = self.get_elem(selector) # get_elem has its own logging and wait
                if select_elem_wrapper:
                    select_obj = Select(select_elem_wrapper)
                    select_obj.select_by_visible_text(text)
                    logger.info(f"[WebScraping.select_drop_down_text] Selected text '{text}' from dropdown '{selector}' on attempt {attempt+1}.")
                    return
                else:
                    logger.error(f"[WebScraping.select_drop_down_text] Dropdown element '{selector}' not found by get_elem.")
                    raise NoSuchElementException(f"Dropdown element '{selector}' not found for select_by_visible_text.")
            except StaleElementReferenceException as e_stale:
                logger.warning(f"[WebScraping.select_drop_down_text] StaleElementReferenceException on attempt {attempt + 1} for '{selector}': {e_stale}. Retrying...")
                if attempt == 1:
                    logger.error(f"[WebScraping.select_drop_down_text] StaleElementReferenceException persisted for '{selector}'.")
                    raise
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"[WebScraping.select_drop_down_text] Failed to select text '{text}' from dropdown '{selector}' on attempt {attempt+1}: {e}")
                if attempt == 1: raise
        logger.error(f"[WebScraping.select_drop_down_text] select_drop_down_text failed for '{selector}' after all attempts.")
        raise Exception(f"select_drop_down_text failed for '{selector}' after all attempts.")


    def go_bottom(self, selector: str = "body"):
        """Scroll to the bottom of the page."""
        logger.info(f"[WebScraping.go_bottom] Scrolling to bottom of element '{selector}'.")
        try:
            elem = self.driver.find_element(By.CSS_SELECTOR, selector)
            elem.send_keys(Keys.CONTROL + Keys.END)
            logger.info(f"[WebScraping.go_bottom] Scrolled to bottom of '{selector}' successfully.")
        except Exception as e:
            logger.error(f"[WebScraping.go_bottom] Failed to scroll to bottom of '{selector}': {e}")
            raise

    def go_top(self, selector: str = "body"):
        """Scroll to the top of the page."""
        logger.info(f"[WebScraping.go_top] Scrolling to top of element '{selector}'.")
        try:
            elem = self.driver.find_element(By.CSS_SELECTOR, selector)
            elem.send_keys(Keys.CONTROL + Keys.UP) # Or Keys.HOME
            logger.info(f"[WebScraping.go_top] Scrolled to top of '{selector}' successfully.")
        except Exception as e:
            logger.error(f"[WebScraping.go_top] Failed to scroll to top of '{selector}': {e}")
            raise

    def go_down(self, selector: str = "body"):
        """Scroll down the page."""
        logger.info(f"[WebScraping.go_down] Scrolling down on element '{selector}'.")
        try:
            elem = self.driver.find_element(By.CSS_SELECTOR, selector)
            elem.send_keys(Keys.PAGE_DOWN)
            logger.info(f"[WebScraping.go_down] Scrolled down on '{selector}' successfully.")
        except Exception as e:
            logger.error(f"[WebScraping.go_down] Failed to scroll down on '{selector}': {e}")
            raise

    def go_up(self, selector: str = "body"):
        """Scroll up the page."""
        logger.info(f"[WebScraping.go_up] Scrolling up on element '{selector}'.")
        try:
            elem = self.driver.find_element(By.CSS_SELECTOR, selector)
            elem.send_keys(Keys.PAGE_UP)
            logger.info(f"[WebScraping.go_up] Scrolled up on '{selector}' successfully.")
        except Exception as e:
            logger.error(f"[WebScraping.go_up] Failed to scroll up on '{selector}': {e}")
            raise

    def switch_to_main_frame(self):
        """Switch to the main frame."""
        logger.info("[WebScraping.switch_to_main_frame] Attempting to switch to default content (main frame).")
        try:
            self.driver.switch_to.default_content()
            logger.info("[WebScraping.switch_to_main_frame] Switched to default content successfully.")
        except Exception as e:
            logger.error(f"[WebScraping.switch_to_main_frame] Failed to switch to default content: {e}")
            raise

    def switch_to_frame(self, frame_selector):
        """Switch to a specific frame."""
        logger.info(f"[WebScraping.switch_to_frame] Attempting to switch to frame with selector: {frame_selector}")
        try:
            frame = self.get_elem(frame_selector) # Uses get_elem which has its own logging
            if frame:
                self.driver.switch_to.frame(frame)
                logger.info(f"[WebScraping.switch_to_frame] Successfully switched to frame: {frame_selector}")
            else:
                logger.error(f"[WebScraping.switch_to_frame] Frame element '{frame_selector}' not found.")
                raise NoSuchElementException(f"Frame '{frame_selector}' not found for switching.")
        except Exception as e: # Catch more general exceptions too
            logger.error(f"[WebScraping.switch_to_frame] Failed to switch to frame '{frame_selector}': {e}")
            raise

    def open_tab(self):
        """Open a new tab."""
        logger.info("[WebScraping.open_tab] Attempting to open a new tab.")
        try:
            self.driver.execute_script("window.open('');")
            logger.info("[WebScraping.open_tab] New tab opened. Current handles: {self.driver.window_handles}")
            self.switch_to_tab(len(self.driver.window_handles) -1) # Switch to the new tab
        except Exception as e:
            logger.error(f"[WebScraping.open_tab] Failed to open new tab: {e}")
            raise

    def close_tab(self):
        """Close the current tab."""
        logger.info("[WebScraping.close_tab] Attempting to close current tab.")
        try:
            self.driver.close()
            logger.info("[WebScraping.close_tab] Current tab closed. Remaining handles: {self.driver.window_handles}")
            if self.driver.window_handles: # Switch to a remaining tab if any
                 self.switch_to_tab(len(self.driver.window_handles) - 1)
        except Exception as e:
            logger.error(f"[WebScraping.close_tab] Failed to close tab: {e}")
            raise

    def switch_to_tab(self, number):
        """Switch to a specific tab by index."""
        logger.info(f"[WebScraping.switch_to_tab] Attempting to switch to tab number {number}.")
        try:
            windows = self.driver.window_handles
            if 0 <= number < len(windows):
                self.driver.switch_to.window(windows[number])
                logger.info(f"[WebScraping.switch_to_tab] Successfully switched to tab number {number} (handle: {windows[number]}).")
            else:
                logger.error(f"[WebScraping.switch_to_tab] Tab number {number} is out of range. Available tabs: {len(windows)}")
                raise IndexError(f"Tab number {number} is out of range.")
        except Exception as e:
            logger.error(f"[WebScraping.switch_to_tab] Failed to switch to tab number {number}: {e}")
            raise

    def refresh_selenium(self, time_units=1, back_tab=0):
        """Refresh the browser by quickly opening and closing a new tab."""
        # This method seems like a workaround. Consider if direct refresh or other waits are more appropriate.
        logger.info(f"[WebScraping.refresh_selenium] Attempting to 'refresh selenium' (units: {time_units}, back_tab_idx: {back_tab}).")
        try:
            self.open_tab() # Logs internally
            # Tab switching is logged internally by open_tab and switch_to_tab
            time.sleep(self.basetime * time_units)
            self.close_tab() # Logs internally
            # Tab switching is logged internally by close_tab
            time.sleep(self.basetime * time_units)
            logger.info("[WebScraping.refresh_selenium] 'Refresh selenium' process completed.")
        except Exception as e:
            logger.error(f"[WebScraping.refresh_selenium] Failed during 'refresh selenium': {e}")
            raise

    def save_page(self, file_html):
        """Save the current page as HTML."""
        logger.info(f"[WebScraping.save_page] Attempting to save current page source to: {file_html}")
        try:
            page_html = self.driver.page_source
            # current_folder = os.path.dirname(__file__) # file_html should ideally be an absolute path or relative to CWD
            # For robustness, ensure the directory for file_html exists or handle errors
            # os.makedirs(os.path.dirname(file_html), exist_ok=True) # If we want to create dirs
            with open(file_html, "w", encoding='utf-8') as page_file:
                page_file.write(page_html)
            logger.info(f"[WebScraping.save_page] Page source successfully saved to '{file_html}'.")
        except Exception as e:
            logger.error(f"[WebScraping.save_page] Failed to save page source to '{file_html}': {e}")
            raise

    def zoom(self, percentage=50):
        """Zoom the page."""
        logger.info(f"[WebScraping.zoom] Attempting to set page zoom to {percentage}%.")
        try:
            script = f"document.body.style.zoom='{percentage}%'"
            self.driver.execute_script(script)
            logger.info(f"[WebScraping.zoom] Page zoom successfully set to {percentage}%.")
        except Exception as e:
            logger.error(f"[WebScraping.zoom] Failed to set page zoom to {percentage}%: {e}")
            raise

    def kill(self):
        """Kill all browser instances by closing all tabs and then quitting the driver."""
        # This method might be redundant if end_browser() is called, which should quit the driver and close all windows.
        # The current implementation might error if end_browser already quit the driver.
        logger.info("[WebScraping.kill] Attempting to kill all browser instances/tabs.")
        try:
            if hasattr(self, 'driver') and self.driver:
                num_tabs = len(self.driver.window_handles)
                logger.debug(f"[WebScraping.kill] Found {num_tabs} tabs to close.")
                for i in range(num_tabs):
                    try:
                        self.switch_to_tab(0) # Switch to the first available tab
                        self.close_tab() # Close it, switch_to_tab in close_tab handles switching to next
                        logger.info(f"[WebScraping.kill] Closed tab {i+1}/{num_tabs}.")
                    except Exception as e:
                        logger.warning(f"[WebScraping.kill] Error closing a tab during kill process (tab {i+1}): {e}")
                        # May occur if a tab closes unexpectedly or driver becomes unresponsive
                logger.info("[WebScraping.kill] All tabs closed (or attempted). Now calling end_browser.")
                self.end_browser() # Ensure the driver itself is quit
            else:
                logger.info("[WebScraping.kill] No active driver instance to kill.")
        except Exception as e:
            logger.error(f"[WebScraping.kill] Failed during kill process: {e}")
            # Do not raise here if the goal is to ensure it tries to quit no matter what

    def scroll(self, selector, scroll_x, scroll_y):
        """Scroll to a specific position within an element."""
        logger.info(f"[WebScraping.scroll] Attempting to scroll element '{selector}' to ({scroll_x}, {scroll_y}).")
        try:
            elem = self.get_elem(selector) # Uses get_elem with its own logging
            if elem:
                self.driver.execute_script("arguments[0].scrollTo(arguments[1], arguments[2])", elem, scroll_x, scroll_y)
                logger.info(f"[WebScraping.scroll] Successfully scrolled element '{selector}' to ({scroll_x}, {scroll_y}).")
            else:
                logger.error(f"[WebScraping.scroll] Element '{selector}' not found for scrolling.")
                # Decide if to raise an error or just log
        except Exception as e:
            logger.error(f"[WebScraping.scroll] Failed to scroll in element '{selector}': {e}")
            raise

    def set_local_storage(self, key: str, value: str):
        """Set a value in the local storage."""
        # Be cautious logging value if it's sensitive
        value_to_log = value if len(value) < 50 else value[:50] + "..."
        logger.info(f"[WebScraping.set_local_storage] Attempting to set localStorage key '{key}' to '{value_to_log}'.")
        try:
            script = f"window.localStorage.setItem(arguments[0], arguments[1]);"
            self.driver.execute_script(script, key, value)
            logger.info(f"[WebScraping.set_local_storage] Successfully set localStorage key '{key}'.")
        except Exception as e:
            logger.error(f"[WebScraping.set_local_storage] Failed to set localStorage key '{key}': {e}")
            raise

    def get_alert_text(self):
        """Get the text from an alert box and accept it."""
        logger.info("[WebScraping.get_alert_text] Checking for alert and attempting to get text/accept.")
        try:
            WebDriverWait(self.driver, 10).until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            logger.info(f"[WebScraping.get_alert_text] Alert found with text: '{alert_text}'. Accepting it.")
            alert.accept()
            logger.info("[WebScraping.get_alert_text] Alert accepted.")
            return alert_text
        except TimeoutException:
            logger.warning("[WebScraping.get_alert_text] No alert present within timeout.")
            return None
        except Exception as e:
            logger.error(f"[WebScraping.get_alert_text] Failed to get alert text or accept: {e}")
            raise

    def dismiss_alert(self):
        """Dismiss an alert box."""
        logger.info("[WebScraping.dismiss_alert] Checking for alert and attempting to dismiss.")
        try:
            WebDriverWait(self.driver, 10).until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            alert_text = alert.text # Log text before dismissing
            logger.info(f"[WebScraping.dismiss_alert] Alert found with text: '{alert_text}'. Dismissing it.")
            alert.dismiss()
            logger.info("[WebScraping.dismiss_alert] Alert dismissed.")
        except TimeoutException:
            logger.warning("[WebScraping.dismiss_alert] No alert present to dismiss within timeout.")
        except Exception as e:
            logger.error(f"[WebScraping.dismiss_alert] Failed to dismiss alert: {e}")
            raise

    def accept_alert(self):
        """Accept an alert box."""
        logger.info("[WebScraping.accept_alert] Checking for alert and attempting to accept.")
        try:
            WebDriverWait(self.driver, 10).until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            alert_text = alert.text # Log text before accepting
            logger.info(f"[WebScraping.accept_alert] Alert found with text: '{alert_text}'. Accepting it.")
            alert.accept()
            logger.info("[WebScraping.accept_alert] Alert accepted.")
        except TimeoutException:
            logger.warning("[WebScraping.accept_alert] No alert present to accept within timeout.")
        except Exception as e:
            logger.error(f"[WebScraping.accept_alert] Failed to accept alert: {e}")
            raise

    def capture_network_traffic(self):
        """Capture network traffic. Requires performance logging to be enabled in ChromeOptions."""
        logger.info("[WebScraping.capture_network_traffic] Attempting to capture network traffic logs.")
        try:
            # Ensure performance logging is enabled, e.g.
            # caps = webdriver.DesiredCapabilities.CHROME.copy()
            # caps['goog:loggingPrefs'] = {'performance': 'ALL'}
            # self.driver = webdriver.Chrome(desired_capabilities=caps, ...)
            logs = self.driver.get_log("performance")
            logger.info(f"[WebScraping.capture_network_traffic] Successfully captured {len(logs)} network log entries.")
            return logs
        except Exception as e:
            logger.error(f"[WebScraping.capture_network_traffic] Failed to capture network traffic: {e}. Ensure performance logging is enabled for the driver.")
            raise

    def clear_cache(self):
        """Clear browser cache (localStorage, sessionStorage, and network cache)."""
        logger.info("[WebScraping.clear_cache] Attempting to clear browser cache.")
        try:
            self.driver.execute_script("window.localStorage.clear();")
            logger.debug("[WebScraping.clear_cache] localStorage cleared.")
            self.driver.execute_script("window.sessionStorage.clear();")
            logger.debug("[WebScraping.clear_cache] sessionStorage cleared.")
            self.driver.execute_cdp_cmd('Network.clearBrowserCache', {})
            logger.debug("[WebScraping.clear_cache] Network browser cache cleared via CDP.")
            logger.info("[WebScraping.clear_cache] Browser cache cleared successfully.")
        except Exception as e:
            logger.error(f"[WebScraping.clear_cache] Failed to clear browser cache: {e}")
            raise

    def bypass_cloudflare(self, url):
        """Attempts a basic Cloudflare bypass by waiting. Might not be effective for advanced challenges."""
        logger.info(f"[WebScraping.bypass_cloudflare] Attempting basic Cloudflare bypass for URL: {url}")
        try:
            self.set_page(url) # Uses internal logging
            logger.info(f"[WebScraping.bypass_cloudflare] Waiting 10 seconds for potential Cloudflare challenge on {url}.")
            time.sleep(10)  # Wait for Cloudflare challenge to complete
            self.driver.execute_script("window.stop();") # Stop any further loading
            logger.info(f"[WebScraping.bypass_cloudflare] Basic Cloudflare bypass attempt completed for {url}.")
        except Exception as e:
            logger.error(f"[WebScraping.bypass_cloudflare] Failed during Cloudflare bypass attempt for URL {url}: {e}")
            raise

    def wait_for_element(self, selector, time_out=10):
        """Wait for an element to be present in the DOM."""
        logger.info(f"[WebScraping.wait_for_element] Waiting for element '{selector}' to be present (timeout: {time_out}s).")
        try:
            WebDriverWait(self.driver, time_out).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            logger.info(f"[WebScraping.wait_for_element] Element '{selector}' is present.")
        except TimeoutException:
            logger.error(f"[WebScraping.wait_for_element] Timeout: Element '{selector}' not found within {time_out} seconds.")
            raise
        except Exception as e:
            logger.error(f"[WebScraping.wait_for_element] Error waiting for element '{selector}': {e}")
            raise


    def wait_for_element_to_be_clickable(self, selector, time_out=10):
        """Wait for an element to be present and clickable."""
        logger.info(f"[WebScraping.wait_for_element_to_be_clickable] Waiting for element '{selector}' to be clickable (timeout: {time_out}s).")
        try:
            WebDriverWait(self.driver, time_out).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            logger.info(f"[WebScraping.wait_for_element_to_be_clickable] Element '{selector}' is clickable.")
        except TimeoutException:
            logger.error(f"[WebScraping.wait_for_element_to_be_clickable] Timeout: Element '{selector}' not clickable within {time_out} seconds.")
            raise
        except Exception as e:
            logger.error(f"[WebScraping.wait_for_element_to_be_clickable] Error waiting for '{selector}' to be clickable: {e}")
            raise

    def wait_for_element_to_disappear(self, selector, time_out=10):
        """Wait for an element to become invisible or not present in the DOM."""
        logger.info(f"[WebScraping.wait_for_element_to_disappear] Waiting for element '{selector}' to disappear (timeout: {time_out}s).")
        try:
            WebDriverWait(self.driver, time_out).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, selector)))
            logger.info(f"[WebScraping.wait_for_element_to_disappear] Element '{selector}' has disappeared.")
        except TimeoutException:
            logger.error(f"[WebScraping.wait_for_element_to_disappear] Timeout: Element '{selector}' did not disappear within {time_out} seconds.")
            raise
        except Exception as e:
            logger.error(f"[WebScraping.wait_for_element_to_disappear] Error waiting for '{selector}' to disappear: {e}")
            raise
    
    def wait_for_text_to_be_present(self, selector, text, time_out=10):
        """Wait for specific text to be present in an element."""
        logger.info(f"[WebScraping.wait_for_text_to_be_present] Waiting for text '{text}' in element '{selector}' (timeout: {time_out}s).")
        try:
            WebDriverWait(self.driver, time_out).until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, selector), text))
            logger.info(f"[WebScraping.wait_for_text_to_be_present] Text '{text}' is present in element '{selector}'.")
        except TimeoutException:
            logger.error(f"[WebScraping.wait_for_text_to_be_present] Timeout: Text '{text}' not in '{selector}' within {time_out}s.")
            raise
        except Exception as e:
            logger.error(f"[WebScraping.wait_for_text_to_be_present] Error waiting for text '{text}' in '{selector}': {e}")
            raise
    
    def wait_for_title(self, title, time_out=10):
        """Wait for the page title to be a specific value."""
        logger.info(f"[WebScraping.wait_for_title] Waiting for page title to be '{title}' (timeout: {time_out}s).")
        try:
            WebDriverWait(self.driver, time_out).until(EC.title_is(title))
            logger.info(f"[WebScraping.wait_for_title] Page title is '{title}'.")
        except TimeoutException:
            logger.error(f"[WebScraping.wait_for_title] Timeout: Title '{title}' not present within {time_out} seconds.")
            raise
        except Exception as e:
            logger.error(f"[WebScraping.wait_for_title] Error waiting for title '{title}': {e}")
            raise

    def wait_for_title_contains(self, title, time_out=10):
        """Wait for the page title to contain a specific value."""
        logger.info(f"[WebScraping.wait_for_title_contains] Waiting for page title to contain '{title}' (timeout: {time_out}s).")
        try:
            WebDriverWait(self.driver, time_out).until(EC.title_contains(title))
            logger.info(f"[WebScraping.wait_for_title_contains] Page title contains '{title}'.")
        except TimeoutException:
            logger.error(f"[WebScraping.wait_for_title_contains] Timeout: Title containing '{title}' not present within {time_out}s.")
            raise
        except Exception as e:
            logger.error(f"[WebScraping.wait_for_title_contains] Error waiting for title containing '{title}': {e}")
            raise

    def refresh_page(self):
        """Refresh the current page."""
        logger.info("[WebScraping.refresh_page] Attempting to refresh the current page.")
        try:
            self.driver.refresh()
            logger.info("[WebScraping.refresh_page] Page refreshed successfully.")
        except Exception as e:
            logger.error(f"[WebScraping.refresh_page] Failed to refresh page: {e}")
            raise

    def execute_script(self, script, *args):
        """Execute a JavaScript script."""
        script_to_log = script if len(script) < 100 else script[:100] + "..."
        logger.info(f"[WebScraping.execute_script] Attempting to execute script: '{script_to_log}' with {len(args)} arguments.")
        try:
            result = self.driver.execute_script(script, *args)
            logger.info(f"[WebScraping.execute_script] Script executed successfully. Result: {type(result)}") # Log type of result, not result itself if large
            logger.debug(f"[WebScraping.execute_script] Script result: {result if isinstance(result, (str, int, float, bool, type(None))) else 'Non-primitive type'}")
            return result
        except Exception as e:
            logger.error(f"[WebScraping.execute_script] Failed to execute script '{script_to_log}': {e}")
            raise

    def close_browser(self):
        """Close the browser. Alias for end_browser for clarity in some contexts."""
        logger.info("[WebScraping.close_browser] Alias called for end_browser.")
        self.end_browser() # end_browser already has logging

    def restart_browser(self, time_out=0):
        """Restart the browser instance."""
        logger.info(f"[WebScraping.restart_browser] Attempting to restart browser (page_load_timeout: {time_out}s).")
        try:
            self.end_browser() # Has its own logging for closing
            logger.info("[WebScraping.restart_browser] Old browser instance closed. Setting up new instance.")
            self.__set_browser_instance__() # Has its own logging for setup
            if time_out > 0 and hasattr(self, 'driver'):
                self.driver.set_page_load_timeout(time_out)
                logger.info(f"[WebScraping.restart_browser] Page load timeout set to {time_out}s for new instance.")
            logger.info("[WebScraping.restart_browser] Browser restarted successfully.")
        except Exception as e:
            logger.error(f"[WebScraping.restart_browser] Failed to restart browser: {e}")
            raise

    def get_user_agent(self):
        """Get the user agent of the browser."""
        logger.info("[WebScraping.get_user_agent] Attempting to get browser user agent.")
        try:
            user_agent = self.driver.execute_script("return navigator.userAgent;")
            logger.info(f"[WebScraping.get_user_agent] User agent retrieved: {user_agent}")
            return user_agent
        except Exception as e:
            logger.error(f"[WebScraping.get_user_agent] Failed to get user agent: {e}")
            raise