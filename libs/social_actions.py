"""
social_actions.py v9 — Actions sociales avancées Facebook

Fonctionnalités :
  subscribe_to_group()       : s'abonner à un groupe (si pas encore membre)
  comment_on_post()          : commenter un post (nouveau ou existant)
  browse_and_comment()       : circuler sur FB et commenter aléatoirement
  send_dm()                  : envoyer un DM (texte + image/vidéo) à ami / abonné page
  process_dm_queue()         : traiter la file DM depuis la DB
  simulate_natural_browse()  : navigation humaine (scroll + mouvements souris)
  browse_page_subscribers()  : récupérer les abonnés d'une page

DOM-agnostic : chaque action utilise des listes de sélecteurs avec fallback progressif.
"""
import random
import time
import json
from typing import Optional, List

try:
    from libs.timing_humanizer import human_delay, human_scroll_to_bottom
    from libs.selector_registry import SelectorRegistry
    from libs.adaptive_selector_resolver import AdaptiveSelectorResolver
    from libs.error_handlers import check_page_state, SessionExpiredError
    from libs.log_emitter import emit
    from libs.database import get_database, BONDatabase
    from libs.notifier import get_notifier
    from libs.config_manager import resolve_media_path
except ImportError:
    from timing_humanizer import human_delay, human_scroll_to_bottom
    from selector_registry import SelectorRegistry
    from adaptive_selector_resolver import AdaptiveSelectorResolver
    from error_handlers import check_page_state, SessionExpiredError
    from log_emitter import emit
    from database import get_database, BONDatabase
    from notifier import get_notifier
    from config_manager import resolve_media_path

DEFAULT_COMMENTS = [
    "Super post !", "Merci pour le partage !", "Très intéressant !",
    "Top !", "Excellent !", "Merci !", "Belle publication !",
]

# Sélecteurs pour la zone de commentaire
SEL_COMMENT_INPUT = [
    "div[contenteditable='true'][aria-label*='omment']",
    "div[contenteditable='true'][aria-label*='ommentaire']",
    "div[data-lexical-editor][contenteditable='true']",
    "div[role='textbox'][aria-label*='omment']",
    "[data-testid='comment-composer-input']",
    "form div[contenteditable='true']",
    "div[aria-label*='Écrire un commentaire']",
    "div[aria-label*='Write a comment']",
]

# Sélecteurs pour le bouton Message
SEL_MESSAGE_BTN = [
    "div[aria-label='Envoyer un message']",
    "div[aria-label='Message']",
    "a[href*='/messages/']:has-text('Message')",
    "[data-testid='send-message-button']",
    "div[role='button']:has-text('Message')",
    "span:has-text('Envoyer un message')",
    "div[aria-label='Contacter']",
]

# Sélecteurs input Messenger
SEL_MESSENGER_INPUT = [
    "div[contenteditable='true'][aria-label*='essage']",
    "div[role='textbox'][data-lexical-editor]",
    "div[contenteditable='true'][role='textbox']",
    "div[aria-label='Message'][contenteditable='true']",
    "div[data-lexical-editor='true']",
]

# Sélecteurs bouton "Rejoindre groupe"
SEL_JOIN_GROUP = [
    "div[role='button']:has-text('Rejoindre le groupe')",
    "div[role='button']:has-text('Join group')",
    "div[role='button']:has-text('Join Group')",
    "a[role='button']:has-text('Rejoindre')",
    "[data-testid='group-join-button']",
    "div[aria-label='Rejoindre le groupe']",
    "div[aria-label='Join group']",
    "div[role='button']:has-text('Demander à rejoindre')",
    "div[role='button']:has-text('Ask to join')",
]

SEL_ALREADY_MEMBER = [
    "div[role='button']:has-text('Membre')",
    "div[role='button']:has-text('Joined')",
    "div[aria-label='Membre']",
    "div[aria-label='Joined']",
    "span:has-text('Membre du groupe')",
]


class SocialActions:
    """
    Actions sociales avancées pour un robot.
    Instanciée par Scraper après open().
    """

    def __init__(self, scraper):
        self.scraper      = scraper
        self.engine       = scraper.engine
        self.selectors    = scraper.selectors
        self.robot_name   = scraper.robot_name
        self.config       = scraper.config
        self.db           = scraper.db
        self._account     = scraper._account_name
        self.notifier     = get_notifier()
        # Résolveur adaptatif hérité du Scraper (déjà initialisé avec le profil UI du compte)
        self._resolver: AdaptiveSelectorResolver = getattr(scraper, "_adaptive_resolver", None)

    @property
    def _page(self):
        return self.scraper._page


    # ── Résolution de sélecteurs adaptative ───────────────────────────────

    def _find(self, key, extra_selectors=None, timeout=5000):
        """Trouve un élément via resolver adaptatif > extra_selectors > registry global."""
        page = self._page
        if not page:
            return None
        candidates = []
        if self._resolver:
            for sel in self._resolver.get_candidates(key):
                if sel not in candidates:
                    candidates.append(sel)
        for sel in (extra_selectors or []):
            if sel not in candidates:
                candidates.append(sel)
        for sel in (self.selectors.get_candidates(key) if self.selectors else []):
            if sel not in candidates:
                candidates.append(sel)
        for sel in candidates:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=timeout):
                    if self._resolver:
                        self._resolver._health.record_success(key, sel)
                    return el
            except Exception:
                continue
        if self._resolver:
            self._resolver._health.record_failure(key, reason="not_found_in_social_actions")
        return None

    def _find_all(self, key, extra_selectors=None, timeout=3000):
        """Retourne tous les éléments correspondants via le resolver adaptatif."""
        page = self._page
        if not page:
            return []
        candidates = []
        if self._resolver:
            for sel in self._resolver.get_candidates(key):
                if sel not in candidates:
                    candidates.append(sel)
        for sel in (extra_selectors or []):
            if sel not in candidates:
                candidates.append(sel)
        for sel in candidates:
            try:
                page.wait_for_selector(sel, timeout=timeout)
                elements = page.query_selector_all(sel)
                if elements:
                    return elements
            except Exception:
                continue
        return []

    # ── Navigation humaine ────────────────────────────────────────────────

    def simulate_natural_browse(self, page=None, duration_s: float = 10.0):
        """Simule une navigation humaine : scroll, pauses, mouvements souris."""
        p = page or self._page
        if not p:
            return
        end_time = time.time() + duration_s
        while time.time() < end_time:
            action = random.choices(
                ["scroll_down", "scroll_up", "mouse_move", "pause"],
                weights=[4, 2, 3, 1]
            )[0]
            try:
                if action == "scroll_down":
                    p.mouse.wheel(0, random.randint(200, 700))
                    human_delay(0.5, 0.3)
                elif action == "scroll_up":
                    p.mouse.wheel(0, -random.randint(100, 300))
                    human_delay(0.4, 0.2)
                elif action == "mouse_move":
                    vp = p.viewport_size or {"width": 1280, "height": 800}
                    x  = random.randint(100, vp["width"] - 100)
                    y  = random.randint(100, vp["height"] - 100)
                    p.mouse.move(x, y, steps=random.randint(5, 20))
                    human_delay(0.3, 0.2)
                else:
                    human_delay(1.0, 0.5)
            except Exception:
                human_delay(0.5, 0.2)

    # ── Abonnement groupe ─────────────────────────────────────────────────

    def subscribe_to_group(self, group_url: str) -> bool:
        """
        S'abonne au groupe si pas encore membre.
        Gère les multiples versions du DOM Facebook.
        """
        if self.db.is_subscribed(self.robot_name, group_url):
            return True

        page = self._page
        if not self.engine.navigate(page, group_url):
            return False
        human_delay(2.0, 0.5)
        check_page_state(page, robot_name=self.scraper.robot_name)

        # Vérifier si déjà membre — résolveur adaptatif + fallback liste statique
        member_el = self._find("join_group_already_member", extra_selectors=SEL_ALREADY_MEMBER, timeout=1500)
        if member_el:
            self.db.mark_subscribed(self.robot_name, group_url)
            return True

        # Clic sur "Rejoindre" — résolveur adaptatif + fallback liste statique
        join_btn = self._find("join_group", extra_selectors=SEL_JOIN_GROUP, timeout=2000)
        if join_btn:
            self.simulate_natural_browse(page, duration_s=2.0)
            join_btn.click()
            human_delay(2.5, 0.5)
            self.db.mark_subscribed(self.robot_name, group_url)
            emit("SUCCESS", "GROUP_SUBSCRIBED",
                 robot=self.robot_name, group=group_url[:60])
            return True

        emit("WARN", "JOIN_BUTTON_NOT_FOUND",
             robot=self.robot_name, group=group_url[:60])
        return False

    # ── Commentaire sous un post ──────────────────────────────────────────

    def comment_on_post(self, group_url: str = None, post_url: str = None,
                         comment_text: str = None, publication_id: int = None) -> bool:
        """
        Commente un post Facebook.
        - Si post_url fourni → navigue directement
        - Sinon → cherche le dernier post du groupe
        Gère le DOM multi-versions.
        """
        db   = self.db
        page = self._page

        if not comment_text:
            comment_text = db.pick_random_comment(self.robot_name)
        if not comment_text:
            comment_text = random.choice(DEFAULT_COMMENTS)

        target_url = post_url or group_url
        if not target_url:
            return False
        if not self.engine.navigate(page, target_url):
            return False
        human_delay(2.0, 0.5)
        check_page_state(page, robot_name=self.scraper.robot_name)
        self.simulate_natural_browse(page, duration_s=random.uniform(3, 6))

        # Résolveur adaptatif (tient compte de la langue du compte) + fallback statique
        comment_el = self._find("comment_input", extra_selectors=SEL_COMMENT_INPUT, timeout=3000)
        if comment_el:
            try:
                comment_el.scroll_into_view_if_needed()
                human_delay(0.5, 0.2)
                comment_el.click()
                human_delay(0.3, 0.1)
                comment_el.press_sequentially(comment_text, delay=random.randint(40, 130))
                human_delay(0.5, 0.2)
                comment_el.press("Enter")
                human_delay(2.0, 0.5)
                db.record_published_comment(
                    self.robot_name, group_url or target_url,
                    comment_text, publication_id
                )
                emit("SUCCESS", "COMMENT_PUBLISHED",
                     robot=self.robot_name, preview=comment_text[:40])
                return True
            except Exception as e:
                emit("WARN", "COMMENT_CLICK_ERROR", error=str(e)[:80])

        emit("WARN", "COMMENT_INPUT_NOT_FOUND", robot=self.robot_name)
        return False

    # ── Navigation + commentaires aléatoires ─────────────────────────────

    def browse_and_comment(self, urls: List[str],
                            max_comments: int = 3) -> int:
        """
        Circule sur Facebook (groupes/amis/pages) et commente des posts.
        Simule un comportement humain naturel.
        Retourne le nombre de commentaires publiés.
        """
        count = 0
        page  = self._page
        for url in urls:
            if count >= max_comments:
                break
            try:
                if not self.engine.navigate(page, url):
                    continue
                human_delay(2.0, 1.0)
                check_page_state(page, robot_name=self.scraper.robot_name)
                self.simulate_natural_browse(page, duration_s=random.uniform(5, 12))

                post_urls = self._find_post_links(page)
                if not post_urls:
                    continue

                target_post = random.choice(post_urls[:5])
                if self.comment_on_post(group_url=url, post_url=target_post):
                    count += 1
                    human_delay(random.uniform(30, 90), 10)

            except (SessionExpiredError, Exception) as e:
                emit("WARN", "BROWSE_COMMENT_ERROR",
                     url=url[:60], error=str(e)[:60])
                continue

        return count

    def _find_post_links(self, page) -> List[str]:
        """Cherche des liens de posts sur la page courante."""
        post_links = []
        selectors_to_try = [
            "a[href*='/posts/']",
            "a[href*='?story_fbid=']",
            "a[href*='/permalink/']",
        ]
        for sel in selectors_to_try:
            try:
                links = page.locator(sel).all()
                for link in links[:15]:
                    href = link.get_attribute("href") or ""
                    if not href:
                        continue
                    if "facebook.com" not in href:
                        href = "https://www.facebook.com" + href
                    href = href.split("?")[0]
                    if href not in post_links:
                        post_links.append(href)
            except Exception:
                continue
        return list(dict.fromkeys(post_links))

    # ── Récupérer abonnés d'une page ─────────────────────────────────────

    def browse_page_subscribers(self, page_url: str,
                                  max_profiles: int = 50) -> List[str]:
        """
        Récupère des URLs de profils d'abonnés d'une page Facebook.
        Utile pour envoyer des DM aux abonnés.
        """
        page     = self._page
        profiles = []
        followers_url = page_url.rstrip("/") + "/followers"

        if not self.engine.navigate(page, followers_url):
            return profiles
        human_delay(2.0, 0.5)

        for _ in range(5):
            self.simulate_natural_browse(page, duration_s=3.0)
            links = page.locator("a[href*='/user/'], a[href*='facebook.com/']").all()
            for link in links:
                href = link.get_attribute("href") or ""
                if "/user/" in href or (
                    "facebook.com/" in href
                    and "/groups/" not in href
                    and "/pages/" not in href
                    and "/events/" not in href
                ):
                    clean = href.split("?")[0].rstrip("/")
                    if clean not in profiles and len(profiles) < max_profiles:
                        profiles.append(clean)
            if len(profiles) >= max_profiles:
                break

        emit("INFO", "PAGE_SUBSCRIBERS_FOUND",
             robot=self.robot_name, count=len(profiles))
        return profiles

    # ── DM ────────────────────────────────────────────────────────────────

    def send_dm(self, target_profile_url: str, text: str,
                 media_paths: List[str] = None,
                 target_type: str = "ami") -> bool:
        """
        Envoie un DM (texte + images/vidéo optionnels) à un profil.
        target_type : "ami" | "abonne"
        """
        page = self._page
        if not self.engine.navigate(page, target_profile_url):
            return False
        human_delay(2.0, 0.5)
        check_page_state(page, robot_name=self.scraper.robot_name)
        self.simulate_natural_browse(page, duration_s=2.0)

        # Trouver et cliquer sur "Message" (résolveur adaptatif multi-langue)
        clicked = False
        msg_btn = self._find("message_btn", SEL_MESSAGE_BTN, timeout=3000)
        if msg_btn:
            try:
                msg_btn.click()
                human_delay(2.0, 0.5)
                clicked = True
            except Exception:
                pass

        if not clicked:
            # Essai direct via URL Messenger
            try:
                fb_id = target_profile_url.rstrip("/").split("/")[-1]
                page.goto(f"https://www.facebook.com/messages/t/{fb_id}")
                human_delay(3.0, 1.0)
                clicked = True
            except Exception:
                pass

        if not clicked:
            emit("WARN", "DM_MESSAGE_BTN_NOT_FOUND",
                 robot=self.robot_name, target=target_profile_url[:60])
            return False

        # Zone de saisie Messenger — résolveur adaptatif + fallback statique
        messenger_el = self._find("messenger_input", extra_selectors=SEL_MESSENGER_INPUT, timeout=5000)
        if messenger_el:
            try:
                messenger_el.click()
                messenger_el.press_sequentially(text, delay=random.randint(40, 130))
                human_delay(0.5, 0.2)
                if media_paths:
                    self._attach_dm_media(page, media_paths)
                messenger_el.press("Enter")
                human_delay(2.0, 0.5)
                emit("SUCCESS", "DM_SENT",
                     robot=self.robot_name, target=target_profile_url[:60])
                return True
            except Exception as e:
                emit("WARN", "DM_SEND_ERROR", error=str(e)[:80])

        emit("WARN", "DM_INPUT_NOT_FOUND", robot=self.robot_name)
        return False

    def _attach_dm_media(self, page, media_paths: List[str]):
        """Attache des fichiers à un DM (images/vidéos)."""
        # Résoudre les chemins
        resolved = []
        for p in media_paths:
            try:
                rp = resolve_media_path(p)
                if rp.exists():
                    resolved.append(str(rp))
            except Exception:
                resolved.append(p)

        if not resolved:
            return

        attach_sels = [
            "input[type='file'][accept*='image']",
            "input[type='file'][accept*='video']",
            "input[type='file']",
            "div[aria-label*='Joindre'] ~ input",
            "div[aria-label*='Attach'] ~ input",
        ]
        for sel in attach_sels:
            try:
                page.set_input_files(sel, resolved[:5])
                human_delay(2.0, 0.5)
                return
            except Exception:
                continue
        emit("WARN", "DM_ATTACH_FAILED", robot=self.robot_name)

    def process_dm_queue(self, limit: int = 10) -> int:
        """Traite la file DM depuis la DB (envois planifiés/en attente)."""
        db    = self.db
        dms   = db.get_pending_dms(self.robot_name, limit=limit)
        count = 0
        for dm in dms:
            try:
                media = json.loads(dm["media_paths"]) if dm.get("media_paths") else None
                ok = self.send_dm(
                    target_profile_url = dm["target_id"],
                    text               = dm["text_content"],
                    media_paths        = media,
                    target_type        = dm["target_type"],
                )
                db.update_dm_status(dm["id"], "sent" if ok else "failed")
                if ok:
                    count += 1
                    human_delay(random.uniform(30, 90), 15)
            except Exception as e:
                db.update_dm_status(dm["id"], "failed", str(e)[:200])
        return count
