"""
bon_scheduler.py v12 — Planification cron par robot (APScheduler + persistance SQLite).

Usage :
  python -m bon schedule add --robot r1 --cron "0 8 * * *"
  python -m bon schedule daemon
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
from datetime import datetime
from typing import List, Optional

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _main_py_argv(*args: str) -> List[str]:
    return [sys.executable, "-m", "bon", *args]


def _run_robot_command(robot_name: str, command_name: str = "post") -> None:
    cmd = command_name.strip() or "post"
    if cmd == "post":
        argv = _main_py_argv("post", "--robot", robot_name, "--headless")
    else:
        argv = _main_py_argv(cmd, "--robot", robot_name)
    subprocess.Popen(
        argv,
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=sys.platform != "win32",
    )


def parse_cron_parts(expr: str) -> dict:
    """Expression 5 champs : minute hour day month day_of_week."""
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError(
            "Cron attendu : 5 champs (minute heure jour mois jour_semaine), ex. '0 8 * * *'"
        )
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }


def load_jobs_from_db():
    from libs.database import get_database
    return [j for j in get_database().scheduler_list_jobs() if j.get("active")]


def sync_apscheduler(sched, db_jobs: Optional[List[dict]] = None):
    """Enregistre les jobs DB dans un scheduler APScheduler."""
    try:
        from apscheduler.triggers.cron import CronTrigger
    except ImportError as e:
        raise RuntimeError("Installez apscheduler : pip install apscheduler") from e

    if db_jobs is None:
        db_jobs = load_jobs_from_db()

    for j in db_jobs:
        jid = j["job_id"]
        try:
            parts = parse_cron_parts(j["cron_expression"])
        except ValueError:
            continue
        robot = j["robot_name"]
        cmd = j.get("command_name") or "post"

        def make_runner(rn: str, c: str, job_id: str):
            def runner():
                from libs.database import get_database
                get_database().scheduler_update_run_meta(
                    job_id, datetime.now().isoformat(), None
                )
                _run_robot_command(rn, c)

            return runner

        trigger = CronTrigger(
            minute=parts["minute"],
            hour=parts["hour"],
            day=parts["day"],
            month=parts["month"],
            day_of_week=parts["day_of_week"],
        )
        sched.add_job(
            make_runner(robot, cmd, jid),
            trigger=trigger,
            id=jid,
            replace_existing=True,
        )


def run_daemon_scheduler(blocking: bool = True) -> None:
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError as e:
        raise RuntimeError(
            "apscheduler manquant. Installez avec : pip install apscheduler>=3.10.0"
        ) from e

    from libs.database import get_database

    db = get_database()
    jobs = load_jobs_from_db()
    if not jobs:
        print("Aucun job actif en base. Ex. : python -m bon schedule add --robot r1 --cron \"0 8 * * *\"")
        return

    if blocking:
        sched = BlockingScheduler()
    else:
        sched = BackgroundScheduler()

    sync_apscheduler(sched, jobs)
    if blocking:
        print(f"Scheduler démarré — {len(jobs)} job(s). Ctrl+C pour arrêter.")
        try:
            sched.start()
        except (KeyboardInterrupt, SystemExit):
            sched.shutdown(wait=False)
    else:
        sched.start()
        return sched
