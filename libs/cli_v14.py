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
import os
import pathlib
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


def _prompt_input(prompt: str, default: Optional[str] = None, required: bool = False) -> str:
    """Lit une saisie interactive avec valeur par défaut optionnelle."""
    suffix = f" [{default}]" if default is not None and default != "" else ""
    while True:
        try:
            value = input(f"{prompt}{suffix}: ").strip()
        except EOFError:
            value = ""
        if value:
            return value
        if default is not None:
            return str(default)
        if not required:
            return ""
        print("  Une valeur est requise.")


def _prompt_int(prompt: str, default: int) -> int:
    while True:
        raw = _prompt_input(prompt, default=str(default))
        try:
            return int(raw)
        except ValueError:
            print("  Merci d'entrer un nombre valide.")


def _prompt_yes_no(prompt: str, default_yes: bool = False) -> bool:
    default = "y" if default_yes else "n"
    while True:
        raw = _prompt_input(prompt, default=default).strip().lower()
        if raw in {"y", "yes", "o", "oui"}:
            return True
        if raw in {"n", "no", "non"}:
            return False
        print("  Réponds par oui/non (y/n).")


def _split_urls(raw: str) -> List[str]:
    return [item.strip() for item in (raw or "").split(",") if item.strip()]


def _ensure_robot_session(robot_name: str):
    """Crée une session logique si le robot n'existe pas encore en base."""
    sm = get_session_manager()
    session = sm.create_session(robot_name, from_db=True)
    return sm, session


def _choose_robot_name(db, prompt: str = "Robot") -> Optional[str]:
    """Choisit automatiquement le seul robot si possible, sinon demande un choix."""
    robots = db.get_all_robots()
    if not robots:
        return None
    if len(robots) == 1:
        return robots[0]["robot_name"]

    print(f"  Robots disponibles ({len(robots)}) :")
    for idx, robot in enumerate(robots, start=1):
        account = robot.get("account_name", "—")
        print(f"  {idx}) {robot['robot_name']}  [{account}]")

    while True:
        raw = _prompt_input(prompt, default="1")
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(robots):
                return robots[idx - 1]["robot_name"]
        for robot in robots:
            if raw == robot["robot_name"]:
                return robot["robot_name"]
        print("  Choix invalide.")


def _get_current_browser_url(robot_name: str) -> str:
    """Retourne l'URL actuelle du navigateur du robot si disponible."""
    try:
        sm = get_session_manager()
        session = sm.get_session(robot_name)
        if not session or not session._browser_ctx:
            return ""
        pages = getattr(session._browser_ctx, "pages", []) or []
        if not pages:
            return ""
        return getattr(pages[0], "url", "") or ""
    except Exception:
        return ""


def _looks_like_checkpoint(url: str) -> bool:
    url = (url or "").lower()
    return "two_step_verification" in url or "checkpoint" in url or "authentication" in url


def _looks_blank(url: str) -> bool:
    url = (url or "").strip().lower()
    return not url or url == "about:blank"


def _pick_active_page(context):
    """Essaie de sélectionner l'onglet réellement utile du contexte."""
    pages = getattr(context, "pages", []) or []
    if not pages:
        return context.new_page()

    for page in pages:
        try:
            url = getattr(page, "url", "") or ""
            if not _looks_blank(url):
                return page
        except Exception:
            continue

    return pages[0]


def _wait_for_page_ready(page, robot_name: str, context_label: str = "publication") -> None:
    """
    Attend que la page Playwright quitte un écran de login / checkpoint.

    Utilisé pendant les workflows de publication pour laisser l'utilisateur
    terminer la connexion Facebook dans la fenêtre ouverte.
    """
    try:
        current_url = getattr(page, "url", "") or ""
    except Exception:
        current_url = ""

    if _looks_blank(current_url):
        print("\n  Facebook est en train d'ouvrir la page de connexion.")
        print(f"  Robot: {robot_name}")
        print("  Si la fenêtre est encore blanche, attends le chargement ou termine la connexion.")
        wait_s = max(1, int(os.getenv("BON_START_WATCH_INTERVAL_S", "5")))
        try:
            while True:
                try:
                    current_url = getattr(page, "url", "") or ""
                except Exception:
                    current_url = ""
                if not _looks_blank(current_url):
                    break
                print(f"  ⏳ {robot_name}: page vide / chargement en cours")
                time.sleep(wait_s)
        except KeyboardInterrupt:
            print("\n  Attente interrompue par l'utilisateur.")
            return

    if not _looks_like_checkpoint(current_url):
        return

    print("\n  Facebook a ouvert un écran de vérification / checkpoint.")
    print(f"  Robot: {robot_name}")
    if current_url:
        print(f"  URL  : {current_url}")
    print("  Termine la connexion / vérification dans la fenêtre puis reviens ici.")
    print("  Le flux attendra tant que la page reste sur cet écran.")

    wait_s = max(1, int(os.getenv("BON_START_WATCH_INTERVAL_S", "5")))
    try:
        while True:
            try:
                current_url = getattr(page, "url", "") or ""
            except Exception:
                current_url = ""
            if not _looks_like_checkpoint(current_url):
                print(f"  ✓ {context_label} prête pour {robot_name}.")
                if current_url:
                    print(f"  URL actuelle: {current_url}")
                return
            print(f"  ⏳ {robot_name}: checkpoint toujours actif")
            if current_url:
                print(f"     URL: {current_url}")
            time.sleep(wait_s)
    except KeyboardInterrupt:
        print("\n  Attente interrompue par l'utilisateur.")


def _wait_for_checkpoint_release(robot_name: str, poll_s: int = 5) -> None:
    """Surveille la page jusqu'à la sortie du checkpoint Facebook."""
    print("\n  Mode watch checkpoint actif.")
    print("  Laisse la fenêtre Facebook ouverte et termine la vérification.")
    print("  Ctrl+C pour interrompre la surveillance.")

    try:
        while True:
            url = _get_current_browser_url(robot_name)
            if not _looks_like_checkpoint(url):
                print(f"  ✓ Vérification terminée pour {robot_name}.")
                if url:
                    print(f"  URL actuelle: {url}")
                return

            print(f"  ⏳ {robot_name}: checkpoint détecté")
            if url:
                print(f"     URL: {url}")
            time.sleep(max(1, poll_s))
    except KeyboardInterrupt:
        print("\n  Surveillance arrêtée par l'utilisateur.")


def _pause_for_login(robot_name: str, next_robot: Optional[str] = None) -> None:
    """Laisse le temps de se connecter à Facebook avant de lancer le robot suivant."""
    current_url = _get_current_browser_url(robot_name)
    checkpoint = _looks_like_checkpoint(current_url)
    message = [
        "\n  Le navigateur est ouvert pour la connexion Facebook.",
        f"  Robot actuel: {robot_name}",
    ]
    if next_robot:
        message.append(f"  Robot suivant: {next_robot}")
    if checkpoint:
        message.append("  Facebook est en verification / checkpoint.")
        message.append("  Termine la verification manuellement dans le navigateur.")
        message.append("  Quand tu as fini, tape 'ok' puis Entrée pour continuer.")
    else:
        message.append("  Si Facebook affiche une vérification en deux étapes, termine-la avant de continuer.")
        message.append("  Ensuite, appuie sur Entrée pour passer au robot suivant.")
    if current_url:
        message.append(f"  URL actuelle: {current_url}")
    print("\n".join(message))

    if sys.stdin.isatty():
        if checkpoint:
            watch_s = int(os.getenv("BON_START_WATCH_INTERVAL_S", "5"))
            _wait_for_checkpoint_release(robot_name, poll_s=watch_s)
        else:
            try:
                input("  Entrée pour lancer le robot suivant...")
            except EOFError:
                pass
    else:
        wait_s = int(os.getenv("BON_START_LOGIN_WAIT_S", "300"))
        print(f"  Terminal non interactif. Pause automatique de {wait_s}s...")
        time.sleep(wait_s)

    try:
        sm = get_session_manager()
        session = sm.get_session(robot_name)
        if session:
            state_file = session.profile_dir / "storage_state.json"
            try:
                session._browser_ctx.storage_state(path=str(state_file))
            except Exception:
                pass
    except Exception:
        pass


def _choose_robot_batch(db) -> List[str]:
    """Demande quels robots démarrer quand aucun robot n'est fourni."""
    robots = db.get_all_robots()
    if not robots:
        return []
    if len(robots) == 1:
        return [robots[0]["robot_name"]]

    print("\n  Choisis le mode de démarrage :")
    print("  1) Tous les robots")
    print("  2) Choisir un ou plusieurs robots")
    print("  0) Annuler")
    choice = _prompt_input("Mode", default="1")

    if choice == "0":
        return []
    if choice == "1":
        return [r["robot_name"] for r in robots]

    print("  Robots disponibles :")
    for idx, robot in enumerate(robots, start=1):
        account = robot.get("account_name", "—")
        print(f"  {idx}) {robot['robot_name']}  [{account}]")

    raw = _prompt_input("Numéros séparés par des virgules (ex: 1,3)", required=True)
    selected: List[str] = []
    for token in _split_urls(raw.replace(" ", ",")):
        if token.isdigit():
            idx = int(token)
            if 1 <= idx <= len(robots):
                name = robots[idx - 1]["robot_name"]
                if name not in selected:
                    selected.append(name)
        else:
            for robot in robots:
                if token == robot["robot_name"] and token not in selected:
                    selected.append(token)
    return selected


def _format_browser_processes(processes: List[dict], limit: int = 5) -> str:
    """Résume les processus navigateur détectés pour un robot."""
    if not processes:
        return ""
    preview = []
    for proc in processes[:limit]:
        pid = proc.get("pid", "?")
        name = proc.get("name", "browser")
        preview.append(f"{name}#{pid}")
    extra = len(processes) - len(preview)
    suffix = f" (+{extra} autres)" if extra > 0 else ""
    return ", ".join(preview) + suffix


def _choose_robot_campaign(db, robot_name: str) -> Optional[dict]:
    """Retourne la campagne préenregistrée à utiliser pour un robot."""
    campaigns = db.get_campaigns_for_robot(robot_name)
    if not campaigns:
        campaigns = db.get_all_campaigns()
    if not campaigns:
        return None
    chosen = campaigns[0]
    if isinstance(chosen, dict) and chosen.get("id"):
        variant = db.pick_random_variant(chosen["name"], language=chosen.get("language", "fr"))
        if variant:
            chosen = dict(chosen)
            chosen["variant"] = variant
    return chosen


def _build_publish_content(db, robot_name: str) -> str:
    """Construit le contenu à publier depuis la campagne du robot."""
    campaign = _choose_robot_campaign(db, robot_name)
    if not campaign:
        return ""

    variant = campaign.get("variant")
    if not variant:
        variant = db.pick_random_variant(campaign["name"], language=campaign.get("language", "fr"))
    if not variant:
        return ""

    text = (variant.get("text") or variant.get("text_fr") or "").strip()
    cta = (variant.get("cta") or "").strip()
    if cta and cta.lower() not in text.lower():
        text = f"{text}\n\n{cta}".strip()
    return text


def _best_effort_publish(page, target_url: str, content: str) -> bool:
    """Essaie de publier un texte sur la cible via des sélecteurs FB génériques."""
    try:
        page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2500)
    except Exception as e:
        _print_err(f"Navigation impossible vers {target_url}: {e}")
        return False

    composer_selectors = [
        "div[data-lexical-editor='true']",
        "div[data-contents='true']",
        "[data-testid='status-attachment-mentions-input']",
        "#composerInput",
        "textarea[name='xhpc_message']",
        "div[data-pagelet='FeedComposer']",
        "div[aria-label*='composer']",
        "div[role='textbox'][contenteditable='true']",
        "div[contenteditable='true'][role='textbox']",
        "div[contenteditable='true']",
    ]
    post_button_selectors = [
        "[data-testid='react-composer-post-button']",
        "div[role='button']:has-text('Publier')",
        "div[role='button']:has-text('Post')",
        "div[role='button']:has-text('Partager')",
        "div[role='button']:has-text('Share')",
        "button:has-text('Publier')",
        "button:has-text('Post')",
    ]

    composer = None
    for sel in composer_selectors:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=1500):
                composer = loc
                break
        except Exception:
            continue

    if not composer:
        _print_err(f"Aucun composer trouvé sur {target_url}")
        return False

    try:
        composer.click()
        try:
            composer.fill(content)
        except Exception:
            composer.press_sequentially(content, delay=25)
        page.wait_for_timeout(1200)
    except Exception as e:
        _print_err(f"Impossible de saisir le contenu: {e}")
        return False

    for sel in post_button_selectors:
        try:
            button = page.locator(sel).first
            if button.is_visible(timeout=1200):
                button.click()
                page.wait_for_timeout(2500)
                return True
        except Exception:
            continue

    try:
        page.keyboard.press("Control+Enter")
        page.wait_for_timeout(2500)
        return True
    except Exception:
        pass

    _print_err("Impossible de trouver le bouton de publication.")
    return False


def _interactive_publish(kind: str) -> None:
    """Lance un flux interactif de publication dans un groupe ou sur une page."""
    db = get_database()
    robot_name = _choose_robot_name(db, prompt="Choix du robot")
    if not robot_name:
        _print_err("Aucun robot disponible.")
        return
    content = _build_publish_content(db, robot_name)
    if not content:
        content = _prompt_input("Contenu à publier", required=True)

    if kind == "group":
        targets = [g["url"] for g in db.get_groups_for_robot(robot_name)]
        if not targets:
            raw_targets = _prompt_input(
                "Aucun groupe assigné. Liens des groupes (séparés par des virgules)",
                required=True,
            )
            targets = _split_urls(raw_targets)
        label = "groupe"
    else:
        raw_target = _prompt_input("Lien de la page", required=True)
        targets = [raw_target]
        label = "page"

    if not targets:
        _print_err("Aucune cible valide fournie.")
        return

    sm, session = _ensure_robot_session(robot_name)
    if not session.is_active() or not getattr(session, "_browser_ctx", None):
        if not sm.start_session(robot_name):
            _print_err(f"Impossible de démarrer la session du robot {robot_name}.")
            return
        session = sm.get_session(robot_name) or session

    _print_header(f"Publication {label}")
    print(f"  Robot   : {robot_name}")
    print(f"  Cibles  : {len(targets)}")
    print(f"  Texte   : {content[:120]}{'...' if len(content) > 120 else ''}")

    try:
        context = session._browser_ctx
        if not context:
            _print_err("Aucun navigateur actif n'est disponible pour ce robot.")
            return

        page = _pick_active_page(context)
        _wait_for_page_ready(page, robot_name, context_label="publication")
        for idx, target_url in enumerate(targets, start=1):
            _wait_for_page_ready(page, robot_name, context_label="publication")
            print(f"  -> [{idx}/{len(targets)}] {target_url}")
            ok = _best_effort_publish(page, target_url, content)
            print(f"     {'✓' if ok else '✗'} terminé")
            if not ok:
                print("     La publication n'a pas été effectuée. Je n'envoie pas le robot au groupe suivant.")
                break
            if idx < len(targets):
                time.sleep(2)

        print("  Le navigateur du robot reste ouvert.")
        input("Appuie sur Entrée pour revenir au terminal...")
    except Exception as e:
        _print_err(f"Échec du lancement navigateur: {e}")


def _interactive_recover_group_links() -> None:
    """Affiche et exporte les groupes connus en base."""
    db = get_database()
    robot_name = _choose_robot_name(db, prompt="Choix du robot")
    groups = db.get_groups_for_robot(robot_name) if robot_name else db.get_all_groups()

    _print_header("Liens des groupes")
    if not groups:
        print("  Aucun groupe en base.")
        return

    print(f"  Groupes actifs trouvés : {len(groups)}")
    for row in groups[:50]:
        print(f"  - {row['url']}")
    if len(groups) > 50:
        print(f"  ... et {len(groups) - 50} autres")

    out_path = _prompt_input("Fichier d'export texte", default="group_links.txt")
    try:
        path = pathlib.Path(out_path)
        path.write_text("\n".join(row["url"] for row in groups) + "\n", encoding="utf-8")
        print(f"  Exporté vers : {path.resolve()}")
    except Exception as e:
        _print_err(f"Export impossible: {e}")


def _interactive_menu() -> None:
    """Menu de démarrage interactif."""
    while True:
        _print_header("Menu interactif")
        print("  1) Publier dans les groupes du robot")
        print("  2) Publier sur une page")
        print("  3) Récupérer les liens des groupes du robot")
        print("  0) Quitter")
        choice = _prompt_input("Choix", default="1")

        if choice == "1":
            _interactive_publish("group")
            return
        if choice == "2":
            _interactive_publish("page")
            return
        if choice == "3":
            _interactive_recover_group_links()
            return
        if choice in {"0", "q", "quit", "exit"}:
            print("  Au revoir.")
            return
        print("  Choix invalide.")


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

    # Si aucun robot spécifié, demander un choix ou démarrer tous les robots actifs
    if not robots:
        try:
            db = get_database()
            if sys.stdin.isatty():
                robots = _choose_robot_batch(db)
            else:
                robots = [r["robot_name"] for r in db.get_all_robots()
                          if r.get("active", 1)]
        except Exception as e:
            _print_err(f"Impossible de lister les robots : {e}")
            sys.exit(1)

    if not robots:
        print("  Démarrage annulé.")
        return

    _print_header("Start Sessions")
    print(f"  Démarrage de {len(robots)} session(s)...\n")

    results = {}
    for idx, robot_name in enumerate(robots):
        session = sm.get_session(robot_name)

        browser_processes = sm.list_browser_processes(robot_name)
        already_open = bool(session and session.is_active())
        orphan_browser = bool(browser_processes)

        if already_open or orphan_browser:
            details = []
            if already_open:
                details.append("session active")
            if orphan_browser:
                details.append(f"navigateur détecté: {_format_browser_processes(browser_processes)}")
            prompt = f"{robot_name} est déjà ouvert ({'; '.join(details)}). Le fermer et relancer ?"

            should_restart = True
            if sys.stdin.isatty():
                should_restart = _prompt_yes_no(prompt, default_yes=True)
            else:
                print(f"  {prompt} -> fermeture automatique")

            if should_restart:
                if already_open:
                    sm.stop_session(robot_name)
                killed = sm.terminate_browser_processes(robot_name)
                if killed:
                    print(f"  Processus navigateur fermés pour {robot_name}: {killed}")
                    time.sleep(1)
                session = sm.create_session(robot_name, from_db=True)
            else:
                print(f"  {robot_name} laissé en l'état.")
                continue

        session = sm.create_session(robot_name, from_db=True)
        ok = sm.start_session(robot_name)
        results[robot_name] = ok
        icon = "✓" if ok else "✗"
        proxy = session.proxy_server or "no proxy"
        print(f"  {icon} {robot_name:<20} [{proxy}]  → {session.state.value}")
        if ok:
            next_robot = robots[idx + 1] if idx + 1 < len(robots) else None
            _pause_for_login(robot_name, next_robot=next_robot)

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
  python -m bon
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
    if argv is None and len(sys.argv) == 1 and sys.stdin.isatty():
        _interactive_menu()
        return

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
        if sys.stdin.isatty():
            _interactive_menu()
        else:
            parser.print_help()
    else:
        _print_err(f"Commande inconnue : {args.command}")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    run_cli()
