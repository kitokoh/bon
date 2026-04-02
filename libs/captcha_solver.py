"""
captcha_solver.py v11 — Intégration 2captcha.com (HTTP, sans dépendance SDK).

Variables :
  BON_2CAPTCHA_KEY  — clé API 2captcha
"""
from __future__ import annotations

import base64
import os
import time
from typing import Optional, Tuple

import requests

IN_URL = "https://2captcha.com/in.php"
RES_URL = "https://2captcha.com/res.php"


class CaptchaSolverError(Exception):
    pass


class CaptchaSolver:
    """Client minimal 2captcha (image, reCAPTCHA v2, hCaptcha)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or os.environ.get("BON_2CAPTCHA_KEY", "")).strip()

    def configured(self) -> bool:
        return bool(self.api_key)

    def balance(self) -> float:
        if not self.configured():
            raise CaptchaSolverError("BON_2CAPTCHA_KEY manquant")
        r = requests.get(
            RES_URL,
            params={"key": self.api_key, "action": "getbalance", "json": 1},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("status") != 1:
            raise CaptchaSolverError(data.get("request", "balance error"))
        return float(data.get("request", 0))

    def _submit(self, payload: dict) -> str:
        payload = {"key": self.api_key, "json": 1, **payload}
        r = requests.post(IN_URL, data=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != 1:
            raise CaptchaSolverError(data.get("request", "submit failed"))
        return str(data["request"])

    def _poll(self, task_id: str, timeout_s: int = 120, interval_s: float = 3.0) -> str:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            r = requests.get(
                RES_URL,
                params={
                    "key": self.api_key,
                    "action": "get",
                    "id": task_id,
                    "json": 1,
                },
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("status") == 1:
                return str(data["request"])
            if data.get("request") == "CAPCHA_NOT_READY":
                time.sleep(interval_s)
                continue
            raise CaptchaSolverError(data.get("request", "poll error"))
        raise CaptchaSolverError("timeout")

    def solve_image_bytes(self, image_bytes: bytes) -> str:
        if not self.configured():
            raise CaptchaSolverError("BON_2CAPTCHA_KEY manquant")
        b64 = base64.b64encode(image_bytes).decode("ascii")
        tid = self._submit({"method": "base64", "body": b64})
        return self._poll(tid)

    def solve_recaptcha_v2(self, sitekey: str, pageurl: str) -> str:
        tid = self._submit(
            {
                "method": "userrecaptcha",
                "googlekey": sitekey,
                "pageurl": pageurl,
            }
        )
        return self._poll(tid, timeout_s=180)

    def solve_hcaptcha(self, sitekey: str, pageurl: str) -> str:
        tid = self._submit(
            {
                "method": "hcaptcha",
                "sitekey": sitekey,
                "pageurl": pageurl,
            }
        )
        return self._poll(tid, timeout_s=180)


def test_captcha_config() -> Tuple[bool, str]:
    """Vérifie la clé 2captcha (solde)."""
    s = CaptchaSolver()
    if not s.configured():
        return False, "Définissez BON_2CAPTCHA_KEY"
    try:
        bal = s.balance()
        return True, f"OK — solde 2captcha : {bal}"
    except Exception as e:
        return False, str(e)


def _emit(event: str, **kw):
    try:
        from libs.log_emitter import emit
        emit("INFO", event, **kw)
    except Exception:
        pass


def _log_captcha_db(
    robot_name: Optional[str],
    solve_type: str,
    status: str,
    error_message: Optional[str] = None,
) -> None:
    try:
        from libs.database import get_database
        get_database().log_captcha_event(
            robot_name or "", solve_type, status, error_message
        )
    except Exception:
        pass


def extract_recaptcha_sitekey(page) -> Optional[str]:
    from urllib.parse import parse_qs, urlparse

    try:
        loc = page.locator("[data-sitekey]")
        n = loc.count()
        for i in range(min(n, 8)):
            handle = loc.nth(i)
            try:
                is_hc = handle.evaluate("el => !!el.closest('.h-captcha')")
            except Exception:
                is_hc = False
            if is_hc:
                continue
            sk = handle.get_attribute("data-sitekey")
            if sk and len(sk) > 10:
                return sk.strip()
    except Exception:
        pass
    try:
        iframe = page.locator("iframe[src*='google.com/recaptcha'], iframe[src*='recaptcha/api']")
        if iframe.count() == 0:
            return None
        src = iframe.first.get_attribute("src") or ""
        if "k=" not in src:
            return None
        qs = parse_qs(urlparse(src).query)
        k = (qs.get("k") or [None])[0]
        return k.strip() if k else None
    except Exception:
        return None


def extract_hcaptcha_sitekey(page) -> Optional[str]:
    from urllib.parse import parse_qs, urlparse

    try:
        loc = page.locator(".h-captcha[data-sitekey], div[data-sitekey].h-captcha")
        if loc.count() > 0:
            sk = loc.first.get_attribute("data-sitekey")
            if sk:
                return sk.strip()
    except Exception:
        pass
    try:
        iframe = page.locator("iframe[src*='hcaptcha.com']")
        if iframe.count() == 0:
            return None
        src = iframe.first.get_attribute("src") or ""
        qs = parse_qs(urlparse(src).query)
        for key in ("sitekey", "k"):
            v = qs.get(key)
            if v and v[0]:
                return v[0].strip()
    except Exception:
        return None


def inject_recaptcha_response(page, token: str) -> None:
    page.evaluate(
        """(t) => {
            document.querySelectorAll('textarea[name="g-recaptcha-response"]').forEach(e => {
                e.value = t;
                e.innerHTML = t;
            });
        }""",
        token,
    )


def inject_hcaptcha_response(page, token: str) -> None:
    page.evaluate(
        """(t) => {
            document.querySelectorAll('textarea[name="h-captcha-response"]').forEach(e => {
                e.value = t;
            });
        }""",
        token,
    )


def try_auto_solve_recaptcha(page, robot_name: Optional[str] = None) -> bool:
    """
    Si BON_AUTO_SOLVE_CAPTCHA=1 et BON_2CAPTCHA_KEY défini : résout reCAPTCHA v2 et injecte le token.
    """
    if os.environ.get("BON_AUTO_SOLVE_CAPTCHA", "").strip().lower() not in (
        "1", "true", "yes", "on",
    ):
        return False
    solver = CaptchaSolver()
    if not solver.configured():
        _log_captcha_db(robot_name, "recaptcha_v2", "skipped", "BON_2CAPTCHA_KEY manquant")
        return False
    sitekey = extract_recaptcha_sitekey(page)
    if not sitekey:
        _log_captcha_db(robot_name, "recaptcha_v2", "failed", "sitekey introuvable")
        return False
    try:
        _emit("CAPTCHA_SOLVE_START", robot=robot_name, kind="recaptcha_v2")
        token = solver.solve_recaptcha_v2(sitekey, page.url)
        inject_recaptcha_response(page, token)
        _log_captcha_db(robot_name, "recaptcha_v2", "success", None)
        return True
    except Exception as e:
        err = str(e)[:300]
        _log_captcha_db(robot_name, "recaptcha_v2", "failed", err)
        try:
            from libs.log_emitter import emit
            emit("WARN", "CAPTCHA_SOLVE_FAILED", robot=robot_name, error=str(e)[:120])
        except Exception:
            pass
        return False


def try_auto_solve_hcaptcha(page, robot_name: Optional[str] = None) -> bool:
    if os.environ.get("BON_AUTO_SOLVE_CAPTCHA", "").strip().lower() not in (
        "1", "true", "yes", "on",
    ):
        return False
    solver = CaptchaSolver()
    if not solver.configured():
        _log_captcha_db(robot_name, "hcaptcha", "skipped", "BON_2CAPTCHA_KEY manquant")
        return False
    sitekey = extract_hcaptcha_sitekey(page)
    if not sitekey:
        _log_captcha_db(robot_name, "hcaptcha", "failed", "sitekey introuvable")
        return False
    try:
        _emit("CAPTCHA_SOLVE_START", robot=robot_name, kind="hcaptcha")
        token = solver.solve_hcaptcha(sitekey, page.url)
        inject_hcaptcha_response(page, token)
        _log_captcha_db(robot_name, "hcaptcha", "success", None)
        return True
    except Exception as e:
        err = str(e)[:300]
        _log_captcha_db(robot_name, "hcaptcha", "failed", err)
        try:
            from libs.log_emitter import emit
            emit("WARN", "CAPTCHA_SOLVE_FAILED", robot=robot_name, error=str(e)[:120])
        except Exception:
            pass
        return False
