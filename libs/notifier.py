"""
notifier.py v10 — Alertes Telegram robustes, multi-robot

Config par priorité (corrigé v10) :
  1. Vars env BON_TELEGRAM_TOKEN + BON_TELEGRAM_CHAT_ID  (global)
  2. config_kv DB : clés "telegram_token", "telegram_chat_id"  (global persisté)
  3. Champs telegram_token / telegram_chat_id du robot en DB  (par robot)

BUG v9 corrigé : get_telegram_config() n'existait pas dans database.py v9.
  → Remplacé par db.config_get() + fallback sur champs robots.
"""
import os, json, threading, urllib.request, urllib.error
from typing import Optional

try:
    from libs.log_emitter import emit
except ImportError:
    from log_emitter import emit

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
_TIMEOUT_S    = 8


class TelegramNotifier:
    def __init__(self):
        self._token:   Optional[str] = None
        self._chat_id: Optional[str] = None
        self._lock = threading.Lock()
        self._load_config()

    def _load_config(self):
        # 1. Vars env (priorité absolue)
        t = os.environ.get("BON_TELEGRAM_TOKEN", "").strip()
        c = os.environ.get("BON_TELEGRAM_CHAT_ID", "").strip()
        if t and c:
            self._token = t; self._chat_id = c; return
        # 2. DB config_kv  (BUG v9 corrigé : config_get au lieu de get_telegram_config)
        try:
            from libs.database import get_database
            db = get_database()
            t = (db.config_get("telegram_token") or "").strip()
            c = (db.config_get("telegram_chat_id") or "").strip()
            if t and c:
                self._token = t; self._chat_id = c; return
        except Exception:
            pass

    def configure(self, token: str, chat_id: str, persist: bool = True):
        with self._lock:
            self._token   = token.strip()
            self._chat_id = str(chat_id).strip()
            if persist:
                try:
                    from libs.database import get_database
                    db = get_database()
                    db.config_set("telegram_token",   self._token)
                    db.config_set("telegram_chat_id", self._chat_id)
                except Exception as e:
                    emit("WARN", "TELEGRAM_DB_SAVE_FAILED", error=str(e))

    def configure_from_robot(self, robot_config: dict):
        """Configure depuis la config robot (champs telegram_token/chat_id)."""
        # Cas 1 : champs directs dans robot config
        token   = (robot_config.get("telegram_token") or "").strip()
        chat_id = str(robot_config.get("telegram_chat_id") or "").strip()
        # Cas 2 : sous-dict "telegram"
        if not token:
            tg = robot_config.get("telegram") or {}
            if isinstance(tg, dict):
                token   = (tg.get("token") or "").strip()
                chat_id = str(tg.get("chat_id") or "").strip()
        if token and chat_id:
            self.configure(token, chat_id, persist=True)
        elif not self.is_configured:
            self._load_config()

    @property
    def is_configured(self):
        return bool(self._token and self._chat_id)

    def send(self, text: str, parse_mode="HTML") -> bool:
        if not self.is_configured: return False
        with self._lock:
            token = self._token; chat_id = self._chat_id
        url     = _TELEGRAM_API.format(token=token)
        payload = json.dumps({
            "chat_id": chat_id, "text": text[:4096],
            "parse_mode": parse_mode, "disable_web_page_preview": True,
        }).encode("utf-8")
        try:
            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if result.get("ok"):
                    emit("DEBUG", "TELEGRAM_SENT", chars=len(text)); return True
                emit("WARN", "TELEGRAM_API_ERROR", desc=result.get("description","?")); return False
        except urllib.error.HTTPError as e:
            emit("WARN", "TELEGRAM_HTTP_ERROR", code=e.code); return False
        except Exception as e:
            emit("WARN", "TELEGRAM_SEND_FAILED", error=str(e)[:80]); return False

    def send_async(self, text: str):
        threading.Thread(target=self.send, args=(text,), daemon=True).start()

    def notify_blocked(self, robot, reason=""):
        self.send_async(f"🔴 <b>ROBOT BLOQUÉ</b>\nRobot : <code>{robot}</code>\nRaison : {reason[:200] or 'Activité suspecte'}\n→ Vérifiez et relancez manuellement.")

    def notify_session_expired(self, robot):
        self.send_async(f"🟡 <b>SESSION EXPIRÉE</b>\nRobot : <code>{robot}</code>\n→ <code>python -m bon robot verify --robot {robot}</code>")

    def notify_captcha(self, robot, url=""):
        self.send_async(f"🟠 <b>CAPTCHA</b>\nRobot : <code>{robot}</code>\nURL : {url[:80] or 'inconnue'}\n→ Intervention manuelle requise.")

    def notify_circuit_open(self, robot, failures, backoff_min):
        self.send_async(f"⚠️ <b>CIRCUIT OUVERT</b>\nRobot : <code>{robot}</code>\nÉchecs : {failures} | Reprise dans : {backoff_min} min")

    def notify_run_summary(self, robot, success, skipped, errors):
        total = success + skipped + errors
        if not total: return
        h = "✅" if not errors else ("⚠️" if errors < success else "🔴")
        self.send_async(f"{h} <b>RUN TERMINÉ</b>\nRobot : <code>{robot}</code>\n✓ {success}/{total}  ⏭ {skipped}  ✗ {errors}")

    def notify_health_alert(self, robot, score):
        if score > 40: return
        self.send_async(f"{'🔴' if score<20 else '🟠'} <b>SCORE BAS</b>\nRobot : <code>{robot}</code>\nScore : {score}/100")

    def notify_dm_sent(self, robot, target, dm_type="ami"):
        self.send_async(f"💬 <b>DM ENVOYÉ</b>\nRobot : <code>{robot}</code>\nCible ({dm_type}) : {target[:60]}")

    def notify_subscribed(self, robot, group_url):
        self.send_async(f"✅ <b>ABONNEMENT</b>\nRobot : <code>{robot}</code>\nGroupe : {group_url[:80]}")

    def notify_ua_outdated(self, robot, current_version, latest_version):
        self.send_async(f"🔧 <b>UA OBSOLÈTE</b>\nRobot : <code>{robot}</code>\nActuel : Chrome/{current_version} | Dernier : Chrome/{latest_version}\n→ <code>python -m bon update-ua</code>")


_notifier: Optional[TelegramNotifier] = None
_notifier_lock = threading.Lock()


def get_notifier() -> TelegramNotifier:
    global _notifier
    if _notifier is None:
        with _notifier_lock:
            if _notifier is None:
                _notifier = TelegramNotifier()
    return _notifier


def notify_critical(robot, error_type, reason=""):
    n = get_notifier()
    if not n.is_configured: return
    if error_type == "FacebookBlockedError":    n.notify_blocked(robot, reason)
    elif error_type == "SessionExpiredError":   n.notify_session_expired(robot)
    elif error_type == "CaptchaDetectedError":  n.notify_captcha(robot)
    else: n.send_async(f"🔴 <b>ERREUR</b>\nRobot : <code>{robot}</code>\n{error_type}: {reason[:200]}")


def notify_run_summary(robot, success, skipped, errors):
    get_notifier().notify_run_summary(robot, success, skipped, errors)
