"""
tests/test_smoke.py — Tests de non-régression fondamentaux
Exécution : python -m pytest tests/ -v
             (sans Playwright ni Facebook — tests purement unitaires)
"""
import sys
import pathlib
import pytest

# Permettre l'import depuis la racine du projet
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1 — resolve_media_path : chemins Windows sur Linux/macOS
# ═══════════════════════════════════════════════════════════════════════════════

class TestResolveMediaPath:
    """Fix F-01 : PureWindowsPath pour les chemins avec antislash."""

    def _get_fn(self):
        from libs.config_manager import resolve_media_path
        return resolve_media_path

    def test_windows_backslash_path_extracts_filename(self):
        """Un chemin Windows absolu doit donner uniquement le nom de fichier."""
        fn = self._get_fn()
        result = fn(r"C:\Users\Administrator\AppData\Roaming\saadiya\media\media10\7.png")
        assert result.name == "7.png", \
            f"Attendu '7.png', obtenu '{result.name}'"

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
        """Un chemin vide ne doit pas lever d'exception."""
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
# TEST 2 — DEFAULT_SESSION_CONFIG : tous les champs requis présents
# ═══════════════════════════════════════════════════════════════════════════════

class TestDefaultSessionConfig:
    """Fix F-02 : DEFAULT_SESSION_CONFIG doit contenir tous les champs utilisés."""

    REQUIRED_FIELDS = [
        "session_name",
        "storage_state",
        "max_groups_per_run",
        "delay_between_groups",
        "max_runs_per_day",
        "cooldown_between_runs_s",
        "last_run_ts",
        "run_count_today",
        "posts",
        "groups",
        "add_comments",
        "comments",
        "marketplace",
    ]

    def _get_config(self):
        from libs.session_manager import DEFAULT_SESSION_CONFIG
        return DEFAULT_SESSION_CONFIG

    def test_all_required_fields_present(self):
        config = self._get_config()
        missing = [f for f in self.REQUIRED_FIELDS if f not in config]
        assert not missing, f"Champs manquants : {missing}"

    def test_add_comments_default_false(self):
        config = self._get_config()
        assert config["add_comments"] is False

    def test_marketplace_default_empty_dict(self):
        config = self._get_config()
        assert isinstance(config["marketplace"], dict)

    def test_comments_default_empty_list(self):
        config = self._get_config()
        assert isinstance(config["comments"], list)

    def test_cooldown_default_7200(self):
        config = self._get_config()
        assert config["cooldown_between_runs_s"] == 7200

    def test_posts_default_list(self):
        config = self._get_config()
        assert isinstance(config["posts"], list)

    def test_groups_default_list(self):
        config = self._get_config()
        assert isinstance(config["groups"], list)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3 — timing_humanizer : check_cooldown et check_session_limit
# ═══════════════════════════════════════════════════════════════════════════════

class TestTimingHumanizer:
    """Vérification des limites de fréquence sans accès réseau ni browser."""

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

    def test_limit_exceeded(self):
        from libs.timing_humanizer import check_session_limit
        assert check_session_limit(10, max_runs_per_day=3) is False

    def test_update_stats_increments_count(self):
        from libs.timing_humanizer import update_session_run_stats
        from datetime import date
        cfg = {"run_count_today": 1, "last_run_date": date.today().isoformat(),
               "last_run_ts": None}
        updated = update_session_run_stats(cfg)
        assert updated["run_count_today"] == 2

    def test_update_stats_resets_on_new_day(self):
        from libs.timing_humanizer import update_session_run_stats
        cfg = {"run_count_today": 5, "last_run_date": "2020-01-01",
               "last_run_ts": None}
        updated = update_session_run_stats(cfg)
        assert updated["run_count_today"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4 — data.json / data1.json : pas de chemins personnels exposés
# ═══════════════════════════════════════════════════════════════════════════════

class TestDataFiles:
    """Fix F-04 : les fichiers d'exemple ne doivent pas contenir de données privées."""

    ROOT = pathlib.Path(__file__).parent.parent

    def _load(self, filename):
        import json
        return json.loads((self.ROOT / filename).read_text(encoding="utf-8"))

    def test_data_json_no_windows_paths(self):
        data = self._load("data.json")
        text = str(data)
        assert "Administrator" not in text
        assert "AppData" not in text
        assert "Users\\" not in text

    def test_data1_json_no_windows_paths(self):
        data = self._load("data1.json")
        text = str(data)
        assert "Administrator" not in text
        assert "AppData" not in text

    def test_data_json_valid_structure(self):
        data = self._load("data.json")
        assert "posts" in data
        assert "groups" in data
        assert isinstance(data["posts"], list)

    def test_data1_json_valid_structure(self):
        data = self._load("data1.json")
        assert "stories" in data or "posts" in data


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5 — check_license : parse_license ne crashe pas sur entrées invalides
# ═══════════════════════════════════════════════════════════════════════════════

class TestLicenseParsing:
    """Vérification que parse_license est robuste."""

    def _parse(self, s):
        from check_license import parse_license
        return parse_license(s)

    def test_empty_string_returns_none(self):
        result = self._parse("")
        assert result[0] is None

    def test_invalid_format_returns_none(self):
        result = self._parse("invalid-key-12345")
        assert result[0] is None

    def test_wrong_prefix_returns_none(self):
        result = self._parse("XXXX030MySerial:AA-BB-CC-DD-EE010101120025TestUser")
        assert result[0] is None

    def test_get_serial_does_not_crash(self):
        """get_serial_number() doit toujours retourner une chaîne, jamais crasher."""
        from check_license import get_serial_number
        result = get_serial_number()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_mac_addresses_returns_list(self):
        from check_license import get_mac_addresses
        macs = get_mac_addresses()
        assert isinstance(macs, list)
        assert len(macs) >= 1
