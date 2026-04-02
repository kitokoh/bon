"""
proxy_util.py v11 — Validation optionnelle d’un proxy HTTP(S) avant lancement navigateur.
"""
from __future__ import annotations

import os
from typing import Optional, Tuple
from urllib.parse import urlparse

import requests


def build_playwright_proxy(
    server: Optional[str],
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> Optional[dict]:
    """Construit le dict proxy Playwright à partir de champs CLI / DB."""
    if not server or not str(server).strip():
        return None
    s = str(server).strip()
    if not s.startswith(("http://", "https://", "socks5://")):
        s = "http://" + s
    d: dict = {"server": s}
    u = (username or "").strip() or None
    p = (password or "").strip() or None
    if u:
        d["username"] = u
    if p:
        d["password"] = p
    return d


def validate_proxy(
    server: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    test_url: Optional[str] = None,
    timeout: float = 12.0,
) -> Tuple[bool, str]:
    """
    Vérifie que le proxy répond (requête HTTP via le proxy).

    Returns:
        (ok, message)
    """
    test_url = test_url or os.environ.get("BON_PROXY_TEST_URL", "https://www.google.com/generate_204")
    px = build_playwright_proxy(server, username, password)
    if not px:
        return False, "Serveur proxy vide"
    parsed = urlparse(px["server"])
    if not parsed.hostname:
        return False, "URL proxy invalide"

    proxies = {
        "http":  px["server"],
        "https": px["server"],
    }
    auth = None
    if px.get("username") or px.get("password"):
        from requests.auth import HTTPProxyAuth
        auth = HTTPProxyAuth(px.get("username") or "", px.get("password") or "")

    try:
        r = requests.get(
            test_url,
            proxies=proxies,
            auth=auth,
            timeout=timeout,
            allow_redirects=True,
        )
        return True, f"HTTP {r.status_code}"
    except requests.RequestException as e:
        return False, str(e)[:200]
