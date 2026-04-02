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
