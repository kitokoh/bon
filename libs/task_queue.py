"""
task_queue.py v14 — File de tâches locale robuste (SQLite)

PHASE 4 : Task Queue robuste
  - Tâches : post, comment, join_group
  - Statuts : pending, running, failed, success
  - Retry avec backoff exponentiel : t = base * 2^n
  - Persistance et récupération après crash

Architecture :
  TaskQueue      → interface principale (enqueue, dequeue, retry)
  Task           → dataclass représentant une tâche
  TaskWorker     → thread consommateur de tâches

Formule retry :
  next_retry = now + base_delay * 2^attempt_number
  base_delay = 30s (configurable)
  max_attempts = 5 (configurable)
"""

import json
import sqlite3
import threading
import time
import pathlib
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List, Callable
from enum import Enum

try:
    from libs.log_emitter import emit
    from libs.database import get_database
except ImportError:
    from log_emitter import emit
    from database import get_database

# ── Types de tâches ───────────────────────────────────────────────────────────

class TaskType(str, Enum):
    POST       = "post"
    COMMENT    = "comment"
    JOIN_GROUP = "join_group"
    DM         = "dm"
    SUBSCRIBE  = "subscribe"


class TaskStatus(str, Enum):
    PENDING  = "pending"
    RUNNING  = "running"
    SUCCESS  = "success"
    FAILED   = "failed"
    DEAD     = "dead"     # max retries atteint → abandon définitif


# ── Dataclass Tâche ───────────────────────────────────────────────────────────

@dataclass
class Task:
    task_type:    str                           # TaskType value
    robot_name:   str
    payload:      Dict[str, Any]                # données spécifiques à la tâche
    task_id:      Optional[int] = None
    status:       str = TaskStatus.PENDING.value
    priority:     int = 5                       # 1 (urgent) → 10 (faible)
    attempt:      int = 0
    max_attempts: int = 5
    base_delay_s: int = 30                      # délai de base pour backoff
    created_at:   Optional[str] = None
    updated_at:   Optional[str] = None
    run_at:       Optional[str] = None          # timestamp planifié (retry)
    error_msg:    Optional[str] = None
    result:       Optional[Dict] = None

    @property
    def next_retry_delay(self) -> int:
        """t = base * 2^n  (backoff exponentiel)"""
        return self.base_delay_s * (2 ** self.attempt)

    @property
    def next_retry_at(self) -> datetime:
        return datetime.now() + timedelta(seconds=self.next_retry_delay)

    @property
    def is_exhausted(self) -> bool:
        return self.attempt >= self.max_attempts

    def to_dict(self) -> Dict:
        return {
            "task_id":      self.task_id,
            "task_type":    self.task_type,
            "robot_name":   self.robot_name,
            "status":       self.status,
            "priority":     self.priority,
            "attempt":      self.attempt,
            "max_attempts": self.max_attempts,
            "created_at":   self.created_at,
            "updated_at":   self.updated_at,
            "run_at":       self.run_at,
            "error_msg":    self.error_msg,
            "payload":      self.payload,
            "result":       self.result,
        }


# ── Gestionnaire de file ──────────────────────────────────────────────────────

class TaskQueue:
    """
    File de tâches persistante sur SQLite.

    Thread-safe. Survit aux crashes (WAL mode).
    Les tâches running au démarrage sont remises en pending (récupération crash).
    """

    DEFAULT_BASE_DELAY = 30   # secondes
    DEFAULT_MAX_RETRIES = 5

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            try:
                from libs.config_manager import LOGS_DIR
                db_path = str(LOGS_DIR / "task_queue.db")
            except ImportError:
                db_path = "logs/task_queue.db"

        self.db_path = pathlib.Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()
        self._recover_crashed_tasks()

    # ── Schéma ───────────────────────────────────────────────────────────

    def _init_schema(self):
        with self._lock:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type    TEXT NOT NULL,
                    robot_name   TEXT NOT NULL,
                    status       TEXT NOT NULL DEFAULT 'pending',
                    priority     INTEGER DEFAULT 5,
                    attempt      INTEGER DEFAULT 0,
                    max_attempts INTEGER DEFAULT 5,
                    base_delay_s INTEGER DEFAULT 30,
                    payload      TEXT NOT NULL DEFAULT '{}',
                    result       TEXT,
                    error_msg    TEXT,
                    run_at       TEXT,
                    created_at   TEXT DEFAULT (datetime('now')),
                    updated_at   TEXT DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_robot_status
                    ON tasks(robot_name, status);

                CREATE INDEX IF NOT EXISTS idx_tasks_run_at
                    ON tasks(run_at, status, priority);

                CREATE TABLE IF NOT EXISTS task_events (
                    event_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id    INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    message    TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
                );
            """)
            self._conn.commit()

    def _recover_crashed_tasks(self):
        """
        Récupération après crash :
        Les tâches status=running au démarrage n'ont pas terminé proprement.
        → Remises en pending (seront retraitées).
        """
        with self._lock:
            cursor = self._conn.execute(
                "SELECT task_id FROM tasks WHERE status = 'running'"
            )
            crashed = [row[0] for row in cursor.fetchall()]
            if crashed:
                self._conn.execute(
                    "UPDATE tasks SET status='pending', updated_at=datetime('now') "
                    "WHERE status='running'"
                )
                self._conn.commit()
                emit("WARN", "TASK_QUEUE_CRASH_RECOVERY",
                     recovered_count=len(crashed),
                     task_ids=crashed)

    # ── Enqueue ───────────────────────────────────────────────────────────

    def enqueue(
        self,
        task_type: str,
        robot_name: str,
        payload: Dict[str, Any],
        priority: int = 5,
        max_attempts: int = DEFAULT_MAX_RETRIES,
        base_delay_s: int = DEFAULT_BASE_DELAY,
        run_at: Optional[datetime] = None,
    ) -> int:
        """
        Ajoute une tâche à la file.
        Retourne le task_id.

        priority : 1 (urgent) → 10 (faible)
        run_at   : planification différée (None = immédiat)
        """
        run_at_str = run_at.isoformat() if run_at else datetime.now().isoformat()

        with self._lock:
            cursor = self._conn.execute(
                """INSERT INTO tasks
                   (task_type, robot_name, status, priority, max_attempts,
                    base_delay_s, payload, run_at)
                   VALUES (?, ?, 'pending', ?, ?, ?, ?, ?)""",
                (task_type, robot_name, priority, max_attempts,
                 base_delay_s, json.dumps(payload), run_at_str)
            )
            task_id = cursor.lastrowid
            self._log_event(task_id, "ENQUEUED",
                            f"type={task_type} priority={priority}")
            self._conn.commit()

        emit("INFO", "TASK_ENQUEUED",
             task_id=task_id, task_type=task_type,
             robot=robot_name, priority=priority)
        return task_id

    def enqueue_post(self, robot_name: str, campaign: str,
                     group_urls: List[str], priority: int = 5) -> int:
        return self.enqueue(
            TaskType.POST.value, robot_name,
            payload={"campaign": campaign, "group_urls": group_urls},
            priority=priority,
        )

    def enqueue_comment(self, robot_name: str, post_urls: List[str],
                        max_comments: int = 3, priority: int = 6) -> int:
        return self.enqueue(
            TaskType.COMMENT.value, robot_name,
            payload={"post_urls": post_urls, "max_comments": max_comments},
            priority=priority,
        )

    def enqueue_join_group(self, robot_name: str, group_url: str,
                           priority: int = 7) -> int:
        return self.enqueue(
            TaskType.JOIN_GROUP.value, robot_name,
            payload={"group_url": group_url},
            priority=priority,
        )

    # ── Dequeue ───────────────────────────────────────────────────────────

    def dequeue(self, robot_name: Optional[str] = None) -> Optional[Task]:
        """
        Récupère la prochaine tâche à traiter.

        Priorité : 1 (urgent) en premier.
        Filtre : run_at <= now (tâches planifiées prêtes).
        Atomique : marque immédiatement running.
        """
        now = datetime.now().isoformat()
        with self._lock:
            if robot_name:
                row = self._conn.execute(
                    """SELECT * FROM tasks
                       WHERE status='pending' AND robot_name=?
                       AND run_at <= ?
                       ORDER BY priority ASC, task_id ASC
                       LIMIT 1""",
                    (robot_name, now)
                ).fetchone()
            else:
                row = self._conn.execute(
                    """SELECT * FROM tasks
                       WHERE status='pending'
                       AND run_at <= ?
                       ORDER BY priority ASC, task_id ASC
                       LIMIT 1""",
                    (now,)
                ).fetchone()

            if not row:
                return None

            task_id = row["task_id"]
            self._conn.execute(
                "UPDATE tasks SET status='running', updated_at=datetime('now') "
                "WHERE task_id=?", (task_id,)
            )
            self._log_event(task_id, "STARTED", f"attempt={row['attempt'] + 1}")
            self._conn.commit()

        return self._row_to_task(row)

    # ── Complétion ────────────────────────────────────────────────────────

    def mark_success(self, task_id: int, result: Optional[Dict] = None) -> None:
        """Marque une tâche comme réussie."""
        with self._lock:
            self._conn.execute(
                """UPDATE tasks SET status='success', result=?,
                   updated_at=datetime('now')
                   WHERE task_id=?""",
                (json.dumps(result) if result else None, task_id)
            )
            self._log_event(task_id, "SUCCESS")
            self._conn.commit()
        emit("INFO", "TASK_SUCCESS", task_id=task_id)

    def mark_failed(self, task_id: int, error_msg: str,
                    retry: bool = True) -> None:
        """
        Marque une tâche comme échouée.

        Si retry=True et attempts < max_attempts :
          → status=pending, run_at = now + base * 2^attempt (backoff exponentiel)
        Sinon :
          → status=dead (abandon définitif)
        """
        with self._lock:
            row = self._conn.execute(
                "SELECT attempt, max_attempts, base_delay_s FROM tasks "
                "WHERE task_id=?", (task_id,)
            ).fetchone()

            if not row:
                return

            attempt = row["attempt"] + 1
            max_att = row["max_attempts"]
            base    = row["base_delay_s"]

            if retry and attempt < max_att:
                # Backoff exponentiel : t = base * 2^n
                delay_s = base * (2 ** attempt)
                next_run = (datetime.now() + timedelta(seconds=delay_s)).isoformat()
                self._conn.execute(
                    """UPDATE tasks SET status='pending', attempt=?,
                       error_msg=?, run_at=?, updated_at=datetime('now')
                       WHERE task_id=?""",
                    (attempt, error_msg, next_run, task_id)
                )
                self._log_event(task_id, "RETRY_SCHEDULED",
                                f"attempt={attempt}/{max_att} "
                                f"delay={delay_s}s next={next_run}")
                emit("WARN", "TASK_RETRY_SCHEDULED",
                     task_id=task_id, attempt=attempt,
                     delay_s=delay_s, next_run=next_run)
            else:
                self._conn.execute(
                    """UPDATE tasks SET status='dead', attempt=?,
                       error_msg=?, updated_at=datetime('now')
                       WHERE task_id=?""",
                    (attempt, error_msg, task_id)
                )
                self._log_event(task_id, "DEAD",
                                f"abandoned after {attempt} attempts")
                emit("ERROR", "TASK_DEAD",
                     task_id=task_id, attempts=attempt,
                     error=error_msg)

            self._conn.commit()

    # ── Statistiques ──────────────────────────────────────────────────────

    def get_stats(self, robot_name: Optional[str] = None) -> Dict:
        """Statistiques de la file par statut."""
        with self._lock:
            if robot_name:
                rows = self._conn.execute(
                    """SELECT status, COUNT(*) as n, task_type
                       FROM tasks WHERE robot_name=?
                       GROUP BY status, task_type""",
                    (robot_name,)
                ).fetchall()
            else:
                rows = self._conn.execute(
                    """SELECT status, COUNT(*) as n, task_type
                       FROM tasks
                       GROUP BY status, task_type"""
                ).fetchall()

        stats: Dict = {"total": 0}
        for row in rows:
            status = row["status"]
            n = row["n"]
            t = row["task_type"]
            stats[status] = stats.get(status, 0) + n
            stats[f"{t}_{status}"] = stats.get(f"{t}_{status}", 0) + n
            stats["total"] += n

        return stats

    def get_pending_count(self, robot_name: Optional[str] = None) -> int:
        now = datetime.now().isoformat()
        with self._lock:
            if robot_name:
                return self._conn.execute(
                    "SELECT COUNT(*) FROM tasks WHERE status='pending' "
                    "AND robot_name=? AND run_at<=?", (robot_name, now)
                ).fetchone()[0]
            return self._conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE status='pending' "
                "AND run_at<=?", (now,)
            ).fetchone()[0]

    def list_tasks(self, robot_name: Optional[str] = None,
                   status: Optional[str] = None,
                   limit: int = 50) -> List[Dict]:
        with self._lock:
            filters = []
            params: List = []
            if robot_name:
                filters.append("robot_name=?"); params.append(robot_name)
            if status:
                filters.append("status=?"); params.append(status)
            where = "WHERE " + " AND ".join(filters) if filters else ""
            params.append(limit)
            rows = self._conn.execute(
                f"SELECT * FROM tasks {where} "
                f"ORDER BY updated_at DESC LIMIT ?", params
            ).fetchall()
        return [self._row_to_task(r).to_dict() for r in rows]

    def purge_old_tasks(self, days: int = 7) -> int:
        """Supprime les tâches success/dead vieilles de N jours."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM tasks WHERE status IN ('success','dead') "
                "AND updated_at < ?", (cutoff,)
            )
            self._conn.commit()
            n = cursor.rowcount
        if n:
            emit("INFO", "TASK_QUEUE_PURGED", deleted=n, older_than_days=days)
        return n

    # ── Interne ───────────────────────────────────────────────────────────

    def _log_event(self, task_id: int, event_type: str,
                   message: str = "") -> None:
        self._conn.execute(
            "INSERT INTO task_events (task_id, event_type, message) "
            "VALUES (?, ?, ?)",
            (task_id, event_type, message)
        )

    def _row_to_task(self, row) -> Task:
        row_dict = dict(row)
        payload = json.loads(row_dict.get("payload") or "{}")
        result  = json.loads(row_dict.get("result") or "null") if row_dict.get("result") else None
        return Task(
            task_id    = row_dict["task_id"],
            task_type  = row_dict["task_type"],
            robot_name = row_dict["robot_name"],
            status     = row_dict["status"],
            priority   = row_dict.get("priority", 5),
            attempt    = row_dict.get("attempt", 0),
            max_attempts = row_dict.get("max_attempts", 5),
            base_delay_s = row_dict.get("base_delay_s", 30),
            payload    = payload,
            result     = result,
            error_msg  = row_dict.get("error_msg"),
            run_at     = row_dict.get("run_at"),
            created_at = row_dict.get("created_at"),
            updated_at = row_dict.get("updated_at"),
        )

    def close(self):
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass


# ── Worker thread ─────────────────────────────────────────────────────────────

class TaskWorker(threading.Thread):
    """
    Thread consommateur de tâches.

    Prend les tâches pending de la file et les exécute via un dispatcher.
    Gère automatiquement les retry et les logs.
    """

    def __init__(
        self,
        queue: TaskQueue,
        dispatcher: Callable[[Task], Dict],
        robot_name: Optional[str] = None,
        poll_interval: float = 5.0,
        name: str = "TaskWorker",
    ):
        super().__init__(name=name, daemon=True)
        self._queue      = queue
        self._dispatcher = dispatcher
        self._robot      = robot_name
        self._poll       = poll_interval
        self._stop_event = threading.Event()
        self._current_task: Optional[Task] = None

    def run(self):
        emit("INFO", "TASK_WORKER_STARTED", robot=self._robot or "all",
             thread=self.name)
        while not self._stop_event.is_set():
            task = self._queue.dequeue(robot_name=self._robot)
            if not task:
                self._stop_event.wait(timeout=self._poll)
                continue

            self._current_task = task
            emit("INFO", "TASK_PROCESSING",
                 task_id=task.task_id, task_type=task.task_type,
                 robot=task.robot_name, attempt=task.attempt + 1)

            try:
                result = self._dispatcher(task)
                self._queue.mark_success(task.task_id, result=result)
            except Exception as e:
                err = str(e)
                emit("ERROR", "TASK_EXECUTION_FAILED",
                     task_id=task.task_id, error=err)
                retry = not task.is_exhausted
                self._queue.mark_failed(task.task_id, error_msg=err, retry=retry)
            finally:
                self._current_task = None

        emit("INFO", "TASK_WORKER_STOPPED", robot=self._robot or "all")

    def stop(self, timeout: float = 10.0):
        self._stop_event.set()
        self.join(timeout=timeout)

    @property
    def current_task(self) -> Optional[Task]:
        return self._current_task


# ── Singleton ─────────────────────────────────────────────────────────────────

_task_queue: Optional[TaskQueue] = None
_tq_lock = threading.Lock()


def get_task_queue() -> TaskQueue:
    global _task_queue
    if _task_queue is None:
        with _tq_lock:
            if _task_queue is None:
                _task_queue = TaskQueue()
    return _task_queue
