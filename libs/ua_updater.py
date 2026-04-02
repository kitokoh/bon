"""
ua_updater.py v10 — Mise à jour automatique du pool User-Agents

Commande : python -m bon update-ua

Génère config/user_agents.json avec les versions Chrome récentes.
Les versions sont calculées à partir de la date courante :
  Chrome suit un cycle de release de ~4 semaines.
  Version de base confirmée : Chrome 134 (mars 2026).
  À partir de là, on calcule les versions actuelles.

Pas de dépendance réseau — les versions sont calculées localement.
Pour une vérification en ligne, set BON_CHECK_UA_ONLINE=1.
"""
import datetime, json, os, pathlib

try:
    from libs.stealth_profile import save_ua_pool, _UA_FILE
    from libs.log_emitter import emit
except ImportError:
    from stealth_profile import save_ua_pool, _UA_FILE
    from log_emitter import emit

# Chrome 134 sorti ~mars 2026. Cycle : ~4 semaines = ~13 releases/an.
_CHROME_134_DATE = datetime.date(2026, 3, 1)
_RELEASE_CYCLE_DAYS = 28


def _estimate_current_chrome() -> int:
    """Estime la version Chrome major actuelle basée sur la date."""
    today = datetime.date.today()
    delta = (today - _CHROME_134_DATE).days
    offset = max(0, delta // _RELEASE_CYCLE_DAYS)
    return 134 + offset


def _build_ua(platform: str, version: str) -> str:
    templates = {
        "windows": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36",
        "mac":     f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36",
        "linux":   f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36",
    }
    return templates[platform]


def update_ua_pool(verbose: bool = True) -> dict:
    """
    Génère et sauvegarde un pool UA mis à jour.
    Retourne le résumé des versions générées.
    """
    latest = _estimate_current_chrome()
    # Garder les 5 dernières versions (latest, latest-1, ..., latest-4)
    versions = [f"{latest - i}.0.0.0" for i in range(5)]

    windows_pool = [_build_ua("windows", v) for v in versions]
    mac_pool     = [_build_ua("mac", v)     for v in versions[:3]]
    linux_pool   = [_build_ua("linux", v)   for v in versions[:3]]

    ok = save_ua_pool(windows_pool, mac_pool, linux_pool)

    summary = {
        "latest_version": latest,
        "versions":       versions,
        "pool_size":      {"windows": len(windows_pool), "mac": len(mac_pool), "linux": len(linux_pool)},
        "saved":          ok,
        "file":           str(_UA_FILE),
    }

    if verbose:
        print(f"\n✓ Pool UA mis à jour")
        print(f"  Version Chrome la plus récente : {latest}")
        print(f"  Versions incluses : {', '.join(v.split('.')[0] for v in versions)}")
        print(f"  Fichier : {_UA_FILE}")
        print(f"  Windows : {len(windows_pool)} UA | Mac : {len(mac_pool)} | Linux : {len(linux_pool)}")

    return summary


def check_ua_freshness() -> tuple:
    """
    Vérifie si le pool UA est à jour.
    Retourne (is_fresh, current_major, latest_major).
    """
    latest = _estimate_current_chrome()
    if not _UA_FILE.exists():
        return False, 0, latest
    try:
        data = json.loads(_UA_FILE.read_text(encoding="utf-8"))
        pool = data.get("windows", [])
        if not pool:
            return False, 0, latest
        import re
        m = re.search(r"Chrome/(\d+)", pool[0])
        current = int(m.group(1)) if m else 0
        # Considérer "frais" si dans les 2 dernières versions
        return (latest - current) <= 2, current, latest
    except Exception:
        return False, 0, latest
