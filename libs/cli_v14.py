"""
cli_v14.py — CLI Pro BON v14

PHASE 6 : CLI pro
  Commandes :
    add-account    — ajouter un compte FB
    assign-proxy   — assigner un proxy à un robot
    start          — démarrer une ou plusieurs sessions
    stop           — arrêter une ou plusieurs sessions
    status         — afficher le statut temps-réel
    logs           — afficher les derniers logs JSON
    queue          — gérer la file de tâches
    enqueue        — ajouter une tâche à la file
    health         — score de santé par compte

  Stats temps-réel :
    - sessions actives
    - taux de succès
    - erreurs classifiées
    - actions/heure
"""

import argparse
import json
import sys
import time
import threading
from datetime import datetime
from typing import List, Optional

try:
    from libs.session_manager import get_session_manager, SessionState
    from libs.task_queue import get_task_queue, TaskType
    from libs.monitor import get_monitor, ErrorClassifier
    from libs.database import get_database
    from libs.log_emitter import emit
except ImportError:
    from session_manager import get_session_manager, SessionState
    from task_queue import get_task_queue, TaskType
    from monitor import get_monitor, ErrorClassifier
    from database import get_database
    from log_emitter import emit


# ── Helpers affichage ─────────────────────────────────────────────────────────

def _print_header(title: str):
    width = 60
    print("\n" + "═" * width)
    print(f"  BON v14 — {title}")
    print("═" * width)


def _print_ok(msg: str):
    print(f"  ✓ {msg}")


def _print_err(msg: str):
    print(f"  ✗ {msg}", file=sys.stderr)


def _fmt_ts(ts: Optional[str]) -> str:
    if not ts:
        return "—"
    try:
        return datetime.fromisoformat(ts).strftime("%H:%M:%S")
    except Exception:
        return ts[:19]


def _health_icon(status: str) -> str:
    return {"healthy": "✓", "degraded": "⚠", "critical": "✗", "dead": "☠"}.get(status, "?")


# ── Commande : add-account ────────────────────────────────────────────────────

def cmd_add_account(args):
    """Ajoute un compte Facebook à la base."""
    db = get_database()
    account = db.ensure_account_exists(
        name=args.name,
        email=getattr(args, "email", None),
        profile_url=getattr(args, "profile_url", None),
    )
    _print_header("Add Account")
    _print_ok(f"Compte '{args.name}' ajouté/mis à jour")
    if getattr(args, "email", None):
        print(f"     Email      : {args.email}")
    if getattr(args, "profile_url", None):
        print(f"     Profil URL : {args.profile_url}")


# ── Commande : assign-proxy ───────────────────────────────────────────────────

def cmd_assign_proxy(args):
    """Assigne un proxy à un robot."""
    db = get_database()
    robot = db.get_robot(args.robot)
    if not robot:
        _print_err(f"Robot inconnu : {args.robot}")
        sys.exit(1)

    db._exec(
        """UPDATE robots SET proxy_server=?, proxy_username=?, proxy_password=?,
           updated_at=datetime('now') WHERE robot_name=?""",
        (args.proxy_server,
         getattr(args, "proxy_user", None),
         getattr(args, "proxy_pass", None),
         args.robot)
    )

    _print_header("Assign Proxy")
    _print_ok(f"Proxy assigné à '{args.robot}'")
    print(f"     Proxy      : {args.proxy_server}")
    if getattr(args, "proxy_user", None):
        print(f"     Auth       : {args.proxy_user}:***")


# ── Commande : start ──────────────────────────────────────────────────────────

def cmd_start(args):
    """Démarre une ou plusieurs sessions."""
    sm = get_session_manager()
    robots = args.robots if hasattr(args, "robots") and args.robots else []

    # Si aucun robot spécifié, démarrer tous les robots actifs
    if not robots:
        try:
            db = get_database()
            robots = [r["robot_name"] for r in db.get_all_robots()
                      if r.get("active", 1)]
        except Exception as e:
            _print_err(f"Impossible de lister les robots : {e}")
            sys.exit(1)

    if not robots:
        _print_err("Aucun robot actif trouvé.")
        sys.exit(1)

    _print_header("Start Sessions")
    print(f"  Démarrage de {len(robots)} session(s)...\n")

    results = {}
    for robot_name in robots:
        session = sm.create_session(robot_name, from_db=True)
        ok = sm.start_session(robot_name)
        results[robot_name] = ok
        icon = "✓" if ok else "✗"
        proxy = session.proxy_server or "no proxy"
        print(f"  {icon} {robot_name:<20} [{proxy}]  → {session.state.value}")

    total_ok = sum(1 for v in results.values() if v)
    print(f"\n  {total_ok}/{len(robots)} sessions démarrées.")


# ── Commande : stop ───────────────────────────────────────────────────────────

def cmd_stop(args):
    """Arrête une ou plusieurs sessions."""
    sm = get_session_manager()
    robots = getattr(args, "robots", []) or []

    if not robots:
        # Arrêter toutes les sessions actives
        active = sm.list_active_sessions()
        if not active:
            print("  Aucune session active.")
            return
        robots = active

    _print_header("Stop Sessions")
    clean = getattr(args, "clean_profile", False)

    for robot_name in robots:
        ok = sm.stop_session(robot_name, clean_profile=clean)
        icon = "✓" if ok else "✗"
        print(f"  {icon} {robot_name} arrêté")

    if clean:
        print("\n  ⚠ Profils Chrome supprimés (cookies perdus)")


# ── Commande : status ─────────────────────────────────────────────────────────

def cmd_status(args):
    """Affiche le statut temps-réel de toutes les sessions."""
    sm = get_session_manager()
    monitor = get_monitor()
    tq = get_task_queue()

    watch = getattr(args, "watch", False)
    interval = getattr(args, "interval", 5)

    def _display():
        sessions = sm.list_sessions()
        snap = monitor.get_snapshot()
        queue_stats = tq.get_stats()

        _print_header("Status")
        now = datetime.now().strftime("%H:%M:%S")
        print(f"  Heure           : {now}")
        print(f"  Sessions totales: {sm.session_count()}")
        print(f"  Sessions actives: {sm.active_count()}")
        print(f"  Actions/heure   : {snap.get('total_aph', 0):.1f}")
        print(f"  Succès moyen    : {snap.get('avg_success_rate', 1)*100:.1f}%")
        print(f"  File (pending)  : {queue_stats.get('pending', 0)}")
        print(f"  File (failed)   : {queue_stats.get('failed', 0)}")

        if sessions:
            print("\n  ┌─────────────────────────────────────────────────┐")
            print(  "  │ Robot               État       Proxy       Uptime│")
            print(  "  ├─────────────────────────────────────────────────┤")
            for s in sessions:
                state = s["state"]
                state_icon = {
                    "running":  "▶ running ",
                    "stopped":  "■ stopped ",
                    "error":    "✗ error   ",
                    "starting": "… starting",
                    "idle":     "○ idle    ",
                }.get(state, state[:9].ljust(9))

                proxy = (s.get("proxy") or "none")[:14]
                uptime = s.get("uptime_s")
                uptime_str = f"{int(uptime)}s" if uptime else "—"

                # Métriques depuis monitor
                acc_data = snap.get("accounts", {}).get(s["robot_name"], {})
                health = acc_data.get("health_score", "—")
                sr = acc_data.get("success_rate_1h", None)
                sr_str = f"{sr*100:.0f}%" if sr is not None else "—"

                print(
                    f"  │ {s['robot_name']:<19} {state_icon}  "
                    f"{proxy:<14} {uptime_str:>6}│"
                )

                if acc_data:
                    print(
                        f"  │   ❤ {health:>3}  ✓{acc_data.get('success_count',0):>4} "
                        f"✗{acc_data.get('failure_count',0):>3}  "
                        f"{acc_data.get('actions_per_hour',0):.0f}aph "
                        f"{sr_str:>5} ok{' '*(15)}│"
                    )
            print("  └─────────────────────────────────────────────────┘")

        # Erreurs récentes
        acc_data_all = snap.get("accounts", {})
        error_summary: dict = {}
        for data in acc_data_all.values():
            for ec, n in data.get("error_counts", {}).items():
                error_summary[ec] = error_summary.get(ec, 0) + n

        if error_summary:
            print("\n  Erreurs (classifiées) :")
            for ec, n in sorted(error_summary.items(), key=lambda x: -x[1])[:6]:
                retryable = ErrorClassifier.is_retryable(
                    ErrorClassifier.classify(ec)
                )
                tag = "retry" if retryable else "FATAL"
                print(f"    {ec:<25} {n:>4}  [{tag}]")

    if watch:
        print("  Mode watch (Ctrl+C pour quitter)...")
        try:
            while True:
                print("\033[2J\033[H", end="")  # clear terminal
                _display()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n  Arrêt du watch.")
    else:
        _display()


# ── Commande : logs ───────────────────────────────────────────────────────────

def cmd_logs(args):
    """Affiche les derniers logs JSON structurés."""
    monitor = get_monitor()
    n = getattr(args, "lines", 30)
    robot_filter = getattr(args, "robot", None)
    event_filter = getattr(args, "event", None)
    json_mode = getattr(args, "json", False)

    logs = monitor.get_recent_logs(n=max(n * 3, 200))  # Lire plus pour filtrer

    # Filtres
    if robot_filter:
        logs = [l for l in logs if l.get("robot") == robot_filter or
                l.get("account") == robot_filter]
    if event_filter:
        logs = [l for l in logs if l.get("event", "").upper() == event_filter.upper()]

    logs = logs[-n:]  # Garder les N derniers après filtrage

    if json_mode:
        for entry in logs:
            print(json.dumps(entry, ensure_ascii=False))
        return

    _print_header("Logs")
    for entry in logs:
        ts = _fmt_ts(entry.get("ts"))
        event = entry.get("event", "?")
        robot = entry.get("robot", entry.get("account", "?"))
        action = entry.get("action_type", "")
        err_class = entry.get("error_class", "")
        msg = entry.get("error_msg", "")[:80]

        if event == "SUCCESS":
            line = f"  ✓ {ts}  {robot:<18} {action}"
        elif event == "FAILURE":
            line = f"  ✗ {ts}  {robot:<18} [{err_class}] {msg}"
        elif event == "SNAPSHOT":
            aph = entry.get("total_aph", 0)
            sr = entry.get("avg_success_rate", 0)
            line = f"  ◈ {ts}  SNAPSHOT  {aph:.1f}aph  {sr*100:.0f}% ok"
        else:
            line = f"  · {ts}  {event:<12} {robot}"

        print(line)

    print(f"\n  {len(logs)} entrée(s) affichée(s).")


# ── Commande : queue ──────────────────────────────────────────────────────────

def cmd_queue(args):
    """Affiche le statut de la file de tâches."""
    tq = get_task_queue()
    robot = getattr(args, "robot", None)
    status_filter = getattr(args, "status", None)

    stats = tq.get_stats(robot_name=robot)
    tasks = tq.list_tasks(robot_name=robot, status=status_filter, limit=30)

    _print_header("Task Queue")
    print(f"  Total      : {stats.get('total', 0)}")
    print(f"  Pending    : {stats.get('pending', 0)}")
    print(f"  Running    : {stats.get('running', 0)}")
    print(f"  Success    : {stats.get('success', 0)}")
    print(f"  Failed     : {stats.get('failed', 0)}")
    print(f"  Dead       : {stats.get('dead', 0)}")

    if tasks:
        print(f"\n  Tâches récentes (max 30) :")
        for t in tasks:
            icon = {"pending": "○", "running": "▶", "success": "✓",
                    "failed": "⚠", "dead": "☠"}.get(t["status"], "?")
            run_at = _fmt_ts(t.get("run_at"))
            err = (t.get("error_msg") or "")[:50]
            print(
                f"  {icon} #{t['task_id']:<5} {t['task_type']:<12} "
                f"{t['robot_name']:<16} att={t['attempt']}/{t['max_attempts']} "
                f"run@{run_at}  {err}"
            )


# ── Commande : enqueue ────────────────────────────────────────────────────────

def cmd_enqueue(args):
    """Ajoute une tâche à la file."""
    tq = get_task_queue()
    task_type = args.type
    robot = args.robot

    if task_type == TaskType.POST.value:
        if not getattr(args, "campaign", None):
            _print_err("--campaign requis pour type=post")
            sys.exit(1)
        groups = (getattr(args, "groups", "") or "").split(",")
        task_id = tq.enqueue_post(robot, args.campaign,
                                  [g.strip() for g in groups if g.strip()])
    elif task_type == TaskType.COMMENT.value:
        urls = (getattr(args, "urls", "") or "").split(",")
        task_id = tq.enqueue_comment(robot,
                                     [u.strip() for u in urls if u.strip()])
    elif task_type == TaskType.JOIN_GROUP.value:
        if not getattr(args, "group_url", None):
            _print_err("--group-url requis pour type=join_group")
            sys.exit(1)
        task_id = tq.enqueue_join_group(robot, args.group_url)
    else:
        _print_err(f"Type inconnu : {task_type}. Valeurs : post, comment, join_group")
        sys.exit(1)

    _print_ok(f"Tâche #{task_id} ajoutée → {task_type} pour {robot}")


# ── Commande : health ─────────────────────────────────────────────────────────

def cmd_health(args):
    """Affiche le score de santé des comptes."""
    monitor = get_monitor()
    robot_filter = getattr(args, "robot", None)

    _print_header("Account Health")

    if robot_filter:
        health = monitor.get_account_health(robot_filter)
        if health:
            icon = _health_icon(health.status)
            print(f"  {icon} {robot_filter:<20} ❤ {health.score:3d}  {health.status}")
            if health.factors:
                print("     Facteurs :")
                for factor, penalty in health.factors.items():
                    print(f"       {factor:<30} {penalty:+d} pts")
        else:
            print(f"  Aucune donnée pour '{robot_filter}'")
        return

    # Tous les robots depuis DB
    try:
        db = get_database()
        robots = db.get_all_robots()
    except Exception:
        robots = []

    if not robots:
        print("  Aucun robot enregistré.")
        return

    for robot in robots:
        name = robot["robot_name"]
        health = monitor.get_account_health(name)
        if health:
            icon = _health_icon(health.status)
            print(f"  {icon} {name:<20} ❤ {health.score:3d}  {health.status}")
        else:
            # Pas encore de métriques en mémoire → score DB
            score = robot.get("health_score", 100)
            status = robot.get("status", "healthy")
            icon = _health_icon(status)
            print(f"  {icon} {name:<20} ❤ {score:3d}  {status}  (DB)")


# ── Parser CLI ────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bon-v14",
        description="BON v14 — Facebook Groups Publisher Pro CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  python -m bon add-account --name robot1 --email test@fb.com
  python -m bon assign-proxy --robot robot1 --proxy-server http://1.2.3.4:8080
  python -m bon start --robots robot1 robot2
  python -m bon status --watch
  python -m bon logs --robot robot1 --lines 50
  python -m bon enqueue --type post --robot robot1 --campaign camp1
  python -m bon queue --status pending
  python -m bon health
        """,
    )
    sub = p.add_subparsers(dest="command")

    # add-account
    aa = sub.add_parser("add-account", help="Ajouter un compte Facebook")
    aa.add_argument("--name", required=True, help="Nom du compte (identifiant interne)")
    aa.add_argument("--email", default=None, help="Email Facebook")
    aa.add_argument("--profile-url", default=None, help="URL du profil Facebook")

    # assign-proxy
    ap = sub.add_parser("assign-proxy", help="Assigner un proxy à un robot")
    ap.add_argument("--robot", required=True)
    ap.add_argument("--proxy-server", required=True, help="ex: http://host:8080")
    ap.add_argument("--proxy-user", default=None)
    ap.add_argument("--proxy-pass", default=None)

    # start
    st = sub.add_parser("start", help="Démarrer des sessions")
    st.add_argument("--robots", nargs="*", metavar="ROBOT",
                    help="Robots à démarrer (tous si omis)")

    # stop
    sp = sub.add_parser("stop", help="Arrêter des sessions")
    sp.add_argument("--robots", nargs="*", metavar="ROBOT",
                    help="Robots à arrêter (tous si omis)")
    sp.add_argument("--clean-profile", action="store_true",
                    help="Supprimer le profil Chrome (⚠ perd les cookies)")

    # status
    sta = sub.add_parser("status", help="Statut temps-réel des sessions")
    sta.add_argument("--watch", action="store_true",
                     help="Mode watch (rafraîchissement automatique)")
    sta.add_argument("--interval", type=int, default=5,
                     help="Intervalle rafraîchissement en secondes (défaut: 5)")

    # logs
    lg = sub.add_parser("logs", help="Derniers logs structurés JSON")
    lg.add_argument("--lines", type=int, default=30, help="Nombre de lignes")
    lg.add_argument("--robot", default=None, help="Filtrer par robot")
    lg.add_argument("--event", default=None,
                    help="Filtrer par type d'événement (SUCCESS, FAILURE, ...)")
    lg.add_argument("--json", action="store_true",
                    help="Sortie brute JSON (une ligne par entrée)")

    # queue
    qu = sub.add_parser("queue", help="Statut de la file de tâches")
    qu.add_argument("--robot", default=None)
    qu.add_argument("--status", default=None,
                    choices=["pending", "running", "success", "failed", "dead"])

    # enqueue
    eq = sub.add_parser("enqueue", help="Ajouter une tâche à la file")
    eq.add_argument("--type", required=True,
                    choices=["post", "comment", "join_group"])
    eq.add_argument("--robot", required=True)
    eq.add_argument("--campaign", default=None, help="Nom de campagne (type=post)")
    eq.add_argument("--groups", default=None,
                    help="URLs groupes séparées par virgule (type=post)")
    eq.add_argument("--urls", default=None,
                    help="URLs posts séparées par virgule (type=comment)")
    eq.add_argument("--group-url", default=None,
                    help="URL du groupe (type=join_group)")
    eq.add_argument("--priority", type=int, default=5)

    # health
    hl = sub.add_parser("health", help="Score de santé des comptes")
    hl.add_argument("--robot", default=None, help="Robot spécifique")

    return p


def run_cli(argv: Optional[List[str]] = None):
    """Point d'entrée CLI v14 (peut être appelé depuis __main__.py)."""
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "add-account":  cmd_add_account,
        "assign-proxy": cmd_assign_proxy,
        "start":        cmd_start,
        "stop":         cmd_stop,
        "status":       cmd_status,
        "logs":         cmd_logs,
        "queue":        cmd_queue,
        "enqueue":      cmd_enqueue,
        "health":       cmd_health,
    }

    if args.command in dispatch:
        try:
            dispatch[args.command](args)
        except KeyboardInterrupt:
            print("\n  Interrompu.")
        except Exception as e:
            _print_err(str(e))
            sys.exit(1)
    elif args.command is None:
        parser.print_help()
    else:
        _print_err(f"Commande inconnue : {args.command}")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    run_cli()
