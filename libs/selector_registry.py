"""
selector_registry.py — Registre de sélecteurs avec fallback automatique et mise à jour CDN

CORRECTIONS v6 :
  - update_from_cdn() : validation du schéma JSON distant avant d'écraser le fichier local.
    Si la réponse ne contient pas la clé 'selectors' ou manque une clé obligatoire,
    la mise à jour est refusée et le fichier local est préservé.
  - Backup automatique avant écrasement : selectors.json.bak
  - Stratégie 4 niveaux : aria-label → data-testid → XPath sémantique → CSS (dernier recours)
"""
import json
import pathlib
import shutil
import requests
from typing import Optional
import os as _os

try:
    from libs.log_emitter import emit
    from libs.config_manager import CONFIG_DIR, load_json, save_json
except ImportError:
    from log_emitter import emit
    from config_manager import CONFIG_DIR, load_json, save_json

SELECTORS_CDN_URL = _os.environ.get("BON_SELECTORS_CDN_URL", "").strip()
CDN_TIMEOUT = int(_os.environ.get("BON_SELECTORS_CDN_TIMEOUT_S", "8"))
SELECTORS_MAX_AGE_DAYS = int(_os.environ.get("BON_SELECTORS_MAX_AGE_DAYS", "7"))

# v11 : pas d’URL CDN par défaut (évite un dépôt fictif). Activez explicitement :
#   BON_USE_CDN=1  +  BON_SELECTORS_CDN_URL=https://.../selectors.json
#   ou  python -m bon config set selectors_cdn_url <url>
BON_USE_CDN = _os.environ.get("BON_USE_CDN", "0").strip().lower() in (
    "1", "true", "yes", "on",
)
CDN_CACHE_TTL_S = int(_os.environ.get("BON_SELECTORS_CACHE_TTL_S", "3600"))

# Clés obligatoires dans selectors.json pour qu'il soit considéré valide
REQUIRED_SELECTOR_KEYS = {
    "display_input", "input", "submit",
    "show_image_input", "add_image",
}


class SelectorNotFound(Exception):
    """Levée quand aucun sélecteur ne correspond pour une clé donnée."""
    def __init__(self, key: str, tried: list):
        self.key   = key
        self.tried = tried
        super().__init__(f"Sélecteur introuvable pour '{key}'. Essayés: {tried}")


def _resolve_selectors_cdn_url() -> str:
    """URL distante : env > config_kv (DB) > vide."""
    if SELECTORS_CDN_URL:
        return SELECTORS_CDN_URL
    try:
        from libs.database import get_database
        u = (get_database().config_get("selectors_cdn_url") or "").strip()
        return u
    except Exception:
        return ""


class SelectorRegistry:
    """
    Registre de sélecteurs Playwright avec fallback automatique.

    Format selectors.json :
    {
        "version": "2026-03",
        "selectors": {
            "post_button": {
                "selectors": [
                    "[role='button'][aria-label*='Post']",
                    "[data-testid='react-composer-post-button']"
                ]
            }
        }
    }
    """

    _cdn_last_attempt_ts: float = 0.0

    def __init__(self, selectors_path: Optional[pathlib.Path] = None):
        if selectors_path is None:
            selectors_path = CONFIG_DIR / "selectors.json"
        self.selectors_path = pathlib.Path(selectors_path)
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        raw = load_json(self.selectors_path)
        if not raw:
            self._data = {"version": "legacy", "selectors": {}}
            emit("WARN", "SELECTORS_EMPTY", path=str(self.selectors_path))
        elif "selectors" in raw:
            self._data = raw
        else:
            self._data = {
                "version": "legacy",
                "selectors": {
                    key: {"selectors": [value]}
                    for key, value in raw.items()
                    if isinstance(value, str)
                }
            }
        version = self._data.get("version", "?")
        emit("INFO", "SELECTORS_LOADED",
             version=version, count=len(self._data.get("selectors", {})))
        self._check_selectors_age(version)

    def _check_selectors_age(self, version: str) -> None:
        if SELECTORS_MAX_AGE_DAYS <= 0 or version in ("legacy", "unknown", "?"):
            return
        try:
            import datetime as _dt
            parts = version.split("-")
            if len(parts) >= 2:
                selector_date = _dt.date(int(parts[0]), int(parts[1]), 1)
                age_days = (_dt.date.today() - selector_date).days
                if age_days > SELECTORS_MAX_AGE_DAYS:
                    emit("WARN", "SELECTORS_STALE",
                         version=version, age_days=age_days,
                         max_days=SELECTORS_MAX_AGE_DAYS,
                         hint="Configurez BON_SELECTORS_CDN_URL ou mettez à jour config/selectors.json")
        except Exception:
            pass

    def _validate_remote(self, remote: dict) -> tuple:
        """
        Valide le JSON distant avant d'écraser le fichier local.

        Returns:
            (bool, str) — (valide, message)
        """
        if not isinstance(remote, dict):
            return False, "Le JSON distant n'est pas un objet"
        if "selectors" not in remote:
            return False, "Clé 'selectors' absente du JSON distant"
        if not isinstance(remote["selectors"], dict):
            return False, "La clé 'selectors' doit être un objet"
        missing = REQUIRED_SELECTOR_KEYS - set(remote["selectors"].keys())
        if missing:
            return False, f"Clés obligatoires manquantes : {missing}"
        if "version" not in remote:
            return False, "Clé 'version' absente"
        return True, "OK"

    def update_from_cdn(self, force: bool = False) -> bool:
        """
        Met à jour selectors.json depuis une URL HTTPS si activé.

        v11 :
          - Requiert BON_USE_CDN=1 (ou équivalent) ET une URL (env ou DB config_kv).
          - Pas d’URL publique imposée : évite les 404 sur un dépôt inexistant.
          - Cache réseau : BON_SELECTORS_CACHE_TTL_S entre deux tentatives complètes.
        """
        if not BON_USE_CDN and not force:
            emit("DEBUG", "SELECTORS_CDN_SKIPPED",
                 reason="BON_USE_CDN désactivé (mettre BON_USE_CDN=1 pour activer)")
            return False

        cdn_url = _resolve_selectors_cdn_url()
        if not cdn_url:
            emit("INFO", "SELECTORS_CDN_NO_URL",
                 hint="Définissez BON_SELECTORS_CDN_URL ou : python -m bon config set selectors_cdn_url <url>")
            return False

        now = __import__("time").time()
        if (not force and SelectorRegistry._cdn_last_attempt_ts
                and (now - SelectorRegistry._cdn_last_attempt_ts) < CDN_CACHE_TTL_S):
            emit("DEBUG", "SELECTORS_CDN_CACHE_TTL",
                 remaining_s=round(CDN_CACHE_TTL_S - (now - SelectorRegistry._cdn_last_attempt_ts), 0))
            return False

        # Fichier local récent : moins d’appels si version locale encore « jeune »
        if self.selectors_path.exists() and not force:
            age_days = (now - self.selectors_path.stat().st_mtime) / 86400
            if age_days < SELECTORS_MAX_AGE_DAYS and age_days < 1.0:
                emit("DEBUG", "SELECTORS_FRESH", age_days=round(age_days, 3),
                     max_age=SELECTORS_MAX_AGE_DAYS)
                return False

        try:
            SelectorRegistry._cdn_last_attempt_ts = now
            resp = requests.get(cdn_url, timeout=CDN_TIMEOUT)
            resp.raise_for_status()
            remote = resp.json()

            valid, msg = self._validate_remote(remote)
            if not valid:
                emit("WARN", "SELECTORS_CDN_INVALID_SCHEMA",
                     reason=msg, url=cdn_url[:60])
                return False

            local_version = self._data.get("version", "0000-00")
            remote_version = remote.get("version", "0000-00")
            if not force and remote_version <= local_version:
                emit("INFO", "SELECTORS_UP_TO_DATE", version=local_version)
                return False

            bak_path = pathlib.Path(str(self.selectors_path) + ".bak")
            if self.selectors_path.exists():
                shutil.copy2(self.selectors_path, bak_path)
                emit("INFO", "SELECTORS_BACKUP_CREATED", path=str(bak_path))

            save_json(self.selectors_path, remote)
            self._data = remote
            emit("SUCCESS", "SELECTORS_UPDATED",
                 old=local_version, new=remote_version, source="cdn")
            return True

        except requests.RequestException:
            emit("INFO", "SELECTORS_LOCAL_FALLBACK",
                 reason="CDN inaccessible ou timeout", url=cdn_url[:60])
            return False
        except Exception as e:
            emit("WARN", "SELECTORS_CDN_ERROR", error=str(e))
            return False

    def get_candidates(self, key: str) -> list:
        sel_data = self._data.get("selectors", {}).get(key, {})
        if isinstance(sel_data, dict):
            return sel_data.get("selectors", [])
        elif isinstance(sel_data, list):
            return sel_data
        elif isinstance(sel_data, str):
            return [sel_data]
        return []

    def find(self, page, key: str, timeout: int = 5000):
        """
        Trouve le premier sélecteur fonctionnel pour une clé donnée.
        Essaie les candidats dans l'ordre (du plus stable au moins stable).

        Raises:
            SelectorNotFound si aucun sélecteur ne fonctionne
        """
        candidates = self.get_candidates(key)
        if not candidates:
            raise SelectorNotFound(key, [])

        tried = []
        for idx, selector in enumerate(candidates):
            try:
                el = page.wait_for_selector(selector, timeout=timeout)
                if el:
                    if idx > 0:
                        emit("WARN", "SELECTOR_FALLBACK",
                             key=key, used_index=idx, selector=selector[:60])
                    return el
            except Exception:
                tried.append(selector[:60])
                continue

        emit("ERROR", "SELECTOR_NOT_FOUND", key=key, tried=tried)
        try:
            screenshot_path = str(
                pathlib.Path("errors") / f"selector_fail_{key}.png"
            )
            pathlib.Path("errors").mkdir(exist_ok=True)
            page.screenshot(path=screenshot_path)
            emit("INFO", "SCREENSHOT_SAVED", path=screenshot_path)
        except Exception:
            pass
        raise SelectorNotFound(key, tried)

    def find_all(self, page, key: str, timeout: int = 3000) -> list:
        candidates = self.get_candidates(key)
        for selector in candidates:
            try:
                page.wait_for_selector(selector, timeout=timeout)
                elements = page.query_selector_all(selector)
                if elements:
                    return elements
            except Exception:
                continue
        return []

    @property
    def version(self) -> str:
        return self._data.get("version", "unknown")
