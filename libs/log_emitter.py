"""
log_emitter.py — Émetteur de logs JSON Lines (v14)
Imite le comportement minimal attendu par `libs/`
"""
import json
import sys
from datetime import datetime

def emit(level: str, event: str, **kwargs):
    """
    Émet un log structuré en JSON Lines sur stderr.
    """
    record = {
        "ts":    datetime.now().isoformat(timespec="milliseconds"),
        "level": level,
        "event": event,
        **kwargs,
    }
    try:
        print(json.dumps(record, ensure_ascii=False), file=sys.stderr)
    except Exception:
        pass

def write_pid():
    pass

def clear_pid():
    pass
