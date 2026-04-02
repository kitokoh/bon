"""
scraper.py v11 — Logique métier Facebook : publication, commentaires, abonnement

Nouveautés v9 :
  - Modèle Robot (robot_name remplace session_name partout)
  - post_in_groups() : anti-doublon strict via db.was_published_recently()
  - _post_text_only() : post texte seul avec sélection couleur fond FB
  - _post_with_images() : 1 ou plusieurs images + caption (avec captcha optionnel)
  - _select_bg_color() : sélectionne la couleur de fond proposée par FB
  - _build_post_text() : construit le texte = variant_text + caption_média (si captcha)
  - subscribe_if_needed() : auto-abonnement avant publication
  - post_comment_after_publish() : commente sous le post créé ou existant
  - pick_media_for_post() : tire aléatoirement des médias pour ce robot/campagne
  - DOM-agnostic : tous les sélecteurs sont multi-variantes avec fallback progressif
"""
import os
import random
import pathlib
import time
from typing import Optional, List, Dict

from libs.playwright_engine import PlaywrightEngine
from libs.selector_registry import SelectorRegistry, SelectorNotFound
from libs.timing_humanizer import (
    human_delay, human_delay_between_groups,
    post_publication_wait, human_scroll_to_bottom
)
from libs.error_handlers import (
    retry, check_page_state, check_group_accessible,
    SessionExpiredError, FacebookBlockedError,
    RateLimitError, NON_RETRYABLE
)
from libs.log_emitter import emit
from libs.config_manager import resolve_media_path
from libs.database import get_database, BONDatabase
from libs.stealth_profile import get_stealth_profile
from libs.circuit_breaker import get_circuit_breaker
from libs.notifier import get_notifier, notify_critical, notify_run_summary
from libs.social_actions import SocialActions
from libs.variant_selector import pick_variant
from automation.selector_health import get_health_manager
from automation.anti_block import get_anti_block_manager

DEFAULT_COMMENTS = [
    "Super post !",
    "Merci pour le partage !",
    "Très intéressant !",
    "Top !",
    "J'aime beaucoup ce contenu.",
    "Excellent partage !",
    "Merci !",
    "Très utile, merci.",
    "Belle publication !",
    "Continuez comme ça !",
]

# Couleurs fond FB disponibles (valeurs CSS approximatives pour matching)
FB_BG_COLORS = {
    "blue":    ["#1877f2", "blue", "bleu"],
    "green":   ["#42b72a", "green", "vert"],
    "red":     ["#fa3e3e", "red", "rouge"],
    "yellow":  ["#f7b928", "yellow", "jaune"],
    "purple":  ["#9b59b6", "purple", "violet"],
    "orange":  ["#e67e22", "orange"],
    "none":    [],
}

# Sélecteurs FB multi-variantes (DOM-agnostic)
SEL_POST_COMPOSER = [
    "div[role='button'][aria-label*='Qu\\'avez-vous en tête']",
    "div[role='button'][aria-label*='What\\'s on your mind']",
    "[data-testid='status-attachment-mentions-input']",
    "div[contenteditable='true'][aria-label*='tête']",
    "div[contenteditable='true'][aria-label*='mind']",
    "div.notranslate[contenteditable='true']",
    "div[role='textbox'][contenteditable='true']",
    "div[aria-multiline='true'][contenteditable='true']",
    "form div[contenteditable='true']",
]

SEL_POST_BUTTON = [
    "div[aria-label='Publier'][role='button']",
    "div[aria-label='Post'][role='button']",
    "[data-testid='react-composer-post-button']",
    "button[type='submit']:has-text('Publier')",
    "button[type='submit']:has-text('Post')",
    "div[role='button']:has-text('Publier')",
    "div[role='button']:has-text('Post')",
]

SEL_IMAGE_INPUT = [
    "input[type='file'][accept*='image']",
    "input[type='file']",
]

SEL_IMAGE_TRIGGER = [
    "div[aria-label*='Photo'][role='button']",
    "div[aria-label*='photo'][role='button']",
    "[data-testid='photo-attachment-button']",
    "input[type='file'][accept*='image']",
    "div[aria-label='Photo/vidéo'][role='button']",
    "div[aria-label='Photo/video'][role='button']",
]


class Scraper:
    """
    Publie des posts Facebook pour un robot donné.
    Composition avec PlaywrightEngine (pas d'héritage).

    Responsabilités :
      - Orchestrer le flux publication groupe par groupe
      - Anti-doublon via database.was_published_recently()
      - Sélection aléatoire variant + médias (avec captcha)
      - Post texte seul (avec couleur fond), multi-images, ou mixte
      - Commentaire post-publication (optionnel)
      - Abonnement auto si non membre
    """

    def __init__(self, engine: PlaywrightEngine, selectors: SelectorRegistry,
                 robot_config: dict, robot_name: str):
        self.engine       = engine
        self.selectors    = selectors
        self.config       = robot_config
        self.robot_name   = robot_name
        # Pour compatibilité avec code legacy qui utilise session_name
        self.session_name = robot_name
        self._context     = None
        self._page        = None
        self.db           = get_database()
        self.health_manager  = get_health_manager()
        self.anti_block      = get_anti_block_manager()
        self.circuit_breaker = get_circuit_breaker()

        _locale   = robot_config.get("locale", "fr-FR")
        _platform = robot_config.get("platform", "windows")
        self.stealth  = get_stealth_profile(locale=_locale, platform=_platform)
        self.notifier = get_notifier()
        self.notifier.configure_from_robot(robot_config)

        # Résoudre account_name depuis la config robot
        self._account_name = robot_config.get("account_name", robot_name)
        self.db.ensure_account_exists(self._account_name)

        # Social actions (initialisé après open())
        self._social: Optional[SocialActions] = None

    # ── Cycle de vie ──────────────────────────────────────────────────────

    def open(self) -> None:
        status = self.db.get_account_status(self._account_name)
        if status == "temporarily_blocked":
            block_info = self.db.get_account_block_info(self._account_name)
            if block_info and not block_info.get("can_resume", False):
                raise FacebookBlockedError(
                    f"Robot {self.robot_name} bloqué jusqu'à {block_info.get('until')}"
                )
        elif status == "session_expired":
            emit("WARN", "SESSION_EXPIRED_DETECTED", robot=self.robot_name)

        storage_state = self.config.get("storage_state", "")
        session_proxy = self.config.get("proxy") or None
        self._context, self._page = self.engine.new_context(
            storage_state=storage_state, proxy=session_proxy
        )
        self.stealth.apply(self._page)
        emit("DEBUG", "STEALTH_PROFILE", **self.stealth.to_dict())

        self.db.update_account_status(self._account_name, "healthy")
        emit("INFO", "ROBOT_START", robot=self.robot_name)

        # Instancier SocialActions maintenant que page est disponible
        self._social = SocialActions(self)

    def close(self) -> None:
        try:
            if self._context:
                self._context.close()
                self._context = None
                self._page    = None
            emit("INFO", "ROBOT_END", robot=self.robot_name)
        except Exception as e:
            emit("WARN", "ROBOT_CLOSE_ERROR", error=str(e))

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *_):
        self.close()

    # ── Flux principal de publication ─────────────────────────────────────

    def post_in_groups(self) -> dict:
        """
        Publie dans tous les groupes assignés au robot.
        Gère : anti-doublon, abonnement, choix aléatoire médias/variant,
               commentaire post-publication.
        """
        db        = self.db
        robot     = db.get_robot(self.robot_name)
        groups    = db.get_groups_for_robot(self.robot_name)
        campaigns = db.get_campaigns_for_robot(self.robot_name)

        if not groups:
            emit("WARN", "NO_GROUPS_FOR_ROBOT", robot=self.robot_name)
            return {"success": 0, "skipped": 0, "errors": 0}

        if not campaigns:
            emit("WARN", "NO_CAMPAIGNS_FOR_ROBOT", robot=self.robot_name)
            return {"success": 0, "skipped": 0, "errors": 0}

        # Warmup : limiter le débit pour les nouveaux comptes
        account_row     = db.get_account(self._account_name)
        warmup_done     = bool((account_row or {}).get("warmup_completed", 0))
        max_per_run     = (3 if not warmup_done else robot.get("max_groups_per_run", 10))
        max_per_hour    = (2 if not warmup_done else robot.get("max_groups_per_hour", 5))
        delay_range     = [robot.get("delay_min_s", 60), robot.get("delay_max_s", 120)]

        success_count = 0
        skipped_count = 0
        error_count   = 0
        ran = 0

        for group in groups:
            if ran >= max_per_run:
                break

            group_url = group["url"]

            # ── Vérification circuit breaker ──────────────────────────────
            if not self.circuit_breaker.allow(self.robot_name):
                emit("WARN", "CIRCUIT_OPEN_SKIP",
                     robot=self.robot_name, group=group_url[:60])
                skipped_count += 1
                continue

            # ── Vérification limite DB ────────────────────────────────────
            can_post, reason = db.can_account_post(self._account_name, max_per_hour)
            if not can_post:
                emit("WARN", "RATE_LIMIT_SKIP",
                     robot=self.robot_name, reason=reason)
                skipped_count += 1
                break

            # ── Choisir campagne + variant ────────────────────────────────
            campaign    = random.choice(campaigns)
            camp_name   = campaign["name"]
            language    = group.get("language", "fr")
            cross_excl = os.environ.get(
                "BON_CROSS_ROBOT_VARIANT_EXCLUSION", "0"
            ).strip().lower() in ("1", "true", "yes", "on")
            variant = pick_variant(
                db,
                robot_name=self.robot_name,
                campaign_name=camp_name,
                group_url=group_url,
                language=language,
                exclusion_days=30,
                exclude_cross_robot=cross_excl,
            )
            if not variant:
                emit("WARN", "NO_VARIANT", robot=self.robot_name, campaign=camp_name)
                skipped_count += 1
                continue

            # ── Anti-doublon : même robot + même groupe + dernières 24h ──
            if db.was_published_recently(self.robot_name, group_url, hours=24,
                                          campaign_name=camp_name,
                                          variant_id=variant["variant_key"]):
                emit("INFO", "ALREADY_PUBLISHED",
                     robot=self.robot_name, group=group_url[:60])
                skipped_count += 1
                continue

            # ── Abonnement auto si nécessaire ─────────────────────────────
            if self._social and not db.is_subscribed(self.robot_name, group_url):
                try:
                    self._social.subscribe_to_group(group_url)
                except Exception as sub_e:
                    emit("WARN", "SUBSCRIBE_ERROR", error=str(sub_e)[:80])

            # ── Sélection médias ──────────────────────────────────────────
            post_type   = variant.get("post_type", "text_image")
            media_items = []
            if post_type != "text_only":
                robot_row = db.get_robot(self.robot_name)
                if robot_row:
                    robot_id = robot_row.get("id") or db._resolve_robot_id(self.robot_name)
                    media_items = db.pick_random_media(self.robot_name, count=random.randint(1, 3))

            # ── Construire le texte final ─────────────────────────────────
            post_text = self._build_post_text(variant, media_items, language)

            # ── Publication ───────────────────────────────────────────────
            try:
                if not self.engine.navigate(self._page, group_url):
                    raise Exception("Navigation échouée vers le groupe")
                human_delay(2.0, 0.5)
                check_page_state(self._page, robot_name=self.robot_name)
                check_group_accessible(self._page, group_url)

                if post_type == "text_only":
                    bg_color = variant.get("bg_color")
                    pub_id   = self._post_text_only(group_url, post_text, camp_name,
                                                     variant["variant_key"], bg_color)
                elif media_items:
                    pub_id = self._post_with_images(
                        group_url, post_text, camp_name, variant["variant_key"],
                        [m["file_path"] for m in media_items]
                    )
                else:
                    # Fallback : texte seul si pas de médias disponibles
                    pub_id = self._post_text_only(group_url, post_text, camp_name,
                                                   variant["variant_key"], None)

                self.circuit_breaker.record_success(self.robot_name)
                success_count += 1
                ran += 1

                if not warmup_done and success_count == 1:
                    db.mark_warmup_completed(self._account_name)

                # Commentaire post-publication (optionnel)
                if self.config.get("add_comments") and pub_id and self._social:
                    human_delay(random.uniform(10, 20), 3)
                    comment_text = db.pick_random_comment(self.robot_name)
                    if not comment_text:
                        comment_text = random.choice(DEFAULT_COMMENTS)
                    self._social.comment_on_post(
                        group_url=group_url,
                        comment_text=comment_text,
                        publication_id=pub_id
                    )

                self.anti_block.notify_post(self._account_name)
                human_delay_between_groups(delay_range[0], delay_range[1])

            except NON_RETRYABLE as e:
                error_count += 1
                self.circuit_breaker.record_failure(self.robot_name, str(e)[:80])
                err_type = type(e).__name__
                db.record_error(robot_name=self.robot_name,
                                account_name=self._account_name,
                                group_url=group_url,
                                error_type=err_type, error_message=str(e)[:200])
                notify_critical(self.robot_name, err_type, str(e)[:200])
                if isinstance(e, (FacebookBlockedError, SessionExpiredError)):
                    break

            except Exception as e:
                error_count += 1
                self.circuit_breaker.record_failure(self.robot_name, str(e)[:80])
                db.record_error(robot_name=self.robot_name,
                                account_name=self._account_name,
                                group_url=group_url,
                                error_type=type(e).__name__, error_message=str(e)[:200])
                emit("WARN", "GROUP_POST_ERROR",
                     robot=self.robot_name, group=group_url[:60], error=str(e)[:80])

        notify_run_summary(self.robot_name, success_count, skipped_count, error_count)
        hs = db.get_health_score(self._account_name)
        self.notifier.notify_health_alert(self.robot_name, hs)
        return {"success": success_count, "skipped": skipped_count, "errors": error_count}

    # ── Construction du texte ─────────────────────────────────────────────

    def _build_post_text(self, variant: dict, media_items: list, language: str) -> str:
        """
        Construit le texte final d'un post :
          variant_text  (texte principal de la variante)
          + caption_aléatoire des médias (si media présents)
          + captcha_text de chaque image (si présent, concaténé à la caption)
        """
        parts = []
        # Texte principal du variant
        main_text = variant.get("text", "") or ""
        if main_text:
            parts.append(main_text.strip())

        # Caption des médias + captcha
        for media in media_items:
            caption_parts = []
            if media.get("description"):
                caption_parts.append(media["description"].strip())
            if media.get("captcha_text"):
                caption_parts.append(media["captcha_text"].strip())
            if caption_parts:
                parts.append(" ".join(caption_parts))

        # CTA (call to action)
        cta = variant.get("cta", "")
        if cta:
            parts.append(cta.strip())

        return "\n\n".join(filter(None, parts))

    # ── Post texte seul (avec couleur fond optionnelle) ───────────────────

    def _post_text_only(self, group_url: str, text: str,
                         campaign_name: str, variant_id: str,
                         bg_color: str = None) -> Optional[int]:
        """
        Publie un post texte seul.
        Si bg_color fourni, tente de sélectionner la couleur de fond FB.
        """
        page = self._page
        composer = self._open_composer(page)
        if not composer:
            raise Exception("Impossible d'ouvrir le compositeur de post")

        self._type_post_text(page, composer, text)

        # Sélection couleur fond si demandée
        if bg_color:
            self._select_bg_color(page, bg_color)

        pub_id = self._click_publish(page, group_url, text, campaign_name,
                                      variant_id, post_type="text_only")
        return pub_id

    def _select_bg_color(self, page, color_hint: str) -> bool:
        """
        Tente de sélectionner une couleur de fond dans le compositeur FB.
        Gère les multiples versions du DOM FB.
        """
        # Ouvrir le sélecteur de couleur
        color_trigger_sels = [
            "div[aria-label='Choisir une couleur d\\'arrière-plan']",
            "div[aria-label='Choose a background color']",
            "[data-testid='background-composer-button']",
            "div[role='button'][aria-label*='couleur']",
            "div[role='button'][aria-label*='color']",
            "div[role='button'][aria-label*='background']",
        ]
        triggered = False
        for sel in color_trigger_sels:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=2000):
                    btn.click()
                    human_delay(0.8, 0.3)
                    triggered = True
                    break
            except Exception:
                continue

        if not triggered:
            return False

        # Sélectionner la couleur spécifique
        color_sels = [
            f"div[aria-label*='{color_hint}'][role='button']",
            f"div[data-color*='{color_hint}']",
            f"div[style*='{color_hint}'][role='button']",
        ]
        for sel in color_sels:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=1500):
                    btn.click()
                    human_delay(0.5, 0.2)
                    return True
            except Exception:
                continue

        # Fallback : cliquer sur le premier bouton de couleur visible
        try:
            color_btns = page.locator(
                "div[role='button'][aria-label]"
                "[style*='background']"
            ).all()
            if color_btns:
                random.choice(color_btns[:6]).click()
                human_delay(0.5, 0.2)
                return True
        except Exception:
            pass
        return False

    # ── Post avec images ──────────────────────────────────────────────────

    def _post_with_images(self, group_url: str, text: str,
                           campaign_name: str, variant_id: str,
                           image_paths: List[str]) -> Optional[int]:
        """
        Publie un post avec 1 ou plusieurs images.
        """
        page = self._page

        # Résoudre les chemins
        resolved_paths = []
        for img in image_paths:
            try:
                p = resolve_media_path(img, self.robot_name)
                if p.exists():
                    resolved_paths.append(str(p))
            except Exception:
                pass
        if not resolved_paths:
            emit("WARN", "NO_VALID_IMAGES", robot=self.robot_name)
            return self._post_text_only(group_url, text, campaign_name,
                                         variant_id, None)

        composer = self._open_composer(page)
        if not composer:
            raise Exception("Impossible d'ouvrir le compositeur")

        # Attacher les images
        attached = self._attach_images(page, resolved_paths)
        if not attached:
            emit("WARN", "IMAGE_ATTACH_FAILED", robot=self.robot_name)

        human_delay(1.5, 0.5)
        self._type_post_text(page, composer, text)

        pub_id = self._click_publish(page, group_url, text, campaign_name,
                                      variant_id, images=resolved_paths,
                                      post_type="text_image")
        return pub_id

    def _attach_images(self, page, image_paths: List[str]) -> bool:
        """Attache des images au compositeur FB (multi-sélecteurs)."""
        # Essai 1 : clic sur le bouton photo/vidéo pour révéler l'input
        for sel in SEL_IMAGE_TRIGGER:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=2000):
                    if "input[type='file']" in sel:
                        page.set_input_files(sel, image_paths[:10])
                        human_delay(2.0, 0.5)
                        return True
                    btn.click()
                    human_delay(1.0, 0.3)
                    break
            except Exception:
                continue

        # Essai 2 : input file direct
        for sel in SEL_IMAGE_INPUT:
            try:
                page.set_input_files(sel, image_paths[:10])
                human_delay(2.0, 0.5)
                return True
            except Exception:
                continue

        # Essai 3 : drag-and-drop sur la zone de composition
        try:
            drop_zone = page.locator("div[contenteditable='true']").first
            if drop_zone.is_visible(timeout=2000):
                page.set_input_files(
                    "input[type='file']",
                    image_paths[:10],
                    no_wait_after=True
                )
                human_delay(2.0, 0.5)
                return True
        except Exception:
            pass

        return False

    # ── Helpers compositeur ───────────────────────────────────────────────

    def _open_composer(self, page):
        """Ouvre la zone de composition du post (multi-sélecteurs)."""
        for sel in SEL_POST_COMPOSER:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=3000):
                    el.click()
                    human_delay(1.0, 0.3)
                    return el
            except Exception:
                continue
        emit("WARN", "COMPOSER_NOT_FOUND", robot=self.robot_name)
        return None

    def _type_post_text(self, page, composer, text: str):
        """Saisit le texte dans le compositeur."""
        try:
            # Chercher la zone editable après le clic
            editable_sels = [
                "div[contenteditable='true'][role='textbox']",
                "div[contenteditable='true'][aria-multiline]",
                "div.notranslate[contenteditable='true']",
                "div[data-lexical-editor][contenteditable='true']",
            ]
            for sel in editable_sels:
                try:
                    el = page.locator(sel).last
                    if el.is_visible(timeout=2000):
                        el.click()
                        human_delay(0.3, 0.1)
                        el.press_sequentially(text, delay=random.randint(30, 100))
                        human_delay(0.5, 0.2)
                        return
                except Exception:
                    continue
            # Fallback : saisir dans le composer initial
            composer.press_sequentially(text, delay=random.randint(30, 100))
            human_delay(0.5, 0.2)
        except Exception as e:
            emit("WARN", "TYPE_TEXT_ERROR", error=str(e)[:80])

    def _click_publish(self, page, group_url: str, text: str,
                        campaign_name: str, variant_id: str,
                        images: list = None, bg_color: str = None,
                        post_type: str = "text_image") -> Optional[int]:
        """Clique sur Publier et enregistre le résultat en DB."""
        published = False
        for sel in SEL_POST_BUTTON:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=3000):
                    btn.click()
                    published = True
                    break
            except Exception:
                continue

        if not published:
            emit("WARN", "PUBLISH_BUTTON_NOT_FOUND", robot=self.robot_name)
            pub_id = self.db.record_publication(
                robot_name=self.robot_name, group_url=group_url,
                status="failed", post_content=text,
                campaign_name=campaign_name, variant_id=variant_id,
                images=images, bg_color=bg_color, post_type=post_type,
                error_message="Bouton Publier introuvable"
            )
            return None

        post_publication_wait()
        check_page_state(page, robot_name=self.robot_name)

        pub_id = self.db.record_publication(
            robot_name=self.robot_name, group_url=group_url,
            status="success", post_content=text[:500],
            campaign_name=campaign_name, variant_id=variant_id,
            images=images, bg_color=bg_color, post_type=post_type
        )
        emit("SUCCESS", "POST_PUBLISHED",
             robot=self.robot_name, group=group_url[:60],
             campaign=campaign_name, variant=variant_id)
        return pub_id

    # ── Marketplace ───────────────────────────────────────────────────────

    def post_in_marketplace(self) -> bool:
        """Publie une annonce Marketplace depuis la config robot."""
        mp_config = self.config.get("marketplace", {})
        if not mp_config:
            emit("WARN", "MARKETPLACE_NOT_CONFIGURED", robot=self.robot_name)
            return False
        # Délégation vers SocialActions ou logique interne similaire
        emit("INFO", "MARKETPLACE_TODO", robot=self.robot_name)
        return False

    # ── Save groups ───────────────────────────────────────────────────────

    def save_groups(self, keyword: str) -> list:
        """Recherche des groupes par mot-clé et les sauvegarde en DB."""
        from urllib.parse import quote as url_quote
        page = self._page
        encoded = url_quote(keyword)
        search_url = f"https://www.facebook.com/search/groups?q={encoded}"

        if not self.engine.navigate(page, search_url):
            return []
        human_delay(2.0, 0.5)
        human_scroll_to_bottom(page, max_iterations=5)

        links = []
        try:
            anchors = page.locator("a[href*='/groups/']").all()
            for a in anchors[:50]:
                href = a.get_attribute("href")
                if href and "/groups/" in href:
                    clean = href.split("?")[0].rstrip("/")
                    if clean not in links and len(links) < 30:
                        links.append(clean)
                        self.db.add_group(url=clean)
                        # Assigner au robot courant
                        self.db.assign_group_to_robot(self.robot_name, clean)
        except Exception as e:
            emit("WARN", "SAVE_GROUPS_ERROR", error=str(e)[:80])
        emit("INFO", "GROUPS_SAVED",
             robot=self.robot_name, count=len(links), keyword=keyword)
        return links

    # ── Accès à SocialActions ─────────────────────────────────────────────

    @property
    def social(self) -> Optional[SocialActions]:
        """Accès aux actions sociales avancées (commentaires, DM, navigation)."""
        return self._social
