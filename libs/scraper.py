"""
scraper.py — Facebook Groups automation.

Responsibilities:
  - save_groups  : Search Facebook by keyword and persist group URLs.
  - post_in_groups  : Publish one post (text + optional image) per group.
  - post_in_groupsx : Publish multi-image posts per group.

Design decisions:
  - All side-effects (navigation, clicks, uploads) are delegated to BrowserEngine.
  - Every public method catches *all* exceptions so a bad group never kills the run.
  - Failed groups are logged and screenshots are captured automatically.
  - Image uploads are sequential (not threaded) because Facebook's dialog
    only accepts one file-input interaction at a time; threading caused races.
  - WAIT_MIN delay between groups is fully configurable via .env.
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
from datetime import datetime
from mimetypes import guess_type
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from selenium.common.exceptions import TimeoutException

from libs.browser import BrowserEngine

# ---------------------------------------------------------------------------
# Environment / configuration
# ---------------------------------------------------------------------------

load_dotenv()

CHROME_FOLDER:   str = os.getenv("CHROME_FOLDER", "")
PROFILE:         str = os.getenv("PROFILE", "")
WAIT_MIN:        int = int(os.getenv("WAIT_MIN", "2"))      # minutes between posts
SCREENSHOT_DIR:  str = os.getenv("SCREENSHOT_DIR", "screenshots")
LOG_DIR:         str = os.getenv("LOG_DIR", "logs")

# ---------------------------------------------------------------------------
# Logging  (file + console)
# ---------------------------------------------------------------------------

Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
Path(SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)

_log_file = Path(LOG_DIR) / f"scraper_{datetime.now():%Y%m%d}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(_log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

class Scraper:
    """
    Facebook Groups automation scraper.

    Usage::

        scraper = Scraper()
        scraper.save_groups("hydraulic press")
        scraper.post_in_groups()
    """

    def __init__(self) -> None:
        # ── Data files ──────────────────────────────────────────────────
        self._data_path  = _ROOT / "data.json"
        self._datax_path = _ROOT / "data1.json"
        self._sel_path   = _ROOT / "config" / "selectors.json"

        self.data:      dict = self._load_json(self._data_path)
        self.datax:     dict = self._load_json(self._datax_path)
        self.selectors: dict = self._load_json(self._sel_path)

        self._validate_config()

        # ── Browser ─────────────────────────────────────────────────────
        self.browser = BrowserEngine(
            chrome_folder=CHROME_FOLDER,
            kill_existing=True,
        )

        # ── Stats ────────────────────────────────────────────────────────
        self._stats = {"success": 0, "failed": 0, "skipped": 0}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_groups(self, keyword: str) -> list[str]:
        """
        Search Facebook for groups matching *keyword* and persist them to
        ``data.json``.  Returns the list of discovered URLs.
        """
        logger.info("Searching groups for keyword: '%s'", keyword)
        url = f"https://www.facebook.com/groups/search/groups/?q={keyword}"
        self.browser.navigate(url)
        time.sleep(3)

        # Scroll until no new results appear (3 consecutive unchanged counts).
        prev_count  = 0
        stable_hits = 0
        selector    = self.selectors["group_link"]

        while stable_hits < 3:
            self.browser.scroll_to_bottom()
            time.sleep(1.5)
            new_count = len(self.browser.find_all(selector))
            if new_count == prev_count:
                stable_hits += 1
            else:
                prev_count  = new_count
                stable_hits = 0
                self.browser.refresh_session()

        links = self.browser.get_attributes(selector, "href", unique=True)
        logger.info("%d groups found.", len(links))

        if links:
            self.data["groups"] = links
            self._save_json(self._data_path, self.data)

        return links

    def post_in_groups(self) -> None:
        """Post one random post (single image) in every saved group."""
        groups = self.data.get("groups", [])
        posts  = self.data.get("posts",  [])

        if not groups:
            logger.error("No groups in data.json — run save_groups first.")
            return
        if not posts:
            logger.error("No posts in data.json.")
            return

        for group_url in groups:
            post = random.choice(posts)
            images = []
            if post.get("image"):
                img = self._resolve_path(post["image"])
                if self._is_valid_image(img):
                    images = [img]

            self._post_in_group(
                group_url=group_url,
                text=post["text"],
                images=images,
            )

        self._log_summary()

    def post_in_groupsx(self) -> None:
        """Post multi-image posts (from data1.json) in every saved group."""
        groups = self.data.get("groups", [])
        posts  = self.datax.get("posts",  [])

        if not groups:
            logger.error("No groups in data.json.")
            return
        if not posts:
            logger.error("No posts in data1.json.")
            return

        for group_url in groups:
            post   = random.choice(posts)
            images = [
                self._resolve_path(img)
                for img in post.get("images", [])
                if self._is_valid_image(self._resolve_path(img))
            ]
            self._post_in_group(
                group_url=group_url,
                text=post["text"],
                images=images,
            )

        self._log_summary()

    # ------------------------------------------------------------------
    # Core posting logic
    # ------------------------------------------------------------------

    def _post_in_group(
        self,
        group_url: str,
        text: str,
        images: list[str],
    ) -> None:
        """
        Attempt to publish *text* (and optional *images*) in *group_url*.

        The method is structured as a pipeline of steps.  Each step that
        fails logs the error and returns early; the next group is tried on
        the next loop iteration.
        """
        logger.info("▶  Posting in: %s", group_url)

        try:
            # 1. Navigate
            self.browser.navigate(group_url)
            self._random_sleep(4, 6)
            self.browser.refresh_session()

            # 2. Open the post composer
            if not self._safe_click("display_input", "composer trigger"):
                self._handle_failed_group(group_url, "composer trigger not found")
                return

            self._random_sleep(1, 2)

            # 3. Type the post text
            if not self._safe_type("input", text, "post text area"):
                self._handle_failed_group(group_url, "text area not found")
                return

            # 4. Upload images (optional – failure falls back to theme)
            if images:
                uploaded = self._upload_images(images)
                if not uploaded:
                    logger.warning("Image upload failed – applying random theme instead.")
                    self._apply_random_theme()

            # 5. Submit
            if not self._safe_click("submit", "submit button"):
                self._handle_failed_group(group_url, "submit button not found")
                return

            # 6. Post-publish actions
            logger.info("✔  Posted successfully in %s", group_url)
            self._stats["success"] += 1

            self._random_sleep(12, 18)
            self._add_comment()
            self._wait_between_groups()

        except Exception as exc:
            self._handle_failed_group(group_url, str(exc))

    # ------------------------------------------------------------------
    # Image upload
    # ------------------------------------------------------------------

    def _upload_images(self, paths: list[str]) -> bool:
        """
        Upload one or more images sequentially.
        Returns True if at least one image was uploaded successfully.
        """
        any_success = False
        for path in paths:
            try:
                self._safe_click("show_image_input", "photo/video button")
                self._random_sleep(1, 2)
                self.browser.send_file(self.selectors["add_image"], path)
                self._random_sleep(1, 2)
                any_success = True
                logger.debug("Uploaded: %s", path)
            except Exception as exc:
                logger.warning("Failed to upload %s: %s", path, exc)
        return any_success

    # ------------------------------------------------------------------
    # Comment
    # ------------------------------------------------------------------

    def _add_comment(self) -> None:
        """
        Try to post a random comment.  Never raises — comment failure is
        non-critical.
        """
        comments = [
            "Super !",
            "Merci pour le partage !",
            "Très intéressant !",
            "Top !",
            "J'aime beaucoup ce contenu.",
        ]
        try:
            comment_sel = self.selectors.get("comment_input")
            submit_sel  = self.selectors.get("submit_comment")
            if not comment_sel or not submit_sel:
                return

            elem = self.browser.find_one(comment_sel, timeout=8)
            if not elem:
                return

            elem.click()
            elem.send_keys(random.choice(comments))
            self._random_sleep(1, 2)
            self._safe_click_js("submit_comment", "submit comment")
        except Exception as exc:
            logger.debug("Comment step skipped: %s", exc)

    # ------------------------------------------------------------------
    # Theme fallback
    # ------------------------------------------------------------------

    def _apply_random_theme(self) -> None:
        try:
            self._safe_click_js("display_themes", "themes panel")
            self._random_sleep(0.5, 1)
            theme_sel = self.selectors["theme"].replace(
                "index", str(random.randint(1, 5))
            )
            self.browser.click_js(theme_sel)
        except Exception as exc:
            logger.debug("Theme application skipped: %s", exc)

    # ------------------------------------------------------------------
    # Safe interaction wrappers (return bool instead of raising)
    # ------------------------------------------------------------------

    def _safe_click(self, key: str, description: str) -> bool:
        try:
            self.browser.click(self.selectors[key])
            return True
        except Exception as exc:
            logger.warning("Cannot click '%s': %s", description, exc)
            return False

    def _safe_click_js(self, key: str, description: str) -> bool:
        try:
            self.browser.click_js(self.selectors[key])
            return True
        except Exception as exc:
            logger.warning("Cannot JS-click '%s': %s", description, exc)
            return False

    def _safe_type(self, key: str, text: str, description: str) -> bool:
        try:
            self.browser.type_text(self.selectors[key], text, clear_first=False)
            return True
        except Exception as exc:
            logger.warning("Cannot type into '%s': %s", description, exc)
            return False

    # ------------------------------------------------------------------
    # Error / diagnostic helpers
    # ------------------------------------------------------------------

    def _handle_failed_group(self, group_url: str, reason: str) -> None:
        self._stats["failed"] += 1
        logger.error("✘  Failed (%s): %s", reason, group_url)
        # Capture screenshot for post-mortem debugging
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = Path(SCREENSHOT_DIR) / f"error_{ts}.png"
        try:
            self.browser.screenshot(str(name))
        except Exception:
            pass

    def _log_summary(self) -> None:
        s = self._stats
        logger.info(
            "Run complete — ✔ %d success | ✘ %d failed | ⏭  %d skipped",
            s["success"], s["failed"], s["skipped"],
        )

    # ------------------------------------------------------------------
    # Timing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _random_sleep(min_s: float = 1.0, max_s: float = 3.0) -> None:
        time.sleep(random.uniform(min_s, max_s))

    def _wait_between_groups(self) -> None:
        wait_s = random.uniform(WAIT_MIN * 60, WAIT_MIN * 70)
        logger.info("Waiting %.0f seconds before next group …", wait_s)
        time.sleep(wait_s)

    # ------------------------------------------------------------------
    # Path / file helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_path(raw: str) -> str:
        """
        Accept both absolute Windows paths (from data.json) and relative
        paths (relative to the project root).
        """
        p = Path(raw)
        if p.is_absolute():
            return str(p)
        resolved = _ROOT / raw
        return str(resolved)

    @staticmethod
    def _is_valid_image(path: str) -> bool:
        if not Path(path).exists():
            logger.warning("Image not found: %s", path)
            return False
        mime, _ = guess_type(path)
        return bool(mime and mime.startswith("image"))

    # ------------------------------------------------------------------
    # JSON helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_json(path: Path) -> dict:
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except FileNotFoundError:
            logger.warning("File not found: %s — using empty dict.", path)
            return {}
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in %s: %s", path, exc)
            return {}

    @staticmethod
    def _save_json(path: Path, data: dict) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=4)
        logger.info("Saved: %s", path)

    # ------------------------------------------------------------------
    # Startup validation
    # ------------------------------------------------------------------

    def _validate_config(self) -> None:
        """Warn early about missing or obviously wrong configuration."""
        if not self.data.get("groups"):
            logger.warning(
                "data.json has no 'groups' — run option 1 (Save groups) first."
            )
        if not self.data.get("posts"):
            logger.warning("data.json has no 'posts' — add posts before running.")
        if not self.selectors:
            raise RuntimeError("config/selectors.json is empty or missing.")

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "Scraper":
        return self

    def __exit__(self, *_) -> None:
        self.browser.quit()
