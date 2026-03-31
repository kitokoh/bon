"""
playwright_engine.py — Moteur Playwright (remplace Selenium / automate.py)
Interface propre, cross-platform, sans taskkill ni WMIC.
"""
import pathlib
import sys
from typing import Optional

try:
    from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("[ERROR] Playwright non installé. Lancez : playwright install chromium")

try:
    from libs.log_emitter import emit
    from libs.config_manager import LOGS_DIR
except ImportError:
    from log_emitter import emit
    from config_manager import LOGS_DIR

SCREENSHOTS_DIR = LOGS_DIR / "errors"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class PlaywrightEngine:
    """
    Moteur navigateur Playwright.
    Gère le cycle de vie du browser, des contexts et des pages.
    
    Usage :
        engine = PlaywrightEngine(headless=False)
        engine.start()
        context, page = engine.new_context(storage_state="sessions/compte1_state.json")
        # ... travail ...
        engine.stop()
    """

    def __init__(
        self,
        headless: bool = False,
        proxy: Optional[dict] = None,
        slow_mo: int = 50,
    ):
        """
        Args:
            headless: True = mode invisible, False = fenêtre visible
            proxy: dict Playwright proxy, ex: {"server": "http://host:port",
                                               "username": "u", "password": "p"}
            slow_mo: délai en ms entre chaque action Playwright (simule vitesse humaine)
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright n'est pas installé. Exécutez : playwright install chromium")

        self.headless = headless
        self.proxy = proxy
        self.slow_mo = slow_mo
        self._playwright = None
        self._browser: Optional[Browser] = None

    def start(self) -> None:
        """Démarre le navigateur Playwright."""
        emit("INFO", "BROWSER_STARTING",
             headless=self.headless, proxy=bool(self.proxy))
        self._playwright = sync_playwright().start()
        launch_opts = {
            "headless": self.headless,
            "slow_mo": self.slow_mo,
        }
        if self.proxy:
            launch_opts["proxy"] = self.proxy

        self._browser = self._playwright.chromium.launch(**launch_opts)
        emit("SUCCESS", "BROWSER_STARTED")

    def stop(self) -> None:
        """Arrête proprement le navigateur (cross-platform, pas de taskkill)."""
        try:
            if self._browser:
                self._browser.close()
                self._browser = None
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
            emit("INFO", "BROWSER_STOPPED")
        except Exception as e:
            emit("WARN", "BROWSER_STOP_ERROR", error=str(e))

    def new_context(
        self,
        storage_state: Optional[str] = None,
        viewport: dict = None,
    ) -> tuple:
        """
        Crée un nouveau contexte navigateur (1 contexte = 1 compte).

        Args:
            storage_state: chemin vers le fichier de session Playwright
            viewport: dict {"width": 1280, "height": 720}

        Returns:
            (BrowserContext, Page)
        """
        if not self._browser:
            raise RuntimeError("Browser non démarré. Appelez start() d'abord.")

        viewport = viewport or {"width": 1280, "height": 720}
        opts = {
            "viewport": viewport,
            "locale": "fr-FR",
            "timezone_id": "Europe/Paris",
        }
        if storage_state and pathlib.Path(storage_state).exists():
            opts["storage_state"] = storage_state
            emit("INFO", "CONTEXT_WITH_SESSION", state=storage_state)
        else:
            emit("INFO", "CONTEXT_NEW_ANONYMOUS")

        context = self._browser.new_context(**opts)

        # Bloquer les ressources inutiles (images, fonts) pour aller plus vite
        # Commenté par défaut car Facebook en a besoin pour certaines interactions
        # context.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2}", lambda route: route.abort())

        page = context.new_page()
        return context, page

    def screenshot_on_error(self, page: Page, error_name: str) -> Optional[str]:
        """Prend un screenshot automatique en cas d'erreur."""
        try:
            path = str(SCREENSHOTS_DIR / f"err_{error_name}.png")
            page.screenshot(path=path)
            emit("INFO", "SCREENSHOT_SAVED", path=path)
            return path
        except Exception as e:
            emit("WARN", "SCREENSHOT_FAILED", error=str(e))
            return None

    def navigate(self, page: Page, url: str, wait_until: str = "domcontentloaded") -> bool:
        """
        Navigue vers une URL de façon sécurisée.
        
        Returns:
            True si navigation réussie, False sinon
        """
        try:
            page.goto(url, wait_until=wait_until, timeout=30000)
            emit("INFO", "NAVIGATING", url=url[:80])
            return True
        except Exception as e:
            emit("ERROR", "NAVIGATION_FAILED", url=url[:80], error=str(e))
            self.screenshot_on_error(page, "navigation_failed")
            return False

    def fill_field(self, page: Page, selector: str, text: str) -> bool:
        """Remplit un champ de texte de façon sécurisée."""
        try:
            page.fill(selector, text)
            return True
        except Exception as e:
            emit("ERROR", "FILL_FIELD_FAILED", selector=selector[:60], error=str(e))
            return False

    def click(self, page: Page, selector: str, timeout: int = 10000) -> bool:
        """Clique sur un élément de façon sécurisée."""
        try:
            page.click(selector, timeout=timeout)
            return True
        except Exception as e:
            emit("ERROR", "CLICK_FAILED", selector=selector[:60], error=str(e))
            self.screenshot_on_error(page, "click_failed")
            return False

    def send_file(self, page: Page, selector: str, file_path: str) -> bool:
        """Upload un fichier (image) via un input[type=file]."""
        try:
            page.set_input_files(selector, file_path)
            return True
        except Exception as e:
            emit("ERROR", "FILE_UPLOAD_FAILED", file=file_path, error=str(e))
            return False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
