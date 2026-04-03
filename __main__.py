"""
__main__.py v14 — Point d'entrée BON

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  NOUVEAUTÉS v14
  ─────────────
  PHASE 2 — Isolation sessions (session_manager.py)
    Profil Chrome dédié par robot, proxy dédié par session,
    0 cookie partagé, parallélisme sûr, lifecycle start/stop/restart

  PHASE 3 — Anti-détection avancé (human_behavior.py)
    Délais Gamma non-linéaires, trajectoires souris Bézier,
    scroll humain, clic randomisé, simulation fatigue

  PHASE 4 — Task Queue SQLite (task_queue.py)
    post / comment / join_group, retry backoff exponentiel
    t = base * 2^n, persistance crash, workers thread

  PHASE 5 — Monitoring industriel (monitor.py)
    Taux succès/compte, classification erreurs, actions/heure,
    health score 0-100, logs JSON structurés

  PHASE 6 — CLI Pro (cli_v14.py)
    add-account, assign-proxy, start, stop, status --watch,
    logs, queue, enqueue, health
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Commandes v14 (CLI Pro) :
  python -m bon add-account --name robot1 --email x@fb.com
  python -m bon assign-proxy --robot robot1 --proxy-server http://host:8080
  python -m bon start [--robots robot1 robot2]
  python -m bon stop  [--robots robot1]
  python -m bon status [--watch] [--interval 5]
  python -m bon logs [--robot robot1] [--lines 50] [--json]
  python -m bon queue [--robot robot1] [--status pending]
  python -m bon enqueue --type post --robot robot1 --campaign camp1
  python -m bon health [--robot robot1]

Commandes historiques (v11+) :
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
    # Proxy
    rcset.add_argument("--proxy-server", default=None)
    rcset.add_argument("--proxy-user", default=None)
    rcset.add_argument("--proxy-pass", default=None)
    # Limites de run
    rcset.add_argument("--max-groups-per-run", type=int, default=None,
                       metavar="N", help="Nombre max de groupes par run (ex. 10)")
    rcset.add_argument("--max-runs-per-day", type=int, default=None,
                       metavar="N", help="Nombre max de runs par jour (ex. 2)")
    rcset.add_argument("--delay-min", type=int, default=None,
                       metavar="SEC", help="Delai min entre groupes en secondes")
    rcset.add_argument("--delay-max", type=int, default=None,
                       metavar="SEC", help="Delai max entre groupes en secondes")
    rcset.add_argument("--cooldown", type=int, default=None,
                       metavar="SEC", help="Cooldown entre runs (ex. 7200)")
    # Localisation
    rcset.add_argument("--locale", default=None,
                       metavar="LOCALE", help="Locale navigateur (ex. fr-FR, en-US)")
    rcset.add_argument("--timezone", default=None,
                       metavar="TZ", help="Timezone (ex. Europe/Paris, America/New_York)")
    # Notifications Telegram
    rcset.add_argument("--telegram-token", default=None,
                       metavar="TOKEN", help="Token bot Telegram")
    rcset.add_argument("--telegram-chat-id", default=None,
                       metavar="ID", help="Chat ID Telegram")
    # CAPTCHA
    rcset.add_argument("--captcha-key", default=None,
                       metavar="KEY", help="Cle 2captcha pour ce robot (None = desactive)")
    rcset.add_argument("--clear-captcha-key", action="store_true",
                       help="Efface la cle captcha de ce robot (retombe sur variable globale)")
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

    ex = sub.add_parser("export", help="Exporter les publications (CSV ou XLSX)")
    ex.add_argument("--out", required=True, help="Fichier .csv ou .xlsx")
    ex.add_argument("--robot", default=None)
    ex.add_argument(
        "--format",
        choices=("csv", "xlsx"),
        default=None,
        help="Par défaut : déduit de l’extension du fichier",
    )

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

    uid = sub.add_parser(
        "ui-detect",
        help="Forcer la re-détection du profil UI (langue/variante) d'un compte",
    )
    uid.add_argument("--robot", required=True, help="Nom du robot à ré-analyser")
    uid.add_argument(
        "--force",
        action="store_true",
        default=True,
        help="Ignore le cache DB et re-détecte depuis le DOM (défaut: True)",
    )

    # ── Commandes v14 (CLI Pro) ───────────────────────────────────────────
    aa = sub.add_parser("add-account", help="[v14] Ajouter un compte Facebook")
    aa.add_argument("--name", required=True)
    aa.add_argument("--email", default=None)
    aa.add_argument("--profile-url", default=None)

    ap = sub.add_parser("assign-proxy", help="[v14] Assigner un proxy à un robot")
    ap.add_argument("--robot", required=True)
    ap.add_argument("--proxy-server", required=True)
    ap.add_argument("--proxy-user", default=None)
    ap.add_argument("--proxy-pass", default=None)

    st = sub.add_parser("start", help="[v14] Démarrer des sessions isolées")
    st.add_argument("--robots", nargs="*", metavar="ROBOT")

    sp = sub.add_parser("stop", help="[v14] Arrêter des sessions")
    sp.add_argument("--robots", nargs="*", metavar="ROBOT")
    sp.add_argument("--clean-profile", action="store_true")

    sta = sub.add_parser("status", help="[v14] Statut temps-réel")
    sta.add_argument("--watch", action="store_true")
    sta.add_argument("--interval", type=int, default=5)

    lg = sub.add_parser("logs", help="[v14] Derniers logs JSON")
    lg.add_argument("--lines", type=int, default=30)
    lg.add_argument("--robot", default=None)
    lg.add_argument("--event", default=None)
    lg.add_argument("--json", action="store_true")

    qu = sub.add_parser("queue", help="[v14] Statut file de tâches")
    qu.add_argument("--robot", default=None)
    qu.add_argument("--status", default=None,
                    choices=["pending", "running", "success", "failed", "dead"])

    eq = sub.add_parser("enqueue", help="[v14] Ajouter une tâche")
    eq.add_argument("--type", required=True, choices=["post", "comment", "join_group"])
    eq.add_argument("--robot", required=True)
    eq.add_argument("--campaign", default=None)
    eq.add_argument("--groups", default=None)
    eq.add_argument("--urls", default=None)
    eq.add_argument("--group-url", default=None)
    eq.add_argument("--priority", type=int, default=5)

    hl = sub.add_parser("health", help="[v14] Score de santé des comptes")
    hl.add_argument("--robot", default=None)

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
    changed = []

    # --- Proxy ---
    if args.proxy_server:
        from libs.proxy_util import build_playwright_proxy
        px = build_playwright_proxy(args.proxy_server, args.proxy_user, args.proxy_pass)
        cfg["proxy"] = px
        cfg["proxy_server"] = px["server"]
        cfg["proxy_username"] = px.get("username") or ""
        cfg["proxy_password"] = px.get("password") or ""
        changed.append("proxy")

    # --- Limites de run ---
    if args.max_groups_per_run is not None:
        cfg["max_groups_per_run"] = args.max_groups_per_run
        changed.append(f"max_groups_per_run={args.max_groups_per_run}")
    if args.max_runs_per_day is not None:
        cfg["max_runs_per_day"] = args.max_runs_per_day
        changed.append(f"max_runs_per_day={args.max_runs_per_day}")
    if args.delay_min is not None:
        cfg["delay_min_s"] = args.delay_min
        changed.append(f"delay_min_s={args.delay_min}")
    if args.delay_max is not None:
        cfg["delay_max_s"] = args.delay_max
        changed.append(f"delay_max_s={args.delay_max}")
    if args.cooldown is not None:
        cfg["cooldown_between_runs_s"] = args.cooldown
        changed.append(f"cooldown_between_runs_s={args.cooldown}")

    # --- Localisation ---
    if args.locale is not None:
        cfg["locale"] = args.locale
        changed.append(f"locale={args.locale}")
    if args.timezone is not None:
        cfg["timezone_id"] = args.timezone
        changed.append(f"timezone_id={args.timezone}")

    # --- Telegram ---
    if args.telegram_token is not None:
        cfg["telegram_token"] = args.telegram_token
        changed.append("telegram_token=***")
    if args.telegram_chat_id is not None:
        cfg["telegram_chat_id"] = args.telegram_chat_id
        changed.append(f"telegram_chat_id={args.telegram_chat_id}")

    # --- CAPTCHA ---
    if getattr(args, "clear_captcha_key", False):
        cfg["captcha_api_key"] = None
        changed.append("captcha_api_key=None (retombe sur BON_2CAPTCHA_KEY global)")
    elif args.captcha_key is not None:
        cfg["captcha_api_key"] = args.captcha_key
        changed.append("captcha_api_key=***")

    if not changed:
        print("Aucun parametre modifie. Utilisez --help pour voir les options.")
        return

    rm.save_config(args.robot, cfg)
    print(f"Config mise a jour pour '{args.robot}' :")
    for c in changed:
        print(f"  ✓ {c}")



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
    fmt = args.format
    if fmt is None:
        low = args.out.lower()
        fmt = "xlsx" if low.endswith(".xlsx") else "csv"
    if fmt == "csv":
        n = db.export_publications_csv(args.out, robot_name=args.robot)
    else:
        try:
            n = db.export_publications_xlsx(args.out, robot_name=args.robot)
        except ImportError as e:
            print(f"✗ {e}")
            sys.exit(1)
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


def cmd_ui_detect(args):
    """
    Force la re-détection du profil UI (langue + variante) d'un robot.
    Lance un navigateur headless, charge Facebook, analyse le DOM,
    et met à jour la base de données.

    Usage : python -m bon ui-detect --robot robot1
    """
    from libs.account_ui_profiler import AccountUIProfiler

    robot_name = args.robot
    rm, cfg = _load_robot(robot_name)

    print(f"\n🔍 Détection du profil UI pour '{robot_name}'...")

    try:
        with sync_playwright() as pw:
            engine = PlaywrightEngine(pw, cfg, robot_name=robot_name)
            page = engine.new_page(headless=True)

            # Charger la page d'accueil FB pour maximiser les signaux DOM
            try:
                page.goto("https://www.facebook.com/?sk=h_nor",
                          wait_until="domcontentloaded", timeout=20000)
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception as e:
                print(f"⚠ Navigation Facebook échouée : {e}")
                print("  Détection sur la page de session courante...")

            db = get_database()
            profiler = AccountUIProfiler(page, db, account_name=robot_name)
            profile = profiler.detect(force_refresh=True)

            print(f"\n✓ Profil UI détecté et sauvegardé :")
            print(f"   Langue    : {profile.lang}")
            print(f"   Variante  : {profile.variant}")
            print(f"   Confiance : {profile.confidence}%")
            print(f"   Source    : {profile.source}")
            print(f"   Timestamp : {profile.detected_at}")

            engine.close()

    except Exception as e:
        emit("ERROR", "UI_DETECT_CMD_FAILED", robot=robot_name, error=str(e))
        print(f"\n✗ Échec de la détection : {e}")
        sys.exit(1)


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
    elif args.command == "ui-detect":
        cmd_ui_detect(args)
    # ── Commandes v14 ────────────────────────────────────────────────────
    elif args.command in (
        "add-account", "assign-proxy", "start", "stop",
        "status", "logs", "queue", "enqueue", "health",
    ):
        from libs.cli_v14 import run_cli
        run_cli(sys.argv[1:])
    elif args.command is None:
        _interactive()
    else:
        print(f"Commande inconnue : {args.command}")
        sys.exit(1)


def _interactive():
    print("BON v14 — Facebook Groups Publisher Pro")
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
