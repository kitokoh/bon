"""
circuit_breaker.py v8 — Circuit breaker persisté en DB

NOUVEAUTES v8:
  - Etat persisté en DB (table circuit_breaker_state) → survit aux redémarrages
  - configure() par compte utilise maintenant la DB
  - Sync health_score ↔ circuit breaker dans la même transaction
  - Correction bug v7: configure() du Registry ne créait pas de config per-account
"""
import threading, time
from datetime import datetime
from enum import Enum
from typing import Optional, Dict

try:
    from libs.log_emitter import emit
except ImportError:
    from log_emitter import emit


class _State(str, Enum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"


class _AccountBreaker:
    def __init__(self, name, failure_threshold=3, recovery_timeout_s=900, half_open_max_ok=2, db=None):
        self.name               = name
        self.failure_threshold  = failure_threshold
        self.recovery_timeout_s = recovery_timeout_s
        self.half_open_max_ok   = half_open_max_ok
        self._db                = db
        self._lock              = threading.Lock()
        # Charger depuis DB si disponible
        self._load_from_db()

    def _load_from_db(self):
        if self._db:
            try:
                data = self._db.get_cb_state(self.name)
                self._state     = _State(data.get("state", "closed"))
                self._failures  = data.get("failures", 0)
                self._successes = data.get("successes", 0)
                opened_at       = data.get("opened_at")
                self._opened_at = time.monotonic() - (
                    (datetime.now() - datetime.fromisoformat(opened_at)).total_seconds()
                    if opened_at else 0
                ) if opened_at else None
                self.recovery_timeout_s = data.get("recovery_timeout_s", self.recovery_timeout_s)
                self.failure_threshold  = data.get("failure_threshold", self.failure_threshold)
                self.half_open_max_ok   = data.get("half_open_max_ok", self.half_open_max_ok)
            except Exception:
                self._state = _State.CLOSED; self._failures = 0
                self._successes = 0; self._opened_at = None
        else:
            self._state = _State.CLOSED; self._failures = 0
            self._successes = 0; self._opened_at = None

    def _persist(self):
        if self._db:
            opened_at_iso = None
            if self._opened_at and self._state == _State.OPEN:
                elapsed = time.monotonic() - self._opened_at
                from datetime import timedelta
                opened_at_iso = (datetime.now() - timedelta(seconds=elapsed)).isoformat()
            try:
                self._db.save_cb_state(
                    self.name, self._state.value, self._failures, self._successes,
                    opened_at_iso, self.recovery_timeout_s, self.failure_threshold, self.half_open_max_ok
                )
            except Exception:
                pass

    @property
    def state(self): return self._state.value

    @property
    def is_open(self): return self._state == _State.OPEN

    def allow(self):
        with self._lock:
            if self._state == _State.CLOSED:
                return True
            if self._state == _State.OPEN:
                elapsed = time.monotonic() - (self._opened_at or 0)
                if elapsed >= self.recovery_timeout_s:
                    self._state = _State.HALF_OPEN; self._successes = 0
                    emit("INFO","CIRCUIT_HALF_OPEN", compte=self.name, after_s=round(elapsed))
                    self._persist()
                    return True
                remaining = round(self.recovery_timeout_s - elapsed)
                emit("WARN","CIRCUIT_STILL_OPEN", compte=self.name, remaining_s=remaining)
                return False
            # HALF_OPEN: autorise 1 tentative
            return True

    def record_success(self):
        with self._lock:
            if self._state == _State.HALF_OPEN:
                self._successes += 1
                if self._successes >= self.half_open_max_ok:
                    self._state = _State.CLOSED; self._failures = 0; self._successes = 0
                    emit("INFO","CIRCUIT_CLOSED", compte=self.name)
                    self._persist()
            elif self._state == _State.CLOSED:
                self._failures = 0
                self._persist()

    def record_failure(self, critical=False):
        with self._lock:
            if critical or self._state == _State.HALF_OPEN:
                self._state = _State.OPEN; self._opened_at = time.monotonic()
                emit("WARN","CIRCUIT_OPEN", compte=self.name, reason="critical" if critical else "half_open_failure")
                self._persist()
                return
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._state = _State.OPEN; self._opened_at = time.monotonic()
                emit("WARN","CIRCUIT_OPEN", compte=self.name, failures=self._failures)
                self._persist()

    def configure(self, failure_threshold=None, recovery_timeout_s=None, half_open_max_ok=None):
        with self._lock:
            if failure_threshold is not None: self.failure_threshold = failure_threshold
            if recovery_timeout_s is not None: self.recovery_timeout_s = recovery_timeout_s
            if half_open_max_ok is not None: self.half_open_max_ok = half_open_max_ok
            self._persist()


class CircuitBreakerRegistry:
    """Registry singleton thread-safe — 1 breaker par compte."""

    _DEFAULT = {"failure_threshold": 3, "recovery_timeout_s": 900, "half_open_max_ok": 2}

    def __init__(self):
        self._lock     = threading.RLock()
        self._breakers: Dict[str, _AccountBreaker] = {}
        self._defaults = dict(self._DEFAULT)
        self._db       = None

    def set_database(self, db):
        """Injecte la DB pour persistance. Appeler juste après init."""
        with self._lock:
            self._db = db
            # Recharger tous les breakers existants depuis la DB
            for name, breaker in self._breakers.items():
                breaker._db = db
                breaker._load_from_db()

    def configure(self, failure_threshold=None, recovery_timeout_s=None,
                  half_open_max_ok=None, account_name=None):
        """Configure les defaults ou un compte spécifique.
        CORRECTION v8: crée le breaker du compte si nécessaire avant de configurer.
        """
        with self._lock:
            if account_name:
                # Créer ou récupérer le breaker de ce compte
                if account_name not in self._breakers:
                    self._breakers[account_name] = _AccountBreaker(
                        account_name, db=self._db, **self._defaults
                    )
                self._breakers[account_name].configure(
                    failure_threshold=failure_threshold,
                    recovery_timeout_s=recovery_timeout_s,
                    half_open_max_ok=half_open_max_ok
                )
            else:
                if failure_threshold is not None: self._defaults["failure_threshold"] = failure_threshold
                if recovery_timeout_s is not None: self._defaults["recovery_timeout_s"] = recovery_timeout_s
                if half_open_max_ok is not None: self._defaults["half_open_max_ok"] = half_open_max_ok

    def _get(self, name: str) -> _AccountBreaker:
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = _AccountBreaker(name, db=self._db, **self._defaults)
            return self._breakers[name]

    def allow(self, account_name: str) -> bool:
        return self._get(account_name).allow()

    def record_success(self, account_name: str):
        self._get(account_name).record_success()

    def record_failure(self, account_name: str, critical: bool = False):
        self._get(account_name).record_failure(critical=critical)

    def get_state(self, account_name: str) -> str:
        return self._get(account_name).state


_registry: Optional[CircuitBreakerRegistry] = None
_reg_lock = threading.Lock()


def get_circuit_breaker() -> CircuitBreakerRegistry:
    global _registry
    if _registry is None:
        with _reg_lock:
            if _registry is None:
                _registry = CircuitBreakerRegistry()
                try:
                    from libs.database import get_database
                    _registry.set_database(get_database())
                except Exception:
                    pass
    return _registry
