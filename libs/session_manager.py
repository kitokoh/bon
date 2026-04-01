"""
session_manager.py v8 — Sessions 100% SQL (plus de {session}.json)

get_config() lit depuis DB en priorité, fallback JSON legacy pour migration.
save_config() écrit UNIQUEMENT en DB.
"""
import pathlib
from typing import Optional

try:
    from libs.config_manager import SESSIONS_DIR, get_session_state_path
    from libs.database import get_database
    from libs.log_emitter import emit
except ImportError:
    from config_manager import SESSIONS_DIR, get_session_state_path
    from database import get_database
    from log_emitter import emit

DEFAULT_SESSION_CONFIG = {
    "session_name": "",
    "storage_state": "",
    "max_groups_per_run": 10,
    "max_groups_per_hour": 5,
    "delay_between_groups": [60, 120],
    "max_runs_per_day": 2,
    "cooldown_between_runs_s": 7200,
    "last_run_ts": None,
    "last_run_date": None,
    "run_count_today": 0,
    "posts": [],
    "groups": [],
    "add_comments": False,
    "comments": [],
    "marketplace": {},
    "proxy": None,
    "locale": "fr-FR",
    "timezone_id": "Europe/Paris",
    "platform": "windows",
    "telegram": None,
}


class SessionManager:
    """
    Gère les sessions Playwright.
    v8: stockage 100% SQL — plus de fichiers {name}.json
    """

    def list_sessions(self) -> list:
        """Liste depuis DB en priorité, fallback sur fichiers state pour migration."""
        db = get_database()
        db_sessions = db.list_sessions()
        if db_sessions:
            return db_sessions
        # Fallback migration: sessions créées avant v8
        return sorted([p.stem.replace("_state","") for p in SESSIONS_DIR.glob("*_state.json")])

    def session_exists(self, session_name: str) -> bool:
        db = get_database()
        row = db.get_session(session_name)
        if row:
            return True
        # Fallback: fichier state existe
        return get_session_state_path(session_name).exists()

    def get_config(self, session_name: str) -> dict:
        """Charge la config depuis DB. Si absente, construit les defaults."""
        db = get_database()
        config = db.get_session(session_name)
        if config:
            # Enrichir avec les posts de la campagne si nécessaire
            return self._enrich_config(session_name, config)

        # Pas en DB → créer defaults et les persister
        config = dict(DEFAULT_SESSION_CONFIG)
        config["session_name"] = session_name
        config["storage_state"] = str(get_session_state_path(session_name))
        db.upsert_session(session_name, config)
        return config

    def _enrich_config(self, session_name: str, config: dict) -> dict:
        """Ajoute les posts/médias depuis la DB si pas déjà présents."""
        db = get_database()
        if not config.get("posts"):
            # Construire les posts depuis les médias de la session
            assets = db.get_media_assets(session_name=session_name)
            posts = []
            for asset in assets:
                posts.append({
                    "text": asset.get("description") or "",
                    "images": [asset["file_path"]],
                    "captcha": asset.get("captcha_text"),
                    "weight": 1,
                })
            config["posts"] = posts
        return config

    def save_config(self, session_name: str, config: dict) -> bool:
        """Sauvegarde la config en DB."""
        try:
            get_database().upsert_session(session_name, config)
            return True
        except Exception as e:
            emit("ERROR", "SESSION_SAVE_ERROR", session=session_name, error=str(e))
            return False

    def create_session(self, session_name: str, browser) -> bool:
        state_path = get_session_state_path(session_name)
        emit("INFO", "SESSION_CREATE_START", session=session_name)
        try:
            context = browser.new_context()
            page = context.new_page()
            page.goto("https://www.facebook.com/login")
            print(f"\n[SESSION] Connectez-vous à Facebook pour '{session_name}'")
            print("[SESSION] Appuyez sur ENTRÉE une fois connecté...")
            input()
            if "/login" in page.url:
                emit("WARN", "SESSION_LOGIN_FAILED", session=session_name)
                context.close(); return False
            context.storage_state(path=str(state_path))
            emit("SUCCESS", "SESSION_SAVED", session=session_name, path=str(state_path))
            config = dict(DEFAULT_SESSION_CONFIG)
            config["session_name"] = session_name
            config["storage_state"] = str(state_path)
            self.save_config(session_name, config)
            context.close(); return True
        except Exception as e:
            emit("ERROR", "SESSION_CREATE_ERROR", session=session_name, error=str(e))
            return False

    def restore_context(self, session_name: str, browser):
        state_path = get_session_state_path(session_name)
        if not state_path.exists():
            raise FileNotFoundError(f"Session '{session_name}' introuvable : {state_path}")
        emit("INFO", "SESSION_RESTORE", session=session_name)
        context = browser.new_context(storage_state=str(state_path))
        page = context.new_page()
        return context, page

    def check_session_valid(self, page) -> bool:
        url = page.url
        if "/login" in url or "login.php" in url:
            emit("WARN", "SESSION_EXPIRED_DETECTED")
            return False
        return True

    def save_state(self, context, session_name: str) -> bool:
        state_path = get_session_state_path(session_name)
        try:
            context.storage_state(path=str(state_path))
            # Mettre à jour le chemin en DB
            db = get_database()
            db._exec("UPDATE sessions SET storage_state_path=?,updated_at=? WHERE session_name=?",
                     (str(state_path), __import__("datetime").datetime.now().isoformat(), session_name))
            emit("INFO", "SESSION_STATE_SAVED", session=session_name)
            return True
        except Exception as e:
            emit("ERROR", "SESSION_STATE_SAVE_ERROR", session=session_name, error=str(e))
            return False

    def delete_session(self, session_name: str) -> bool:
        ok = True
        db = get_database()
        db._exec("UPDATE sessions SET active=0 WHERE session_name=?", (session_name,))
        for path in [get_session_state_path(session_name)]:
            try:
                path.unlink(missing_ok=True)
            except Exception as e:
                emit("WARN", "SESSION_DELETE_ERROR", session=session_name, error=str(e))
                ok = False
        if ok:
            emit("INFO", "SESSION_DELETED", session=session_name)
        return ok
