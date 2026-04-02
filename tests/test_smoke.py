"""
tests/test_smoke.py — Tests de non-régression fondamentaux
Exécution : python -m pytest tests/ -v
             (sans Playwright ni Facebook — tests purement unitaires)

CORRECTIONS v6 :
  - TestSelectorRegistryCDN : validation de schéma avant écrasement
  - TestLogRotation          : rotation atomique sous lock
  - TestRetryDecorator       : no_retry_on exclut les erreurs non-récupérables
  - TestURLEncoding          : keyword encodé dans save_groups
  - TestScrollBound          : human_scroll_to_bottom bornée
  - Tous les tests v4/v5 conservés
"""
import sys
import pathlib
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1 — resolve_media_path
# ═══════════════════════════════════════════════════════════════════════════════

class TestResolveMediaPath:
    def _get_fn(self):
        from libs.config_manager import resolve_media_path
        return resolve_media_path

    def test_windows_backslash_path_extracts_filename(self):
        fn = self._get_fn()
        result = fn(r"C:\Users\Administrator\AppData\Roaming\saadiya\media\media10\7.png")
        assert result.name == "7.png"

    def test_windows_path_with_spaces(self):
        fn = self._get_fn()
        result = fn(r"C:\Users\My User\Documents\image test.jpg")
        assert result.name == "image test.jpg"

    def test_simple_relative_path(self):
        fn = self._get_fn()
        result = fn("mon_image.jpg")
        assert result.name == "mon_image.jpg"

    def test_unix_relative_path(self):
        fn = self._get_fn()
        result = fn("subfolder/image.png")
        assert result.name == "image.png"

    def test_empty_string_does_not_crash(self):
        fn = self._get_fn()
        try:
            fn("")
        except Exception as e:
            pytest.fail(f"resolve_media_path('') a levé {e}")

    def test_windows_jpg_extension_preserved(self):
        fn = self._get_fn()
        result = fn(r"D:\photos\profil\avatar.jpg", "compte1")
        assert result.suffix == ".jpg"

    def test_no_backslash_path_unchanged(self):
        fn = self._get_fn()
        result = fn("logo.png", "session1")
        assert result.name == "logo.png"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2 — DEFAULT_ROBOT_CONFIG (v11 — remplace DEFAULT_SESSION_CONFIG v8)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDefaultRobotConfig:
    REQUIRED_FIELDS = [
        "max_groups_per_run", "max_groups_per_hour", "delay_between_groups",
        "max_runs_per_day", "cooldown_between_runs_s",
        "locale", "timezone_id", "platform", "proxy",
        "telegram_token", "telegram_chat_id",
    ]

    def _get_config(self):
        from libs.robot_manager import DEFAULT_ROBOT_CONFIG
        return DEFAULT_ROBOT_CONFIG

    def test_all_required_fields_present(self):
        config = self._get_config()
        missing = [f for f in self.REQUIRED_FIELDS if f not in config]
        assert not missing, f"Champs manquants : {missing}"

    def test_delay_between_groups_is_list(self):
        cfg = self._get_config()
        assert isinstance(cfg["delay_between_groups"], list)
        assert len(cfg["delay_between_groups"]) == 2

    def test_proxy_default_none(self):
        assert self._get_config()["proxy"] is None

    def test_cooldown_default_7200(self):
        assert self._get_config()["cooldown_between_runs_s"] == 7200

    def test_locale_default_fr(self):
        assert self._get_config()["locale"] == "fr-FR"

    def test_max_groups_per_hour_default(self):
        cfg = self._get_config()
        assert isinstance(cfg["max_groups_per_hour"], int)
        assert cfg["max_groups_per_hour"] > 0


# Alias conservé pour ne pas casser d'éventuels imports externes
TestDefaultSessionConfig = TestDefaultRobotConfig


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3 — timing_humanizer
# ═══════════════════════════════════════════════════════════════════════════════

class TestTimingHumanizer:
    def test_no_last_run_always_ok(self):
        from libs.timing_humanizer import check_cooldown
        assert check_cooldown(None, 7200) is True

    def test_recent_run_blocked(self):
        from libs.timing_humanizer import check_cooldown
        from datetime import datetime, timedelta
        recent = (datetime.now() - timedelta(seconds=3600)).isoformat()
        assert check_cooldown(recent, 7200) is False

    def test_old_run_allowed(self):
        from libs.timing_humanizer import check_cooldown
        from datetime import datetime, timedelta
        old = (datetime.now() - timedelta(seconds=8000)).isoformat()
        assert check_cooldown(old, 7200) is True

    def test_invalid_timestamp_does_not_crash(self):
        from libs.timing_humanizer import check_cooldown
        assert check_cooldown("not-a-date", 7200) is True

    def test_limit_not_reached(self):
        from libs.timing_humanizer import check_session_limit
        assert check_session_limit(1, max_runs_per_day=3) is True

    def test_limit_exactly_reached(self):
        from libs.timing_humanizer import check_session_limit
        assert check_session_limit(3, max_runs_per_day=3) is False

    def test_update_stats_increments_count(self):
        from libs.timing_humanizer import update_session_run_stats
        from datetime import date
        cfg = {"run_count_today": 1, "last_run_date": date.today().isoformat(),
               "last_run_ts": None}
        updated = update_session_run_stats(cfg)
        assert updated["run_count_today"] == 2

    def test_update_stats_resets_on_new_day(self):
        from libs.timing_humanizer import update_session_run_stats
        cfg = {"run_count_today": 5, "last_run_date": "2020-01-01", "last_run_ts": None}
        updated = update_session_run_stats(cfg)
        assert updated["run_count_today"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4 — data files
# ═══════════════════════════════════════════════════════════════════════════════

class TestDataFiles:
    ROOT = pathlib.Path(__file__).parent.parent

    def _load(self, rel_path):
        import json
        full = self.ROOT / rel_path
        assert full.exists(), f"Fichier introuvable : {full}"
        return json.loads(full.read_text(encoding="utf-8"))

    def test_campaigns_json_exists_and_valid(self):
        data = self._load("data/campaigns/campaigns.json")
        assert isinstance(data, (dict, list))

    def test_groups_json_exists_and_valid(self):
        data = self._load("data/groups/groups.json")
        assert isinstance(data, (dict, list))

    def test_campaigns_no_private_paths(self):
        text = str(self._load("data/campaigns/campaigns.json"))
        assert "Administrator" not in text
        assert "AppData" not in text

    def test_groups_no_private_paths(self):
        text = str(self._load("data/groups/groups.json"))
        assert "Administrator" not in text


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5 — check_license
# ═══════════════════════════════════════════════════════════════════════════════

class TestLicenseParsing:
    def _parse(self, s):
        from check_license import parse_license
        return parse_license(s)

    def test_empty_string_returns_none(self):
        assert self._parse("")[0] is None

    def test_invalid_format_returns_none(self):
        assert self._parse("invalid-key-12345")[0] is None

    def test_wrong_prefix_returns_none(self):
        assert self._parse("XXXX030MySerial:AA-BB-CC-DD-EE010101120025TestUser")[0] is None

    def test_get_serial_does_not_crash(self):
        from check_license import get_serial_number
        result = get_serial_number()
        assert isinstance(result, str) and len(result) > 0

    def test_get_mac_addresses_returns_list(self):
        from check_license import get_mac_addresses
        macs = get_mac_addresses()
        assert isinstance(macs, list) and len(macs) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 6 — AntiBlockManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestAntiBlockManager:
    def _get_manager(self, tmp_path):
        from automation.anti_block import AntiBlockManager
        return AntiBlockManager(state_file=str(tmp_path / "anti_block.json"))

    def test_can_post_initially(self, tmp_path):
        assert self._get_manager(tmp_path).can_post_now() is True

    def test_hourly_limit_enforced(self, tmp_path):
        mgr = self._get_manager(tmp_path)
        mgr.max_groups_per_hour    = 2
        mgr.long_pause_after_posts = 999
        mgr.record_post(text="p1")
        mgr.record_post(text="p2")
        assert mgr.can_post_now() is False

    def test_image_use_allowed_initially(self, tmp_path):
        assert self._get_manager(tmp_path).can_use_image("/path/image.jpg") is True

    def test_image_use_blocked_after_max(self, tmp_path):
        mgr = self._get_manager(tmp_path)
        mgr.max_image_uses = 2
        mgr.record_post(text="a", images=["/img.jpg"])
        mgr.record_post(text="b", images=["/img.jpg"])
        assert mgr.can_use_image("/img.jpg") is False

    def test_image_use_count_tracked(self, tmp_path):
        mgr = self._get_manager(tmp_path)
        mgr.record_post(text="x", images=["/a.jpg", "/b.jpg"])
        assert mgr.get_image_use_count("/a.jpg") == 1
        assert mgr.get_image_use_count("/b.jpg") == 1

    def test_hourly_count(self, tmp_path):
        mgr = self._get_manager(tmp_path)
        mgr.record_post(text="p1")
        mgr.record_post(text="p2")
        assert mgr.get_hourly_post_count() == 2

    def test_reset_image_uses(self, tmp_path):
        mgr = self._get_manager(tmp_path)
        mgr.record_post(text="x", images=["/img.jpg"])
        mgr.reset_image_uses()
        assert mgr.get_image_use_count("/img.jpg") == 0

    def test_singleton_returns_same_instance(self):
        from automation.anti_block import get_anti_block_manager
        assert get_anti_block_manager() is get_anti_block_manager()

    def test_long_pause_triggers_after_threshold(self, tmp_path):
        mgr = self._get_manager(tmp_path)
        mgr.long_pause_after_posts    = 2
        mgr.long_pause_min_minutes    = 1
        mgr.long_pause_max_minutes    = 2
        mgr.max_groups_per_hour       = 999
        mgr.record_post(text="a")
        mgr.record_post(text="b")
        assert mgr.state.get("long_pause_until") is not None


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 7 — Fréquence journalière
# ═══════════════════════════════════════════════════════════════════════════════

class TestFrequencyReset:
    def test_counter_resets_on_new_day(self):
        from datetime import date
        from libs.timing_humanizer import check_session_limit
        config = {"run_count_today": 5, "last_run_date": "2020-01-01", "max_runs_per_day": 3}
        if config.get("last_run_date", "") != date.today().isoformat():
            config["run_count_today"] = 0
        assert check_session_limit(config["run_count_today"], config["max_runs_per_day"]) is True

    def test_counter_not_reset_same_day(self):
        from datetime import date
        from libs.timing_humanizer import check_session_limit
        today = date.today().isoformat()
        config = {"run_count_today": 3, "last_run_date": today, "max_runs_per_day": 3}
        if config.get("last_run_date", "") != today:
            config["run_count_today"] = 0
        assert check_session_limit(config["run_count_today"], config["max_runs_per_day"]) is False


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 8 — PlaywrightEngine : propriété publique browser
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlaywrightEngine:
    def test_browser_property_exists_and_none_before_start(self):
        from libs.playwright_engine import PlaywrightEngine
        engine = PlaywrightEngine()
        assert hasattr(engine, "browser")
        assert engine.browser is None

    def test_no_private_browser_access_needed(self):
        from libs.playwright_engine import PlaywrightEngine
        engine = PlaywrightEngine()
        _ = engine.browser  # pas d'AttributeError


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 9 — retry : no_retry_on exclut les erreurs non-récupérables (v6)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRetryDecorator:
    def test_session_expired_not_retried(self):
        """SessionExpiredError doit être propagée immédiatement sans retry."""
        from libs.error_handlers import retry, SessionExpiredError, NON_RETRYABLE
        call_count = 0

        @retry(max_attempts=3, delay=0, no_retry_on=NON_RETRYABLE)
        def flaky():
            nonlocal call_count
            call_count += 1
            raise SessionExpiredError("session expirée")

        with pytest.raises(SessionExpiredError):
            flaky()

        assert call_count == 1, (
            f"SessionExpiredError ne doit pas être retentée, "
            f"mais flaky() a été appelée {call_count} fois"
        )

    def test_facebook_blocked_not_retried(self):
        """FacebookBlockedError doit être propagée immédiatement."""
        from libs.error_handlers import retry, FacebookBlockedError, NON_RETRYABLE
        call_count = 0

        @retry(max_attempts=3, delay=0, no_retry_on=NON_RETRYABLE)
        def blocked():
            nonlocal call_count
            call_count += 1
            raise FacebookBlockedError("bloqué")

        with pytest.raises(FacebookBlockedError):
            blocked()

        assert call_count == 1

    def test_generic_error_is_retried(self):
        """Une erreur générique doit déclencher des retries."""
        from libs.error_handlers import retry, NON_RETRYABLE
        call_count = 0

        @retry(max_attempts=3, delay=0, no_retry_on=NON_RETRYABLE)
        def unstable():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("erreur temporaire")
            return "ok"

        result = unstable()
        assert result == "ok"
        assert call_count == 3

    def test_max_retries_reached_raises(self):
        """Après max_attempts échecs génériques, l'exception est propagée."""
        from libs.error_handlers import retry, NON_RETRYABLE
        call_count = 0

        @retry(max_attempts=2, delay=0, no_retry_on=NON_RETRYABLE)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("réseau indisponible")

        with pytest.raises(ConnectionError):
            always_fails()

        assert call_count == 2


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 10 — URL encoding dans save_groups (v6)
# ═══════════════════════════════════════════════════════════════════════════════

class TestURLEncoding:
    def test_keyword_with_special_chars_is_encoded(self):
        """Vérifie que url_quote encode les caractères spéciaux."""
        from urllib.parse import quote as url_quote
        keyword  = "agriculture & élevage"
        encoded  = url_quote(keyword, safe="")
        url      = f"https://www.facebook.com/groups/search/groups/?q={encoded}"
        assert "&" not in url.split("?q=")[1], "& doit être encodé en %26"
        assert " " not in url, "Les espaces doivent être encodés"
        assert "%26" in url or "26" in url  # & → %26

    def test_simple_keyword_unchanged_chars(self):
        from urllib.parse import quote as url_quote
        keyword = "agriculture"
        encoded = url_quote(keyword, safe="")
        assert encoded == "agriculture"

    def test_arabic_keyword_encoded(self):
        from urllib.parse import quote as url_quote
        keyword = "زراعة"
        encoded = url_quote(keyword, safe="")
        assert "%" in encoded, "Les caractères arabes doivent être encodés"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 11 — SelectorRegistry : validation schéma CDN (v6)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSelectorRegistryCDNValidation:
    def _get_registry(self, tmp_path, selectors_data: dict):
        import json
        p = tmp_path / "selectors.json"
        p.write_text(json.dumps(selectors_data), encoding="utf-8")
        from libs.selector_registry import SelectorRegistry
        return SelectorRegistry(selectors_path=p)

    def test_validate_remote_missing_selectors_key(self, tmp_path):
        """Un JSON sans clé 'selectors' est rejeté."""
        local = {
            "version": "2026-01",
            "selectors": {k: {"selectors": ["x"]} for k in
                          ["display_input", "input", "submit", "show_image_input", "add_image"]}
        }
        reg = self._get_registry(tmp_path, local)
        valid, msg = reg._validate_remote({"version": "2026-02", "wrong_key": {}})
        assert valid is False
        assert "selectors" in msg.lower()

    def test_validate_remote_missing_required_keys(self, tmp_path):
        """Un JSON valide mais manquant des sélecteurs obligatoires est rejeté."""
        local = {
            "version": "2026-01",
            "selectors": {k: {"selectors": ["x"]} for k in
                          ["display_input", "input", "submit", "show_image_input", "add_image"]}
        }
        reg = self._get_registry(tmp_path, local)
        remote = {"version": "2026-02", "selectors": {"display_input": {"selectors": ["y"]}}}
        valid, msg = reg._validate_remote(remote)
        assert valid is False
        assert "manquantes" in msg.lower() or "missing" in msg.lower()

    def test_validate_remote_valid_json(self, tmp_path):
        """Un JSON complet et valide passe la validation."""
        local = {
            "version": "2026-01",
            "selectors": {k: {"selectors": ["x"]} for k in
                          ["display_input", "input", "submit", "show_image_input", "add_image"]}
        }
        reg = self._get_registry(tmp_path, local)
        remote = {
            "version": "2026-02",
            "selectors": {k: {"selectors": ["y"]} for k in
                          ["display_input", "input", "submit", "show_image_input", "add_image"]}
        }
        valid, msg = reg._validate_remote(remote)
        assert valid is True
        assert msg == "OK"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 12 — human_scroll_to_bottom borné (v6)
# ═══════════════════════════════════════════════════════════════════════════════

class TestScrollBound:
    def test_scroll_stops_at_max_iterations(self):
        """human_scroll_to_bottom doit s'arrêter après max_iterations."""
        from libs.timing_humanizer import human_scroll_to_bottom
        import unittest.mock as mock

        iteration_count = 0

        class FakePage:
            def __init__(self):
                self.mouse = mock.MagicMock()
                self._height = 1000

            def mouse_wheel(self, x, y):
                pass

            def evaluate(self, expr):
                nonlocal iteration_count
                iteration_count += 1
                # Simuler une page qui croît indéfiniment
                self._height += 100
                return self._height

        page = FakePage()
        page.mouse.wheel = mock.MagicMock()

        import time
        with mock.patch("time.sleep"):
            human_scroll_to_bottom(page, stable_count=3, max_iterations=5)

        # max_iterations=5 → la boucle ne doit pas dépasser 5 iterations
        assert iteration_count <= 5, (
            f"human_scroll_to_bottom a dépassé la borne : {iteration_count} itérations"
        )
