"""
config_validator.py — Validation de la configuration de session au démarrage
Vérifie les URLs de groupes, les chemins d'images, les paramètres obligatoires.

CORRECTIONS v5 :
  - Validation locale et timezone_id contre listes Playwright connues
  - Validation proxy (format dict attendu)
  - Validation max_groups_per_hour
"""
import pathlib
import re
from typing import Optional

try:
    from libs.log_emitter import emit
    from libs.config_manager import resolve_media_path
except ImportError:
    from log_emitter import emit
    from config_manager import resolve_media_path

FB_GROUP_RE = re.compile(
    r"^https?://(?:www\.)?facebook\.com/groups/[\w./-]+/?$"
)

# Locales valides Playwright (sous-ensemble courant — non exhaustif)
VALID_LOCALES = {
    "fr-FR", "fr-BE", "fr-CH", "fr-CA",
    "en-US", "en-GB", "en-AU", "en-CA",
    "ar-MA", "ar-SA", "ar-AE", "ar-DZ", "ar-TN",
    "tr-TR", "de-DE", "es-ES", "es-MX", "pt-BR",
    "it-IT", "nl-NL", "pl-PL", "ru-RU", "zh-CN",
}

# Timezones valides Playwright (IANA — sous-ensemble courant)
VALID_TIMEZONES = {
    "Europe/Paris", "Europe/Brussels", "Europe/Zurich",
    "Europe/London", "Europe/Berlin", "Europe/Madrid",
    "Europe/Rome", "Europe/Amsterdam", "Europe/Warsaw",
    "Africa/Casablanca", "Africa/Algiers", "Africa/Tunis",
    "Asia/Dubai", "Asia/Riyadh", "Asia/Istanbul",
    "America/New_York", "America/Chicago", "America/Los_Angeles",
    "America/Toronto", "America/Sao_Paulo",
    "Asia/Shanghai", "Asia/Tokyo", "Australia/Sydney",
    "UTC",
}


class ConfigError(Exception):
    """Erreur de configuration bloquante."""
    pass


class ConfigWarning(Exception):
    """Avertissement de configuration non bloquant."""
    pass


def validate_session_config(config: dict, session_name: str) -> list[str]:
    """
    Valide la configuration d'une session.

    Returns:
        Liste de messages d'avertissement (vide = tout OK)

    Raises:
        ConfigError si une erreur bloquante est détectée
    """
    warnings = []
    errors = []

    # ── Champs obligatoires ─────────────────────────────────
    if not config.get("session_name"):
        errors.append("session_name manquant")

    if not config.get("storage_state"):
        errors.append("storage_state manquant (session non créée ?)")
    elif not pathlib.Path(config["storage_state"]).exists():
        errors.append(
            f"Fichier session introuvable : {config['storage_state']}\n"
            f"  → Lancez : python -m bon login --session {session_name}"
        )

    # ── Groupes ─────────────────────────────────────────────
    groups = config.get("groups", [])
    if not groups:
        warnings.append("Aucun groupe configuré — rien à publier")
    else:
        invalid_groups = []
        for url in groups:
            if not FB_GROUP_RE.match(url):
                invalid_groups.append(url)
        if invalid_groups:
            warnings.append(
                f"{len(invalid_groups)} URL(s) de groupe invalide(s) :\n" +
                "\n".join(f"  • {u}" for u in invalid_groups[:5])
            )

    # ── Posts ────────────────────────────────────────────────
    posts = config.get("posts", [])
    if not posts:
        warnings.append("Aucun post configuré — rien à publier")
    else:
        missing_images = []
        for i, post in enumerate(posts):
            if not post.get("text", "").strip():
                warnings.append(f"Post #{i+1} : texte vide")
            image = post.get("image", "") or (post.get("images", [""])[0] if post.get("images") else "")
            if image:
                resolved = resolve_media_path(image, session_name)
                if not resolved.exists():
                    missing_images.append(str(resolved))
        if missing_images:
            warnings.append(
                f"{len(missing_images)} image(s) introuvable(s) :\n" +
                "\n".join(f"  • {p}" for p in missing_images[:5])
            )

    # ── Paramètres numériques ────────────────────────────────
    max_groups = config.get("max_groups_per_run", 10)
    if not isinstance(max_groups, int) or max_groups < 1:
        warnings.append(f"max_groups_per_run invalide ({max_groups}) → forcé à 10")

    max_per_hour = config.get("max_groups_per_hour", 5)
    if not isinstance(max_per_hour, int) or not (1 <= max_per_hour <= 20):
        warnings.append(
            f"max_groups_per_hour invalide ({max_per_hour}) — doit être entre 1 et 20 → forcé à 5"
        )

    delay = config.get("delay_between_groups", [60, 120])
    if not (isinstance(delay, list) and len(delay) == 2 and delay[0] <= delay[1]):
        warnings.append(f"delay_between_groups invalide ({delay}) → valeur défaut [60, 120]")

    max_runs = config.get("max_runs_per_day", 2)
    if not isinstance(max_runs, int) or max_runs < 1:
        warnings.append(f"max_runs_per_day invalide ({max_runs}) → forcé à 2")

    # ── Locale et timezone (valeurs Playwright connues) ──────
    locale = config.get("locale", "fr-FR")
    if locale not in VALID_LOCALES:
        warnings.append(
            f"locale '{locale}' non reconnue dans la liste Playwright validée. "
            f"Le contexte pourrait planter silencieusement. "
            f"Valeurs acceptées : {', '.join(sorted(VALID_LOCALES)[:8])}..."
        )

    timezone = config.get("timezone_id", "Europe/Paris")
    if timezone not in VALID_TIMEZONES:
        warnings.append(
            f"timezone_id '{timezone}' non reconnue dans la liste Playwright validée. "
            f"Le contexte pourrait planter silencieusement. "
            f"Valeurs acceptées : {', '.join(sorted(VALID_TIMEZONES)[:8])}..."
        )

    # ── Proxy (format attendu) ───────────────────────────────
    proxy = config.get("proxy")
    if proxy is not None:
        if not isinstance(proxy, dict):
            errors.append(
                f"proxy doit être un dict ou null, reçu : {type(proxy).__name__}. "
                f"Format attendu : {{\"server\": \"http://host:port\", "
                f"\"username\": \"u\", \"password\": \"p\"}}"
            )
        elif "server" not in proxy:
            errors.append(
                "proxy.server manquant. "
                "Format attendu : {\"server\": \"http://host:port\"}"
            )
        else:
            server = proxy["server"]
            if not (server.startswith("http://") or server.startswith("https://")
                    or server.startswith("socks5://")):
                warnings.append(
                    f"proxy.server '{server}' — protocole inhabituel. "
                    f"Playwright accepte http://, https://, socks5://"
                )

    # ── Émission des logs ────────────────────────────────────
    for w in warnings:
        emit("WARN", "CONFIG_WARNING", session=session_name, msg=w)

    if errors:
        error_text = "\n".join(f"  ✗ {e}" for e in errors)
        emit("ERROR", "CONFIG_INVALID", session=session_name, count=len(errors))
        raise ConfigError(
            f"Configuration invalide pour '{session_name}' :\n{error_text}"
        )

    if not warnings:
        emit("INFO", "CONFIG_OK", session=session_name,
             groups=len(groups), posts=len(posts))

    return warnings


def validate_selectors(selectors_data: dict) -> list[str]:
    """
    Vérifie que le fichier selectors.json contient bien les clés essentielles.

    Returns:
        Liste d'avertissements (vide = OK)
    """
    warnings = []
    required_keys = [
        "display_input", "input", "submit",
        "show_image_input", "add_image",
    ]
    sel = selectors_data.get("selectors", selectors_data)  # support ancien format
    for key in required_keys:
        if key not in sel:
            warnings.append(f"Sélecteur manquant : '{key}'")

    version = selectors_data.get("version", "legacy")
    if version == "legacy":
        warnings.append(
            "Sélecteurs en format legacy (ancien format plat). "
            "Migrez vers le format v2 avec listes de fallback."
        )

    # Vérifier que les sélecteurs de thème utilisent {theme_index} et non 'index'
    theme_candidates = sel.get("theme", [])
    if isinstance(theme_candidates, list):
        legacy_theme = [s for s in theme_candidates if "index" in s and "{theme_index}" not in s]
        if legacy_theme:
            warnings.append(
                f"{len(legacy_theme)} sélecteur(s) de thème utilisent l'ancien placeholder "
                f"'index' (littéral) au lieu de '{{theme_index}}'. "
                f"Migrez pour éviter les remplacements silencieusement incorrects."
            )

    for w in warnings:
        emit("WARN", "SELECTORS_WARNING", msg=w)

    return warnings

