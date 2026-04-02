"""
session_manager.py — Alias de compatibilité v8→v11

Ce module est conservé UNIQUEMENT pour la rétrocompatibilité avec
du code existant qui importe SessionManager ou DEFAULT_SESSION_CONFIG.

En v11, utilisez directement :
  from libs.robot_manager import RobotManager, DEFAULT_ROBOT_CONFIG

Toutes les méthodes délèguent à RobotManager et BONDatabase v11.
Les méthodes de session SQL obsolètes (get_session, upsert_session,
get_media_assets sur session) sont remplacées par leurs équivalents robot.
"""
import pathlib
from typing import Optional

try:
    from libs.config_manager import SESSIONS_DIR, get_session_state_path
    from libs.database import get_database
    from libs.log_emitter import emit
    from libs.robot_manager import RobotManager, DEFAULT_ROBOT_CONFIG
except ImportError:
    from config_manager import SESSIONS_DIR, get_session_state_path
    from database import get_database
    from log_emitter import emit
    from robot_manager import RobotManager, DEFAULT_ROBOT_CONFIG

# Rétrocompat : DEFAULT_SESSION_CONFIG remappé sur DEFAULT_ROBOT_CONFIG
# avec les champs legacy ajoutés pour ne pas casser les imports existants
DEFAULT_SESSION_CONFIG = {
    **DEFAULT_ROBOT_CONFIG,
    # Champs legacy v8 conservés pour compatibilité
    "session_name":    "",
    "storage_state":   "",
    "last_run_ts":     None,
    "last_run_date":   None,
    "run_count_today": 0,
    "posts":           [],
    "groups":          [],
    "add_comments":    False,
    "comments":        [],
    "marketplace":     {},
}


class SessionManager:
    """
    Alias rétrocompat v8 → délègue à RobotManager v11.
    Ne plus utiliser directement — préférer RobotManager.
    """

    def __init__(self):
        self._rm = RobotManager()

    # ── Listage ──────────────────────────────────────────────────────────

    def list_sessions(self) -> list:
        """Liste les robots (anciennement sessions)."""
        return self._rm.list_robots()

    def session_exists(self, session_name: str) -> bool:
        return self._rm.robot_exists(session_name)

    # ── Config ───────────────────────────────────────────────────────────

    def get_config(self, session_name: str) -> dict:
        """Charge la config depuis DB via RobotManager, injecte les champs legacy."""
        cfg = self._rm.get_config(session_name)
        legacy = {
            "session_name":    session_name,
            "storage_state":   cfg.get("storage_state", ""),
            "last_run_ts":     None,
            "last_run_date":   None,
            "run_count_today": 0,
            "posts":           [],
            "groups":          [],
            "add_comments":    False,
            "comments":        [],
            "marketplace":     {},
        }
        return {**legacy, **cfg}

    def save_config(self, session_name: str, config: dict) -> bool:
        """Sauvegarde la config via RobotManager."""
        return self._rm.save_config(session_name, config)

    # ── Création / restauration ───────────────────────────────────────────

    def create_session(self, session_name: str, browser) -> bool:
        """Crée une session (= robot) via login Facebook manuel."""
        return self._rm.create_robot(session_name, browser,
                                     account_name=session_name)

    def restore_context(self, session_name: str, browser):
        return self._rm.restore_context(session_name, browser)

    def check_session_valid(self, page) -> bool:
        return self._rm.check_session_valid(page)

    def save_state(self, context, session_name: str) -> bool:
        return self._rm.save_state(context, session_name)

    def delete_session(self, session_name: str) -> bool:
        return self._rm.delete_robot(session_name)
