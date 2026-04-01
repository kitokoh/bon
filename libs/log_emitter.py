"""
log_emitter.py — Émetteur de logs structurés JSON Lines
Format lisible par l'app PyQt via un simple tail du fichier activity.jsonl

CORRECTIONS v6 :
  - Rotation log protégée par un threading.Lock (écriture + rotation atomiques)
  - _rotate_if_needed() appelée avant l'ouverture du fichier, sous le même lock
    → élimine la fenêtre de concurrence entre rename et open sur Windows
"""
import json
import datetime
import pathlib
import sys
import threading

try:
    from libs.config_manager import LOGS_DIR
except ImportError:
    LOGS_DIR = pathlib.Path("logs")
    LOGS_DIR.mkdir(exist_ok=True)

LOG_FILE         = LOGS_DIR / "activity.jsonl"
PID_FILE         = LOGS_DIR / "running.pid"
LOG_MAX_BYTES    = 5 * 1024 * 1024   # 5 Mo
LOG_BACKUP_COUNT = 3

_log_lock = threading.Lock()


def _rotate_if_needed() -> None:
    """
    Effectue une rotation si le fichier dépasse LOG_MAX_BYTES.
    Doit être appelée sous _log_lock.
    """
    try:
        if not LOG_FILE.exists() or LOG_FILE.stat().st_size < LOG_MAX_BYTES:
            return
        for i in range(LOG_BACKUP_COUNT, 0, -1):
            src = pathlib.Path(f"{LOG_FILE}.{i}")
            dst = pathlib.Path(f"{LOG_FILE}.{i + 1}")
            if src.exists():
                if i == LOG_BACKUP_COUNT:
                    src.unlink()
                else:
                    src.rename(dst)
        LOG_FILE.rename(pathlib.Path(f"{LOG_FILE}.1"))
    except Exception as e:
        print(f"[LOG] Rotation échouée : {e}", file=sys.stderr)


def emit(level: str, event: str, **kwargs) -> None:
    """
    Émet un événement de log structuré en JSON Lines.
    Format : {"ts": "...", "level": "INFO", "event": "POST_PUBLISHED", ...}

    Niveaux : DEBUG, INFO, SUCCESS, WARN, ERROR
    Thread-safe : rotation + écriture sont atomiques sous le même lock.
    """
    entry = {
        "ts":    datetime.datetime.now().isoformat(timespec="seconds"),
        "level": level,
        "event": event,
        **kwargs,
    }
    line = json.dumps(entry, ensure_ascii=False)

    with _log_lock:
        _rotate_if_needed()
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            print(f"[LOG] Impossible d'écrire dans {LOG_FILE}: {e}", file=sys.stderr)

    _console_print(level, event, kwargs)


def _console_print(level: str, event: str, details: dict) -> None:
    """Affichage coloré en console."""
    colors = {
        "DEBUG":   "\033[37m",
        "INFO":    "\033[36m",
        "SUCCESS": "\033[32m",
        "WARN":    "\033[33m",
        "ERROR":   "\033[31m",
    }
    reset = "\033[0m"
    color = colors.get(level, "")
    detail_str = " | ".join(f"{k}={v}" for k, v in details.items()) if details else ""
    msg = f"{color}[{level}] {event}{reset}"
    if detail_str:
        msg += f"  {detail_str}"
    print(msg)


def log_info(event: str, **kwargs) -> None:    emit("INFO",    event, **kwargs)
def log_success(event: str, **kwargs) -> None: emit("SUCCESS", event, **kwargs)
def log_warn(event: str, **kwargs) -> None:    emit("WARN",    event, **kwargs)
def log_error(event: str, **kwargs) -> None:   emit("ERROR",   event, **kwargs)
def log_debug(event: str, **kwargs) -> None:   emit("DEBUG",   event, **kwargs)


def write_pid() -> None:
    """Écrit le PID du processus courant."""
    import os
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception as e:
        emit("WARN", "PID_WRITE_FAILED", error=str(e))


def clear_pid() -> None:
    """Supprime le fichier PID à l'arrêt propre."""
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def get_recent_logs(n: int = 50) -> list:
    """Retourne les n derniers événements de log."""
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        result = []
        for line in lines[-n:]:
            try:
                result.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                pass
        return result
    except FileNotFoundError:
        return []
