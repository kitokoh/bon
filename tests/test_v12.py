"""
test_v12.py -- Tests de regression v12

Couvre les nouvelles fonctionnalites et corrections v12 :
  - close() / __del__ sur BONDatabase (FIX G2)
  - reset_database() pour les tests
  - captcha_api_key par robot en DB (FIX G3)
  - get_publications_paginated() avec filtres date (V12-P5)
  - _publication_export_rows() avec filtres date
  - export_publications_csv() avec filtres date
  - check_optional_deps() dans libs/__init__
  - robot config set etendu (smoke CLI)
"""
import pathlib
import sys
import tempfile
import warnings

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from libs.database import BONDatabase, get_database, reset_database
from tests.factories import RobotFactory, CampaignFactory, GroupFactory


# ── Helpers ───────────────────────────────────────────────────────────────────

def _memdb() -> BONDatabase:
    """Cree une DB :memory: fraiche."""
    return BONDatabase(":memory:")


def _tmpdb() -> BONDatabase:
    """Cree une DB fichier temporaire fraiche."""
    p = pathlib.Path(tempfile.gettempdir()) / "test_bon_v12_unit.db"
    if p.exists():
        p.unlink()
    return BONDatabase(str(p))


# ── FIX G2 : close() + __del__ ───────────────────────────────────────────────

def test_close_is_idempotent():
    """Appels multiples a close() ne levent pas d'exception."""
    db = _memdb()
    db.close()
    db.close()   # doit etre silencieux
    db.close()
    print("  close() idempotent OK")


def test_closed_connect_raises():
    """_connect() apres close() leve RuntimeError."""
    db = _memdb()
    db.close()
    try:
        db._connect()
        assert False, "RuntimeError attendu"
    except RuntimeError as e:
        assert "fermee" in str(e).lower() or "close" in str(e).lower()
    print("  _connect() apres close() -> RuntimeError OK")


def test_no_resource_warning_on_close():
    """Aucun ResourceWarning ne doit etre emis apres close() explicite."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        db = _memdb()
        _ = db.get_all_robots()
        db.close()
    resource_warns = [x for x in w if issubclass(x.category, ResourceWarning)]
    assert len(resource_warns) == 0, f"ResourceWarning inattendu : {resource_warns}"
    print("  Pas de ResourceWarning apres close() OK")


def test_memory_db_tables_survive_across_calls():
    """La connexion persistante permet aux tables :memory: de survivre entre appels."""
    db = _memdb()
    db.upsert_robot("r_persist", "acc_persist",
                    "/tmp/r_persist.json", {})
    assert db.robot_exists("r_persist")
    db.close()
    print("  Tables :memory: persistantes entre appels OK")


# ── reset_database() ─────────────────────────────────────────────────────────

def test_reset_database_replaces_singleton():
    """reset_database() installe une nouvelle instance comme singleton."""
    db1 = _memdb()
    reset_database(db1)
    assert get_database() is db1
    # Nettoyage
    reset_database(None)
    db1.close()
    print("  reset_database() OK")


def test_reset_database_to_none_triggers_recreation():
    """Apres reset_database(None), get_database() cree une nouvelle instance."""
    reset_database(None)
    db_new = get_database()
    assert db_new is not None
    # Ne pas fermer le singleton global (il sera reutilise)
    print("  reset_database(None) -> recreation OK")


# ── FIX G3 : captcha_api_key par robot ───────────────────────────────────────

def test_captcha_api_key_column_exists():
    """La colonne captcha_api_key existe dans la table robots."""
    db = _memdb()
    cols = db._query("PRAGMA table_info(robots)")
    col_names = [c["name"] for c in cols]
    assert "captcha_api_key" in col_names, f"Colonne manquante, colonnes: {col_names}"
    db.close()
    print("  captcha_api_key colonne existe OK")


def test_upsert_robot_with_captcha_key():
    """upsert_robot() accepte captcha_api_key dans la config."""
    db = _memdb()
    rid = db.upsert_robot(
        "r_captcha", "acc_captcha", "/tmp/r.json",
        {"captcha_api_key": "my_secret_key_123"}
    )
    assert rid > 0
    robot = db.get_robot("r_captcha")
    assert robot is not None
    assert robot.get("captcha_api_key") == "my_secret_key_123"
    db.close()
    print("  upsert_robot avec captcha_api_key OK")


def test_captcha_key_defaults_to_none():
    """Sans captcha_api_key dans la config, la valeur est NULL."""
    db = _memdb()
    db.upsert_robot("r_no_captcha", "acc_nc", "/tmp/r2.json", {})
    robot = db.get_robot("r_no_captcha")
    assert robot is not None
    assert robot.get("captcha_api_key") is None
    db.close()
    print("  captcha_api_key NULL par defaut OK")


def test_captcha_key_can_be_updated():
    """On peut modifier captcha_api_key via un second upsert_robot."""
    db = _memdb()
    db.upsert_robot("r_upd", "acc_upd", "/tmp/r3.json", {"captcha_api_key": "old_key"})
    db.upsert_robot("r_upd", "acc_upd", "/tmp/r3.json", {"captcha_api_key": "new_key"})
    robot = db.get_robot("r_upd")
    assert robot["captcha_api_key"] == "new_key"
    db.close()
    print("  captcha_api_key mise a jour OK")


def test_captcha_solver_uses_robot_key():
    """CaptchaSolver() utilise la cle DB si disponible, sans BON_2CAPTCHA_KEY."""
    import os
    os.environ.pop("BON_2CAPTCHA_KEY", None)

    db = _memdb()
    db.upsert_robot("r_cs", "acc_cs", "/tmp/r4.json",
                    {"captcha_api_key": "robot_specific_key"})
    reset_database(db)

    from libs.captcha_solver import CaptchaSolver
    solver = CaptchaSolver(robot_name="r_cs")
    assert solver.configured()
    assert solver.api_key == "robot_specific_key"

    reset_database(None)
    db.close()
    print("  CaptchaSolver utilise cle robot DB OK")


# ── V12-P5 : Filtres date sur publications ───────────────────────────────────

def _setup_publications_db():
    """DB :memory: avec 3 publications a des dates differentes."""
    db = _memdb()
    RobotFactory.create(db, "rdate", "accdate")
    gurl = "https://facebook.com/groups/date_test/"
    db.add_group(gurl)
    db.assign_group_to_robot("rdate", gurl)
    camp = CampaignFactory.create(db, "camp_date", variant_count=3)
    db.assign_campaign_to_robot("rdate", camp["name"])
    # Injection SQL directe pour controler created_at
    dates = ["2026-01-15T10:00:00", "2026-02-20T12:00:00", "2026-03-25T14:00:00"]
    for i, dt in enumerate(dates):
        gid = db._query_scalar("SELECT id FROM groups WHERE url=?", (gurl,))
        aid = db._query_scalar("SELECT id FROM accounts WHERE name='accdate'")
        db._exec(
            """INSERT INTO publications
               (robot_name, account_id, group_id, campaign_name, variant_id,
                status, created_at, published_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            ("rdate", aid, gid, camp["name"], f"v{i+1}", "success", dt, dt)
        )
    return db, gurl, camp


def test_publications_paginated_no_filter():
    """Sans filtre date, toutes les publications sont retournees."""
    db, _, _ = _setup_publications_db()
    rows = db.get_publications_paginated(limit=10, robot_name="rdate")
    assert len(rows) == 3
    db.close()
    print("  get_publications_paginated sans filtre OK")


def test_publications_paginated_date_from():
    """date_from filtre les publications anterieures."""
    db, _, _ = _setup_publications_db()
    rows = db.get_publications_paginated(
        limit=10, robot_name="rdate", date_from="2026-02-01"
    )
    assert len(rows) == 2, f"Attendu 2, obtenu {len(rows)}"
    for r in rows:
        assert r["created_at"] >= "2026-02-01"
    db.close()
    print("  get_publications_paginated date_from OK")


def test_publications_paginated_date_to():
    """date_to filtre les publications posterieures."""
    db, _, _ = _setup_publications_db()
    rows = db.get_publications_paginated(
        limit=10, robot_name="rdate", date_to="2026-02-28"
    )
    assert len(rows) == 2, f"Attendu 2, obtenu {len(rows)}"
    db.close()
    print("  get_publications_paginated date_to OK")


def test_publications_paginated_date_range():
    """date_from + date_to combine les deux filtres."""
    db, _, _ = _setup_publications_db()
    rows = db.get_publications_paginated(
        limit=10, robot_name="rdate",
        date_from="2026-02-01", date_to="2026-02-28"
    )
    assert len(rows) == 1
    assert "2026-02-20" in rows[0]["created_at"]
    db.close()
    print("  get_publications_paginated date_from+date_to OK")


def test_publication_export_rows_date_filter():
    """_publication_export_rows() respecte les filtres date."""
    db, _, _ = _setup_publications_db()
    rows = db._publication_export_rows(robot_name="rdate", date_from="2026-03-01")
    assert len(rows) == 1
    assert "2026-03-25" in rows[0]["created_at"]
    db.close()
    print("  _publication_export_rows date_from OK")


def test_export_csv_date_filter(tmp_path):
    """export_publications_csv() passe les filtres date a _publication_export_rows."""
    db, _, _ = _setup_publications_db()
    out = tmp_path / "filtered.csv"
    n = db.export_publications_csv(str(out), robot_name="rdate",
                                   date_from="2026-01-01", date_to="2026-01-31")
    assert n == 1
    text = out.read_text(encoding="utf-8")
    assert "2026-01-15" in text
    assert "2026-02-20" not in text
    db.close()
    print("  export_publications_csv avec filtre date OK")


# ── check_optional_deps() ─────────────────────────────────────────────────────

def test_check_optional_deps_returns_dict():
    """check_optional_deps() retourne un dict avec les bonnes cles."""
    from libs import check_optional_deps
    status = check_optional_deps()
    assert isinstance(status, dict)
    for key in ("flask", "flask_limiter", "apscheduler", "openpyxl"):
        assert key in status, f"Cle manquante : {key}"
        assert isinstance(status[key], bool)
    print("  check_optional_deps() OK")


def test_flask_detected_as_available():
    """flask est present dans requirements.txt et doit etre detecte."""
    from libs import check_optional_deps
    status = check_optional_deps()
    # flask est une dependance directe — si le test tourne, il est installe
    try:
        import flask
        assert status["flask"] is True
    except ImportError:
        pass  # Environnement sans flask, on skip
    print("  flask detection OK")


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all():
    import tempfile, pathlib as _pl

    tmp = _pl.Path(tempfile.gettempdir())

    tests = [
        # G2 : close()
        test_close_is_idempotent,
        test_closed_connect_raises,
        test_no_resource_warning_on_close,
        test_memory_db_tables_survive_across_calls,
        # reset_database()
        test_reset_database_replaces_singleton,
        test_reset_database_to_none_triggers_recreation,
        # G3 : captcha_api_key
        test_captcha_api_key_column_exists,
        test_upsert_robot_with_captcha_key,
        test_captcha_key_defaults_to_none,
        test_captcha_key_can_be_updated,
        test_captcha_solver_uses_robot_key,
        # P5 : filtres date
        test_publications_paginated_no_filter,
        test_publications_paginated_date_from,
        test_publications_paginated_date_to,
        test_publications_paginated_date_range,
        test_publication_export_rows_date_filter,
        lambda: test_export_csv_date_filter(tmp),
        # libs/__init__
        test_check_optional_deps_returns_dict,
        test_flask_detected_as_available,
    ]

    passed = failed = 0
    for t in tests:
        name = getattr(t, "__name__", str(t))
        try:
            t()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {name}: {e}")
            import traceback; traceback.print_exc()
            failed += 1

    total = passed + failed
    print(f"\nBON v12 — {passed}/{total} tests passes")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
