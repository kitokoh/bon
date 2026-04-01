"""
__main__.py v9 — Point d'entrée BON

Commandes :
  python -m bon robot create --robot <nom> [--account <nom>]
  python -m bon robot list
  python -m bon robot verify --robot <nom>
  python -m bon robot delete --robot <nom>
  python -m bon post --robot <nom> [--headless]
  python -m bon save-groups --robot <nom> --keyword <mot>
  python -m bon comment --robot <nom> --urls url1,url2
  python -m bon dm --robot <nom> --target <url> --text <txt>
  python -m bon dm-queue --robot <nom>
  python -m bon migrate [--sessions] [--data]
  python -m bon dashboard
"""
import sys, argparse, pathlib

# ── Licence ─────────────────────────────────────────────────────────────────
try:
    from check_license import is_license_valid
    if not is_license_valid():
        print("\n✗ Licence invalide ou expirée.\n", file=sys.stderr)
        sys.exit(1)
except Exception as _e:
    print(f"[WARN] Licence ignorée : {_e}", file=sys.stderr)

# ── Playwright ───────────────────────────────────────────────────────────────
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
from libs.config_validator import validate_session_config, ConfigError


# ── Bootstrap DB (import JSON → SQL, idempotent) ─────────────────────────────
def _bootstrap():
    db = get_database()
    for path, fn in [
        (pathlib.Path("data/campaigns/campaigns.json"), db.import_campaigns_from_json),
        (pathlib.Path("data/groups/groups.json"),       db.import_groups_from_json),
    ]:
        if path.exists():
            fn(path)


# ── Parseur ───────────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(description="BON v9 — Facebook Groups Publisher")
    sub = p.add_subparsers(dest="command")

    # robot
    r = sub.add_parser("robot", help="Gestion des robots")
    rsub = r.add_subparsers(dest="robot_cmd")
    rc = rsub.add_parser("create"); rc.add_argument("--robot", required=True); rc.add_argument("--account")
    rsub.add_parser("list")
    rv = rsub.add_parser("verify"); rv.add_argument("--robot", required=True)
    rd = rsub.add_parser("delete"); rd.add_argument("--robot", required=True)

    # post
    pp = sub.add_parser("post"); pp.add_argument("--robot", required=True); pp.add_argument("--headless", action="store_true")

    # save-groups
    sg = sub.add_parser("save-groups"); sg.add_argument("--robot", required=True); sg.add_argument("--keyword", required=True); sg.add_argument("--headless", action="store_true")

    # comment
    co = sub.add_parser("comment"); co.add_argument("--robot", required=True); co.add_argument("--urls", required=True); co.add_argument("--max", type=int, default=3)

    # dm
    dm = sub.add_parser("dm"); dm.add_argument("--robot", required=True); dm.add_argument("--target", required=True); dm.add_argument("--text", required=True); dm.add_argument("--media", nargs="*")

    # dm-queue
    dq = sub.add_parser("dm-queue"); dq.add_argument("--robot", required=True); dq.add_argument("--limit", type=int, default=10)

    # migrate
    mg = sub.add_parser("migrate"); mg.add_argument("--sessions", action="store_true"); mg.add_argument("--data", action="store_true")

    # dashboard
    sub.add_parser("dashboard")

    return p.parse_args()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _load_robot(robot_name: str):
    rm = RobotManager()
    if not rm.robot_exists(robot_name):
        emit("ERROR", "ROBOT_NOT_FOUND", robot=robot_name)
        print(f"\n✗ Robot '{robot_name}' introuvable.")
        print(f"  Créez-le : python -m bon robot create --robot {robot_name}")
        sys.exit(1)
    config = rm.get_config(robot_name)
    storage = config.get("storage_state", "")
    if storage and not pathlib.Path(storage).exists():
        emit("WARN", "STORAGE_STATE_MISSING", robot=robot_name)
    return rm, config


def _check_limits(robot_name: str):
    db = get_database()
    can_run, reason = db.check_run_limits(robot_name)
    if not can_run:
        emit("WARN", "RUN_LIMIT_EXIT", robot=robot_name, reason=reason)
        sys.exit(0)


def _build_scraper(args, config, robot_name):
    headless       = getattr(args, "headless", False)
    selectors_path = CONFIG_DIR / "selectors.json"
    if not selectors_path.exists():
        selectors_path = pathlib.Path("config") / "selectors.json"
    selectors = SelectorRegistry(selectors_path)
    selectors.update_from_cdn()
    engine  = PlaywrightEngine(
        headless    = headless,
        locale      = config.get("locale", "fr-FR"),
        timezone_id = config.get("timezone_id", "Europe/Paris"),
    )
    scraper = Scraper(engine, selectors, config, robot_name)
    return engine, scraper


# ── Commandes ─────────────────────────────────────────────────────────────────
def cmd_robot_create(args):
    rm = RobotManager()
    account = getattr(args, "account", None) or args.robot
    engine  = PlaywrightEngine(headless=False)
    engine.start()
    try:
        ok = rm.create_robot(args.robot, engine.browser, account_name=account)
        if ok:
            print(f"\n✓ Robot '{args.robot}' créé (compte : {account})")
        else:
            print(f"\n✗ Création échouée pour '{args.robot}'")
            sys.exit(1)
    finally:
        engine.stop()


def cmd_robot_list():
    robots = RobotManager().list_robots()
    if robots:
        print(f"Robots disponibles ({len(robots)}) :")
        for r in robots:
            robot_data = get_database().get_robot(r)
            status = robot_data.get("status", "?") if robot_data else "?"
            print(f"  • {r}  (compte: {robot_data.get('account_name','?')}, santé: {robot_data.get('health_score','?')}/100)")
    else:
        print("Aucun robot configuré.\nCréez-en un : python -m bon robot create --robot robot1")


def cmd_robot_verify(args):
    rm, config = _load_robot(args.robot)
    engine = PlaywrightEngine(headless=True)
    engine.start()
    try:
        ctx, page = engine.new_context(storage_state=config.get("storage_state", ""))
        page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=20000)
        if "/login" in page.url:
            print(f"✗ Robot '{args.robot}' : session expirée.")
            sys.exit(1)
        print(f"✓ Robot '{args.robot}' : session valide.")
        ctx.close()
    finally:
        engine.stop()


def cmd_robot_delete(args):
    ok = RobotManager().delete_robot(args.robot)
    print(f"{'✓' if ok else '✗'} Robot '{args.robot}' {'supprimé' if ok else 'erreur suppression'}")


def cmd_post(args):
    rm, config = _load_robot(args.robot)
    _check_limits(args.robot)
    engine, scraper = _build_scraper(args, config, args.robot)
    db = get_database()

    def cleanup():
        try: scraper.close(); engine.stop()
        except Exception: pass
        clear_pid()

    engine.start(); write_pid()
    setup_graceful_shutdown(cleanup)
    try:
        with scraper:
            stats = scraper.post_in_groups()
            emit("SUCCESS", "RUN_COMPLETE", robot=args.robot, **stats)
            db.record_run(args.robot)
    except KeyboardInterrupt:
        emit("INFO", "INTERRUPTED_BY_USER")
    except Exception as e:
        emit("ERROR", "RUN_FAILED", robot=args.robot, error=str(e))
        sys.exit(1)
    finally:
        engine.stop(); clear_pid()


def cmd_save_groups(args):
    rm, config = _load_robot(args.robot)
    engine, scraper = _build_scraper(args, config, args.robot)
    engine.start(); write_pid()
    try:
        with scraper:
            links = scraper.save_groups(args.keyword)
            print(f"\n✓ {len(links)} groupes sauvegardés pour '{args.robot}'")
    finally:
        engine.stop(); clear_pid()


def cmd_comment(args):
    rm, config = _load_robot(args.robot)
    engine, scraper = _build_scraper(args, config, args.robot)
    engine.start(); write_pid()
    try:
        with scraper:
            urls  = [u.strip() for u in args.urls.split(",") if u.strip()]
            count = scraper.social.browse_and_comment(urls, max_comments=args.max)
            print(f"\n✓ {count} commentaire(s) publiés")
    finally:
        engine.stop(); clear_pid()


def cmd_dm(args):
    rm, config = _load_robot(args.robot)
    engine, scraper = _build_scraper(args, config, args.robot)
    engine.start(); write_pid()
    try:
        with scraper:
            ok = scraper.social.send_dm(
                target_profile_url = args.target,
                text               = args.text,
                media_paths        = getattr(args, "media", None),
            )
            print(f"\n{'✓' if ok else '✗'} DM {'envoyé' if ok else 'échoué'}")
    finally:
        engine.stop(); clear_pid()


def cmd_dm_queue(args):
    rm, config = _load_robot(args.robot)
    engine, scraper = _build_scraper(args, config, args.robot)
    engine.start(); write_pid()
    try:
        with scraper:
            count = scraper.social.process_dm_queue(limit=args.limit)
            print(f"\n✓ {count} DM traités depuis la file")
    finally:
        engine.stop(); clear_pid()


def cmd_migrate(args):
    rm  = RobotManager()
    db  = get_database()
    all = not (args.sessions or args.data)
    total = 0
    if args.sessions or all:
        n = rm.migrate_sessions_to_robots()
        print(f"✓ {n} session(s) → robots")
        total += n
    if args.data or all:
        c1 = db.import_campaigns_from_json(pathlib.Path("data/campaigns/campaigns.json"))
        c2 = db.import_groups_from_json(pathlib.Path("data/groups/groups.json"))
        print(f"✓ {c1} campagne(s), {c2} groupe(s) importés en SQL")
        total += c1 + c2
    print(f"\n✓ Migration v9 — {total} élément(s) traités")


def cmd_dashboard():
    stats = get_database().get_dashboard_stats()
    print("\n" + "="*45)
    print("  BON v9 — Dashboard")
    print("="*45)
    for k, v in stats.items():
        label = k.replace("_", " ").capitalize()
        print(f"  {label:<30} {v}")
    print("="*45)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    _bootstrap()
    args = parse_args()

    if args.command == "robot":
        rc = getattr(args, "robot_cmd", None)
        if rc == "create": cmd_robot_create(args)
        elif rc == "list":   cmd_robot_list()
        elif rc == "verify": cmd_robot_verify(args)
        elif rc == "delete": cmd_robot_delete(args)
        else: print("Usage: python -m bon robot [create|list|verify|delete] ...")
    elif args.command == "post":          cmd_post(args)
    elif args.command == "save-groups":   cmd_save_groups(args)
    elif args.command == "comment":       cmd_comment(args)
    elif args.command == "dm":            cmd_dm(args)
    elif args.command == "dm-queue":      cmd_dm_queue(args)
    elif args.command == "migrate":       cmd_migrate(args)
    elif args.command == "dashboard":     cmd_dashboard()
    elif args.command is None:            _interactive()
    else:
        print(f"Commande inconnue : {args.command}")
        sys.exit(1)


def _interactive():
    print("BON v9 — Facebook Groups Publisher")
    print("="*40)
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
    print("4) Quitter")
    choice = input("Choix : ").strip()
    ns = argparse.Namespace(robot=robot, headless=False, command="post")
    if choice == "1":   cmd_post(ns)
    elif choice == "2":
        keyword = input("Mot-clé : ").strip()
        ns.keyword = keyword
        cmd_save_groups(ns)
    elif choice == "3": cmd_dashboard()


if __name__ == "__main__":
    main()
