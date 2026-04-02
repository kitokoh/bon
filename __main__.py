"""
__main__.py v10 — Point d'entrée BON

Commandes :
  python -m bon robot create --robot <nom> [--account <nom>]
  python -m bon robot list
  python -m bon robot verify --robot <nom>
  python -m bon robot delete --robot <nom>
  python -m bon post --robot <nom> [--headless]
  python -m bon save-groups --robot <nom> --keyword <mot>
  python -m bon comment --robot <nom> --urls url1,url2 [--max N]
  python -m bon dm --robot <nom> --target <url> --text <txt> [--media f1 f2]
  python -m bon dm-queue --robot <nom> [--limit N]
  python -m bon migrate [--sessions] [--data]
  python -m bon dashboard
  python -m bon update-ua          ← NOUVEAU v10
"""
import sys, argparse, pathlib

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
        (pathlib.Path("data/groups/groups.json"),       db.import_groups_from_json),
    ]:
        if path.exists():
            fn(path)
    # Vérifier fraîcheur UA au démarrage
    try:
        from libs.ua_updater import check_ua_freshness
        fresh, current, latest = check_ua_freshness()
        if not fresh:
            print(f"[WARN] UA obsolètes : Chrome/{current} → Chrome/{latest} disponible")
            print(f"       Mettez à jour : python -m bon update-ua")
    except Exception:
        pass


def parse_args():
    p = argparse.ArgumentParser(description="BON v10 — Facebook Groups Publisher")
    sub = p.add_subparsers(dest="command")

    # robot
    r    = sub.add_parser("robot", help="Gestion des robots")
    rsub = r.add_subparsers(dest="robot_cmd")
    rc   = rsub.add_parser("create")
    rc.add_argument("--robot",   required=True)
    rc.add_argument("--account", default=None)
    rsub.add_parser("list")
    rv = rsub.add_parser("verify"); rv.add_argument("--robot", required=True)
    rd = rsub.add_parser("delete"); rd.add_argument("--robot", required=True)

    # post
    pp = sub.add_parser("post")
    pp.add_argument("--robot",   required=True)
    pp.add_argument("--headless", action="store_true")

    # save-groups
    sg = sub.add_parser("save-groups")
    sg.add_argument("--robot",   required=True)
    sg.add_argument("--keyword", required=True)
    sg.add_argument("--headless", action="store_true")

    # comment
    co = sub.add_parser("comment")
    co.add_argument("--robot", required=True)
    co.add_argument("--urls",  required=True, help="URLs séparées par virgule")
    co.add_argument("--max",   type=int, default=3)

    # dm
    dm = sub.add_parser("dm")
    dm.add_argument("--robot",  required=True)
    dm.add_argument("--target", required=True, help="URL profil Facebook cible")
    dm.add_argument("--text",   required=True)
    dm.add_argument("--media",  nargs="*", default=None)

    # dm-queue
    dq = sub.add_parser("dm-queue")
    dq.add_argument("--robot", required=True)
    dq.add_argument("--limit", type=int, default=10)

    # migrate
    mg = sub.add_parser("migrate")
    mg.add_argument("--sessions", action="store_true")
    mg.add_argument("--data",     action="store_true")

    # dashboard
    sub.add_parser("dashboard")

    # update-ua (NOUVEAU v10)
    sub.add_parser("update-ua", help="Mettre à jour le pool User-Agents (Chrome)")

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
    rm      = RobotManager()
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
    db     = get_database()
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
            print(f"  {r:<20} {rd.get('account_name','?'):<25} {rd.get('health_score','?'):>5}/100  {rd.get('status','?')}{cb_state}")
        print()
    else:
        print("Aucun robot configuré.")
        print("  python -m bon robot create --robot robot1")


def cmd_robot_verify(args):
    rm, config = _load_robot(args.robot)
    engine = PlaywrightEngine(headless=True)
    engine.start()
    try:
        ctx, page = engine.new_context(storage_state=config.get("storage_state", ""))
        page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=20000)
        if "/login" in page.url:
            print(f"✗ Robot '{args.robot}' : session expirée. Reconnectez-vous.")
            ctx.close(); sys.exit(1)
        print(f"✓ Robot '{args.robot}' : session valide.")
        ctx.close()
    finally:
        engine.stop()


def cmd_robot_delete(args):
    ok = RobotManager().delete_robot(args.robot)
    print(f"{'✓' if ok else '✗'} Robot '{args.robot}' {'supprimé' if ok else ': erreur suppression'}")


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
            print(f"\n✓ Run terminé : succès={stats.get('success',0)} | ignorés={stats.get('skipped',0)} | erreurs={stats.get('errors',0)}")
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
            print(f"\n{'✓' if ok else '✗'} DM {'envoyé' if ok else 'échoué'} → {args.target[:60]}")
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
    rm    = RobotManager()
    db    = get_database()
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
    print(f"\n✓ Migration v10 — {total} élément(s) traités")


def cmd_dashboard():
    db    = get_database()
    stats = db.get_dashboard_stats()
    print("\n" + "="*50)
    print("  BON v10 — Dashboard")
    print("="*50)
    print(f"  {'Robots actifs':<30} {stats.get('total_robots', 0)}")
    print(f"  {'Comptes sains':<30} {stats.get('healthy_accounts', 0)}/{stats.get('total_accounts', 0)}")
    print(f"  {'Comptes bloqués':<30} {stats.get('blocked_accounts', 0)}")
    print(f"  {'Groupes actifs':<30} {stats.get('total_groups', 0)}")
    print(f"  {'Campagnes':<30} {stats.get('total_campaigns', 0)}")
    print(f"  {'Médias':<30} {stats.get('total_media_assets', 0)}")
    print(f"  {'DMs en attente':<30} {stats.get('pending_dms', 0)}")
    print(f"  {'Posts aujourd hui':<30} {stats.get('posts_today', 0)} "
          f"(✓{stats.get('successful_posts_today',0)} ✗{stats.get('failed_posts_today',0)})")
    print(f"  {'Erreurs aujourd hui':<30} {stats.get('errors_today', 0)}")
    print("="*50)

    # Détail robots
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
            max_runs   = r.get("max_runs_per_day", 2)
            print(f"    • {r['robot_name']:<20} ❤ {r.get('health_score',100):3d}  "
                  f"{r.get('status','?'):<20} runs:{runs_today}/{max_runs}{cb_state}")

    # Alerte UA
    try:
        from libs.ua_updater import check_ua_freshness
        fresh, cur, lat = check_ua_freshness()
        ua_status = f"Chrome/{cur} ✓" if fresh else f"Chrome/{cur} → {lat} OBSOLÈTE ⚠"
        print(f"\n  User-Agent pool : {ua_status}")
        if not fresh:
            print(f"  → python -m bon update-ua")
    except Exception:
        pass
    print()


def cmd_update_ua():
    """Met à jour le pool User-Agents Chrome."""
    from libs.ua_updater import update_ua_pool
    update_ua_pool(verbose=True)
    # Invalider le cache stealth
    try:
        from libs import stealth_profile
        stealth_profile._ua_cache = {}
        stealth_profile._profiles = {}
        print("  Cache stealth invalidé.")
    except Exception:
        pass


def main():
    _bootstrap()
    args = parse_args()

    if args.command == "robot":
        rc = getattr(args, "robot_cmd", None)
        if rc == "create":   cmd_robot_create(args)
        elif rc == "list":   cmd_robot_list()
        elif rc == "verify": cmd_robot_verify(args)
        elif rc == "delete": cmd_robot_delete(args)
        else: print("Usage: python -m bon robot [create|list|verify|delete] ...")
    elif args.command == "post":        cmd_post(args)
    elif args.command == "save-groups": cmd_save_groups(args)
    elif args.command == "comment":     cmd_comment(args)
    elif args.command == "dm":          cmd_dm(args)
    elif args.command == "dm-queue":    cmd_dm_queue(args)
    elif args.command == "migrate":     cmd_migrate(args)
    elif args.command == "dashboard":   cmd_dashboard()
    elif args.command == "update-ua":   cmd_update_ua()
    elif args.command is None:          _interactive()
    else:
        print(f"Commande inconnue : {args.command}")
        sys.exit(1)


def _interactive():
    print("BON v10 — Facebook Groups Publisher")
    print("="*40)
    robots = RobotManager().list_robots()
    if not robots:
        print("Aucun robot. Créez-en un :")
        print("  python -m bon robot create --robot robot1")
        return
    print("Robots :", ", ".join(robots))
    robot = input("Robot à utiliser : ").strip()
    if robot not in robots:
        print("Robot introuvable."); return
    print("\n1) Publier dans les groupes")
    print("2) Sauvegarder des groupes")
    print("3) Dashboard")
    print("4) Mettre à jour les User-Agents")
    print("5) Quitter")
    choice = input("Choix : ").strip()
    ns = argparse.Namespace(robot=robot, headless=False, command="post")
    if choice == "1":   cmd_post(ns)
    elif choice == "2":
        keyword = input("Mot-clé : ").strip()
        ns.keyword = keyword
        cmd_save_groups(ns)
    elif choice == "3": cmd_dashboard()
    elif choice == "4": cmd_update_ua()


if __name__ == "__main__":
    main()
