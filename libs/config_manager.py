"""
config_manager.py v8 — Chemins cross-platform
load_json/save_json conservés UNIQUEMENT pour selectors.json (fichier technique)
Plus de JSON pour les données métier (sessions, campaigns, groups, telegram)
"""
import sys, json, pathlib
from typing import Optional

def get_app_dir():
    if sys.platform == "win32":
        base = pathlib.Path.home() / "AppData" / "Roaming" / "bon"
    elif sys.platform == "darwin":
        base = pathlib.Path.home() / "Library" / "Application Support" / "bon"
    else:
        base = pathlib.Path.home() / ".config" / "bon"
    base.mkdir(parents=True, exist_ok=True)
    return base

APP_DIR      = get_app_dir()
SESSIONS_DIR = APP_DIR / "sessions"
LOGS_DIR     = APP_DIR / "logs"
MEDIA_DIR    = APP_DIR / "media"
CONFIG_DIR   = APP_DIR / "config"

for _dir in (SESSIONS_DIR, LOGS_DIR, MEDIA_DIR, CONFIG_DIR):
    _dir.mkdir(parents=True, exist_ok=True)


def load_json(path: pathlib.Path) -> dict:
    """Charge un fichier JSON. Usage réservé aux fichiers techniques (selectors.json)."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        print(f"[CONFIG] Erreur JSON dans {path}: {e}")
        return {}


def save_json(path: pathlib.Path, data: dict) -> bool:
    """Sauvegarde JSON. Usage réservé aux fichiers techniques (selectors.json)."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[CONFIG] Erreur sauvegarde {path}: {e}")
        return False


def list_sessions() -> list:
    """Liste les sessions (depuis DB en priorité)."""
    try:
        from libs.database import get_database
        return get_database().list_sessions()
    except Exception:
        return [p.stem.replace("_state","") for p in SESSIONS_DIR.glob("*_state.json")]


def get_session_config_path(session_name: str) -> pathlib.Path:
    """Conservé pour compatibilité legacy uniquement."""
    return SESSIONS_DIR / f"{session_name}.json"


def get_session_state_path(session_name: str) -> pathlib.Path:
    return SESSIONS_DIR / f"{session_name}_state.json"


def resolve_media_path(relative_or_absolute: str, session_name: Optional[str] = None) -> pathlib.Path:
    s = relative_or_absolute.strip()
    if "\\" in s:
        filename = pathlib.PureWindowsPath(s).name
    else:
        filename = pathlib.Path(s).name
    p = pathlib.Path(s)
    if p.is_absolute() and p.exists():
        return p
    if session_name:
        candidate = MEDIA_DIR / session_name / filename
        if candidate.exists():
            return candidate
    candidate = MEDIA_DIR / filename
    if candidate.exists():
        return candidate
    return MEDIA_DIR / filename
