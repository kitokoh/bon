"""
__main__.py v11 — Point d'entrée BON

Commandes principales :
  python -m bon robot create --robot <nom> [--account <nom>] [--proxy-server URL ...]
  python -m bon robot config show|set|clear-proxy --robot <nom>
  python -m bon post --robot <nom> [--headless] [--validate-proxy]
  python -m bon export --out fichier.csv [--robot <nom>]
  python -m bon captcha test
  python -m bon schedule add|list|remove|daemon ...
  python -m bon api --host 127.0.0.1 --port 8765
  python -m bon config set|get <clé> [valeur]
  python -m bon selectors update [--force]
  python -m bon migrate | dashboard | update-ua
"""
import argparse
import hashlib
import json
import pathlib
import sys

try:
    from check_license import is_license_valid
    if not is_license_valid():
        print("\n✗ Licence invalide ou expirée.\n", file=sys.stderr)
        sys.exit(1)
except Exception as _e:
    print(f"[WARN] Licence ignorée : {_e}", file=sys.stderr)

try:
    from playwright.sync_api import sync_playwright  # noqa
except ImportError:
    print("\n✗ Playwright non installé. Lancez : python install.py\n", file=sys.stderr)
    sys.exit(1)

from libs.playwright_engine import PlaywrightEngine
from libs.selector_registry import SelectorRegistry
from libs.robot_manager import RobotManager
from libs.scraper import Scraper
from libs.config_manager import CONFIG_DIR
from libs.database import get_database
from libs.log_emitter import emit, write_pid, clear_pid
from libs.error_handlers import setup_graceful_shutdown


def _bootstrap():
    """Import JSON → SQL au démarrage (idempotent)."""
    db = get_database()
    for path, fn in [
        (pathlib.Path("data/campaigns/campaigns.json"), db.import_campaigns_from_json),
        (pathlib.Path("data/groups/groups.json"), db.import_groups_from_json),
    ]:
        if path.exists():
            fn(path)
    try:
        from libs.ua_updater import check_ua_freshness
        fresh, current, latest = check_ua_freshness()
        if not fresh:
            print(f"[WARN] UA obsolètes : Chrome/{current} → Chrome/{latest} disponible")
            print("       Mettez à jour : python -m bon update-ua")
    except Exception:
        pass


def parse_args():
    p = argparse.ArgumentParser(description="BON v11 — Facebook Groups Publisher")
    sub = p.add_subparsers(dest="command")

    r = sub.add_parser("robot", help="Gestion des robots")
    rsub = r.add_subparsers(dest="robot_cmd")

    rc = rsub.add_parser("create")
    rc.add_argument("--robot", required=True)
    rc.add_argument("--account", default=None)
    rc.add_argument("--proxy-server", default=None, help="ex. http://host:8080")
    rc.add_argument("--proxy-user", default=None)
    rc.add_argument("--proxy-pass", default=None)
    rc.add_argument("--no-proxy-check", action="store_true", help="Ne pas tester le proxy")

    rsub.add_parser("list")
    rv = rsub.add_parser("verify")
    rv.add_argument("--robot", required=True)
    rd = rsub.add_parser("delete")
    rd.add_argument("--robot", required=True)

    rcfg = rsub.add_parser("config", help="Afficher / modifier la config robot")
    rcfg_sub = rcfg.add_subparsers(dest="robot_config_cmd")
    rcs = rcfg_sub.add_parser("show")
    rcs.add_argument("--robot", required=True)
    rcset = rcfg_sub.add_parser("set")
    rcset.add_argument("--robot", required=True)
    rcset.add_argument("--proxy-server", default=None)
    rcset.add_argument("--proxy-user", default=None)
    rcset.add_argument("--proxy-pass", default=None)
    rcc = rcfg_sub.add_parser("clear-proxy")
    rcc.add_argument("--robot", required=True)

    pp = sub.add_parser("post")
    pp.add_argument("--robot", required=True)
    pp.add_argument("--headless", action="store_true")
    pp.add_argument("--validate-proxy", action="store_true", help="Tester le proxy avant run")

    sg = sub.add_parser("save-groups")
    sg.add_argument("--robot", required=True)
    sg.add_argument("--keyword", required=True)
    sg.add_argument("--headless", action="store_true")
    sg.add_argument("--validate-proxy", action="store_true")

    co = sub.add_parser("comment")
    co.add_argument("--robot", required=True)
    co.add_argument("--urls", required=True, help="URLs séparées par virgule")
    co.add_argument("--max", type=int, default=3)

    dm = sub.add_parser("dm")
    dm.add_argument("--robot", required=True)
    dm.add_argument("--target", required=True, help="URL profil Facebook cible")
    dm.add_argument("--text", required=True)
    dm.add_argument("--media", nargs="*", default=None)

    dq = sub.add_parser("dm-queue")
    dq.add_argument("--robot", required=True)
    dq.add_argument("--limit", type=int, default=10)

    mg = sub.add_parser("migrate")
    mg.add_argument("--sessions", action="store_true")
    mg.add_argument("--data", action="store_true")

    sub.add_parser("dashboard")
    sub.add_parser("update-ua", help="Mettre à jour le pool User-Agents (Chrome)")

    ex = sub.add_parser("export", help="Exporter les publications en CSV")
    ex.add_argument("--out", required=True)
    ex.add_argument("--robot", default=None)

    cap = sub.add_parser("captcha", help="2captcha (clé BON_2CAPTCHA_KEY)")
    cap_sub = cap.add_subparsers(dest="captcha_cmd")
    cap_sub.add_parser("test")

    sch = sub.add_parser("schedule", help="Planification cron (APScheduler)")
    sch_sub = sch.add_subparsers(dest="schedule_cmd")
    sadd = sch_sub.add_parser("add")
    sadd.add_argument("--robot", required=True)
    sadd.add_argument("--cron", required=True, help="5 champs, ex. '0 8 * * *'")
    sadd.add_argument("--command", default="post")
    sadd.add_argument("--job-id", default=None, dest="job_id")
    sch_sub.add_parser("list")
    srm = sch_sub.add_parser("remove")
    srm.add_argument("--job-id", required=True, dest="job_id")
    sch_sub.add_parser("daemon")

    api = sub.add_parser("api", help="API REST (Flask, BON_API_TOKEN requis)")
    api.add_argument("--host", default="127.0.0.1")
    api.add_argument("--port", type=int, default=8765)

    gcfg = sub.add_parser("config", help="Config globale (SQLite config_kv)")
    gcfg_sub = gcfg.add_subparsers(dest="global_config_cmd")
    gc_set = gcfg_sub.add_parser("set")
    gc_set.add_argument("key")
    gc_set.add_argument("value")
    gc_get = gcfg_sub.add_parser("get")
    gc_get.add_argument("key")

    sel = sub.add_parser("selectors", help="Mise à jour sélecteurs (CDN)")
    sel_sub = sel.add_subparsers(dest="selectors_cmd")
    su = sel_sub.add_parser("update")
    su.add_argument("--force", action="store_true")

    return p.parse_args()


def _load_robot(robot_name: str):
    rm = RobotManager()
    if not rm.robot_exists(robot_name):
        emit("ERROR", "ROBOT_NOT_FOUND", robot=robot_name)
        print(f"\n✗ Robot '{robot_name}' introuvable.")
        print(f"  Créez-le : python -m bon robot create --robot {robot_name}")
        sys.exit(1)
    return rm, rm.get_config(robot_name)


def _check_limits(robot_name: str):
    db = get_database()
    can_run, reason = db.check_run_limits(robot_name)
    if not can_run:
        emit("WARN", "RUN_LIMIT_EXIT", robot=robot_name, reason=reason)
        print(f"\n⏸ Robot '{robot_name}' : {reason}")
        sys.exit(0)


def _maybe_validate_proxy(config: dict, enabled: bool) -> None:
    if not enabled:
        return
    px = config.get("proxy")
    if not px or not px.get("server"):
        return
    from libs.proxy_util import validate_proxy
    ok, msg = validate_proxy(
        px["server"],
        px.get("username"),
        px.get("password"),
    )
    if not ok:
        print(f"\n✗ Proxy invalide : {msg}")
        sys.exit(1)
    print(f"✓ Proxy OK ({msg})")


def _build_scraper(args, config, robot_name):
    headless = getattr(args, "headless", False)
    selectors_path = CONFIG_DIR / "selectors.json"
    if not selectors_path.exists():
        selectors_path = pathlib.Path("config") / "selectors.json"
    selectors = SelectorRegistry(selectors_path)
    selectors.update_from_cdn()
    engine = PlaywrightEngine(
        headless=headless,
        locale=config.get("locale", "fr-FR"),
        timezone_id=config.get("timezone_id", "Europe/Paris"),
        proxy=config.get("proxy"),
    )
    scraper = Scraper(engine, selectors, config, robot_name)
    return engine, scraper


def cmd_robot_create(args):
    from libs.proxy_util import build_playwright_proxy, validate_proxy

    rm = RobotManager()
    account = getattr(args, "account", None) or args.robot
    px = None
    if args.proxy_server:
        px = build_playwright_proxy(args.proxy_server, args.proxy_user, args.proxy_pass)
        if px and not args.no_proxy_check:
            ok, msg = validate_proxy(
                px["server"],
                px.get("username"),
                px.get("password"),
            )
            if not ok:
                print(f"\n✗ Proxy invalide : {msg}")
                print("  Utilisez --no-proxy-check pour ignorer ce test.")
                sys.exit(1)
            print(f"✓ Proxy OK ({msg})")

    engine = PlaywrightEngine(headless=False, proxy=px)
    engine.start()
    try:
        ok = rm.create_robot(
            args.robot,
            engine.browser,
            account_name=account,
            context_proxy=px,
        )
        if ok:
            print(f"\n✓ Robot '{args.robot}' créé (compte : {account})")
        else:
            print(f"\n✗ Création échouée pour '{args.robot}'")
            sys.exit(1)
    finally:
        engine.stop()


def cmd_robot_config_show(args):
    _, config = _load_robot(args.robot)
    safe = json.loads(json.dumps(config, default=str))
    if isinstance(safe.get("proxy"), dict) and safe["proxy"].get("password"):
        safe["proxy"] = dict(safe["proxy"])
        safe["proxy"]["password"] = "***"
    print(json.dumps(safe, indent=2, ensure_ascii=False))


def cmd_robot_config_set(args):
    rm, cfg = _load_robot(args.robot)
    if args.proxy_server:
        from libs.proxy_util import build_playwright_proxy
        px = build_playwright_proxy(args.proxy_server, args.proxy_user, args.proxy_pass)
        cfg["proxy"] = px
        cfg["proxy_server"] = px["server"]
        cfg["proxy_username"] = px.get("username") or ""
        cfg["proxy_password"] = px.get("password") or ""
    rm.save_config(args.robot, cfg)
    print(f"✓ Config enregistrée pour '{args.robot}'")


def cmd_robot_config_clear_proxy(args):
    rm, cfg = _load_robot(args.robot)
    cfg["proxy"] = None
    cfg["proxy_server"] = None
    cfg["proxy_username"] = None
    cfg["proxy_password"] = None
    rm.save_config(args.robot, cfg)
    print(f"✓ Proxy effacé pour '{args.robot}'")


def cmd_robot_list():
    db = get_database()
    robots = RobotManager().list_robots()
    if robots:
        print(f"\nRobots disponibles ({len(robots)}) :")
        print(f"  {'Robot':<20} {'Compte':<25} {'Santé':>6}  {'Statut'}")
        print(f"  {'-'*70}")
        for r in robots:
            rd = db.get_robot(r) or {}
            cb_state = ""
            try:
                from libs.circuit_breaker import get_circuit_breaker
                state = get_circuit_breaker().get_state(r)
                cb_state = f" [CB:{state}]"
            except Exception:
                pass
            px = "oui" if rd.get("proxy_server") else "non"
            print(
                f"  {r:<20} {rd.get('account_name', '?'):<25} "
                f"{rd.get('health_score', '?'):>5}/100  {rd.get('status', '?')}{cb_state}  proxy:{px}"
            )
        print()
    else:
        print("Aucun robot configuré.")
        print("  python -m bon robot create --robot robot1")


def cmd_robot_verify(args):
    _, config = _load_robot(args.robot)
    px = config.get("proxy")
    engine = PlaywrightEngine(headless=True, proxy=px)
    engine.start()
    try:
        ctx, page = engine.new_context(storage_state=config.get("storage_state", ""))
        page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=20000)
        if "/login" in page.url:
            print(f"✗ Robot '{args.robot}' : session expirée. Reconnectez-vous.")
            ctx.close()
            sys.exit(1)
        print(f"✓ Robot '{args.robot}' : session valide.")
        ctx.close()
    finally:
        engine.stop()


def cmd_robot_delete(args):
    ok = RobotManager().delete_robot(args.robot)
    print(f"{'✓' if ok else '✗'} Robot '{args.robot}' {'supprimé' if ok else ': erreur suppression'}")


def cmd_post(args):
    _, config = _load_robot(args.robot)
    _maybe_validate_proxy(config, getattr(args, "validate_proxy", False))
    _check_limits(args.robot)
    engine, scraper = _build_scraper(args, config, args.robot)
    db = get_database()

    def cleanup():
        try:
            scraper.close()
            engine.stop()
        except Exception:
            pass
        clear_pid()

    engine.start()
    write_pid()
    setup_graceful_shutdown(cleanup)
    try:
        with scraper:
            stats = scraper.post_in_groups()
            emit("SUCCESS", "RUN_COMPLETE", robot=args.robot, **stats)
            db.record_run(args.robot)
            print(
                f"\n✓ Run terminé : succès={stats.get('success', 0)} | "
                f"ignorés={stats.get('skipped', 0)} | erreurs={stats.get('errors', 0)}"
            )
    except KeyboardInterrupt:
        emit("INFO", "INTERRUPTED_BY_USER")
    except Exception as e:
        emit("ERROR", "RUN_FAILED", robot=args.robot, error=str(e))
        sys.exit(1)
    finally:
        engine.stop()
        clear_pid()


def cmd_save_groups(args):
    _, config = _load_robot(args.robot)
    _maybe_validate_proxy(config, getattr(args, "validate_proxy", False))
    engine, scraper = _build_scraper(args, config, args.robot)
    engine.start()
    write_pid()
    try:
        with scraper:
            links = scraper.save_groups(args.keyword)
            print(f"\n✓ {len(links)} groupes sauvegardés pour '{args.robot}'")
    finally:
        engine.stop()
        clear_pid()


def cmd_comment(args):
    _, config = _load_robot(args.robot)
    engine, scraper = _build_scraper(args, config, args.robot)
    engine.start()
    write_pid()
    try:
        with scraper:
            urls = [u.strip() for u in args.urls.split(",") if u.strip()]
            count = scraper.social.browse_and_comment(urls, max_comments=args.max)
            print(f"\n✓ {count} commentaire(s) publiés")
    finally:
        engine.stop()
        clear_pid()


def cmd_dm(args):
    _, config = _load_robot(args.robot)
    engine, scraper = _build_scraper(args, config, args.robot)
    engine.start()
    write_pid()
    try:
        with scraper:
            ok = scraper.social.send_dm(
                target_profile_url=args.target,
                text=args.text,
                media_paths=getattr(args, "media", None),
            )
            print(f"\n{'✓' if ok else '✗'} DM {'envoyé' if ok else 'échoué'} → {args.target[:60]}")
    finally:
        engine.stop()
        clear_pid()


def cmd_dm_queue(args):
    _, config = _load_robot(args.robot)
    engine, scraper = _build_scraper(args, config, args.robot)
    engine.start()
    write_pid()
    try:
        with scraper:
            count = scraper.social.process_dm_queue(limit=args.limit)
            print(f"\n✓ {count} DM traités depuis la file")
    finally:
        engine.stop()
        clear_pid()


def cmd_migrate(args):
    rm = RobotManager()
    db = get_database()
    do_all = not (args.sessions or args.data)
    total = 0
    if args.sessions or do_all:
        n = rm.migrate_sessions_to_robots()
        print(f"✓ Sessions migrées → robots : {n}")
        total += n
    if args.data or do_all:
        c1 = db.import_campaigns_from_json(pathlib.Path("data/campaigns/campaigns.json"))
        c2 = db.import_groups_from_json(pathlib.Path("data/groups/groups.json"))
        print(f"✓ Campagnes importées : {c1} | Groupes : {c2}")
        total += c1 + c2
    print(f"\n✓ Migration v11 — {total} élément(s) traités")


def cmd_dashboard():
    db = get_database()
    stats = db.get_dashboard_stats()
    print("\n" + "=" * 50)
    print("  BON v11 — Dashboard")
    print("=" * 50)
    print(f"  {'Robots actifs':<30} {stats.get('total_robots', 0)}")
    print(f"  {'Comptes sains':<30} {stats.get('healthy_accounts', 0)}/{stats.get('total_accounts', 0)}")
    print(f"  {'Comptes bloqués':<30} {stats.get('blocked_accounts', 0)}")
    print(f"  {'Groupes actifs':<30} {stats.get('total_groups', 0)}")
    print(f"  {'Campagnes':<30} {stats.get('total_campaigns', 0)}")
    print(f"  {'Médias':<30} {stats.get('total_media_assets', 0)}")
    print(f"  {'DMs en attente':<30} {stats.get('pending_dms', 0)}")
    print(
        f"  {'Posts aujourd hui':<30} {stats.get('posts_today', 0)} "
        f"(✓{stats.get('successful_posts_today', 0)} ✗{stats.get('failed_posts_today', 0)})"
    )
    print(f"  {'Erreurs aujourd hui':<30} {stats.get('errors_today', 0)}")
    print("=" * 50)

    robots = db.get_all_robots()
    if robots:
        print("\n  Robots :")
        try:
            from libs.circuit_breaker import get_circuit_breaker
            cb = get_circuit_breaker()
        except Exception:
            cb = None
        for r in robots:
            cb_state = f" CB:{cb.get_state(r['robot_name'])}" if cb else ""
            run_stats = db.get_run_stats(r["robot_name"])
            runs_today = run_stats.get("run_count", 0)
            max_runs = r.get("max_runs_per_day", 2)
            print(
                f"    • {r['robot_name']:<20} ❤ {r.get('health_score', 100):3d}  "
                f"{r.get('status', '?'):<20} runs:{runs_today}/{max_runs}{cb_state}"
            )

    try:
        from libs.ua_updater import check_ua_freshness
        fresh, cur, lat = check_ua_freshness()
        ua_status = f"Chrome/{cur} ✓" if fresh else f"Chrome/{cur} → {lat} OBSOLÈTE ⚠"
        print(f"\n  User-Agent pool : {ua_status}")
        if not fresh:
            print("  → python -m bon update-ua")
    except Exception:
        pass
    print()


def cmd_update_ua():
    from libs.ua_updater import update_ua_pool
    update_ua_pool(verbose=True)
    try:
        from libs import stealth_profile
        stealth_profile._ua_cache = {}
        stealth_profile._profiles = {}
        print("  Cache stealth invalidé.")
    except Exception:
        pass


def cmd_export(args):
    db = get_database()
    n = db.export_publications_csv(args.out, robot_name=args.robot)
    print(f"✓ {n} ligne(s) → {args.out}")


def cmd_captcha_test(_args):
    from libs.captcha_solver import test_captcha_config
    ok, msg = test_captcha_config()
    print(msg)
    if not ok:
        sys.exit(1)


def cmd_schedule_add(args):
    db = get_database()
    if not db.get_robot(args.robot):
        print(f"✗ Robot inconnu : {args.robot}")
        sys.exit(1)
    jid = args.job_id or f"bon_{args.robot}_{hashlib.md5(args.cron.encode()).hexdigest()[:12]}"
    db.scheduler_upsert_job(jid, args.robot, args.cron, args.command, 1)
    print(f"✓ Job planificateur '{jid}' → robot={args.robot} cron={args.cron!r}")
    print("  Lancez : python -m bon schedule daemon")


def cmd_schedule_list(_args):
    for j in get_database().scheduler_list_jobs():
        print(
            f"  {j['job_id']:<28} robot={j['robot_name']:<12} active={j['active']} "
            f"cron={j['cron_expression']!r} cmd={j.get('command_name', 'post')}"
        )


def cmd_schedule_remove(args):
    if get_database().scheduler_delete_job(args.job_id):
        print(f"✓ Job supprimé : {args.job_id}")
    else:
        print(f"✗ Job introuvable : {args.job_id}")
        sys.exit(1)


def cmd_schedule_daemon(_args):
    from libs.bon_scheduler import run_daemon_scheduler
    run_daemon_scheduler(blocking=True)


def cmd_api(args):
    from libs.rest_api import run
    run(host=args.host, port=args.port)


def cmd_global_config_set(args):
    get_database().config_set(args.key, args.value)
    print(f"✓ config_kv[{args.key}] = {args.value!r}")


def cmd_global_config_get(args):
    v = get_database().config_get(args.key)
    print(v if v is not None else "")


def cmd_selectors_update(args):
    selectors_path = CONFIG_DIR / "selectors.json"
    if not selectors_path.exists():
        selectors_path = pathlib.Path("config") / "selectors.json"
    reg = SelectorRegistry(selectors_path)
    ok = reg.update_from_cdn(force=bool(args.force))
    print("✓ Sélecteurs mis à jour." if ok else "(aucune mise à jour — voir logs / config CDN)")


def main():
    _bootstrap()
    args = parse_args()

    if args.command == "robot":
        rc = getattr(args, "robot_cmd", None)
        rcc = getattr(args, "robot_config_cmd", None)
        if rc == "create":
            cmd_robot_create(args)
        elif rc == "list":
            cmd_robot_list()
        elif rc == "verify":
            cmd_robot_verify(args)
        elif rc == "delete":
            cmd_robot_delete(args)
        elif rc == "config":
            if rcc == "show":
                cmd_robot_config_show(args)
            elif rcc == "set":
                cmd_robot_config_set(args)
            elif rcc == "clear-proxy":
                cmd_robot_config_clear_proxy(args)
            else:
                print("Usage: python -m bon robot config [show|set|clear-proxy] ...")
        else:
            print("Usage: python -m bon robot [create|list|verify|delete|config] ...")
    elif args.command == "post":
        cmd_post(args)
    elif args.command == "save-groups":
        cmd_save_groups(args)
    elif args.command == "comment":
        cmd_comment(args)
    elif args.command == "dm":
        cmd_dm(args)
    elif args.command == "dm-queue":
        cmd_dm_queue(args)
    elif args.command == "migrate":
        cmd_migrate(args)
    elif args.command == "dashboard":
        cmd_dashboard()
    elif args.command == "update-ua":
        cmd_update_ua()
    elif args.command == "export":
        cmd_export(args)
    elif args.command == "captcha":
        if getattr(args, "captcha_cmd", None) == "test":
            cmd_captcha_test(args)
        else:
            print("Usage: python -m bon captcha test")
    elif args.command == "schedule":
        sc = getattr(args, "schedule_cmd", None)
        if sc == "add":
            cmd_schedule_add(args)
        elif sc == "list":
            cmd_schedule_list(args)
        elif sc == "remove":
            cmd_schedule_remove(args)
        elif sc == "daemon":
            cmd_schedule_daemon(args)
        else:
            print("Usage: python -m bon schedule [add|list|remove|daemon] ...")
    elif args.command == "api":
        cmd_api(args)
    elif args.command == "config":
        gcc = getattr(args, "global_config_cmd", None)
        if gcc == "set":
            cmd_global_config_set(args)
        elif gcc == "get":
            cmd_global_config_get(args)
        else:
            print("Usage: python -m bon config [set|get] ...")
    elif args.command == "selectors":
        if getattr(args, "selectors_cmd", None) == "update":
            cmd_selectors_update(args)
        else:
            print("Usage: python -m bon selectors update [--force]")
    elif args.command is None:
        _interactive()
    else:
        print(f"Commande inconnue : {args.command}")
        sys.exit(1)


def _interactive():
    print("BON v11 — Facebook Groups Publisher")
    print("=" * 40)
    robots = RobotManager().list_robots()
    if not robots:
        print("Aucun robot. Créez-en un :")
        print("  python -m bon robot create --robot robot1")
        return
    print("Robots :", ", ".join(robots))
    robot = input("Robot à utiliser : ").strip()
    if robot not in robots:
        print("Robot introuvable.")
        return
    print("\n1) Publier dans les groupes")
    print("2) Sauvegarder des groupes")
    print("3) Dashboard")
    print("4) Mettre à jour les User-Agents")
    print("5) Quitter")
    choice = input("Choix : ").strip()
    ns = argparse.Namespace(robot=robot, headless=False, command="post", validate_proxy=False)
    if choice == "1":
        cmd_post(ns)
    elif choice == "2":
        keyword = input("Mot-clé : ").strip()
        ns.keyword = keyword
        cmd_save_groups(ns)
    elif choice == "3":
        cmd_dashboard()
    elif choice == "4":
        cmd_update_ua()


if __name__ == "__main__":
    main()
