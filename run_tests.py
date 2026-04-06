#!/usr/bin/env python3
"""
run_tests.py — Lanceur de tests autonome pour BON
Fonctionne SANS pytest, SANS internet, SANS Playwright
Usage : python3 run_tests.py
"""

import sys
import os
import json
import time
import pathlib
import tempfile
import traceback

# ─── Résolution automatique du répertoire racine ─────────────────────────────
# Robuste sous Windows/PowerShell même avec espaces et parenthèses dans le nom.

def _find_root() -> pathlib.Path:
    candidates = []
    try:
        candidates.append(pathlib.Path(__file__).resolve().parent)
    except Exception:
        pass
    try:
        candidates.append(pathlib.Path(sys.argv[0]).resolve().parent)
    except Exception:
        pass
    candidates.append(pathlib.Path(os.getcwd()).resolve())

    for c in candidates:
        if (c / "libs" / "config_manager.py").exists():
            return c
        for sub in c.iterdir() if c.is_dir() else []:
            if sub.is_dir() and (sub / "libs" / "config_manager.py").exists():
                return sub

    return candidates[0] if candidates else pathlib.Path(os.getcwd())

_ROOT = _find_root()

# ── Forcer la résolution correcte de 'libs' ──────────────────────────────────
# On retire tous les 'libs' parasites (Python313, win32...) du sys.path,
# puis on insère notre dossier ROOT EN PREMIER pour qu'il ait priorité absolue.
_libs_str = str(_ROOT / "libs")
_root_str = str(_ROOT)

# Purger les anciennes entrées libs du namespace (évite le namespace package)
sys.modules.pop("libs", None)
for _k in [k for k in sys.modules if k.startswith("libs.")]:
    sys.modules.pop(_k, None)

# Mettre _ROOT en tête de sys.path
if _root_str in sys.path:
    sys.path.remove(_root_str)
sys.path.insert(0, _root_str)

os.chdir(_ROOT)

# ─── Couleurs terminal ────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# ─── Mini framework de test ───────────────────────────────────────────────────
results = []

def test(name, group="Général"):
    """Décorateur pour enregistrer un test."""
    def decorator(fn):
        results.append({"name": name, "group": group, "fn": fn, "status": None, "error": None, "duration": 0})
        return fn
    return decorator

def run_all():
    groups_seen = []
    passed = failed = skipped = 0

    for r in results:
        if r["group"] not in groups_seen:
            groups_seen.append(r["group"])
            print(f"\n{CYAN}{BOLD}━━━ {r['group']} ━━━{RESET}")

        t0 = time.perf_counter()
        try:
            r["fn"]()
            r["status"] = "PASS"
            passed += 1
            dur = time.perf_counter() - t0
            print(f"  {GREEN}✅ PASS{RESET}  {r['name']}  {YELLOW}({dur*1000:.0f}ms){RESET}")
        except AssertionError as e:
            r["status"] = "FAIL"
            r["error"] = str(e) or "Assertion échouée"
            failed += 1
            dur = time.perf_counter() - t0
            print(f"  {RED}❌ FAIL{RESET}  {r['name']}")
            print(f"         {RED}└─ {r['error']}{RESET}")
        except Exception as e:
            r["status"] = "ERROR"
            r["error"] = f"{type(e).__name__}: {e}"
            failed += 1
            dur = time.perf_counter() - t0
            print(f"  {RED}💥 ERR {RESET}  {r['name']}")
            print(f"         {RED}└─ {r['error']}{RESET}")

    total = passed + failed + skipped
    bar = "█" * passed + "░" * failed
    color = GREEN if failed == 0 else RED

    print(f"\n{BOLD}{'═'*55}{RESET}")
    print(f"{BOLD}  BON — Résultats  [{bar}]{RESET}")
    print(f"{'═'*55}")
    print(f"  {GREEN}Passés  : {passed}{RESET}")
    if failed:
        print(f"  {RED}Échoués : {failed}{RESET}")
    print(f"  Total   : {total}")
    print(f"{'═'*55}")

    if failed == 0:
        print(f"\n{GREEN}{BOLD}  🎉 Tous les tests passent !{RESET}\n")
    else:
        print(f"\n{RED}{BOLD}  ⚠️  {failed} test(s) en échec — voir détails ci-dessus{RESET}\n")

    sys.exit(0 if failed == 0 else 1)


# ══════════════════════════════════════════════════════════════════════════════
# GROUPE 1 — config_manager
# ══════════════════════════════════════════════════════════════════════════════

@test("Chemin Windows avec backslash", group="1 · config_manager")
def _():
    from libs.config_manager import resolve_media_path
    r = resolve_media_path(r"C:\Users\Administrator\AppData\media\7.png")
    assert r.name == "7.png", f"Attendu '7.png', obtenu '{r.name}'"

@test("Chemin Windows avec espaces", group="1 · config_manager")
def _():
    from libs.config_manager import resolve_media_path
    r = resolve_media_path(r"C:\Users\Mon Dossier\image test.jpg")
    assert r.name == "image test.jpg"

@test("Chemin Unix relatif simple", group="1 · config_manager")
def _():
    from libs.config_manager import resolve_media_path
    r = resolve_media_path("logo.png")
    assert r.name == "logo.png"

@test("Chaîne vide ne lève pas d'exception", group="1 · config_manager")
def _():
    from libs.config_manager import resolve_media_path
    try:
        resolve_media_path("")
    except Exception as e:
        raise AssertionError(f"resolve_media_path('') a levé {e}")

@test("Extension préservée (.jpg)", group="1 · config_manager")
def _():
    from libs.config_manager import resolve_media_path
    r = resolve_media_path(r"D:\photos\avatar.jpg", "compte1")
    assert r.suffix == ".jpg"


# ══════════════════════════════════════════════════════════════════════════════
# GROUPE 2 — robot_manager / DEFAULT_ROBOT_CONFIG
# ══════════════════════════════════════════════════════════════════════════════

@test("Champs obligatoires présents", group="2 · robot_manager")
def _():
    from libs.robot_manager import DEFAULT_ROBOT_CONFIG
    required = [
        "max_groups_per_run", "max_groups_per_hour",
        "delay_between_groups", "max_runs_per_day",
        "cooldown_between_runs_s", "locale",
    ]
    missing = [f for f in required if f not in DEFAULT_ROBOT_CONFIG]
    assert not missing, f"Champs manquants dans DEFAULT_ROBOT_CONFIG : {missing}"

@test("max_groups_per_run est un entier positif", group="2 · robot_manager")
def _():
    from libs.robot_manager import DEFAULT_ROBOT_CONFIG
    v = DEFAULT_ROBOT_CONFIG["max_groups_per_run"]
    assert isinstance(v, int) and v > 0, f"Valeur invalide : {v!r}"

@test("delay_between_groups est un nombre ou une plage [min, max]", group="2 · robot_manager")
def _():
    from libs.robot_manager import DEFAULT_ROBOT_CONFIG
    v = DEFAULT_ROBOT_CONFIG["delay_between_groups"]
    if isinstance(v, list):
        assert len(v) == 2 and v[0] > 0 and v[1] >= v[0], f"Plage invalide : {v!r}"
    elif isinstance(v, (int, float)):
        assert v > 0, f"Valeur invalide : {v!r}"
    else:
        raise AssertionError(f"Type inattendu pour delay_between_groups : {type(v).__name__}")

@test("RobotManager s'importe sans erreur", group="2 · robot_manager")
def _():
    from libs.robot_manager import RobotManager  # noqa


# ══════════════════════════════════════════════════════════════════════════════
# GROUPE 3 — database
# ══════════════════════════════════════════════════════════════════════════════

@test("BONDatabase s'instancie avec un fichier temporaire", group="3 · database")
def _():
    from libs.database import BONDatabase
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    db = BONDatabase(db_path)
    assert db is not None

@test("BONDatabase : création des tables sans exception", group="3 · database")
def _():
    from libs.database import BONDatabase
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(pathlib.Path(tmpdir) / "test.db")
        db = BONDatabase(db_path)
        # Si les tables sont créées à l'init, pas d'exception = OK
        assert db is not None


# ══════════════════════════════════════════════════════════════════════════════
# GROUPE 4 — circuit_breaker
# ══════════════════════════════════════════════════════════════════════════════

@test("CircuitBreakerRegistry s'importe", group="4 · circuit_breaker")
def _():
    from libs.circuit_breaker import CircuitBreakerRegistry  # noqa

@test("CircuitBreakerRegistry s'instancie", group="4 · circuit_breaker")
def _():
    from libs.circuit_breaker import CircuitBreakerRegistry
    reg = CircuitBreakerRegistry()
    assert reg is not None


# ══════════════════════════════════════════════════════════════════════════════
# GROUPE 5 — config_validator
# ══════════════════════════════════════════════════════════════════════════════

@test("validate_session_config s'importe", group="5 · config_validator")
def _():
    from libs.config_validator import validate_session_config  # noqa

@test("Config vide retourne des erreurs (pas d'exception)", group="5 · config_validator")
def _():
    from libs.config_validator import validate_session_config, ConfigError
    try:
        result = validate_session_config({}, "test_session")
        # Soit retourne une liste de warnings/errors, soit lève ConfigError
        assert isinstance(result, list)
    except ConfigError:
        pass  # Comportement attendu également

@test("validate_selectors s'importe", group="5 · config_validator")
def _():
    from libs.config_validator import validate_selectors  # noqa


# ══════════════════════════════════════════════════════════════════════════════
# GROUPE 6 — timing_humanizer
# ══════════════════════════════════════════════════════════════════════════════

@test("human_delay s'importe", group="6 · timing_humanizer")
def _():
    from libs.timing_humanizer import human_delay  # noqa

@test("jitter retourne un float positif", group="6 · timing_humanizer")
def _():
    from libs.timing_humanizer import jitter
    v = jitter(500)
    assert isinstance(v, (int, float)) and v >= 0, f"jitter a retourné {v!r}"

@test("human_delay_between_groups s'importe", group="6 · timing_humanizer")
def _():
    from libs.timing_humanizer import human_delay_between_groups  # noqa

@test("check_session_limit s'importe", group="6 · timing_humanizer")
def _():
    from libs.timing_humanizer import check_session_limit  # noqa


# ══════════════════════════════════════════════════════════════════════════════
# GROUPE 7 — stealth_profile
# ══════════════════════════════════════════════════════════════════════════════

@test("StealthProfile s'importe", group="7 · stealth_profile")
def _():
    from libs.stealth_profile import StealthProfile  # noqa

@test("StealthProfile s'instancie sans arguments", group="7 · stealth_profile")
def _():
    from libs.stealth_profile import StealthProfile
    import inspect
    sig = inspect.signature(StealthProfile.__init__)
    params = [p for p in sig.parameters if p != "self"]
    if not params:
        sp = StealthProfile()
        assert sp is not None
    else:
        # Instanciation avec dict vide si nécessaire
        try:
            sp = StealthProfile({})
            assert sp is not None
        except Exception:
            sp = StealthProfile()
            assert sp is not None


# ══════════════════════════════════════════════════════════════════════════════
# GROUPE 8 — fichiers JSON de configuration
# ══════════════════════════════════════════════════════════════════════════════

@test("config/selectors.json — JSON valide et non vide", group="8 · fichiers config")
def _():
    with open("config/selectors.json") as f:
        data = json.load(f)
    assert isinstance(data, dict) and len(data) > 0, "selectors.json vide ou format invalide"

@test("config/labels.json — JSON valide", group="8 · fichiers config")
def _():
    with open("config/labels.json") as f:
        data = json.load(f)
    assert isinstance(data, (dict, list))

@test("config/user_agents.json — JSON valide et liste non vide", group="8 · fichiers config")
def _():
    with open("config/user_agents.json") as f:
        data = json.load(f)
    assert isinstance(data, (list, dict)) and len(data) > 0

@test("data/campaigns/campaigns.json — JSON valide", group="8 · fichiers config")
def _():
    with open("data/campaigns/campaigns.json") as f:
        data = json.load(f)
    assert isinstance(data, (list, dict))

@test("data/groups/groups.json — JSON valide", group="8 · fichiers config")
def _():
    with open("data/groups/groups.json") as f:
        data = json.load(f)
    assert isinstance(data, (list, dict))

@test("config/selectors/facebook_fr.json — JSON valide", group="8 · fichiers config")
def _():
    with open("config/selectors/facebook_fr.json") as f:
        data = json.load(f)
    assert isinstance(data, dict) and len(data) > 0


# ══════════════════════════════════════════════════════════════════════════════
# GROUPE 9 — imports principaux
# ══════════════════════════════════════════════════════════════════════════════

@test("Scraper s'importe", group="9 · imports principaux")
def _():
    from libs.scraper import Scraper  # noqa

@test("SocialActions s'importe", group="9 · imports principaux")
def _():
    from libs.social_actions import SocialActions  # noqa

@test("notifier s'importe (TelegramNotifier)", group="9 · imports principaux")
def _():
    from libs.notifier import TelegramNotifier  # noqa

@test("selector_registry s'importe", group="9 · imports principaux")
def _():
    from libs.selector_registry import SelectorRegistry  # noqa

@test("log_emitter s'importe", group="9 · imports principaux")
def _():
    from libs import log_emitter  # noqa

@test("error_handlers s'importe", group="9 · imports principaux")
def _():
    from libs import error_handlers  # noqa


# ══════════════════════════════════════════════════════════════════════════════
# GROUPE 10 — database : logique métier
# ══════════════════════════════════════════════════════════════════════════════

def _fresh_db():
    """Crée une BONDatabase en mémoire — à fermer après usage."""
    from libs.database import BONDatabase
    return BONDatabase(":memory:")

@test("upsert_robot crée un robot récupérable", group="10 · database métier")
def _():
    db = _fresh_db()
    try:
        db.upsert_robot("robot1", "compte@fb.com", "session.json")
        r = db.get_robot("robot1")
        assert r is not None, "get_robot() a retourné None"
        assert r["robot_name"] == "robot1"
    finally:
        db.close()

@test("robot_exists / delete_robot cohérents", group="10 · database métier")
def _():
    db = _fresh_db()
    try:
        db.upsert_robot("robot_del", "del@fb.com", "s.json")
        assert db.robot_exists("robot_del"), "robot devrait exister après upsert"
        db.delete_robot("robot_del")
        assert not db.robot_exists("robot_del"), "robot devrait être supprimé"
    finally:
        db.close()

@test("campaign + variant + pick_random_variant", group="10 · database métier")
def _():
    db = _fresh_db()
    try:
        db.upsert_campaign("ma_campagne", "test")
        c = db.get_campaign_by_name("ma_campagne")
        assert c is not None, "campagne introuvable après upsert"
        db.upsert_variant(c["id"], "v1", text_fr="Bonjour le monde !")
        variants = db.get_variants(c["id"])
        assert len(variants) == 1, f"attendu 1 variant, obtenu {len(variants)}"
        picked = db.pick_random_variant("ma_campagne", language="fr")
        assert picked is not None, "pick_random_variant a retourné None"
        assert "Bonjour" in picked.get("text", ""), f"texte inattendu : {picked}"
    finally:
        db.close()

@test("was_published_recently : vrai après publication, faux pour groupe inconnu", group="10 · database métier")
def _():
    db = _fresh_db()
    try:
        db.upsert_robot("robot_pub", "pub@fb.com", "s.json")
        db.add_group("https://facebook.com/groups/111", name="Groupe A")
        db.record_publication("robot_pub", "https://facebook.com/groups/111",
                               account_name="pub@fb.com")
        assert db.was_published_recently("robot_pub",
                                         "https://facebook.com/groups/111",
                                         hours=24), "devrait être True après publication"
        assert not db.was_published_recently("robot_pub",
                                              "https://facebook.com/groups/999",
                                              hours=24), "devrait être False pour groupe inconnu"
    finally:
        db.close()

@test("add_comment + pick_random_comment retourne le texte inséré", group="10 · database métier")
def _():
    db = _fresh_db()
    try:
        db.upsert_robot("robot_cmt", "cmt@fb.com", "s.json")
        db.add_comment("Super article !", robot_name="robot_cmt")
        c = db.pick_random_comment("robot_cmt")
        assert c is not None, "pick_random_comment a retourné None"
        assert "Super" in c, f"texte inattendu : {c!r}"
    finally:
        db.close()

@test("config_set / config_get / config_get avec valeur par défaut", group="10 · database métier")
def _():
    db = _fresh_db()
    try:
        db.config_set("ma_cle", "ma_valeur")
        assert db.config_get("ma_cle") == "ma_valeur"
        assert db.config_get("cle_inexistante", default="defaut") == "defaut"
    finally:
        db.close()

@test("get_dashboard_stats retourne les clés attendues", group="10 · database métier")
def _():
    db = _fresh_db()
    try:
        stats = db.get_dashboard_stats()
        required_keys = [
            "total_robots", "total_accounts", "total_groups",
            "total_campaigns", "posts_today", "errors_today",
        ]
        missing = [k for k in required_keys if k not in stats]
        assert not missing, f"Clés manquantes dans dashboard_stats : {missing}"
    finally:
        db.close()

@test("import_groups_from_json charge les groupes du fichier", group="10 · database métier")
def _():
    db = _fresh_db()
    try:
        n = db.import_groups_from_json("data/groups/groups.json")
        assert isinstance(n, int) and n >= 0, f"import_groups_from_json a retourné {n!r}"
    finally:
        db.close()

@test("import_campaigns_from_json charge les campagnes du fichier", group="10 · database métier")
def _():
    db = _fresh_db()
    try:
        n = db.import_campaigns_from_json("data/campaigns/campaigns.json")
        assert isinstance(n, int) and n >= 0, f"import_campaigns_from_json a retourné {n!r}"
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
# GROUPE 11 — circuit_breaker : logique d'état
# ══════════════════════════════════════════════════════════════════════════════

@test("État initial est CLOSED et allow() retourne True", group="11 · circuit_breaker logique")
def _():
    from libs.circuit_breaker import CircuitBreakerRegistry
    reg = CircuitBreakerRegistry()
    assert reg.get_state("robot_a") == "closed", f"état initial inattendu : {reg.get_state('robot_a')}"
    assert reg.allow("robot_a") is True

@test("3 échecs consécutifs ouvrent le circuit (OPEN)", group="11 · circuit_breaker logique")
def _():
    from libs.circuit_breaker import CircuitBreakerRegistry
    reg = CircuitBreakerRegistry()
    reg.record_failure("robot_b")
    reg.record_failure("robot_b")
    assert reg.get_state("robot_b") == "closed", "2 échecs ne doivent pas ouvrir le circuit"
    reg.record_failure("robot_b")
    assert reg.get_state("robot_b") == "open", "3 échecs doivent ouvrir le circuit"

@test("Circuit OPEN : allow() retourne False", group="11 · circuit_breaker logique")
def _():
    from libs.circuit_breaker import CircuitBreakerRegistry
    reg = CircuitBreakerRegistry()
    for _ in range(3):
        reg.record_failure("robot_c")
    assert reg.allow("robot_c") is False, "circuit ouvert doit bloquer allow()"

@test("Échec critique ouvre le circuit immédiatement", group="11 · circuit_breaker logique")
def _():
    from libs.circuit_breaker import CircuitBreakerRegistry
    reg = CircuitBreakerRegistry()
    reg.record_failure("robot_d", critical=True)
    assert reg.get_state("robot_d") == "open", "échec critique doit ouvrir le circuit en 1 coup"

@test("record_success remet le circuit à CLOSED", group="11 · circuit_breaker logique")
def _():
    from libs.circuit_breaker import CircuitBreakerRegistry
    reg = CircuitBreakerRegistry()
    reg.record_failure("robot_e")
    reg.record_success("robot_e")
    assert reg.get_state("robot_e") == "closed", "succès doit refermer le circuit"

@test("Robots indépendants : l'état d'un robot n'affecte pas l'autre", group="11 · circuit_breaker logique")
def _():
    from libs.circuit_breaker import CircuitBreakerRegistry
    reg = CircuitBreakerRegistry()
    for _ in range(3):
        reg.record_failure("robot_f1")
    assert reg.get_state("robot_f1") == "open"
    assert reg.get_state("robot_f2") == "closed", "robot_f2 ne doit pas être affecté"


# ══════════════════════════════════════════════════════════════════════════════
# GROUPE 12 — selector_registry : candidats et version
# ══════════════════════════════════════════════════════════════════════════════

@test("SelectorRegistry charge config/selectors.json sans erreur", group="12 · selector_registry")
def _():
    from libs.selector_registry import SelectorRegistry
    sr = SelectorRegistry(selectors_path=pathlib.Path("config/selectors.json"))
    assert sr is not None

@test("version est une chaîne non vide", group="12 · selector_registry")
def _():
    from libs.selector_registry import SelectorRegistry
    sr = SelectorRegistry(selectors_path=pathlib.Path("config/selectors.json"))
    v = sr.version
    assert isinstance(v, str) and len(v) > 0, f"version invalide : {v!r}"

@test("get_candidates('display_input') retourne des candidats", group="12 · selector_registry")
def _():
    from libs.selector_registry import SelectorRegistry
    sr = SelectorRegistry(selectors_path=pathlib.Path("config/selectors.json"))
    c = sr.get_candidates("display_input")
    assert isinstance(c, list) and len(c) > 0, "aucun candidat pour 'display_input'"

@test("get_candidates('submit') retourne des candidats", group="12 · selector_registry")
def _():
    from libs.selector_registry import SelectorRegistry
    sr = SelectorRegistry(selectors_path=pathlib.Path("config/selectors.json"))
    c = sr.get_candidates("submit")
    assert isinstance(c, list) and len(c) > 0, "aucun candidat pour 'submit'"

@test("get_candidates clé inexistante retourne liste vide (pas d'exception)", group="12 · selector_registry")
def _():
    from libs.selector_registry import SelectorRegistry
    sr = SelectorRegistry(selectors_path=pathlib.Path("config/selectors.json"))
    c = sr.get_candidates("cle_qui_nexiste_pas")
    assert isinstance(c, list), f"attendu une liste, obtenu {type(c).__name__}"

@test("Tous les sélecteurs FR sont présents dans facebook_fr.json", group="12 · selector_registry")
def _():
    with open("config/selectors/facebook_fr.json") as f:
        data = json.load(f)
    assert len(data) > 0, "facebook_fr.json est vide"
    # Chaque valeur doit être une chaîne ou une liste
    for key, val in data.items():
        assert isinstance(val, (str, list, dict)), \
            f"Type inattendu pour '{key}' : {type(val).__name__}"


# ══════════════════════════════════════════════════════════════════════════════
# LANCEMENT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\n{BOLD}{CYAN}{'═'*55}")
    print(f"  BON — Lanceur de tests autonome")
    print(f"  (sans pytest · sans internet · sans Playwright)")
    print(f"{'═'*55}{RESET}")
    print(f"{YELLOW}  Racine détectée : {_ROOT}{RESET}")
    print(f"{YELLOW}  libs/ trouvé    : {(_ROOT / 'libs').is_dir()}{RESET}")
    print(f"{YELLOW}  config/ trouvé  : {(_ROOT / 'config').is_dir()}{RESET}")

    # Lister ce qui est dans libs/ pour débugger
    _libs = _ROOT / 'libs'
    if _libs.is_dir():
        _files = sorted(f.name for f in _libs.iterdir() if f.suffix == '.py')
        print(f"{YELLOW}  libs/*.py       : {', '.join(_files[:5])}...{RESET}")
    else:
        print(f"{RED}  ⚠ libs/ INTROUVABLE — vérifiez que run_tests.py est dans le bon dossier{RESET}")
        print(f"{RED}    sys.path[0] = {sys.path[0]}{RESET}")
        print(f"{RED}    os.getcwd() = {os.getcwd()}{RESET}")
        try:
            print(f"{RED}    __file__    = {__file__}{RESET}")
        except Exception:
            pass
        print()
    print()
    run_all()