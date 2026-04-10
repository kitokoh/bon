"""
session_manager.py v14 — Isolation stricte des sessions par compte

PHASE 2 : Isolation sessions
  - Chaque compte a son propre répertoire de profil Chrome
  - Chaque session utilise un proxy dédié
  - Aucun cookie ou stockage partagé
  - Sessions parallèles sûres
  - Lifecycle complet : start / stop / restart

Architecture :
  SessionManager         → orchestre toutes les sessions
  IsolatedSession        → 1 session = 1 compte = 1 profil Chrome = 1 proxy
  SessionLifecycle       → état FSM : idle → starting → running → stopping → stopped → error
"""

import os
import time
import uuid
import shutil
import threading
import pathlib
import json
import subprocess
from atexit import register as atexit_register
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Callable
from datetime import datetime

try:
    from libs.log_emitter import emit
    from libs.database import get_database
except ImportError:
    from log_emitter import emit
    from database import get_database

# ── Répertoire racine des profils Chrome isolés ──────────────────────────────
try:
    from libs.config_manager import CONFIG_DIR
    PROFILES_ROOT = CONFIG_DIR.parent / "chrome_profiles"
except ImportError:
    PROFILES_ROOT = pathlib.Path("chrome_profiles")

PROFILES_ROOT = PROFILES_ROOT.resolve()
PROFILES_ROOT.mkdir(parents=True, exist_ok=True)


# ── États de session ──────────────────────────────────────────────────────────

class SessionState(str, Enum):
    IDLE     = "idle"
    STARTING = "starting"
    RUNNING  = "running"
    STOPPING = "stopping"
    STOPPED  = "stopped"
    ERROR    = "error"


# ── Dataclass session ─────────────────────────────────────────────────────────

@dataclass
class IsolatedSession:
    """
    Représente une session isolée pour un robot/compte.

    Garanties d'isolation :
      - user_data_dir unique par session → aucun cookie partagé
      - proxy dédié (ou None si pas de proxy)
      - pas d'accès concurrent au même profil Chrome
    """
    robot_name: str
    account_name: str
    proxy_server:   Optional[str] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None

    # Géré en interne
    session_id:   str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    state:        SessionState = SessionState.IDLE
    started_at:   Optional[datetime] = None
    stopped_at:   Optional[datetime] = None
    error_msg:    Optional[str] = None
    run_count:    int = 0
    _lock:        threading.RLock = field(default_factory=threading.RLock, repr=False)

    # Référence au browser Playwright (géré par PlaywrightEngine)
    _browser_ctx: Optional[object] = field(default=None, repr=False)
    _playwright: Optional[object] = field(default=None, repr=False)

    @property
    def profile_dir(self) -> pathlib.Path:
        """
        Répertoire Chrome UNIQUE et DÉDIÉ à ce robot.
        Format : chrome_profiles/<robot_name>/
        Le répertoire persiste entre les runs pour conserver les cookies.
        """
        p = (PROFILES_ROOT / self._safe_name(self.robot_name)).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @staticmethod
    def _safe_name(name: str) -> str:
        """Convertit un nom en chemin de fichier sûr."""
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)

    @property
    def proxy_config(self) -> Optional[Dict]:
        """Retourne la config proxy Playwright ou None."""
        if not self.proxy_server:
            return None
        cfg: Dict = {"server": self.proxy_server}
        if self.proxy_username:
            cfg["username"] = self.proxy_username
        if self.proxy_password:
            cfg["password"] = self.proxy_password
        return cfg

    def is_active(self) -> bool:
        return self.state in (SessionState.STARTING, SessionState.RUNNING)

    def uptime_seconds(self) -> Optional[float]:
        if self.started_at:
            end = self.stopped_at or datetime.now()
            return (end - self.started_at).total_seconds()
        return None

    def to_dict(self) -> Dict:
        return {
            "session_id":   self.session_id,
            "robot_name":   self.robot_name,
            "account_name": self.account_name,
            "state":        self.state.value,
            "started_at":   self.started_at.isoformat() if self.started_at else None,
            "stopped_at":   self.stopped_at.isoformat() if self.stopped_at else None,
            "uptime_s":     self.uptime_seconds(),
            "run_count":    self.run_count,
            "proxy":        self.proxy_server or "none",
            "profile_dir":  str(self.profile_dir),
            "error":        self.error_msg,
        }


# ── Gestionnaire de sessions ──────────────────────────────────────────────────

class SessionManager:
    """
    Orchestre toutes les sessions isolées.

    Thread-safe. Supporte l'exécution parallèle de N sessions.
    Chaque session a son propre profil Chrome et proxy → 0 contamination.
    """

    def __init__(self):
        self._sessions: Dict[str, IsolatedSession] = {}
        self._lock = threading.RLock()

    # ── Création ──────────────────────────────────────────────────────────

    def create_session(
        self,
        robot_name: str,
        account_name: Optional[str] = None,
        proxy_server: Optional[str] = None,
        proxy_username: Optional[str] = None,
        proxy_password: Optional[str] = None,
        from_db: bool = True,
    ) -> IsolatedSession:
        """
        Crée une session isolée pour un robot.

        Si from_db=True, charge les paramètres proxy depuis la base.
        Les paramètres explicites ont priorité sur la base.
        """
        with self._lock:
            if robot_name in self._sessions:
                existing = self._sessions[robot_name]
                if existing.is_active():
                    emit("WARN", "SESSION_ALREADY_ACTIVE", robot=robot_name,
                         state=existing.state.value)
                    return existing
                # Session arrêtée → on en recrée une propre
                del self._sessions[robot_name]

            # Charger config proxy depuis DB si disponible
            if from_db:
                try:
                    db = get_database()
                    robot_cfg = db.get_robot(robot_name)
                    if robot_cfg:
                        account_name  = account_name  or robot_cfg.get("account_name", robot_name)
                        proxy_server  = proxy_server  or robot_cfg.get("proxy_server")
                        proxy_username= proxy_username or robot_cfg.get("proxy_username")
                        proxy_password= proxy_password or robot_cfg.get("proxy_password")
                except Exception as e:
                    emit("WARN", "SESSION_DB_LOAD_FAILED", robot=robot_name, error=str(e))

            session = IsolatedSession(
                robot_name=robot_name,
                account_name=account_name or robot_name,
                proxy_server=proxy_server,
                proxy_username=proxy_username,
                proxy_password=proxy_password,
            )
            self._sessions[robot_name] = session
            emit("INFO", "SESSION_CREATED", robot=robot_name,
                 proxy=proxy_server or "none",
                 profile_dir=str(session.profile_dir))
            return session

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def start_session(self, robot_name: str) -> bool:
        """Démarre une session (transition idle/stopped → running)."""
        session = self._get_session(robot_name)
        if not session:
            emit("ERROR", "SESSION_NOT_FOUND", robot=robot_name)
            return False

        with session._lock:
            if session.state == SessionState.RUNNING:
                emit("WARN", "SESSION_ALREADY_RUNNING", robot=robot_name)
                return True
            if session.state == SessionState.STARTING:
                emit("WARN", "SESSION_ALREADY_STARTING", robot=robot_name)
                return False

            session.state = SessionState.STARTING
            emit("INFO", "SESSION_STARTING", robot=robot_name,
                 session_id=session.session_id)

        last_error: Optional[Exception] = None
        for attempt in range(1, 3):
            try:
                # Vérification isolation profil
                self._verify_profile_isolation(session)

                # Ouvre un navigateur Playwright distinct pour ce robot.
                browser_ctx = self._launch_isolated_browser(session)
                if browser_ctx is None:
                    raise RuntimeError("Impossible d'ouvrir un navigateur isole")

                with session._lock:
                    session.state = SessionState.RUNNING
                    session.started_at = datetime.now()
                    session.run_count += 1
                    session.error_msg = None
                    session._browser_ctx = browser_ctx
                    session._playwright = getattr(browser_ctx, "_bon_playwright", None)

                emit("INFO", "SESSION_STARTED", robot=robot_name,
                     run_count=session.run_count,
                     profile_dir=str(session.profile_dir),
                     browser="playwright_persistent_context")
                return True

            except Exception as e:
                last_error = e
                emit("WARN", "SESSION_START_ATTEMPT_FAILED",
                     robot=robot_name, attempt=attempt, error=str(e))

                if attempt == 1:
                    try:
                        killed = self.terminate_browser_processes(robot_name)
                    except Exception:
                        killed = 0
                    if killed > 0:
                        time.sleep(1)
                        continue
                break

        with session._lock:
            session.state = SessionState.ERROR
            session.error_msg = str(last_error) if last_error else "Impossible d'ouvrir un navigateur isole"
            if session._browser_ctx:
                try:
                    session._browser_ctx.close()
                except Exception:
                    pass
                try:
                    if session._playwright:
                        session._playwright.stop()
                except Exception:
                    pass
                session._browser_ctx = None
                session._playwright = None
        self._close_playwright_runtime_if_idle()
        emit("ERROR", "SESSION_START_FAILED", robot=robot_name, error=str(last_error) if last_error else "Impossible d'ouvrir un navigateur isole")
        return False

    def stop_session(self, robot_name: str, clean_profile: bool = False) -> bool:
        """Arrête une session proprement."""
        session = self._get_session(robot_name)
        if not session:
            emit("WARN", "SESSION_NOT_FOUND_STOP", robot=robot_name)
            return False

        with session._lock:
            if session.state in (SessionState.STOPPED, SessionState.IDLE):
                return True

            session.state = SessionState.STOPPING
            emit("INFO", "SESSION_STOPPING", robot=robot_name)

        try:
            # Fermer le browser context si présent
            if session._browser_ctx:
                try:
                    self._persist_session_state(session)
                    session._browser_ctx.close()
                except Exception:
                    pass
                try:
                    pw = session._playwright
                    if pw:
                        pw.stop()
                except Exception:
                    pass
                session._browser_ctx = None
                session._playwright = None

            self._close_playwright_runtime_if_idle()

            # Optionnel : nettoyer le profil (attention = perd les cookies)
            if clean_profile and session.profile_dir.exists():
                shutil.rmtree(session.profile_dir, ignore_errors=True)
                emit("INFO", "SESSION_PROFILE_CLEANED", robot=robot_name)

            with session._lock:
                session.state = SessionState.STOPPED
                session.stopped_at = datetime.now()

            emit("INFO", "SESSION_STOPPED", robot=robot_name,
                 uptime_s=round(session.uptime_seconds() or 0, 1))
            return True

        except Exception as e:
            with session._lock:
                session.state = SessionState.ERROR
                session.error_msg = str(e)
            emit("ERROR", "SESSION_STOP_FAILED", robot=robot_name, error=str(e))
            self._close_playwright_runtime_if_idle()
            return False

    def restart_session(self, robot_name: str) -> bool:
        """Redémarre une session (stop → start)."""
        emit("INFO", "SESSION_RESTARTING", robot=robot_name)
        self.stop_session(robot_name)
        time.sleep(2)  # Pause courte avant redémarrage
        return self.start_session(robot_name)

    def _profile_dir_for_robot(self, robot_name: str) -> pathlib.Path:
        """Calcule le répertoire de profil attendu pour un robot."""
        return (PROFILES_ROOT / IsolatedSession._safe_name(robot_name)).resolve()

    def list_browser_processes(self, robot_name: str) -> List[Dict]:
        """
        Retourne les processus navigateur liés au profil du robot.

        Utile quand le process Playwright/Chrome est resté vivant après un crash
        ou une fermeture incomplète de l'app.
        """
        profile_str = str(self._profile_dir_for_robot(robot_name))
        if not profile_str:
            return []

        ps_script = (
            "$needle = [regex]::Escape('%s'); "
            "$items = @("
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.CommandLine -and $_.CommandLine -match $needle } | "
            "Select-Object ProcessId,Name,CommandLine"
            "); "
            "if ($items) { $items | ConvertTo-Json -Compress } else { '[]' }"
        ) % profile_str.replace("'", "''")

        try:
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            raw = (completed.stdout or "").strip()
            if not raw:
                return []
            payload = json.loads(raw)
            if isinstance(payload, dict):
                payload = [payload]
            results: List[Dict] = []
            for item in payload or []:
                try:
                    results.append({
                        "pid": int(item.get("ProcessId")),
                        "name": item.get("Name", ""),
                        "command_line": item.get("CommandLine", ""),
                    })
                except Exception:
                    continue
            return results
        except Exception as e:
            emit("WARN", "SESSION_PROCESS_SCAN_FAILED", robot=robot_name, error=str(e))
            return []

    def terminate_browser_processes(self, robot_name: str) -> int:
        """
        Termine les processus navigateur associés au profil du robot.

        Retourne le nombre de PIDs arrêtés avec succès.
        """
        processes = self.list_browser_processes(robot_name)
        stopped = 0
        for proc in processes:
            pid = proc.get("pid")
            if not pid:
                continue
            try:
                result = subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
                if result.returncode == 0:
                    stopped += 1
                    emit("INFO", "SESSION_BROWSER_PROCESS_KILLED",
                         robot=robot_name, pid=pid)
                else:
                    emit("WARN", "SESSION_BROWSER_PROCESS_KILL_FAILED",
                         robot=robot_name, pid=pid,
                         output=(result.stderr or result.stdout or "")[:200])
            except Exception as e:
                emit("WARN", "SESSION_BROWSER_PROCESS_KILL_ERROR",
                     robot=robot_name, pid=pid, error=str(e))
        return stopped

    # ── Lecture ───────────────────────────────────────────────────────────

    def get_session(self, robot_name: str) -> Optional[IsolatedSession]:
        return self._get_session(robot_name)

    def list_sessions(self) -> List[Dict]:
        with self._lock:
            return [s.to_dict() for s in self._sessions.values()]

    def list_active_sessions(self) -> List[str]:
        with self._lock:
            return [name for name, s in self._sessions.items() if s.is_active()]

    def session_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for s in self._sessions.values() if s.is_active())

    # ── Playwright integration ────────────────────────────────────────────

    def build_playwright_launch_args(self, session: IsolatedSession) -> Dict:
        """
        Construit les arguments de lancement Playwright pour une session isolée.

        Clé : user_data_dir = profil unique → isolation totale des cookies/storage.
        """
        args = {
            "user_data_dir": str(session.profile_dir),
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                f"--profile-directory={session.robot_name}",
            ],
        }
        if session.proxy_config:
            args["proxy"] = session.proxy_config

        return args

    def _get_playwright_runtime(self):
        """Retourne une instance Playwright sync partagée dans le process."""
        global _playwright_runtime
        with _playwright_lock:
            if _playwright_runtime is None:
                try:
                    from playwright.sync_api import sync_playwright
                except Exception as e:
                    emit("ERROR", "PLAYWRIGHT_IMPORT_FAILED", error=str(e))
                    return None
                _playwright_runtime = sync_playwright().start()
            return _playwright_runtime

    def _close_playwright_runtime_if_idle(self):
        """Ferme le runtime partagé si aucune session active ne reste."""
        global _playwright_runtime
        with _playwright_lock:
            if _playwright_runtime is not None and self.active_count() == 0:
                try:
                    _playwright_runtime.stop()
                except Exception:
                    pass
                _playwright_runtime = None

    def _launch_isolated_browser(self, session: IsolatedSession):
        """Lance un contexte navigateur persistant et isolé pour un robot."""
        launch_args = self.build_playwright_launch_args(session)
        launch_args["headless"] = False

        try:
            pw = self._get_playwright_runtime()
            if pw is None:
                return None
            context = pw.chromium.launch_persistent_context(**launch_args)

            page = None
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
            except Exception:
                pass

            if page is not None:
                current_url = getattr(page, "url", "") or ""
                if "two_step_verification" in current_url or "checkpoint" in current_url:
                    emit("WARN", "SESSION_CHECKPOINT_DETECTED",
                         robot=session.robot_name,
                         url=current_url[:180])
                else:
                    emit("INFO", "SESSION_LOGIN_READY",
                         robot=session.robot_name,
                         url=current_url[:180] if current_url else "unknown")

            emit("INFO", "SESSION_BROWSER_OPENED",
                 robot=session.robot_name,
                 profile_dir=str(session.profile_dir))
            return context
        except Exception as e:
            emit("ERROR", "SESSION_BROWSER_OPEN_FAILED",
                 robot=session.robot_name, error=str(e))
            return None

    def _persist_session_state(self, session: IsolatedSession) -> None:
        """Sauvegarde explicitement l'état du navigateur sur disque."""
        if not session._browser_ctx:
            return
        state_file = session.profile_dir / "storage_state.json"
        try:
            session._browser_ctx.storage_state(path=str(state_file))
        except Exception:
            pass

    # ── Interne ───────────────────────────────────────────────────────────

    def _get_session(self, robot_name: str) -> Optional[IsolatedSession]:
        with self._lock:
            return self._sessions.get(robot_name)

    def _verify_profile_isolation(self, session: IsolatedSession) -> None:
        """
        Vérifie qu'aucune autre session active n'utilise le même profil.
        Lève RuntimeError si conflit détecté.
        """
        profile_str = str(session.profile_dir)
        with self._lock:
            for name, other in self._sessions.items():
                if name == session.robot_name:
                    continue
                if other.is_active() and str(other.profile_dir) == profile_str:
                    raise RuntimeError(
                        f"Conflit profil Chrome : robot '{name}' utilise déjà "
                        f"'{profile_str}'. Isolation compromise."
                    )

    def stop_all(self) -> int:
        """Arrête toutes les sessions actives. Retourne le nombre arrêtées."""
        with self._lock:
            names = list(self._sessions.keys())
        count = 0
        for name in names:
            if self.stop_session(name):
                count += 1
        return count


# ── Singleton ─────────────────────────────────────────────────────────────────

_session_manager: Optional[SessionManager] = None
_sm_lock = threading.Lock()
_playwright_runtime = None
_playwright_lock = threading.Lock()


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        with _sm_lock:
            if _session_manager is None:
                _session_manager = SessionManager()
    return _session_manager


def _shutdown_playwright_on_exit():
    global _playwright_runtime
    with _playwright_lock:
        if _playwright_runtime is not None:
            try:
                _playwright_runtime.stop()
            except Exception:
                pass
            _playwright_runtime = None


atexit_register(_shutdown_playwright_on_exit)
