"""
scraper.py — Logique métier Facebook (publication groupes, marketplace, commentaires)
Composition avec PlaywrightEngine — aucun héritage, cross-platform, sans Selenium.
"""
import random
import time
import pathlib
from typing import Optional, List

from libs.playwright_engine import PlaywrightEngine
from libs.selector_registry import SelectorRegistry, SelectorNotFound
from libs.timing_humanizer import (
    human_delay, human_delay_between_groups,
    post_publication_wait, random_scroll, human_scroll_to_bottom
)
from libs.error_handlers import (
    retry, check_page_state, check_group_accessible,
    SessionExpiredError, FacebookBlockedError,
    RateLimitError, CaptchaDetectedError
)
from libs.log_emitter import emit
from libs.config_manager import resolve_media_path

# Commentaires aléatoires par défaut (personnalisables via config)
DEFAULT_COMMENTS = [
    "Super post !",
    "Merci pour le partage !",
    "Très intéressant !",
    "Top !",
    "J'aime beaucoup ce contenu.",
    "Excellent partage !",
    "Merci !",
]


class Scraper:
    """
    Publie des posts dans des groupes Facebook et gère les interactions.

    Utilise composition avec PlaywrightEngine (pas d'héritage).
    Reçoit engine, selectors et session_config en paramètre → testable et modulaire.
    """

    def __init__(
        self,
        engine: PlaywrightEngine,
        selectors: SelectorRegistry,
        session_config: dict,
        session_name: str,
    ):
        self.engine       = engine
        self.selectors    = selectors
        self.config       = session_config
        self.session_name = session_name
        self._context     = None
        self._page        = None

    # ──────────────────────────────────────────
    # Cycle de vie du contexte
    # ──────────────────────────────────────────

    def open(self) -> None:
        """Ouvre le contexte navigateur avec la session du compte."""
        storage_state = self.config.get("storage_state", "")
        self._context, self._page = self.engine.new_context(
            storage_state=storage_state
        )
        emit("INFO", "SESSION_START", compte=self.session_name)

    def close(self) -> None:
        """Ferme le contexte navigateur proprement."""
        try:
            if self._context:
                self._context.close()
                self._context = None
                self._page    = None
            emit("INFO", "SESSION_END", compte=self.session_name)
        except Exception as e:
            emit("WARN", "SESSION_CLOSE_ERROR", error=str(e))

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *_):
        self.close()

    # ──────────────────────────────────────────
    # Publication dans les groupes (mode simple — 1 image)
    # ──────────────────────────────────────────

    def post_in_groups(self) -> dict:
        """
        Publie un post aléatoire dans chaque groupe configuré.
        Mode : 1 image par post (ou thème si pas d'image).

        Returns:
            dict {"success": N, "skipped": N, "errors": N}
        """
        return self._run_groups_loop(multi_image=False)

    # ──────────────────────────────────────────
    # Publication multi-images (post_in_groupsx)
    # ──────────────────────────────────────────

    def post_in_groups_multi(self) -> dict:
        """
        Publie un post avec plusieurs images dans chaque groupe.
        Équivalent de l'ancien post_in_groupsx().

        Returns:
            dict {"success": N, "skipped": N, "errors": N}
        """
        return self._run_groups_loop(multi_image=True)

    def _run_groups_loop(self, multi_image: bool = False) -> dict:
        """Boucle commune pour post_in_groups et post_in_groups_multi."""
        groups     = self.config.get("groups", [])
        posts      = self.config.get("posts", [])
        max_groups = int(self.config.get("max_groups_per_run", 10))
        delay_cfg  = self.config.get("delay_between_groups", [60, 120])

        if not groups:
            emit("WARN", "NO_GROUPS_CONFIGURED", compte=self.session_name)
            return {"success": 0, "skipped": 0, "errors": 0}
        if not posts:
            emit("WARN", "NO_POSTS_CONFIGURED", compte=self.session_name)
            return {"success": 0, "skipped": 0, "errors": 0}

        groups_to_process = groups[:max_groups]
        if len(groups) > max_groups:
            emit("INFO", "GROUPS_LIMITED", total=len(groups), processing=max_groups)

        stats = {"success": 0, "skipped": 0, "errors": 0}

        for idx, group_url in enumerate(groups_to_process, 1):
            post      = self._pick_post(posts)
            post_text = post.get("text", "")

            # Images : liste (multi) ou image unique
            if multi_image:
                images = self._resolve_images_list(
                    post.get("images", []) or ([post.get("image")] if post.get("image") else [])
                )
            else:
                single = post.get("image") or (post.get("images", [""])[0] if post.get("images") else "")
                images = self._resolve_images_list([single]) if single else []

            emit("INFO", "GROUP_START",
                 compte=self.session_name,
                 group=idx, total=len(groups_to_process),
                 url=group_url, images=len(images))

            try:
                success = self._post_in_group(group_url, post_text, images)
                if success:
                    stats["success"] += 1
                    # Commentaires optionnels post-publication
                    if self.config.get("add_comments", False):
                        self._add_comment_after_post()
                else:
                    stats["skipped"] += 1
            except (SessionExpiredError, FacebookBlockedError, RateLimitError) as e:
                emit("ERROR", "CRITICAL_STOPPING", compte=self.session_name, error=str(e))
                stats["errors"] += 1
                break
            except Exception as e:
                emit("ERROR", "GROUP_ERROR", groupe=group_url[:80], error=str(e))
                self.engine.screenshot_on_error(self._page, f"group_err_{idx}")
                stats["errors"] += 1

            # Délai entre groupes (sauf dernier)
            if idx < len(groups_to_process):
                human_delay_between_groups(
                    min_s=float(delay_cfg[0]),
                    max_s=float(delay_cfg[1])
                )

        emit("INFO", "SESSION_STATS", compte=self.session_name, **stats)
        return stats

    # ──────────────────────────────────────────
    # _post_in_group — cœur de la publication
    # ──────────────────────────────────────────

    @retry(max_attempts=3, delay=4, backoff=2)
    def _post_in_group(self, group_url: str, post_text: str,
                       images: List[str]) -> bool:
        """
        Publie un post dans un groupe Facebook. Retryable 3×.

        Args:
            group_url: URL complète du groupe
            post_text: Texte du post
            images:    Liste de chemins absolus d'images (peut être vide)

        Returns:
            True si publié, False si groupe ignoré
        """
        page = self._page

        # — Navigation —
        if not self.engine.navigate(page, group_url):
            return False
        human_delay(2.5, 0.8)

        # — État de la page —
        check_page_state(page)
        if not check_group_accessible(page):
            emit("WARN", "GROUP_SKIPPED_INACCESSIBLE", url=group_url[:80])
            return False

        # — Ouvrir la zone de saisie —
        try:
            btn = self.selectors.find(page, "display_input", timeout=10000)
            btn.click()
        except SelectorNotFound:
            emit("WARN", "DISPLAY_INPUT_NOT_FOUND", url=group_url[:80])
            return False
        human_delay(1.5, 0.5)

        # — Vérifier l'état après le clic (popup login possible) —
        check_page_state(page)

        # — Saisie du texte —
        try:
            field = self.selectors.find(page, "input", timeout=8000)
            field.click()
            # press_sequentially = API Playwright correcte (pas de boucle manuell)
            field.press_sequentially(post_text, delay=random.randint(40, 160))
            human_delay(1.0, 0.3)
        except SelectorNotFound:
            emit("WARN", "INPUT_NOT_FOUND", url=group_url[:80])
            return False

        # — Upload images —
        if images:
            uploaded = self._upload_images_sequential(page, images)
            if not uploaded:
                # Fallback : appliquer un thème coloré
                self._apply_theme(page)
        elif not images:
            # Pas d'image → essayer un thème si texte court
            if len(post_text) < 120:
                self._apply_theme(page)

        # — Soumettre —
        try:
            submit = self.selectors.find(page, "submit", timeout=10000)
            submit.click()
            post_publication_wait()
            emit("SUCCESS", "POST_PUBLISHED",
                 compte=self.session_name,
                 groupe=group_url[:80],
                 preview=post_text[:60])
            return True
        except SelectorNotFound:
            emit("ERROR", "SUBMIT_NOT_FOUND", url=group_url[:80])
            self.engine.screenshot_on_error(page, "submit_missing")
            return False

    # ──────────────────────────────────────────
    # Upload images (séquentiel, thread-safe)
    # ──────────────────────────────────────────

    def _upload_images_sequential(self, page, images: List[str]) -> bool:
        """
        Upload des images une par une (séquentiel = thread-safe avec Playwright).
        Jusqu'à 30 images maximum (limite Facebook).

        Returns:
            True si au moins 1 image uploadée avec succès
        """
        images = images[:30]  # limite Facebook
        uploaded_count = 0

        try:
            # Ouvrir le sélecteur d'images
            show_btn = self.selectors.find(page, "show_image_input", timeout=6000)
            show_btn.click()
            human_delay(1.2, 0.4)
        except SelectorNotFound:
            emit("WARN", "SHOW_IMAGE_BTN_NOT_FOUND")
            return False

        for img_path in images:
            if not pathlib.Path(img_path).exists():
                emit("WARN", "IMAGE_SKIP_NOT_FOUND", path=img_path)
                continue
            try:
                # Playwright gère nativement le file chooser
                add_sel = self.selectors.get_candidates("add_image")
                if add_sel:
                    page.set_input_files(add_sel[0], img_path)
                    human_delay(1.5, 0.5)
                    uploaded_count += 1
                    emit("DEBUG", "IMAGE_UPLOADED", path=img_path[-50:])
            except Exception as e:
                emit("WARN", "IMAGE_UPLOAD_FAIL", path=img_path[-50:], error=str(e))

        emit("INFO", "IMAGES_UPLOAD_DONE",
             requested=len(images), uploaded=uploaded_count)
        return uploaded_count > 0

    # ──────────────────────────────────────────
    # Thème (fallback si pas d'image)
    # ──────────────────────────────────────────

    def _apply_theme(self, page) -> None:
        """Applique un thème coloré si aucune image disponible."""
        try:
            theme_btn = self.selectors.find(page, "display_themes", timeout=4000)
            theme_btn.click()
            human_delay(0.8, 0.2)
            # Sélectionner un thème aléatoire parmi les 5 premiers
            theme_idx = random.randint(1, 5)
            candidates = self.selectors.get_candidates("theme")
            if candidates:
                sel = candidates[0].replace("index", str(theme_idx))
                page.click(sel, timeout=3000)
                emit("DEBUG", "THEME_APPLIED", index=theme_idx)
        except Exception as e:
            emit("WARN", "THEME_SKIP", reason=str(e))

    # ──────────────────────────────────────────
    # Commentaires post-publication
    # ──────────────────────────────────────────

    def _add_comment_after_post(self) -> None:
        """
        Ajoute un commentaire aléatoire après la publication.
        Activable via "add_comments": true dans la config de session.
        Les commentaires personnalisés sont dans "comments": [...].
        """
        page     = self._page
        comments = self.config.get("comments", DEFAULT_COMMENTS)
        if not comments:
            return

        comment = random.choice(comments)
        human_delay(3, 1)  # attendre que le post soit visible

        try:
            comment_input = self.selectors.find(page, "comment_input", timeout=8000)
            comment_input.click()
            human_delay(0.5, 0.2)
            comment_input.press_sequentially(comment, delay=random.randint(40, 130))
            human_delay(0.5, 0.2)

            # Soumettre avec Entrée (méthode standard Facebook)
            comment_input.press("Enter")
            human_delay(2, 0.5)
            emit("SUCCESS", "COMMENT_ADDED",
                 compte=self.session_name,
                 preview=comment[:40])
        except SelectorNotFound:
            emit("WARN", "COMMENT_INPUT_NOT_FOUND")
        except Exception as e:
            emit("WARN", "COMMENT_FAILED", error=str(e))

    # ──────────────────────────────────────────
    # Sauvegarde des groupes
    # ──────────────────────────────────────────

    def save_groups(self, keyword: str) -> List[str]:
        """
        Recherche les groupes Facebook pour un mot-clé et retourne les URLs.

        Returns:
            Liste dédupliquée des URLs de groupes trouvées
        """
        page       = self._page
        search_url = f"https://www.facebook.com/groups/search/groups/?q={keyword}"
        emit("INFO", "SAVE_GROUPS_START", keyword=keyword)

        if not self.engine.navigate(page, search_url):
            return []

        human_delay(3.0, 0.8)
        check_page_state(page)

        # Scroll jusqu'à stabilisation de la page
        human_scroll_to_bottom(page, stable_count=3)

        # Extraire les URLs via le sélecteur group_link
        links = []
        try:
            elements = self.selectors.find_all(page, "group_link")
            for el in elements:
                href = el.get_attribute("href")
                if href and "facebook.com/groups/" in href:
                    clean = href.split("?")[0].rstrip("/") + "/"
                    links.append(clean)
        except Exception as e:
            emit("WARN", "GROUP_LINK_EXTRACT_ERROR", error=str(e))

        # Dédupliquer en préservant l'ordre
        links = list(dict.fromkeys(links))
        emit("SUCCESS", "GROUPS_SAVED", keyword=keyword, count=len(links))

        self.config["groups"] = links
        return links

    # ──────────────────────────────────────────
    # Marketplace
    # ──────────────────────────────────────────

    @retry(max_attempts=2, delay=5)
    def post_in_marketplace(self) -> bool:
        """
        Publie une annonce dans Facebook Marketplace.
        Configuration dans la clé "marketplace" de la config session.

        Returns:
            True si publié, False sinon
        """
        mkt = self.config.get("marketplace", {})
        if not mkt:
            emit("WARN", "MARKETPLACE_NOT_CONFIGURED", compte=self.session_name)
            return False

        page = self._page
        emit("INFO", "MARKETPLACE_START", compte=self.session_name)

        if not self.engine.navigate(page, "https://www.facebook.com/marketplace/create/item"):
            return False
        human_delay(3.0, 1.0)
        check_page_state(page)

        try:
            # Titre
            title = random.choice(mkt.get("titles", ["Produit"]))
            title_field = self.selectors.find(page, "marketplace_title", timeout=8000)
            title_field.click()
            title_field.press_sequentially(title, delay=random.randint(50, 150))
            human_delay(0.8, 0.2)

            # Prix
            price = str(mkt.get("price", "1"))
            price_field = self.selectors.find(page, "marketplace_price", timeout=6000)
            price_field.click()
            price_field.press_sequentially(price, delay=random.randint(80, 180))
            human_delay(0.5, 0.2)

            # Description
            desc = random.choice(mkt.get("descriptions", ["Description"]))
            desc_field = self.selectors.find(page, "marketplace_description", timeout=6000)
            desc_field.click()
            desc_field.press_sequentially(desc, delay=random.randint(40, 130))
            human_delay(1.0, 0.3)

            # Images Marketplace
            mkt_images = self._resolve_images_list(mkt.get("images", []))
            if mkt_images:
                try:
                    add_photos = self.selectors.find(page, "marketplace_add_photos", timeout=5000)
                    add_photos.click()
                    human_delay(1, 0.3)
                    page.set_input_files("input[type='file']", mkt_images[:10])
                    human_delay(3, 1)
                except SelectorNotFound:
                    emit("WARN", "MARKETPLACE_PHOTOS_BTN_NOT_FOUND")

            # Soumettre
            submit = self.selectors.find(page, "marketplace_submit", timeout=8000)
            submit.click()
            human_delay(3, 1)

            emit("SUCCESS", "MARKETPLACE_PUBLISHED",
                 compte=self.session_name, titre=title)
            return True

        except SelectorNotFound as e:
            emit("ERROR", "MARKETPLACE_SELECTOR_MISSING",
                 compte=self.session_name, error=str(e))
            self.engine.screenshot_on_error(page, "marketplace_error")
            return False

    # ──────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────

    @staticmethod
    def _pick_post(posts: list) -> dict:
        """Sélection aléatoire pondérée d'un post (champ 'weight')."""
        if not posts:
            return {}
        weights = [max(1, p.get("weight", 1)) for p in posts]
        return random.choices(posts, weights=weights, k=1)[0]

    def _resolve_images_list(self, images: List[str]) -> List[str]:
        """
        Résout et filtre une liste de chemins d'images.
        Gère les chemins Windows legacy, relatifs et absolus.

        Returns:
            Liste de chemins absolus existants
        """
        resolved = []
        for img in images:
            if not img:
                continue
            p = resolve_media_path(img, self.session_name)
            if p.exists():
                resolved.append(str(p))
            else:
                emit("WARN", "IMAGE_NOT_FOUND", path=str(p))
        return resolved
