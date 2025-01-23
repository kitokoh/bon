import os
import time
import zipfile
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service

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
                 chrome_folder="", user_agent=False, 
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
            command = 'taskkill /IM "chrome.eexe" /F'
            os.system(command)
            logger.info("Chrome killed successfully.")

        if self.__start_openning__:
            self.__set_browser_instance__()

        if time_out > 0:
            self.driver.set_page_load_timeout(time_out)

    def __set_browser_instance__(self):
        """Configure and start the browser instance."""
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

    def screenshot(self, base_name):
        """Take a screenshot of the current page."""
        if str(base_name).endswith(".png"):
            file_name = base_name
        else:
            file_name = f"{base_name}.png"
        self.driver.save_screenshot(file_name)

    def full_screenshot(self, path: str):
        """Take a full screenshot of the current page."""
        original_size = self.driver.get_window_size()
        required_width = self.driver.execute_script('return document.body.parentNode.scrollWidth')
        required_height = self.driver.execute_script('return document.body.parentNode.scrollHeight')
        self.driver.set_window_size(required_width, required_height)
        self.screenshot(path)  # avoids scrollbar
        self.driver.set_window_size(original_size['width'], original_size['height'])

    def get_browser(self):
        """Get the current browser instance."""
        return self.driver

    def end_browser(self):
        """Close the browser instance."""
        self.driver.quit()

    def __reload_browser__(self):
        """Reload the browser instance."""
        self.end_browser()
        self.driver = self.get_browser()
        self.driver.get(self.__web_page__)

    def send_data(self, selector, data):
        """Send data to an input field."""
        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
        elem.send_keys(data)

    def click(self, selector):
        """Click on an element."""
        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
        elem.click()

    def wait_load(self, selector, time_out=1, refresh_back_tab=-1):
        """Wait for an element to load."""
        total_time = 0
        while True:
            if total_time < time_out:
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

    def wait_die(self, selector, time_out=10):
        """Wait for an element to disappear."""
        total_time = 0
        while True:
            if total_time < time_out:
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

    def get_text(self, selector):
        """Get the text of an element."""
        try:
            elem = self.driver.find_element(By.CSS_SELECTOR, selector)
            return elem.text
        except Exception as e:
            logger.error(f"Failed to get text: {e}")
            return None

    def get_texts(self, selector):
        """Get the texts of multiple elements."""
        texts = []
        elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
        for elem in elems:
            try:
                texts.append(elem.text)
            except Exception as e:
                logger.error(f"Failed to get text: {e}")
                continue
        return texts

    def set_attrib(self, selector, attrib_name, attrib_value):
        """Set an attribute of an element."""
        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
        self.driver.execute_script(f"arguments[0].setAttribute('{attrib_name}', '{attrib_value}');", elem)

    def get_attrib(self, selector, attrib_name):
        """Get an attribute of an element."""
        try:
            elem = self.driver.find_element(By.CSS_SELECTOR, selector)
            return elem.get_attribute(attrib_name)
        except Exception as e:
            logger.error(f"Failed to get attribute: {e}")
            return None

    def get_attribs(self, selector, attrib_name, allow_duplicates=True, allow_empty=True):
        """Get attributes of multiple elements."""
        attributes = []
        elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
        for elem in elems:
            try:
                attribute = elem.get_attribute(attrib_name)
                if not allow_duplicates and attribute in attributes:
                    continue
                if not allow_empty and attribute.strip() == "":
                    continue
                attributes.append(attribute)
            except Exception as e:
                logger.error(f"Failed to get attribute: {e}")
                continue
        return attributes

    def get_elem(self, selector):
        """Get a single element."""
        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
        return elem

    def get_elems(self, selector):
        """Get multiple elements."""
        elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
        return elems

    def set_page_js(self, web_page, new_tab=False):
        """Set the current page using JavaScript."""
        self.__web_page__ = web_page
        if new_tab:
            script = f'window.open("{web_page}");'
        else:
            script = f'window.open("{web_page}").focus();'
        self.driver.execute_script(script)

    def set_page(self, web_page, time_out=0, break_time_out=False):
        """Set the current page."""
        try:
            self.__web_page__ = web_page
            if time_out > 0:
                self.driver.set_page_load_timeout(time_out)
            self.driver.get(self.__web_page__)
        except Exception as e:
            if break_time_out:
                raise Exception(f"Time out to load page: {web_page}")
            else:
                self.driver.execute_script("window.stop();")

    def click_js(self, selector: str):
        """Click on an element using JavaScript."""
        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
        self.driver.execute_script("arguments[0].click();", elem)

    def select_drop_down_index(self, selector, index):
        """Select an option from a dropdown by index."""
        select_elem = Select(self.get_elem(selector))
        select_elem.select_by_index(index)

    def select_drop_down_text(self, selector, text):
        """Select an option from a dropdown by visible text."""
        select_elem = Select(self.get_elem(selector))
        select_elem.select_by_visible_text(text)

    def go_bottom(self, selector: str = "body"):
        """Scroll to the bottom of the page."""
        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
        elem.send_keys(Keys.CONTROL + Keys.END)

    def go_top(self, selector: str = "body"):
        """Scroll to the top of the page."""
        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
        elem.send_keys(Keys.CONTROL + Keys.UP)

    def go_down(self, selector: str = "body"):
        """Scroll down the page."""
        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
        elem.send_keys(Keys.PAGE_DOWN)

    def go_up(self, selector: str = "body"):
        """Scroll up the page."""
        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
        elem.send_keys(Keys.PAGE_UP)

    def switch_to_main_frame(self):
        """Switch to the main frame."""
        self.driver.switch_to.default_content()

    def switch_to_frame(self, frame_selector):
        """Switch to a specific frame."""
        frame = self.get_elem(frame_selector)
        self.driver.switch_to.frame(frame)

    def open_tab(self):
        """Open a new tab."""
        self.driver.execute_script("window.open('');")

    def close_tab(self):
        """Close the current tab."""
        try:
            self.driver.close()
        except Exception as e:
            logger.error(f"Failed to close tab: {e}")

    def switch_to_tab(self, number):
        """Switch to a specific tab."""
        windows = self.driver.window_handles
        self.driver.switch_to.window(windows[number])

    def refresh_selenium(self, time_units=1, back_tab=0):
        """Refresh the browser."""
        self.open_tab()
        self.switch_to_tab(len(self.driver.window_handles) - 1)
        time.sleep(self.basetime * time_units)
        self.close_tab()
        self.switch_to_tab(back_tab)
        time.sleep(self.basetime * time_units)

    def save_page(self, file_html):
        """Save the current page as HTML."""
        page_html = self.driver.page_source
        current_folder = os.path.dirname(__file__)
        page_file = open(os.path.join(current_folder, file_html), "w", encoding='utf-8')
        page_file.write(page_html)
        page_file.close()

    def zoom(self, percentage=50):
        """Zoom the page."""
        script = f"document.body.style.zoom='{percentage}%'"
        self.driver.execute_script(script)

    def kill(self):
        """Kill all browser instances."""
        tabs = self.driver.window_handles
        for _ in tabs:
            self.switch_to_tab(0)
            self.end_browser()

    def scroll(self, selector, scroll_x, scroll_y):
        """Scroll to a specific position."""
        elem = self.get_elem(selector)
        self.driver.execute_script("arguments[0].scrollTo(arguments[1], arguments[2])", elem, scroll_x, scroll_y)

    def set_local_storage(self, key: str, value: str):
        """Set a value in the local storage."""
        script = f"window.localStorage.setItem('{key}', '{value}')"
        self.driver.execute_script(script)
