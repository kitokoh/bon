"""
notifier.py v8 — Alertes Telegram avec config 100% SQL (plus de telegram.json)

Priorité config:
  1. Vars env BON_TELEGRAM_TOKEN + BON_TELEGRAM_CHAT_ID
  2. Table config_kv en DB (clés: telegram_token, telegram_chat_id)
  3. Champ "telegram" dans la config session (→ écrit en DB)
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
        # 1. Vars env
        env_token   = os.environ.get("BON_TELEGRAM_TOKEN", "").strip()
        env_chat_id = os.environ.get("BON_TELEGRAM_CHAT_ID", "").strip()
        if env_token and env_chat_id:
            self._token = env_token; self._chat_id = env_chat_id; return
        # 2. DB
        try:
            from libs.database import get_database
            db = get_database()
            cfg = db.get_telegram_config()
            if cfg:
                self._token   = cfg.get("token", "").strip() or None
                self._chat_id = cfg.get("chat_id", "").strip() or None
        except Exception:
            pass

    def configure(self, token: str, chat_id: str, persist: bool = True):
        with self._lock:
            self._token   = token.strip()
            self._chat_id = str(chat_id).strip()
            if persist:
                try:
                    from libs.database import get_database
                    get_database().set_telegram_config(self._token, self._chat_id)
                except Exception as e:
                    emit("WARN", "TELEGRAM_DB_SAVE_FAILED", error=str(e))

    def configure_from_session(self, session_config: dict):
        tg = session_config.get("telegram")
        if isinstance(tg, dict):
            token   = tg.get("token","").strip()
            chat_id = str(tg.get("chat_id","")).strip()
            if token and chat_id:
                self.configure(token, chat_id, persist=True)
        # Recharger depuis DB si pas encore configuré
        if not self.is_configured:
            self._load_config()

    @property
    def is_configured(self):
        return bool(self._token and self._chat_id)

    def send(self, text: str, parse_mode="HTML") -> bool:
        if not self.is_configured: return False
        with self._lock:
            token = self._token; chat_id = self._chat_id
        url     = _TELEGRAM_API.format(token=token)
        payload = json.dumps({"chat_id": chat_id, "text": text[:4096],
                               "parse_mode": parse_mode,
                               "disable_web_page_preview": True}).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if result.get("ok"): emit("DEBUG","TELEGRAM_SENT", chars=len(text)); return True
                emit("WARN","TELEGRAM_API_ERROR", desc=result.get("description","?")); return False
        except urllib.error.HTTPError as e:
            emit("WARN","TELEGRAM_HTTP_ERROR", code=e.code); return False
        except Exception as e:
            emit("WARN","TELEGRAM_SEND_FAILED", error=str(e)[:80]); return False

    def send_async(self, text: str):
        t = threading.Thread(target=self.send, args=(text,), daemon=True); t.start()

    def notify_blocked(self, account, reason=""):
        self.send_async(f"🔴 <b>COMPTE BLOQUÉ</b>\nCompte : <code>{account}</code>\nRaison : {reason[:200] or 'Activité suspecte détectée'}\n→ Vérifiez et relancez manuellement.")

    def notify_session_expired(self, account):
        self.send_async(f"🟡 <b>SESSION EXPIRÉE</b>\nCompte : <code>{account}</code>\n→ Relancez : <code>python -m bon login --session {account}</code>")

    def notify_captcha(self, account, url=""):
        self.send_async(f"🟠 <b>CAPTCHA DÉTECTÉ</b>\nCompte : <code>{account}</code>\nURL : {url[:80] or 'inconnue'}\n→ Intervention manuelle requise.")

    def notify_circuit_open(self, account, failures, backoff_min):
        self.send_async(f"⚠️ <b>CIRCUIT OUVERT</b>\nCompte : <code>{account}</code>\nÉchecs consécutifs : {failures}\nReprise dans : {backoff_min} min")

    def notify_run_summary(self, account, success, skipped, errors):
        total = success + skipped + errors
        if total == 0: return
        health = "✅" if errors == 0 else ("⚠️" if errors < success else "🔴")
        self.send_async(f"{health} <b>RUN TERMINÉ</b>\nCompte : <code>{account}</code>\n✓ Succès : {success} / {total}\n⏭ Ignorés : {skipped}  |  ✗ Erreurs : {errors}")

    def notify_health_alert(self, account, health_score):
        if health_score > 40: return
        emoji = "🔴" if health_score < 20 else "🟠"
        self.send_async(f"{emoji} <b>SCORE DE SANTÉ BAS</b>\nCompte : <code>{account}</code>\nScore : {health_score}/100\n→ Réduisez la fréquence.")

    def notify_dm_sent(self, account, target, dm_type="ami"):
        self.send_async(f"💬 <b>DM ENVOYÉ</b>\nCompte : <code>{account}</code>\nCible ({dm_type}) : {target[:60]}")

    def notify_subscribed(self, account, group_url):
        self.send_async(f"✅ <b>ABONNEMENT</b>\nCompte : <code>{account}</code>\nGroupe : {group_url[:80]}")


_notifier: Optional[TelegramNotifier] = None
_notifier_lock = threading.Lock()


def get_notifier() -> TelegramNotifier:
    global _notifier
    if _notifier is None:
        with _notifier_lock:
            if _notifier is None:
                _notifier = TelegramNotifier()
    return _notifier


def notify_critical(account, error_type, reason=""):
    n = get_notifier()
    if not n.is_configured: return
    if error_type == "FacebookBlockedError": n.notify_blocked(account, reason)
    elif error_type == "SessionExpiredError": n.notify_session_expired(account)
    elif error_type == "CaptchaDetectedError": n.notify_captcha(account)
    else: n.send_async(f"🔴 <b>ERREUR CRITIQUE</b>\nCompte : <code>{account}</code>\nType : {error_type}\nDétail : {reason[:200]}")


def notify_run_summary(account, success, skipped, errors):
    get_notifier().notify_run_summary(account, success, skipped, errors)
