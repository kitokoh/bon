"""
stealth_profile.py v10 — Fingerprinting anti-détection natif CDP

NOUVEAUTÉS v10 :
  - UA pool mis à jour : Chrome 130-134 (avril 2026)
  - Chargement dynamique depuis config/user_agents.json (si présent)
  - Commande CLI : python -m bon update-ua  → met à jour le fichier UA
  - Sec-Ch-Ua synchronisé avec la version Chrome réelle du UA choisi
  - Fallback automatique sur pool hardcodé si fichier absent

Techniques (inchangées, toujours 10 vecteurs) :
  1. navigator.webdriver → undefined
  2. window.chrome présent
  3. navigator.languages cohérent avec locale
  4. navigator.plugins réalistes (3 plugins Chrome)
  5. deviceMemory + hardwareConcurrency
  6. Screen dimensions
  7. Canvas 2D noise unique par session
  8. WebGL vendor/renderer spoofing
  9. Permissions API
  10. Connection API réaliste
"""

import random, json, re
import pathlib
from typing import Optional

try:
    from libs.log_emitter import emit
    from libs.config_manager import CONFIG_DIR
except ImportError:
    from log_emitter import emit
    CONFIG_DIR = pathlib.Path("config")

# ── Pool UA mis à jour v10 (Chrome 130-134, avril 2026) ─────────────────────

_UA_POOL_WINDOWS_DEFAULT = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
]
_UA_POOL_MAC_DEFAULT = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
]
_UA_POOL_LINUX_DEFAULT = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
]

_HARDWARE_PROFILES = [
    (8,  4,  1920, 1080),
    (8,  8,  1920, 1080),
    (16, 8,  2560, 1440),
    (16, 12, 2560, 1440),
    (8,  4,  1366,  768),
    (8,  6,  1440,  900),
    (16, 8,  1920, 1200),
    (32, 16, 3840, 2160),
]

_UA_FILE = CONFIG_DIR / "user_agents.json"
_ua_cache: dict = {}


def _load_ua_pool(platform: str) -> list:
    """Charge le pool UA depuis fichier (si présent), sinon défauts."""
    global _ua_cache
    if not _ua_cache:
        if _UA_FILE.exists():
            try:
                data = json.loads(_UA_FILE.read_text(encoding="utf-8"))
                _ua_cache = data
                emit("DEBUG", "UA_POOL_LOADED_FROM_FILE",
                     updated_at=data.get("updated_at", "?"))
            except Exception as e:
                emit("WARN", "UA_POOL_FILE_ERROR", error=str(e))
    defaults = {
        "windows": _UA_POOL_WINDOWS_DEFAULT,
        "mac":     _UA_POOL_MAC_DEFAULT,
        "linux":   _UA_POOL_LINUX_DEFAULT,
    }
    key = platform.lower()
    if _ua_cache and key in _ua_cache:
        pool = _ua_cache[key]
        if isinstance(pool, list) and pool:
            return pool
    return defaults.get(key, _UA_POOL_WINDOWS_DEFAULT)


def _extract_chrome_version(ua: str) -> str:
    """Extrait la version Chrome depuis un UA string. Ex: '134.0.0.0'"""
    m = re.search(r"Chrome/(\d+\.\d+\.\d+\.\d+)", ua)
    return m.group(1) if m else "134.0.0.0"


def _pick_user_agent(platform: str = "windows") -> str:
    return random.choice(_load_ua_pool(platform))


def _pick_hardware_profile() -> dict:
    mem, cpu, sw, sh = random.choice(_HARDWARE_PROFILES)
    return {"deviceMemory": mem, "hardwareConcurrency": cpu,
            "screenWidth": sw, "screenHeight": sh}


def _canvas_noise_token() -> int:
    return random.randint(1, 15)


def _build_stealth_script(profile: dict, user_agent: str,
                           canvas_noise: int, locale: str) -> str:
    languages_map = {
        "fr": '["fr-FR","fr","en-US","en"]',
        "ar": '["ar","ar-MA","fr-FR","fr","en"]',
        "tr": '["tr-TR","tr","en-US","en"]',
        "en": '["en-US","en","en-GB"]',
        "de": '["de-DE","de","en-US","en"]',
        "es": '["es-ES","es","en-US","en"]',
        "pt": '["pt-BR","pt","en-US","en"]',
        "it": '["it-IT","it","en-US","en"]',
    }
    lang_prefix   = (locale or "fr-FR").split("-")[0].lower()
    languages_js  = languages_map.get(lang_prefix, '["fr-FR","fr","en-US","en"]')
    chrome_ver    = _extract_chrome_version(user_agent).split(".")[0]  # major only
    hw = profile

    return f"""
(function() {{
    'use strict';
    try {{ Object.defineProperty(navigator,'webdriver',{{get:()=>undefined,configurable:true}}); }} catch(e){{}}
    if (!window.chrome) {{
        window.chrome = {{
            app:{{isInstalled:false}},
            runtime:{{onConnect:{{addListener:()=>{{}},removeListener:()=>{{}}}},onMessage:{{addListener:()=>{{}},removeListener:()=>{{}}}}}},
        }};
    }}
    try {{ Object.defineProperty(navigator,'languages',{{get:()=>{languages_js},configurable:true}}); }} catch(e){{}}
    try {{
        const pd=[
            {{name:'Chrome PDF Plugin',filename:'internal-pdf-viewer',description:'Portable Document Format'}},
            {{name:'Chrome PDF Viewer',filename:'mhjfbmdgcfjbbpaeojofohoefgiehjai',description:''}},
            {{name:'Native Client',filename:'internal-nacl-plugin',description:''}},
        ];
        const fp=Object.create(PluginArray.prototype);
        pd.forEach((p,i)=>{{
            const pl=Object.create(Plugin.prototype);
            Object.defineProperty(pl,'name',{{get:()=>p.name}});
            Object.defineProperty(pl,'filename',{{get:()=>p.filename}});
            Object.defineProperty(pl,'description',{{get:()=>p.description}});
            Object.defineProperty(pl,'length',{{get:()=>1}});
            fp[i]=pl;
        }});
        Object.defineProperty(fp,'length',{{get:()=>pd.length}});
        Object.defineProperty(navigator,'plugins',{{get:()=>fp,configurable:true}});
    }} catch(e){{}}
    try {{ Object.defineProperty(navigator,'deviceMemory',{{get:()=>{hw['deviceMemory']},configurable:true}}); }} catch(e){{}}
    try {{ Object.defineProperty(navigator,'hardwareConcurrency',{{get:()=>{hw['hardwareConcurrency']},configurable:true}}); }} catch(e){{}}
    try {{
        Object.defineProperty(screen,'width',{{get:()=>{hw['screenWidth']}}});
        Object.defineProperty(screen,'height',{{get:()=>{hw['screenHeight']}}});
        Object.defineProperty(screen,'availWidth',{{get:()=>{hw['screenWidth']}}});
        Object.defineProperty(screen,'availHeight',{{get:()=>{hw['screenHeight']}-40}});
        Object.defineProperty(screen,'colorDepth',{{get:()=>24}});
        Object.defineProperty(screen,'pixelDepth',{{get:()=>24}});
    }} catch(e){{}}
    const _n={canvas_noise};
    const _og=HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext=function(t,...a){{
        const ctx=_og.call(this,t,...a);
        if(!ctx||t!=='2d')return ctx;
        const _ft=ctx.fillText.bind(ctx);
        ctx.fillText=function(tx,x,y,...r){{return _ft(tx,x+_n*0.0001,y+_n*0.0001,...r);}};
        const _fr=ctx.fillRect.bind(ctx);
        ctx.fillRect=function(x,y,w,h){{return _fr(x+_n*0.0001,y,w,h);}};
        return ctx;
    }};
    const _gp=WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter=function(p){{
        if(p===37445)return 'Intel Inc.';
        if(p===37446)return 'Intel Iris OpenGL Engine';
        return _gp.call(this,p);
    }};
    if(typeof WebGL2RenderingContext!=='undefined'){{
        const _g2=WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter=function(p){{
            if(p===37445)return 'Intel Inc.';
            if(p===37446)return 'Intel Iris OpenGL Engine';
            return _g2.call(this,p);
        }};
    }}
    const _oq=navigator.permissions&&navigator.permissions.query;
    if(_oq){{
        navigator.permissions.query=function(d){{
            if(d&&d.name==='notifications')return Promise.resolve({{state:'prompt',onchange:null}});
            return _oq.call(navigator.permissions,d);
        }};
    }}
    try {{
        if(navigator.connection){{
            Object.defineProperty(navigator.connection,'rtt',{{get:()=>50}});
            Object.defineProperty(navigator.connection,'downlink',{{get:()=>10}});
            Object.defineProperty(navigator.connection,'effectiveType',{{get:()=>'4g'}});
        }}
    }} catch(e){{}}
}})();
"""


class StealthProfile:
    def __init__(self, locale="fr-FR", platform="windows", seed=None):
        if seed is not None:
            random.seed(seed)
        self.locale       = locale
        self.platform     = platform
        self.user_agent   = _pick_user_agent(platform)
        self.hw_profile   = _pick_hardware_profile()
        self.canvas_noise = _canvas_noise_token()
        self.chrome_major = _extract_chrome_version(self.user_agent).split(".")[0]
        self._script      = _build_stealth_script(
            self.hw_profile, self.user_agent, self.canvas_noise, locale
        )

    def apply(self, page) -> None:
        try:
            page.add_init_script(self._script)
            page.set_extra_http_headers({
                "Accept-Language":     self._accept_language(),
                "Accept-Encoding":     "gzip, deflate, br",
                "Accept":              "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Sec-Ch-Ua":           f'"Chromium";v="{self.chrome_major}", "Google Chrome";v="{self.chrome_major}", "Not-A.Brand";v="99"',
                "Sec-Ch-Ua-Mobile":    "?0",
                "Sec-Ch-Ua-Platform":  f'"{self.platform.capitalize()}"',
                "Upgrade-Insecure-Requests": "1",
            })
            emit("DEBUG", "STEALTH_APPLIED",
                 ua=self.user_agent[-40:], chrome=self.chrome_major,
                 canvas=self.canvas_noise,
                 hw=f"{self.hw_profile['deviceMemory']}GB/{self.hw_profile['hardwareConcurrency']}c")
        except Exception as e:
            emit("WARN", "STEALTH_APPLY_FAILED", error=str(e))

    def _accept_language(self) -> str:
        m = {
            "fr": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "ar": "ar;q=1.0,fr-FR;q=0.9,en-US;q=0.8",
            "tr": "tr-TR,tr;q=0.9,en-US;q=0.8",
            "en": "en-US,en;q=0.9",
            "de": "de-DE,de;q=0.9,en-US;q=0.8",
            "es": "es-ES,es;q=0.9,en-US;q=0.8",
            "pt": "pt-BR,pt;q=0.9,en-US;q=0.8",
            "it": "it-IT,it;q=0.9,en-US;q=0.8",
        }
        return m.get((self.locale or "fr-FR").split("-")[0].lower(),
                     "fr-FR,fr;q=0.9,en-US;q=0.8")

    def to_dict(self) -> dict:
        return {
            "user_agent":    self.user_agent,
            "chrome_major":  self.chrome_major,
            "locale":        self.locale,
            "platform":      self.platform,
            "canvas_noise":  self.canvas_noise,
            "device_memory": self.hw_profile["deviceMemory"],
            "hw_concurrency":self.hw_profile["hardwareConcurrency"],
            "screen":        f"{self.hw_profile['screenWidth']}x{self.hw_profile['screenHeight']}",
        }


def get_current_chrome_major() -> str:
    """Retourne la version Chrome major actuellement utilisée (pour alertes)."""
    pool = _load_ua_pool("windows")
    ua   = pool[0] if pool else ""
    return _extract_chrome_version(ua).split(".")[0]


def save_ua_pool(windows: list, mac: list, linux: list) -> bool:
    """Sauvegarde un pool UA mis à jour dans config/user_agents.json."""
    try:
        import datetime
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "updated_at": datetime.datetime.now().strftime("%Y-%m"),
            "windows":    windows,
            "mac":        mac,
            "linux":      linux,
        }
        _UA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                             encoding="utf-8")
        global _ua_cache
        _ua_cache = data
        emit("INFO", "UA_POOL_SAVED", path=str(_UA_FILE))
        return True
    except Exception as e:
        emit("ERROR", "UA_POOL_SAVE_ERROR", error=str(e))
        return False


_profiles: dict = {}


def get_stealth_profile(locale="fr-FR", platform="windows") -> StealthProfile:
    key = f"{locale}:{platform}"
    if key not in _profiles:
        _profiles[key] = StealthProfile(locale=locale, platform=platform)
    return _profiles[key]
