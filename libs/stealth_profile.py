"""
stealth_profile.py — Fingerprinting anti-détection natif (CDP, 0 dépendance externe)

Techniques implémentées :
  1. navigator.webdriver → undefined  (détection bot #1 sur Facebook)
  2. Canvas 2D + WebGL noise          (fingerprint cross-session unique)
  3. navigator.plugins / mimeTypes    (liste réaliste, non vide)
  4. navigator.languages              (cohérent avec locale du contexte)
  5. window.chrome                    (présence obligatoire sur Chromium)
  6. User-Agent réaliste + cohérent   (sync avec locale)
  7. Screen / deviceMemory / hardwareConcurrency (profil matériel crédible)
  8. Permissions API                  (éviter notification-denied fingerprint)

Usage :
    engine = PlaywrightEngine(...)
    engine.start()
    context, page = engine.new_context(...)
    apply_stealth(page)    # ← une ligne, avant toute navigation
    page.goto("https://www.facebook.com/")

Aucune dépendance : playwright-stealth, puppeteer-extra, etc. sont superflus.
Tout passe par CDP (page.add_init_script + page.route) supporté nativement.
"""

import random
import json
from typing import Optional

try:
    from libs.log_emitter import emit
except ImportError:
    from log_emitter import emit


# ── Pool de User-Agents réalistes (Chromium 122–124, mis à jour mars 2025) ──────

_UA_POOL_WINDOWS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]
_UA_POOL_MAC = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]
_UA_POOL_LINUX = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

# Profils matériels crédibles : (deviceMemory, hardwareConcurrency, screenW, screenH)
_HARDWARE_PROFILES = [
    (8,  4,  1920, 1080),
    (8,  8,  1920, 1080),
    (16, 8,  2560, 1440),
    (16, 12, 2560, 1440),
    (8,  4,  1366,  768),
    (8,  6,  1440,  900),
    (16, 8,  1920, 1200),
]


def _pick_hardware_profile() -> dict:
    mem, cpu, sw, sh = random.choice(_HARDWARE_PROFILES)
    return {
        "deviceMemory": mem,
        "hardwareConcurrency": cpu,
        "screenWidth": sw,
        "screenHeight": sh,
    }


def _pick_user_agent(platform: str = "windows") -> str:
    pool = {
        "windows": _UA_POOL_WINDOWS,
        "mac":     _UA_POOL_MAC,
        "linux":   _UA_POOL_LINUX,
    }.get(platform.lower(), _UA_POOL_WINDOWS)
    return random.choice(pool)


def _canvas_noise_token() -> int:
    """Valeur de bruit fixe par session (reproductible mais unique)."""
    return random.randint(1, 15)


def _build_stealth_script(profile: dict, user_agent: str,
                           canvas_noise: int, locale: str) -> str:
    """
    Construit le script JS injecté avant chaque page via add_init_script.
    Toutes les modifications s'appliquent AVANT que Facebook charge son JS.
    """
    languages_map = {
        "fr": '["fr-FR", "fr", "en-US", "en"]',
        "ar": '["ar", "ar-MA", "fr-FR", "fr", "en"]',
        "tr": '["tr-TR", "tr", "en-US", "en"]',
        "en": '["en-US", "en", "en-GB"]',
        "de": '["de-DE", "de", "en-US", "en"]',
        "es": '["es-ES", "es", "en-US", "en"]',
        "pt": '["pt-BR", "pt", "en-US", "en"]',
        "it": '["it-IT", "it", "en-US", "en"]',
    }
    lang_prefix = (locale or "fr-FR").split("-")[0].lower()
    languages_js = languages_map.get(lang_prefix, '["fr-FR", "fr", "en-US", "en"]')

    hw = profile
    device_memory = hw["deviceMemory"]
    hw_concurrency = hw["hardwareConcurrency"]
    screen_w = hw["screenWidth"]
    screen_h = hw["screenHeight"]

    return f"""
(function() {{
    'use strict';

    // ── 1. navigator.webdriver → undefined ──────────────────────────────────
    // Technique : redefine via Object.defineProperty (non-configurable par défaut)
    try {{
        Object.defineProperty(navigator, 'webdriver', {{
            get: () => undefined,
            configurable: true,
        }});
    }} catch(e) {{}}

    // ── 2. window.chrome (obligatoire sur vrai Chrome) ───────────────────────
    if (!window.chrome) {{
        window.chrome = {{
            app: {{ isInstalled: false }},
            runtime: {{
                onConnect: {{ addListener: () => {{}}, removeListener: () => {{}} }},
                onMessage: {{ addListener: () => {{}}, removeListener: () => {{}} }},
            }},
        }};
    }}

    // ── 3. navigator.languages (cohérent avec locale) ───────────────────────
    try {{
        Object.defineProperty(navigator, 'languages', {{
            get: () => {languages_js},
            configurable: true,
        }});
    }} catch(e) {{}}

    // ── 4. Plugins réalistes (Chrome normal en a 3) ──────────────────────────
    try {{
        const pluginData = [
            {{ name: 'Chrome PDF Plugin',    filename: 'internal-pdf-viewer', description: 'Portable Document Format' }},
            {{ name: 'Chrome PDF Viewer',    filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' }},
            {{ name: 'Native Client',        filename: 'internal-nacl-plugin', description: '' }},
        ];
        const fakePlugins = Object.create(PluginArray.prototype);
        pluginData.forEach((p, i) => {{
            const plugin = Object.create(Plugin.prototype);
            Object.defineProperty(plugin, 'name',        {{ get: () => p.name }});
            Object.defineProperty(plugin, 'filename',    {{ get: () => p.filename }});
            Object.defineProperty(plugin, 'description', {{ get: () => p.description }});
            Object.defineProperty(plugin, 'length',      {{ get: () => 1 }});
            fakePlugins[i] = plugin;
        }});
        Object.defineProperty(fakePlugins, 'length', {{ get: () => pluginData.length }});
        Object.defineProperty(navigator, 'plugins', {{
            get: () => fakePlugins,
            configurable: true,
        }});
    }} catch(e) {{}}

    // ── 5. deviceMemory + hardwareConcurrency ────────────────────────────────
    try {{
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {device_memory},
            configurable: true,
        }});
    }} catch(e) {{}}
    try {{
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {hw_concurrency},
            configurable: true,
        }});
    }} catch(e) {{}}

    // ── 6. Screen dimensions ─────────────────────────────────────────────────
    try {{
        Object.defineProperty(screen, 'width',       {{ get: () => {screen_w} }});
        Object.defineProperty(screen, 'height',      {{ get: () => {screen_h} }});
        Object.defineProperty(screen, 'availWidth',  {{ get: () => {screen_w} }});
        Object.defineProperty(screen, 'availHeight', {{ get: () => {screen_h} - 40 }});
        Object.defineProperty(screen, 'colorDepth',  {{ get: () => 24 }});
        Object.defineProperty(screen, 'pixelDepth',  {{ get: () => 24 }});
    }} catch(e) {{}}

    // ── 7. Canvas 2D noise (fingerprint unique par session) ──────────────────
    // Modifie fillText/fillRect d'un pixel imperceptible, rend le hash unique
    const _noise = {canvas_noise};
    const _origGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(type, ...args) {{
        const ctx = _origGetContext.call(this, type, ...args);
        if (!ctx || type !== '2d') return ctx;
        const _origFillText = ctx.fillText.bind(ctx);
        ctx.fillText = function(text, x, y, ...rest) {{
            return _origFillText(text, x + _noise * 0.0001, y + _noise * 0.0001, ...rest);
        }};
        const _origFillRect = ctx.fillRect.bind(ctx);
        ctx.fillRect = function(x, y, w, h) {{
            return _origFillRect(x + _noise * 0.0001, y, w, h);
        }};
        return ctx;
    }};

    // ── 8. WebGL vendor / renderer spoofing ──────────────────────────────────
    const _origGetParam = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {{
        if (param === 37445) return 'Intel Inc.';            // UNMASKED_VENDOR_WEBGL
        if (param === 37446) return 'Intel Iris OpenGL Engine'; // UNMASKED_RENDERER_WEBGL
        return _origGetParam.call(this, param);
    }};
    if (typeof WebGL2RenderingContext !== 'undefined') {{
        const _origGet2 = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(param) {{
            if (param === 37445) return 'Intel Inc.';
            if (param === 37446) return 'Intel Iris OpenGL Engine';
            return _origGet2.call(this, param);
        }};
    }}

    // ── 9. Permissions API (éviter fingerprint via "denied") ─────────────────
    const _origQuery = navigator.permissions && navigator.permissions.query;
    if (_origQuery) {{
        navigator.permissions.query = function(desc) {{
            if (desc && desc.name === 'notifications') {{
                return Promise.resolve({{ state: 'prompt', onchange: null }});
            }}
            return _origQuery.call(navigator.permissions, desc);
        }};
    }}

    // ── 10. Connection API réaliste ──────────────────────────────────────────
    try {{
        if (navigator.connection) {{
            Object.defineProperty(navigator.connection, 'rtt',           {{ get: () => 50 }});
            Object.defineProperty(navigator.connection, 'downlink',      {{ get: () => 10 }});
            Object.defineProperty(navigator.connection, 'effectiveType', {{ get: () => '4g' }});
        }}
    }} catch(e) {{}}

}})();
"""


class StealthProfile:
    """
    Applique un profil de furtivité cohérent à une page Playwright.

    Chaque instance mémorise un profil stable pour toute la durée d'une session
    (user-agent, hardware, canvas noise). Cela garantit la cohérence si Facebook
    compare des signatures entre requêtes d'une même session.

    Usage:
        stealth = StealthProfile(locale="fr-FR", platform="windows")
        stealth.apply(page)   # avant page.goto(...)
    """

    def __init__(
        self,
        locale: str = "fr-FR",
        platform: str = "windows",
        seed: Optional[int] = None,
    ):
        """
        Args:
            locale:    locale du contexte Playwright (ex: "fr-FR", "ar-MA")
            platform:  "windows" | "mac" | "linux"
            seed:      entier pour reproductibilité (tests). None = aléatoire.
        """
        if seed is not None:
            random.seed(seed)

        self.locale       = locale
        self.platform     = platform
        self.user_agent   = _pick_user_agent(platform)
        self.hw_profile   = _pick_hardware_profile()
        self.canvas_noise = _canvas_noise_token()
        self._script      = _build_stealth_script(
            self.hw_profile, self.user_agent,
            self.canvas_noise, locale
        )

    def apply(self, page) -> None:
        """
        Injecte le script de furtivité dans la page.

        DOIT être appelé avant page.goto().
        Le script s'exécutera au tout début de chaque nouveau document chargé.
        """
        try:
            page.add_init_script(self._script)
            # Synchronise aussi le user-agent au niveau CDP
            page.set_extra_http_headers({
                "Accept-Language": self._accept_language(),
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": f'"{self.platform.capitalize()}"',
                "Upgrade-Insecure-Requests": "1",
            })
            emit("DEBUG", "STEALTH_APPLIED",
                 ua=self.user_agent[-40:],
                 canvas_noise=self.canvas_noise,
                 hw=f"{self.hw_profile['deviceMemory']}GB/{self.hw_profile['hardwareConcurrency']}cores")
        except Exception as e:
            emit("WARN", "STEALTH_APPLY_FAILED", error=str(e))

    def _accept_language(self) -> str:
        lang_prefix = (self.locale or "fr-FR").split("-")[0].lower()
        mapping = {
            "fr": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "ar": "ar;q=1.0,fr-FR;q=0.9,en-US;q=0.8",
            "tr": "tr-TR,tr;q=0.9,en-US;q=0.8",
            "en": "en-US,en;q=0.9",
            "de": "de-DE,de;q=0.9,en-US;q=0.8",
            "es": "es-ES,es;q=0.9,en-US;q=0.8",
            "pt": "pt-BR,pt;q=0.9,en-US;q=0.8",
            "it": "it-IT,it;q=0.9,en-US;q=0.8",
        }
        return mapping.get(lang_prefix, "fr-FR,fr;q=0.9,en-US;q=0.8")

    def to_dict(self) -> dict:
        """Sérialise le profil pour audit/logging."""
        return {
            "user_agent":        self.user_agent,
            "locale":            self.locale,
            "platform":          self.platform,
            "canvas_noise":      self.canvas_noise,
            "device_memory":     self.hw_profile["deviceMemory"],
            "hw_concurrency":    self.hw_profile["hardwareConcurrency"],
            "screen":            f"{self.hw_profile['screenWidth']}x{self.hw_profile['screenHeight']}",
        }


# ── Singleton par locale (cohérence sur la durée d'un run) ───────────────────

_profiles: dict = {}


def get_stealth_profile(locale: str = "fr-FR",
                         platform: str = "windows") -> StealthProfile:
    """
    Retourne (ou crée) un profil de furtivité stable pour une locale donnée.
    Un seul profil par (locale, platform) par processus → cohérence garantie.
    """
    key = f"{locale}:{platform}"
    if key not in _profiles:
        _profiles[key] = StealthProfile(locale=locale, platform=platform)
    return _profiles[key]
