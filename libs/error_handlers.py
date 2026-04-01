"""
error_handlers.py — Décorateur retry exponentiel + détection des états bloquants Facebook

CORRECTIONS v6 :
  - retry() : paramètre no_retry_on=(SessionExpiredError, FacebookBlockedError, ...)
    Les erreurs non-récupérables sans intervention humaine ne sont jamais retentées.
    Retenter une session expirée gaspille 20-30s et peut aggraver un blocage Facebook.
  - Détection CAPTCHA : page.locator(...).count() > 0 (v3, conservé)
"""
import functools
import time
import signal
import sys
from typing import Callable, Type, Tuple

try:
    from libs.log_emitter import emit
except ImportError:
    from log_emitter import emit


# ──────────────────────────────────────────────
# Exceptions métier (définies avant retry pour pouvoir les référencer)
# ──────────────────────────────────────────────

class FacebookBlockedError(Exception):
    """Compte temporairement bloqué ou checkpoint détecté."""

class SessionExpiredError(Exception):
    """Session Facebook expirée — login requis."""

class GroupUnavailableError(Exception):
    """Groupe inaccessible (404, privé, supprimé)."""

class RateLimitError(Exception):
    """Rate limiting Facebook détecté."""

class CaptchaDetectedError(Exception):
    """CAPTCHA détecté — intervention manuelle requise."""


# Tuple des erreurs non-récupérables par défaut (ne jamais retenter)
NON_RETRYABLE: Tuple[Type[Exception], ...] = (
    SessionExpiredError,
    FacebookBlockedError,
    CaptchaDetectedError,
)


# ──────────────────────────────────────────────
# Décorateur retry exponentiel
# ──────────────────────────────────────────────

def retry(
    max_attempts: int = 3,
    delay: float = 2.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    no_retry_on: Tuple[Type[Exception], ...] = NON_RETRYABLE,
):
    """
    Décorateur retry avec backoff exponentiel.

    Args:
        max_attempts:  nombre maximum de tentatives
        delay:         délai initial entre tentatives (secondes)
        backoff:       multiplicateur du délai à chaque échec
        exceptions:    types d'exceptions qui déclenchent un retry
        no_retry_on:   sous-ensemble d'exceptions à NE JAMAIS retenter
                       (ex: SessionExpiredError, FacebookBlockedError).
                       Ces erreurs sont propagées immédiatement, même si elles
                       font partie de `exceptions`.

    Usage :
        @retry(max_attempts=3, delay=4, backoff=2)
        def _post_in_group(self, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            wait = delay
            last_error = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except no_retry_on as e:
                    # Erreur non-récupérable : propager immédiatement sans retry
                    emit("ERROR", "NON_RETRYABLE_ERROR",
                         func=func.__name__,
                         error_type=type(e).__name__,
                         error=str(e)[:120])
                    raise
                except exceptions as e:
                    last_error = e
                    if attempt == max_attempts:
                        emit("ERROR", "MAX_RETRIES_REACHED",
                             func=func.__name__,
                             attempts=max_attempts,
                             error=str(e))
                        raise
                    emit("WARN", "RETRY",
                         func=func.__name__,
                         attempt=attempt,
                         max=max_attempts,
                         wait_s=round(wait, 1),
                         error=str(e)[:80])
                    time.sleep(wait)
                    wait *= backoff
            raise last_error  # ne devrait pas être atteint
        return wrapper
    return decorator


# ──────────────────────────────────────────────
# Détection des états bloquants
# ──────────────────────────────────────────────

def check_page_state(page) -> None:
    """
    Analyse l'état courant de la page Playwright et lève une exception
    appropriée si un état bloquant est détecté.
    À appeler avant chaque action importante.
    """
    url = page.url

    # 1. Session expirée
    if "/login" in url or "login.php" in url:
        emit("ERROR", "SESSION_EXPIRED", url=url)
        raise SessionExpiredError(f"Session expirée, URL: {url}")

    # 2. Checkpoint
    if "/checkpoint" in url:
        emit("ERROR", "ACCOUNT_CHECKPOINT", url=url)
        raise FacebookBlockedError(f"Checkpoint Facebook, URL: {url}")

    # 3. Messages de blocage dans le DOM
    try:
        content = page.content()
        block_phrases = [
            "You're Temporarily Blocked",
            "Vous êtes temporairement bloqué",
            "Geçici olarak engellendi",
            "محظور مؤقتًا",
            "temporarily restricted",
        ]
        if any(phrase.lower() in content.lower() for phrase in block_phrases):
            emit("ERROR", "ACCOUNT_RATE_LIMITED", url=url)
            raise RateLimitError("Compte temporairement bloqué par Facebook")
    except (FacebookBlockedError, RateLimitError):
        raise
    except Exception:
        pass

    # 4. CAPTCHA — utiliser .count() > 0 (frame_locator() est toujours truthy)
    try:
        if page.locator("iframe[src*='recaptcha']").count() > 0:
            emit("WARN", "CAPTCHA_DETECTED", url=url)
            raise CaptchaDetectedError("reCAPTCHA détecté sur la page")
    except CaptchaDetectedError:
        raise
    except Exception:
        pass


def check_group_accessible(page) -> bool:
    """
    Vérifie si le groupe est accessible (pas de page d'erreur / contenu indisponible).
    Retourne True si accessible, False sinon.
    """
    url = page.url
    try:
        content = page.content()
        unavailable_phrases = [
            "This content isn't available",
            "Ce contenu n'est pas disponible",
            "Bu içerik mevcut değil",
            "هذا المحتوى غير متاح",
        ]
        if any(phrase.lower() in content.lower() for phrase in unavailable_phrases):
            emit("WARN", "GROUP_UNAVAILABLE", url=url)
            return False
        return True
    except Exception as e:
        emit("WARN", "GROUP_CHECK_ERROR", url=url, error=str(e))
        return False


def setup_graceful_shutdown(cleanup_fn: Callable) -> None:
    """
    Installe un handler SIGTERM pour arrêt propre.
    PyQt peut envoyer SIGTERM pour stopper le module après le groupe en cours.
    """
    def _handler(signum, frame):
        emit("INFO", "SIGTERM_RECEIVED")
        try:
            cleanup_fn()
        except Exception as e:
            emit("WARN", "CLEANUP_ERROR", error=str(e))
        sys.exit(0)

    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, _handler)
