"""
robot_manager.py v9 — Gestion des robots (instances nommées robot1, robot2...)

Chaque robot = 1 compte Facebook + 1 storage_state Playwright.
Remplace session_manager.py (conservé en alias pour rétrocompat).

API :
  rm = RobotManager()
  rm.create_robot("robot1", browser, account_name="compte_principal")
  config = rm.get_config("robot1")
  rm.save_config("robot1", config)
  robots = rm.list_robots()           → ["robot1", "robot2"]
"""
import pathlib
from typing import Optional, List

try:
    from libs.config_manager import SESSIONS_DIR, get_session_state_path
    from libs.database import get_database, BONDatabase
    from libs.log_emitter import emit
except ImportError:
    from config_manager import SESSIONS_DIR, get_session_state_path
    from database import get_database, BONDatabase
    from log_emitter import emit


DEFAULT_ROBOT_CONFIG = {
    "max_groups_per_run":      10,
    "max_groups_per_hour":     5,
    "delay_between_groups":    [60, 120],
    "max_runs_per_day":        2,
    "cooldown_between_runs_s": 7200,
    "locale":                  "fr-FR",
    "timezone_id":             "Europe/Paris",
    "platform":                "windows",
    "proxy":                   None,
    "telegram_token":          "",
    "telegram_chat_id":        "",
}


class RobotManager:
    """
    Gère les robots Playwright v9.
    Le storage_state Playwright reste sur disque (fichier binaire opaque).
    Toute la config robot est en base SQLite.
    """

    def __init__(self):
        self.db: BONDatabase = get_database()

    # ── Existence / listage ────────────────────────────────────────────────

    def robot_exists(self, robot_name: str) -> bool:
        """Un robot existe si son storage_state est sur disque ET en base."""
        state_path = get_session_state_path(robot_name)
        return state_path.exists() and self.db.robot_exists(robot_name)

    def list_robots(self) -> List[str]:
        return self.db.list_robot_names()

    # ── Config ────────────────────────────────────────────────────────────

    def get_config(self, robot_name: str) -> dict:
        """Retourne la config du robot depuis la DB (ou défauts)."""
        robot = self.db.get_robot(robot_name)
        if not robot:
            cfg = dict(DEFAULT_ROBOT_CONFIG)
            cfg["robot_name"]     = robot_name
            cfg["storage_state"]  = str(get_session_state_path(robot_name))
            cfg["account_name"]   = robot_name
            return cfg
        # Adapter au format attendu par Scraper/Engine
        cfg = {
            "robot_name":              robot["robot_name"],
            "account_name":            robot["account_name"],
            "storage_state":           robot.get("storage_state_path", ""),
            "max_groups_per_run":      robot.get("max_groups_per_run", 10),
            "max_groups_per_hour":     robot.get("max_groups_per_hour", 5),
            "delay_between_groups":    robot.get("delay_between_groups", [60, 120]),
            "max_runs_per_day":        robot.get("max_runs_per_day", 2),
            "cooldown_between_runs_s": robot.get("cooldown_between_runs_s", 7200),
            "locale":                  robot.get("locale", "fr-FR"),
            "timezone_id":             robot.get("timezone_id", "Europe/Paris"),
            "platform":                robot.get("platform", "windows"),
            "proxy":                   robot.get("proxy"),
            # I1-FIX (v13): clé captcha par robot — None = pas de clé spécifique,
            # CaptchaSolver utilisera BON_2CAPTCHA_KEY global si présent.
            "captcha_api_key":         robot.get("captcha_api_key"),
            "telegram":                {
                "token":   robot.get("telegram_token", ""),
                "chat_id": robot.get("telegram_chat_id", ""),
            } if robot.get("telegram_token") else None,
        }
        return cfg

    def save_config(self, robot_name: str, config: dict) -> bool:
        """Sauvegarde la config du robot en base."""
        try:
            account_name = config.get("account_name", robot_name)
            storage_path = config.get("storage_state",
                                      str(get_session_state_path(robot_name)))
            self.db.upsert_robot(robot_name, account_name, storage_path, config)
            emit("DEBUG", "ROBOT_CONFIG_SAVED", robot=robot_name)
            return True
        except Exception as e:
            emit("ERROR", "ROBOT_CONFIG_SAVE_ERROR", robot=robot_name, error=str(e))
            return False

    # ── Création ──────────────────────────────────────────────────────────

    def create_robot(self, robot_name: str, browser,
                     account_name: str = None,
                     config: dict = None,
                     context_proxy: dict = None) -> bool:
        """
        Lance une fenêtre navigateur pour login manuel FB,
        puis enregistre le robot en base.

        robot_name  : identifiant unique (ex: 'robot1')
        account_name: nom du compte Facebook (défaut = robot_name)
        config      : config optionnelle (surcharge les défauts)
        """
        if not account_name:
            account_name = robot_name
        state_path = get_session_state_path(robot_name)
        emit("INFO", "ROBOT_CREATE_START", robot=robot_name, account=account_name)

        try:
            ctx_kw = {}
            if context_proxy:
                ctx_kw["proxy"] = context_proxy
            context = browser.new_context(**ctx_kw)
            page    = context.new_page()
            page.goto("https://www.facebook.com/login")

            print(f"\n[ROBOT] Connectez-vous à Facebook pour '{robot_name}' ({account_name})")
            print("[ROBOT] Appuyez sur ENTRÉE une fois connecté...")
            input()

            if "/login" in page.url:
                emit("WARN", "ROBOT_LOGIN_FAILED", robot=robot_name)
                context.close()
                return False

            SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=str(state_path))
            emit("SUCCESS", "ROBOT_STATE_SAVED",
                 robot=robot_name, path=str(state_path))

            cfg = dict(DEFAULT_ROBOT_CONFIG)
            cfg.update(config or {})
            cfg["storage_state"] = str(state_path)
            cfg["account_name"]  = account_name
            if context_proxy:
                srv = context_proxy.get("server") or ""
                if srv:
                    cfg["proxy_server"] = srv
                    cfg["proxy_username"] = context_proxy.get("username") or ""
                    cfg["proxy_password"] = context_proxy.get("password") or ""

            self.db.upsert_robot(robot_name, account_name, str(state_path), cfg)
            self.db.ensure_account_exists(account_name)
            emit("SUCCESS", "ROBOT_CREATED", robot=robot_name)
            context.close()
            return True

        except Exception as e:
            emit("ERROR", "ROBOT_CREATE_ERROR", robot=robot_name, error=str(e))
            return False

    def restore_context(self, robot_name: str, browser):
        """Crée un contexte Playwright à partir du storage_state du robot."""
        state_path = get_session_state_path(robot_name)
        if not state_path.exists():
            raise FileNotFoundError(
                f"Robot '{robot_name}' : storage_state introuvable → {state_path}"
            )
        emit("INFO", "ROBOT_RESTORE", robot=robot_name)
        context = browser.new_context(storage_state=str(state_path))
        page    = context.new_page()
        return context, page

    def save_state(self, context, robot_name: str) -> bool:
        """Sauvegarde l'état courant du robot (cookies actualisés)."""
        state_path = get_session_state_path(robot_name)
        try:
            context.storage_state(path=str(state_path))
            emit("INFO", "ROBOT_STATE_SAVED", robot=robot_name)
            return True
        except Exception as e:
            emit("ERROR", "ROBOT_STATE_SAVE_ERROR", robot=robot_name, error=str(e))
            return False

    def delete_robot(self, robot_name: str) -> bool:
        """Supprime un robot (storage_state + ligne DB)."""
        ok = True
        state_path = get_session_state_path(robot_name)
        try:
            state_path.unlink(missing_ok=True)
        except Exception as e:
            emit("WARN", "ROBOT_FILE_DELETE_ERROR", robot=robot_name, error=str(e))
            ok = False
        if not self.db.delete_robot(robot_name):
            ok = False
        if ok:
            emit("INFO", "ROBOT_DELETED", robot=robot_name)
        return ok

    def check_session_valid(self, page) -> bool:
        url = page.url
        if "/login" in url or "login.php" in url:
            emit("WARN", "ROBOT_SESSION_EXPIRED_DETECTED")
            return False
        return True

    # ── Migration one-shot sessions → robots ──────────────────────────────

    def migrate_sessions_to_robots(self) -> int:
        """
        Migration one-shot v8 → v9 :
        Importe les anciens enregistrements 'sessions' comme 'robots'.
        Idempotent.
        """
        count = 0
        try:
            sessions = self.db._query("SELECT * FROM sessions")
        except Exception:
            return 0
        for s in sessions:
            robot_name   = s.get("session_name", "")
            account_name = s.get("account_name", robot_name)
            state_path   = s.get("storage_state_path", "")
            if not robot_name or self.db.robot_exists(robot_name):
                continue
            config = {
                "max_groups_per_run":      s.get("max_groups_per_run", 10),
                "max_groups_per_hour":     s.get("max_groups_per_hour", 5),
                "delay_between_groups":    [s.get("delay_min_s", 60), s.get("delay_max_s", 120)],
                "max_runs_per_day":        s.get("max_runs_per_day", 2),
                "cooldown_between_runs_s": s.get("cooldown_between_runs_s", 7200),
                "locale":                  s.get("locale", "fr-FR"),
                "timezone_id":             s.get("timezone_id", "Europe/Paris"),
                "platform":                s.get("platform", "windows"),
                "telegram_token":          s.get("telegram_token", ""),
                "telegram_chat_id":        s.get("telegram_chat_id", ""),
            }
            self.db.upsert_robot(robot_name, account_name, state_path, config)
            count += 1
        if count:
            emit("INFO", "SESSIONS_MIGRATED_TO_ROBOTS", count=count)
        return count


# Alias rétrocompat
SessionManager = RobotManager
