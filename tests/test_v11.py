"""
test_v11.py — Régressions v11 : export CSV, scheduler, captcha log, exclusion cross-robot.
"""
import csv
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from libs.database import BONDatabase
from libs.variant_selector import pick_variant
from tests.factories import RobotFactory, CampaignFactory, GroupFactory


def _db():
    p = pathlib.Path(tempfile.gettempdir()) / "test_bon_v11_unit.db"
    if p.exists():
        p.unlink()
    return BONDatabase(str(p))


def test_export_publications_csv():
    db = _db()
    RobotFactory.create(db, "r1", "acc1")
    gurl = "https://facebook.com/groups/999001/"
    db.add_group(gurl, name="G1")
    db.assign_group_to_robot("r1", gurl)
    camp = CampaignFactory.create(db, "c1", variant_count=2)
    db.assign_campaign_to_robot("r1", camp["name"])
    db.record_publication(
        "r1",
        gurl,
        status="success",
        post_content="hello",
        campaign_name=camp["name"],
        variant_id="v1",
    )
    out = pathlib.Path(tempfile.gettempdir()) / "bon_export_test.csv"
    n = db.export_publications_csv(str(out), robot_name="r1")
    assert n >= 1
    text = out.read_text(encoding="utf-8")
    assert "r1" in text and "success" in text
    with open(out, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 1
    out.unlink(missing_ok=True)


def test_publications_paginated():
    db = _db()
    RobotFactory.create(db, "r2", "acc2")
    gurl = "https://facebook.com/groups/999002/"
    db.add_group(gurl)
    db.assign_group_to_robot("r2", gurl)
    camp = CampaignFactory.create(db, "c2", variant_count=3)
    db.assign_campaign_to_robot("r2", camp["name"])
    for i in range(3):
        db.record_publication(
            "r2",
            gurl,
            status="success",
            campaign_name=camp["name"],
            variant_id=f"v{i+1}",
        )
    page = db.get_publications_paginated(limit=2, offset=0, robot_name="r2")
    assert len(page) == 2


def test_captcha_log_and_scheduler():
    db = _db()
    db.log_captcha_event("r1", "recaptcha", "ok", None)
    db.log_captcha_event("r1", "recaptcha", "failed", "timeout")
    stats = db.get_captcha_solve_stats(days=30)
    assert len(stats) >= 1
    db.scheduler_upsert_job("j_test", "r1", "0 8 * * *", "post", 1)
    jobs = db.scheduler_list_jobs()
    assert any(j["job_id"] == "j_test" for j in jobs)
    assert db.scheduler_delete_job("j_test")


def test_variant_cross_robot_exclusion():
    db = _db()
    RobotFactory.create(db, "ra", "acca")
    RobotFactory.create(db, "rb", "accb")
    gurl = "https://facebook.com/groups/888777/"
    db.add_group(gurl)
    db.assign_group_to_robot("ra", gurl)
    db.assign_group_to_robot("rb", gurl)
    camp = CampaignFactory.create(db, "cross_camp", variant_count=3)
    db.assign_campaign_to_robot("ra", camp["name"])
    db.assign_campaign_to_robot("rb", camp["name"])
    vkeys = [v["variant_key"] for v in db.get_variants(camp["id"])]
    used_key = vkeys[0]
    db.record_publication(
        "ra",
        gurl,
        status="success",
        campaign_name=camp["name"],
        variant_id=used_key,
    )
    v_same = pick_variant(
        db,
        "rb",
        camp["name"],
        group_url=gurl,
        language="fr",
        exclusion_days=30,
        exclude_cross_robot=False,
    )
    assert v_same is not None
    v_cross = pick_variant(
        db,
        "rb",
        camp["name"],
        group_url=gurl,
        language="fr",
        exclusion_days=30,
        exclude_cross_robot=True,
    )
    assert v_cross is not None
    assert v_cross.get("variant_key") != used_key or len(vkeys) == 1


def test_selector_cdn_disabled_by_default():
    os.environ.pop("BON_USE_CDN", None)
    os.environ.pop("BON_SELECTORS_CDN_URL", None)
    import importlib
    import libs.selector_registry as sr
    importlib.reload(sr)
    reg = sr.SelectorRegistry(pathlib.Path("config") / "selectors.json")
    assert reg.update_from_cdn() is False


def run_all():
    tests = [
        test_export_publications_csv,
        test_publications_paginated,
        test_captcha_log_and_scheduler,
        test_variant_cross_robot_exclusion,
        test_selector_cdn_disabled_by_default,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"✓ {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"✗ {t.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    print(f"\nBON v11 — {passed}/{passed+failed} tests")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
