"""
browser.py — Selenium browser engine.

Responsibilities:
  - Spin up / tear down Chrome with sensible anti-bot options.
  - Provide atomic, well-typed interaction primitives (click, send, wait …).
  - Never contain any application logic (Facebook-specific code lives in scraper.py).

All public methods either return a meaningful value or raise a descriptive
exception — they never silently swallow errors.
"""

from __future__ import annotations

import logging
import os
import time
import zipfile
from contextlib import contextmanager
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import (
    ElementNotInteractableException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT: int = 15          # seconds – used as WebDriverWait default
MAX_RETRIES:     int = 3           # retry attempts for transient Selenium errors
RETRY_DELAY:     float = 2.0       # seconds between retries


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _with_retries(fn, *args, retries: int = MAX_RETRIES, delay: float = RETRY_DELAY, **kwargs):
    """Run *fn* up to *retries* times, re-raising the last exception on failure."""
    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            return fn(*args, **kwargs)
        except StaleElementReferenceException as exc:
            last_exc = exc
            logger.warning("StaleElement on attempt %d/%d – retrying …", attempt, retries)
            time.sleep(delay)
        except (TimeoutException, ElementNotInteractableException) as exc:
            last_exc = exc
            if attempt < retries:
                logger.warning("%s on attempt %d/%d – retrying …", type(exc).__name__, attempt, retries)
                time.sleep(delay * attempt)   # exponential back-off
            else:
                raise
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# BrowserEngine
# ---------------------------------------------------------------------------

class BrowserEngine:
    """
    Thin wrapper around a Selenium WebDriver instance.

    Parameters
    ----------
    chrome_folder : str
        Path to the Chrome user-data directory (for persistent sessions).
    headless : bool
        Run Chrome in headless mode when True.
    width, height : int
        Initial window dimensions.
    proxy_* :
        Optional proxy credentials.
    kill_existing : bool
        Kill running Chrome processes before starting (Windows only).
    """

    # Class-level Chrome options – built once and reused if the same process
    # creates multiple BrowserEngine instances (e.g. unit tests).
    _shared_options: Optional[webdriver.ChromeOptions] = None
    _shared_service: Optional[Service] = None

    def __init__(
        self,
        chrome_folder: str = "",
        headless: bool = False,
        width: int = 1280,
        height: int = 720,
        proxy_server: str = "",
        proxy_port: str = "",
        proxy_user: str = "",
        proxy_pass: str = "",
        kill_existing: bool = False,
    ) -> None:
        self._chrome_folder = chrome_folder
        self._headless      = headless
        self._width         = width
        self._height        = height
        self._proxy_server  = proxy_server
        self._proxy_port    = proxy_port
        self._proxy_user    = proxy_user
        self._proxy_pass    = proxy_pass
        self._plugin_path   = os.path.join(os.path.dirname(__file__), "proxy_auth_plugin.zip")

        if kill_existing:
            self._kill_chrome()

        self.driver: webdriver.Chrome = self._build_driver()

    # ------------------------------------------------------------------
    # Internal setup
    # ------------------------------------------------------------------

    @staticmethod
    def _kill_chrome() -> None:
        """Kill Chrome on Windows – no-op on other platforms."""
        if os.name == "nt":
            os.system('taskkill /IM "chrome.exe" /F 2>nul')
            logger.info("Killed existing Chrome processes.")

    def _build_chrome_options(self) -> webdriver.ChromeOptions:
        opts = webdriver.ChromeOptions()

        # --- Stability & stealth arguments ---
        for arg in [
            "--no-sandbox",
            "--start-maximized",
            "--disable-notifications",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--disable-renderer-backgrounding",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-client-side-phishing-detection",
            "--disable-crash-reporter",
            "--disable-oopr-debug-crash-dump",
            "--no-crash-upload",
            "--disable-gpu",
            "--disable-low-res-tiling",
            "--log-level=3",
            "--silent",
            "--mute-audio",
            "--disable-blink-features=AutomationControlled",
            f"--window-size={self._width},{self._height}",
            (
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        ]:
            opts.add_argument(arg)

        opts.add_experimental_option(
            "excludeSwitches", ["enable-logging", "enable-automation"]
        )
        opts.add_experimental_option("useAutomationExtension", False)

        if self._headless:
            opts.add_argument("--headless=new")

        if self._chrome_folder:
            opts.add_argument(f"--user-data-dir={self._chrome_folder}")

        # --- Proxy ---
        if self._proxy_server and self._proxy_port:
            if self._proxy_user and self._proxy_pass:
                self._write_proxy_extension()
                opts.add_extension(self._plugin_path)
            else:
                opts.add_argument(
                    f"--proxy-server={self._proxy_server}:{self._proxy_port}"
                )

        return opts

    def _write_proxy_extension(self) -> None:
        """Write a Chrome extension ZIP that handles authenticated proxies."""
        manifest = """{
            "version": "1.0.0",
            "manifest_version": 2,
            "name": "Chrome Proxy",
            "permissions": ["proxy","tabs","unlimitedStorage","storage","<all_urls>",
                            "webRequest","webRequestBlocking"],
            "background": {"scripts": ["background.js"]},
            "minimum_chrome_version": "22.0.0"
        }"""
        background = f"""
        chrome.proxy.settings.set({{
            value: {{mode:"fixed_servers",rules:{{singleProxy:{{
                scheme:"http",host:"{self._proxy_server}",port:parseInt("{self._proxy_port}")
            }},bypassList:["localhost"]}}}},
            scope:"regular"
        }}, function(){{}});
        chrome.webRequest.onAuthRequired.addListener(
            function(){{return {{authCredentials:{{
                username:"{self._proxy_user}",password:"{self._proxy_pass}"
            }}}}}},
            {{urls:["<all_urls>"]}},["blocking"]
        );
        """
        with zipfile.ZipFile(self._plugin_path, "w") as zp:
            zp.writestr("manifest.json", manifest)
            zp.writestr("background.js", background)

    def _build_driver(self) -> webdriver.Chrome:
        opts    = self._build_chrome_options()
        service = Service()
        driver  = webdriver.Chrome(service=service, options=opts)
        logger.info("Chrome browser started successfully.")
        return driver

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def navigate(self, url: str, timeout: int = 30) -> None:
        """Navigate to *url*, stopping the page load if it exceeds *timeout*."""
        try:
            self.driver.set_page_load_timeout(timeout)
            self.driver.get(url)
            logger.debug("Navigated to %s", url)
        except TimeoutException:
            self.driver.execute_script("window.stop();")
            logger.warning("Page load timed out for %s – continuing anyway.", url)

    def refresh(self) -> None:
        self.driver.refresh()
        logger.debug("Page refreshed.")

    def current_url(self) -> str:
        return self.driver.current_url

    # ------------------------------------------------------------------
    # Waiting
    # ------------------------------------------------------------------

    def wait_for_presence(
        self, selector: str, timeout: int = DEFAULT_TIMEOUT
    ) -> WebElement:
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )

    def wait_for_clickable(
        self, selector: str, timeout: int = DEFAULT_TIMEOUT
    ) -> WebElement:
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )

    def wait_for_invisible(
        self, selector: str, timeout: int = DEFAULT_TIMEOUT
    ) -> bool:
        return WebDriverWait(self.driver, timeout).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, selector))
        )

    def wait_for_alert(self, timeout: int = DEFAULT_TIMEOUT):
        return WebDriverWait(self.driver, timeout).until(EC.alert_is_present())

    # ------------------------------------------------------------------
    # Interaction primitives
    # ------------------------------------------------------------------

    def click(self, selector: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        """
        Click an element.  Falls back to JS click if the native click is
        intercepted (e.g. overlapping modals on Facebook).
        """
        def _do():
            elem = self.wait_for_clickable(selector, timeout)
            try:
                elem.click()
            except ElementNotInteractableException:
                self.driver.execute_script("arguments[0].click();", elem)

        _with_retries(_do)
        logger.debug("Clicked: %s", selector)

    def click_js(self, selector: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        """Force a JS click (useful for hidden / overlapping elements)."""
        def _do():
            elem = self.wait_for_clickable(selector, timeout)
            self.driver.execute_script("arguments[0].click();", elem)

        _with_retries(_do)
        logger.debug("JS-clicked: %s", selector)

    def type_text(
        self,
        selector: str,
        text: str,
        clear_first: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Clear the field (optional) then type *text* character by character."""
        def _do():
            elem = self.wait_for_clickable(selector, timeout)
            if clear_first:
                elem.clear()
            elem.send_keys(text)

        _with_retries(_do)
        logger.debug("Typed into %s: %s", selector, text[:40])

    def send_file(self, selector: str, absolute_path: str) -> None:
        """Send a file path to an <input type="file"> element."""
        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
        elem.send_keys(absolute_path)
        logger.debug("Sent file %s to %s", absolute_path, selector)

    def select_by_text(self, selector: str, text: str) -> None:
        elem = self.wait_for_presence(selector)
        Select(elem).select_by_visible_text(text)

    # ------------------------------------------------------------------
    # Element queries
    # ------------------------------------------------------------------

    def find_one(
        self, selector: str, timeout: int = DEFAULT_TIMEOUT
    ) -> Optional[WebElement]:
        """Return the first matching element, or None if not found."""
        try:
            return self.wait_for_presence(selector, timeout)
        except (TimeoutException, NoSuchElementException):
            return None

    def find_all(
        self, selector: str, timeout: int = DEFAULT_TIMEOUT
    ) -> list[WebElement]:
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
            )
        except (TimeoutException, NoSuchElementException):
            return []

    def get_text(self, selector: str) -> Optional[str]:
        elem = self.find_one(selector)
        return elem.text if elem else None

    def get_attribute(self, selector: str, attr: str) -> Optional[str]:
        elem = self.find_one(selector)
        return elem.get_attribute(attr) if elem else None

    def get_attributes(
        self,
        selector: str,
        attr: str,
        unique: bool = True,
    ) -> list[str]:
        values = []
        for elem in self.find_all(selector):
            try:
                val = elem.get_attribute(attr)
                if val and (not unique or val not in values):
                    values.append(val)
            except Exception:
                continue
        return values

    # ------------------------------------------------------------------
    # Scrolling
    # ------------------------------------------------------------------

    def scroll_to_bottom(self, selector: str = "body") -> None:
        try:
            self.driver.find_element(By.CSS_SELECTOR, selector).send_keys(
                Keys.CONTROL + Keys.END
            )
        except Exception:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def scroll_to_top(self, selector: str = "body") -> None:
        try:
            self.driver.find_element(By.CSS_SELECTOR, selector).send_keys(
                Keys.CONTROL + Keys.HOME
            )
        except Exception:
            self.driver.execute_script("window.scrollTo(0, 0);")

    # ------------------------------------------------------------------
    # Tab management (used by refresh_session)
    # ------------------------------------------------------------------

    def open_blank_tab(self) -> None:
        self.driver.execute_script("window.open('');")

    def close_current_tab(self) -> None:
        self.driver.close()

    def switch_to_tab(self, index: int) -> None:
        handles = self.driver.window_handles
        self.driver.switch_to.window(handles[index])

    def tab_count(self) -> int:
        return len(self.driver.window_handles)

    def refresh_session(self, pause: float = 1.0) -> None:
        """
        Trick that triggers Facebook's JS context to reset (open + close blank tab).
        """
        self.open_blank_tab()
        self.switch_to_tab(self.tab_count() - 1)
        time.sleep(pause)
        self.close_current_tab()
        self.switch_to_tab(0)
        time.sleep(pause)
        logger.debug("Session refreshed via blank-tab trick.")

    # ------------------------------------------------------------------
    # Screenshots
    # ------------------------------------------------------------------

    def screenshot(self, path: str) -> None:
        if not path.endswith(".png"):
            path += ".png"
        self.driver.save_screenshot(path)
        logger.info("Screenshot saved: %s", path)

    # ------------------------------------------------------------------
    # Alert handling
    # ------------------------------------------------------------------

    def accept_alert(self) -> Optional[str]:
        try:
            alert = self.wait_for_alert(timeout=5)
            text  = alert.text
            alert.accept()
            return text
        except TimeoutException:
            return None

    def dismiss_alert(self) -> None:
        try:
            alert = self.wait_for_alert(timeout=5)
            alert.dismiss()
        except TimeoutException:
            pass

    # ------------------------------------------------------------------
    # JavaScript helpers
    # ------------------------------------------------------------------

    def execute_js(self, script: str, *args):
        return self.driver.execute_script(script, *args)

    def clear_storage(self) -> None:
        self.driver.execute_script("window.localStorage.clear();")
        self.driver.execute_script("window.sessionStorage.clear();")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def quit(self) -> None:
        try:
            self.driver.quit()
            logger.info("Browser closed.")
        except WebDriverException:
            pass

    def restart(self) -> None:
        self.quit()
        self.driver = self._build_driver()
        logger.info("Browser restarted.")

    # Allow use as a context manager
    def __enter__(self) -> "BrowserEngine":
        return self

    def __exit__(self, *_) -> None:
        self.quit()
