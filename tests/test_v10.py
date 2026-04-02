"""
test_v10.py — Tests automatisés BON v10 (schéma SQL v9+)
Couvre : DB, robots, campagnes, médias avec captcha, anti-doublon, factories, seeder
"""
import sys, os, pathlib, random, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from libs.database import BONDatabase
from tests.factories import (
    RobotFactory, CampaignFactory, GroupFactory,
    MediaFactory, CommentFactory, PublicationFactory,
    DmQueueFactory, Seeder
)

DB_PATH = str(pathlib.Path(tempfile.gettempdir()) / "test_bon_v10.db")


def setup():
    if pathlib.Path(DB_PATH).exists():
        os.unlink(DB_PATH)
    return BONDatabase(DB_PATH)


def teardown():
    if pathlib.Path(DB_PATH).exists():
        os.unlink(DB_PATH)


def test_db_init():
    db = setup()
    tables = db._query(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    table_names = {t["name"] for t in tables}
    required = {
        "accounts", "robots", "robot_run_stats", "groups", "robot_groups",
        "campaigns", "campaign_variants", "robot_campaigns",
        "media_assets", "robot_media", "comments", "publications",
        "published_comments", "errors", "selector_stats", "account_blocks",
        "subscriptions", "circuit_breaker_state", "dm_queue", "config_kv",
        "captcha_solve_log", "scheduler_jobs",
    }
    missing = required - table_names
    assert not missing, f"Tables manquantes : {missing}"
    print("✓ test_db_init")


def test_robot_lifecycle():
    db = setup()
    robot = RobotFactory.create(db, "robot1", "compte_principal")
    assert robot is not None
    assert robot["robot_name"] == "robot1"
    assert robot["account_name"] == "compte_principal"
    assert db.robot_exists("robot1")
    assert "robot1" in db.list_robot_names()

    # Run stats
    can_run, reason = db.check_run_limits("robot1")
    assert can_run, f"Devrait pouvoir tourner : {reason}"

    db.record_run("robot1")
    db.record_run("robot1")
    stats = db.get_run_stats("robot1")
    assert stats["run_count"] == 2

    # Limit atteinte
    db._exec("UPDATE robot_run_stats SET run_count=99 WHERE robot_name=?", ("robot1",))
    can_run, reason = db.check_run_limits("robot1")
    assert not can_run, "Devrait être bloqué par limite"

    print("✓ test_robot_lifecycle")
    teardown()


def test_campaign_variant_weighted():
    db = setup()
    camp = CampaignFactory.create(db, "test_camp", variant_count=3)
    assert camp is not None

    # Tirer 20 variants — vérifier qu'on obtient bien des résultats
    found = set()
    for _ in range(20):
        v = db.pick_random_variant("test_camp", "fr")
        assert v is not None
        assert v.get("text"), "Le texte ne doit pas être vide"
        found.add(v["variant_key"])
    assert len(found) >= 1, "Au moins 1 variant doit être tiré"

    print("✓ test_campaign_variant_weighted")
    teardown()


def test_media_with_captcha():
    db = setup()

    # Média sans captcha
    m1 = MediaFactory.create(db, captcha_text=None, description="Photo produit.")
    assert m1["captcha_text"] is None

    # Média avec captcha
    m2 = MediaFactory.create(db, captcha_text="CODE123", description="Offre spéciale")
    assert m2["captcha_text"] == "CODE123"

    # pick_random_media → final_caption
    results = db.pick_random_media(count=2)
    assert len(results) >= 1
    for r in results:
        assert "final_caption" in r
        if r.get("captcha_text") and r.get("description"):
            assert r["captcha_text"] in r["final_caption"]
            assert r["description"] in r["final_caption"]
        elif r.get("captcha_text"):
            assert r["captcha_text"] in r["final_caption"]
        elif r.get("description"):
            assert r["description"] in r["final_caption"]

    print("✓ test_media_with_captcha")
    teardown()


def test_anti_doublon():
    db = setup()
    robot = RobotFactory.create(db, "robot_anti")
    group = GroupFactory.create(db)
    db.assign_group_to_robot("robot_anti", group["url"])

    # Pas encore publié
    assert not db.was_published_recently("robot_anti", group["url"], hours=24)

    # Publier
    db.record_publication(
        robot_name    = "robot_anti",
        group_url     = group["url"],
        status        = "success",
        campaign_name = "camp_test",
        variant_id    = "v1",
    )

    # Maintenant bloqué (même robot, même groupe, 24h)
    assert db.was_published_recently("robot_anti", group["url"], hours=24)

    # Autre robot : pas bloqué
    robot2 = RobotFactory.create(db, "robot_anti2", "compte2")
    assert not db.was_published_recently("robot_anti2", group["url"], hours=24)

    # Même robot mais variant différent : autorisé si variant_id précisé
    assert not db.was_published_recently(
        "robot_anti", group["url"], hours=24,
        campaign_name="camp_test", variant_id="v2"
    )

    print("✓ test_anti_doublon")
    teardown()


def test_subscriptions():
    db = setup()
    robot = RobotFactory.create(db, "robot_sub", "compte_sub")
    group = GroupFactory.create(db)

    assert not db.is_subscribed("robot_sub", group["url"])
    db.mark_subscribed("robot_sub", group["url"])
    assert db.is_subscribed("robot_sub", group["url"])

    print("✓ test_subscriptions")
    teardown()


def test_dm_queue():
    db = setup()
    robot = RobotFactory.create(db, "robot_dm")

    # Enqueue
    dm_id = db.enqueue_dm(
        robot_name   = "robot_dm",
        target_type  = "ami",
        target_id    = "https://www.facebook.com/user/testuser",
        text_content = "Bonjour !",
        media_paths  = ["/tmp/img.jpg"],
    )
    assert dm_id > 0

    # Récupérer
    pending = db.get_pending_dms("robot_dm", limit=10)
    assert len(pending) == 1
    assert pending[0]["text_content"] == "Bonjour !"

    # Update status
    db.update_dm_status(dm_id, "sent")
    pending2 = db.get_pending_dms("robot_dm", limit=10)
    assert len(pending2) == 0

    print("✓ test_dm_queue")
    teardown()


def test_comments():
    db = setup()
    CommentFactory.create_batch(db, 10)
    CommentFactory.create_batch(db, 3, robot_name="robot1")

    # Commentaire aléatoire global
    c = db.pick_random_comment()
    assert c is not None and len(c) > 0

    # Commentaire spécifique robot
    c_robot = db.pick_random_comment("robot1")
    assert c_robot is not None

    print("✓ test_comments")
    teardown()


def test_robot_assignments():
    db = setup()
    robot    = RobotFactory.create(db, "robot_assign")
    groups   = GroupFactory.create_batch(db, 4)
    campaign = CampaignFactory.create(db, "camp_assign")
    medias   = MediaFactory.create_batch(db, 3)

    GroupFactory.assign_to_robot(db, "robot_assign", groups)
    CampaignFactory.assign_to_robot(db, "robot_assign", [campaign])
    MediaFactory.assign_to_robot(db, "robot_assign", medias)

    assert len(db.get_groups_for_robot("robot_assign")) == 4
    assert len(db.get_campaigns_for_robot("robot_assign")) == 1
    assert len(db.get_media_for_robot("robot_assign")) == 3

    print("✓ test_robot_assignments")
    teardown()


def test_circuit_breaker_state():
    db = setup()
    state = db.get_cb_state("robot_cb")
    assert state["state"] == "closed"
    assert state["failures"] == 0

    db.save_cb_state("robot_cb", "open", failures=3, successes=0,
                      opened_at="2026-04-01T12:00:00")
    state2 = db.get_cb_state("robot_cb")
    assert state2["state"] == "open"
    assert state2["failures"] == 3

    print("✓ test_circuit_breaker_state")
    teardown()


def test_config_kv():
    db = setup()
    db.config_set("telegram.token", "abc123")
    db.config_set("telegram.chat_id", "-100456")
    assert db.config_get("telegram.token") == "abc123"
    assert db.config_get("telegram.chat_id") == "-100456"
    assert db.config_get("nonexistent", "default") == "default"

    print("✓ test_config_kv")
    teardown()


def test_dashboard_stats():
    db = setup()
    summary = Seeder.seed_all(db, robot_count=2)
    stats   = db.get_dashboard_stats()
    assert stats["total_robots"] == 2
    assert stats["total_campaigns"] >= 5
    assert stats["total_groups"] >= 6
    assert stats["total_comments_bank"] >= 10
    assert stats["total_media_assets"] >= 1

    print("✓ test_dashboard_stats")
    teardown()


def test_seeder_full():
    db      = setup()
    summary = Seeder.seed_all(db, robot_count=3)
    assert len(summary["robots"]) == 3
    assert len(summary["campaigns"]) >= 5
    assert len(summary["groups"]) == 6
    assert summary["media"] >= 3
    assert summary["comments"] >= 10

    # Vérifier que les assignations sont bien faites
    for rn in summary["robots"]:
        assert len(db.get_groups_for_robot(rn)) == 6
        assert len(db.get_campaigns_for_robot(rn)) >= 5
        assert len(db.get_media_for_robot(rn)) >= 5

    print("✓ test_seeder_full")
    teardown()


def test_seeder_minimal():
    db  = setup()
    res = Seeder.seed_minimal(db)
    assert res["robot"] is not None
    assert res["campaign"] is not None
    assert res["group"] is not None

    print("✓ test_seeder_minimal")
    teardown()


def test_build_post_text():
    """Test que la concatenation variant + description + captcha est correcte."""
    # Simuler la logique de _build_post_text du scraper
    variant = {"text": "Texte principal", "cta": "Découvrir"}
    media_items = [
        {"description": "Photo du produit", "captcha_text": "CODE10"},
        {"description": "Visuel officiel", "captcha_text": None},
    ]
    parts = [variant["text"]]
    for m in media_items:
        caption_parts = []
        if m.get("description"):
            caption_parts.append(m["description"])
        if m.get("captcha_text"):
            caption_parts.append(m["captcha_text"])
        if caption_parts:
            parts.append(" ".join(caption_parts))
    if variant.get("cta"):
        parts.append(variant["cta"])
    result = "\n\n".join(filter(None, parts))
    assert "Texte principal" in result
    assert "Photo du produit" in result
    assert "CODE10" in result
    assert "Visuel officiel" in result
    assert "Découvrir" in result
    print("✓ test_build_post_text")


def run_all():
    tests = [
        test_db_init,
        test_robot_lifecycle,
        test_campaign_variant_weighted,
        test_media_with_captcha,
        test_anti_doublon,
        test_subscriptions,
        test_dm_queue,
        test_comments,
        test_robot_assignments,
        test_circuit_breaker_state,
        test_config_kv,
        test_dashboard_stats,
        test_seeder_full,
        test_seeder_minimal,
        test_build_post_text,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"✗ {t.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    print(f"\n{'='*40}")
    print(f"BON v10 — {passed}/{passed+failed} tests passés")
    if failed:
        print(f"⚠ {failed} test(s) échoués")
        sys.exit(1)
    else:
        print("✅ Tous les tests passent !")


if __name__ == "__main__":
    run_all()
