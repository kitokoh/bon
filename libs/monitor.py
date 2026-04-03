"""
monitor.py v14 — Monitoring industriel

PHASE 5 : Monitoring industriel
  - Taux de succès par compte
  - Classification des erreurs
  - Actions par heure
  - Score de santé compte
  - Logs structurés JSON

Architecture :
  Monitor          → collecteur central de métriques
  ErrorClassifier  → catégorise les erreurs pour routing intelligent
  HealthScorer     → calcule score de santé 0-100 par compte
  MetricsSnapshot  → snapshot exportable en JSON
"""

import json
import time
import threading
import pathlib
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

try:
    from libs.log_emitter import emit
    from libs.database import get_database
except ImportError:
    from log_emitter import emit
    from database import get_database


# ── Classification des erreurs ────────────────────────────────────────────────

class ErrorClass(str, Enum):
    # Erreurs réseau/proxy
    PROXY_ERROR      = "proxy_error"       # proxy mort, timeout
    NETWORK_TIMEOUT  = "network_timeout"   # timeout page
    CONNECTION_RESET = "connection_reset"  # connexion coupée

    # Erreurs Facebook
    ACCOUNT_BLOCKED  = "account_blocked"   # compte suspendu/bloqué
    CHECKPOINT       = "checkpoint"        # vérification identité FB
    RATE_LIMITED     = "rate_limited"      # limite d'actions FB
    CAPTCHA          = "captcha"           # captcha non résolu
    SESSION_EXPIRED  = "session_expired"   # session expiré → re-login
    GROUP_BANNED     = "group_banned"      # banni du groupe
    POST_REJECTED    = "post_rejected"     # post refusé par FB

    # Erreurs DOM/sélecteurs
    SELECTOR_MISS    = "selector_miss"     # sélecteur introuvable
    DOM_CHANGED      = "dom_changed"       # FB a changé le DOM

    # Erreurs système
    CRASH            = "crash"             # exception non gérée
    DISK_FULL        = "disk_full"         # espace disque
    MEMORY           = "memory"            # OOM

    UNKNOWN          = "unknown"


# Mots-clés pour la classification automatique
_ERROR_PATTERNS: List[Tuple[ErrorClass, List[str]]] = [
    (ErrorClass.ACCOUNT_BLOCKED,  ["blocked", "suspended", "disabled", "bloqué", "suspendu"]),
    (ErrorClass.CHECKPOINT,       ["checkpoint", "verification", "confirm", "identity"]),
    (ErrorClass.RATE_LIMITED,     ["rate limit", "too many", "trop de", "temporarily"]),
    (ErrorClass.CAPTCHA,          ["captcha", "recaptcha", "hcaptcha", "challenge"]),
    (ErrorClass.SESSION_EXPIRED,  ["session", "login", "connexion", "expired", "expiré"]),
    (ErrorClass.GROUP_BANNED,     ["banned from group", "banni", "removed from"]),
    (ErrorClass.POST_REJECTED,    ["post rejected", "refused", "refusé", "doesn't follow"]),
    (ErrorClass.PROXY_ERROR,      ["proxy", "407", "502", "503", "tunnel"]),
    (ErrorClass.NETWORK_TIMEOUT,  ["timeout", "timed out", "timeouterror"]),
    (ErrorClass.CONNECTION_RESET, ["connection reset", "connection refused", "econnreset"]),
    (ErrorClass.SELECTOR_MISS,    ["no element", "not found", "introuvable", "locator"]),
    (ErrorClass.DOM_CHANGED,      ["dom changed", "selector changed", "element changed"]),
    (ErrorClass.DISK_FULL,        ["no space", "disk full", "enospc"]),
    (ErrorClass.MEMORY,           ["out of memory", "oom", "memoryerror"]),
]


class ErrorClassifier:
    """Classifie une erreur par analyse de mots-clés."""

    @staticmethod
    def classify(error_msg: str) -> ErrorClass:
        msg = error_msg.lower()
        for error_class, keywords in _ERROR_PATTERNS:
            if any(kw in msg for kw in keywords):
                return error_class
        return ErrorClass.UNKNOWN

    @staticmethod
    def is_fatal(error_class: ErrorClass) -> bool:
        """Erreurs fatales → arrêt du robot recommandé."""
        return error_class in (
            ErrorClass.ACCOUNT_BLOCKED,
            ErrorClass.CHECKPOINT,
            ErrorClass.GROUP_BANNED,
        )

    @staticmethod
    def is_retryable(error_class: ErrorClass) -> bool:
        """Erreurs retryables → retry avec backoff."""
        return error_class in (
            ErrorClass.NETWORK_TIMEOUT,
            ErrorClass.CONNECTION_RESET,
            ErrorClass.PROXY_ERROR,
            ErrorClass.CAPTCHA,
            ErrorClass.SELECTOR_MISS,
            ErrorClass.RATE_LIMITED,
            ErrorClass.SESSION_EXPIRED,
        )


# ── Score de santé ─────────────────────────────────────────────────────────────

@dataclass
class HealthScore:
    """Score de santé d'un compte (0-100)."""
    account: str
    score: int = 100
    status: str = "healthy"   # healthy | degraded | critical | dead
    factors: Dict[str, int] = field(default_factory=dict)
    computed_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)


class HealthScorer:
    """
    Calcule le score de santé d'un compte.

    Score initial : 100
    Pénalités :
      - Chaque échec consécutif    : -10 pts
      - Erreur fatale              : -40 pts
      - Erreur rate_limited        : -15 pts
      - Captcha non résolu         : -20 pts
      - Taux succès < 70%          : -15 pts
      - Inactivité > 24h           : -5 pts
    Récupération :
      - Succès consécutif          : +5 pts (max 100)
    """

    @staticmethod
    def compute(stats: Dict) -> HealthScore:
        account = stats.get("account", "unknown")
        score = 100
        factors: Dict[str, int] = {}

        total  = max(stats.get("total_posts", 0), 1)
        ok     = stats.get("successful_posts", 0)
        failed = stats.get("failed_posts", 0)
        consec = stats.get("consecutive_failures", 0)
        blocked = stats.get("blocked_count", 0)

        # Taux de succès
        success_rate = ok / total
        if success_rate < 0.5:
            penalty = -25
            factors["low_success_rate"] = penalty
            score += penalty
        elif success_rate < 0.7:
            penalty = -15
            factors["degraded_success_rate"] = penalty
            score += penalty

        # Échecs consécutifs
        if consec > 0:
            penalty = min(-10 * consec, -40)
            factors["consecutive_failures"] = penalty
            score += penalty

        # Comptes bloqués
        if blocked > 0:
            penalty = -30 * min(blocked, 2)
            factors["blocks"] = penalty
            score += penalty

        # Erreurs par type
        errors_by_class = stats.get("errors_by_class", {})
        fatal_count = errors_by_class.get("account_blocked", 0) + \
                      errors_by_class.get("checkpoint", 0)
        if fatal_count > 0:
            penalty = -40
            factors["fatal_errors"] = penalty
            score += penalty

        rl_count = errors_by_class.get("rate_limited", 0)
        if rl_count > 2:
            penalty = -15
            factors["rate_limited"] = penalty
            score += penalty

        cap_count = errors_by_class.get("captcha", 0)
        if cap_count > 1:
            penalty = -20
            factors["captcha_failures"] = penalty
            score += penalty

        # Inactivité
        last_activity = stats.get("last_activity_date")
        if last_activity:
            try:
                last = datetime.fromisoformat(last_activity)
                hours_inactive = (datetime.now() - last).total_seconds() / 3600
                if hours_inactive > 48:
                    penalty = -10
                    factors["inactivity_48h"] = penalty
                    score += penalty
                elif hours_inactive > 24:
                    penalty = -5
                    factors["inactivity_24h"] = penalty
                    score += penalty
            except Exception:
                pass

        score = max(0, min(100, score))

        if score >= 80:
            status = "healthy"
        elif score >= 60:
            status = "degraded"
        elif score >= 30:
            status = "critical"
        else:
            status = "dead"

        return HealthScore(account=account, score=score,
                           status=status, factors=factors)


# ── Métriques en mémoire ──────────────────────────────────────────────────────

@dataclass
class AccountMetrics:
    """Métriques temps-réel d'un compte (fenêtre glissante)."""
    account: str
    robot: str
    actions: deque = field(default_factory=lambda: deque(maxlen=1000))
    errors:  deque = field(default_factory=lambda: deque(maxlen=500))
    error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    success_count: int = 0
    failure_count: int = 0

    def record_success(self, action_type: str = "post"):
        self.actions.append({"ts": time.time(), "type": action_type, "ok": True})
        self.success_count += 1

    def record_failure(self, error_msg: str, action_type: str = "post"):
        err_class = ErrorClassifier.classify(error_msg)
        self.actions.append({"ts": time.time(), "type": action_type,
                              "ok": False, "error_class": err_class.value})
        self.errors.append({
            "ts": time.time(),
            "error_class": err_class.value,
            "msg": error_msg[:200],
        })
        self.error_counts[err_class.value] += 1
        self.failure_count += 1

    def success_rate(self, window_minutes: int = 60) -> float:
        cutoff = time.time() - window_minutes * 60
        recent = [a for a in self.actions if a["ts"] >= cutoff]
        if not recent:
            return 1.0
        return sum(1 for a in recent if a["ok"]) / len(recent)

    def actions_per_hour(self) -> float:
        cutoff = time.time() - 3600
        recent = [a for a in self.actions if a["ts"] >= cutoff]
        return len(recent)

    def to_dict(self) -> Dict:
        return {
            "account":          self.account,
            "robot":            self.robot,
            "success_count":    self.success_count,
            "failure_count":    self.failure_count,
            "success_rate_1h":  round(self.success_rate(60), 3),
            "actions_per_hour": self.actions_per_hour(),
            "error_counts":     dict(self.error_counts),
            "recent_errors":    list(self.errors)[-5:],
        }


# ── Moniteur principal ────────────────────────────────────────────────────────

class Monitor:
    """
    Collecteur central de métriques pour tous les robots/comptes.

    - Enregistre succès/échecs en temps réel
    - Calcule scores de santé
    - Exporte des snapshots JSON structurés
    - Persiste les métriques dans la base
    """

    def __init__(self, log_dir: Optional[str] = None):
        self._metrics: Dict[str, AccountMetrics] = {}
        self._lock = threading.RLock()

        if log_dir is None:
            try:
                from libs.config_manager import LOGS_DIR
                self._log_dir = LOGS_DIR
            except ImportError:
                self._log_dir = pathlib.Path("logs")
        else:
            self._log_dir = pathlib.Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)

        self._log_file = self._log_dir / "bon_monitor.jsonl"

    # ── Enregistrement ────────────────────────────────────────────────────

    def record_success(self, robot: str, account: str,
                       action_type: str = "post",
                       group_url: Optional[str] = None) -> None:
        metrics = self._get_or_create(robot, account)
        metrics.record_success(action_type)
        self._write_log({
            "event":       "SUCCESS",
            "robot":       robot,
            "account":     account,
            "action_type": action_type,
            "group_url":   group_url,
            "ts":          datetime.now().isoformat(),
        })
        emit("INFO", "MONITOR_SUCCESS",
             robot=robot, action=action_type,
             success_rate=round(metrics.success_rate(), 3),
             aph=metrics.actions_per_hour())

    def record_failure(self, robot: str, account: str,
                       error_msg: str,
                       action_type: str = "post",
                       group_url: Optional[str] = None) -> ErrorClass:
        metrics = self._get_or_create(robot, account)
        metrics.record_failure(error_msg, action_type)
        err_class = ErrorClassifier.classify(error_msg)
        is_fatal = ErrorClassifier.is_fatal(err_class)

        self._write_log({
            "event":       "FAILURE",
            "robot":       robot,
            "account":     account,
            "action_type": action_type,
            "error_class": err_class.value,
            "error_msg":   error_msg[:300],
            "is_fatal":    is_fatal,
            "group_url":   group_url,
            "ts":          datetime.now().isoformat(),
        })

        log_level = "ERROR" if is_fatal else "WARN"
        emit(log_level, "MONITOR_FAILURE",
             robot=robot, error_class=err_class.value,
             is_fatal=is_fatal, error=error_msg[:150])

        # Persister en base
        try:
            db = get_database()
            db.record_error(robot_name=robot, account_name=account,
                            group_url=group_url, error_type=err_class.value,
                            error_message=error_msg[:500])
        except Exception:
            pass

        return err_class

    # ── Snapshots ─────────────────────────────────────────────────────────

    def get_snapshot(self) -> Dict:
        """Snapshot complet de l'état du monitoring."""
        with self._lock:
            accounts_data = {}
            for key, m in self._metrics.items():
                health = self._compute_health_for_metrics(m)
                accounts_data[key] = {
                    **m.to_dict(),
                    "health_score": health.score,
                    "health_status": health.status,
                    "health_factors": health.factors,
                }

        total_aph = sum(
            d["actions_per_hour"] for d in accounts_data.values()
        )
        avg_success = (
            sum(d["success_rate_1h"] for d in accounts_data.values()) /
            max(len(accounts_data), 1)
        )

        snap = {
            "snapshot_at":        datetime.now().isoformat(),
            "active_accounts":    len(accounts_data),
            "total_aph":          round(total_aph, 1),
            "avg_success_rate":   round(avg_success, 3),
            "accounts":           accounts_data,
        }

        self._write_log({"event": "SNAPSHOT", **snap})
        return snap

    def get_account_health(self, robot: str) -> Optional[HealthScore]:
        with self._lock:
            m = self._metrics.get(robot)
        if not m:
            return None
        return self._compute_health_for_metrics(m)

    def print_dashboard(self) -> None:
        """Affiche un tableau de bord texte."""
        snap = self.get_snapshot()
        print("\n" + "=" * 60)
        print(f"  BON v14 — Monitor  [{snap['snapshot_at'][:19]}]")
        print("=" * 60)
        print(f"  Comptes actifs   : {snap['active_accounts']}")
        print(f"  Actions/heure    : {snap['total_aph']}")
        print(f"  Taux succès moy  : {snap['avg_success_rate']*100:.1f}%")
        print("-" * 60)
        for key, data in snap["accounts"].items():
            health_icon = {"healthy": "✓", "degraded": "⚠",
                           "critical": "✗", "dead": "☠"}.get(
                data["health_status"], "?")
            print(
                f"  {health_icon} {data['robot']:<18} "
                f"❤{data['health_score']:3d}  "
                f"✓{data['success_count']} ✗{data['failure_count']}  "
                f"{data['actions_per_hour']:.0f}aph  "
                f"{data['success_rate_1h']*100:.0f}% ok"
            )
            if data.get("error_counts"):
                top_errors = sorted(
                    data["error_counts"].items(),
                    key=lambda x: -x[1]
                )[:3]
                errs = " | ".join(f"{k}:{v}" for k, v in top_errors)
                print(f"    ↳ Erreurs : {errs}")
        print("=" * 60 + "\n")

    # ── Interne ───────────────────────────────────────────────────────────

    def _get_or_create(self, robot: str, account: str) -> AccountMetrics:
        with self._lock:
            if robot not in self._metrics:
                self._metrics[robot] = AccountMetrics(
                    account=account, robot=robot
                )
            return self._metrics[robot]

    def _compute_health_for_metrics(self, m: AccountMetrics) -> HealthScore:
        """Calcule le health score à partir des métriques en mémoire."""
        stats = {
            "account":              m.account,
            "total_posts":         m.success_count + m.failure_count,
            "successful_posts":    m.success_count,
            "failed_posts":        m.failure_count,
            "consecutive_failures": 0,
            "blocked_count":       m.error_counts.get("account_blocked", 0),
            "errors_by_class":     dict(m.error_counts),
        }
        # Compléter depuis DB si possible
        try:
            db = get_database()
            db_account = db.get_account(m.account)
            if db_account:
                stats.update({
                    "consecutive_failures": db_account.get("consecutive_failures", 0),
                    "last_activity_date":   db_account.get("last_activity_date"),
                })
        except Exception:
            pass

        return HealthScorer.compute(stats)

    def _write_log(self, data: Dict) -> None:
        """Écrit un événement structuré JSON dans le fichier de log."""
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass

    def get_recent_logs(self, n: int = 50) -> List[Dict]:
        """Lit les N dernières lignes du fichier de log."""
        try:
            with open(self._log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            parsed = []
            for line in lines[-n:]:
                try:
                    parsed.append(json.loads(line.strip()))
                except Exception:
                    pass
            return parsed
        except Exception:
            return []


# ── Singleton ─────────────────────────────────────────────────────────────────

_monitor: Optional[Monitor] = None
_mon_lock = threading.Lock()


def get_monitor() -> Monitor:
    global _monitor
    if _monitor is None:
        with _mon_lock:
            if _monitor is None:
                _monitor = Monitor()
    return _monitor
