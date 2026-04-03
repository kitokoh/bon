# BON v14 — Changelog & Guide

## Nouveaux modules (Phases 2–6)

---

## PHASE 2 — Isolation sessions (`libs/session_manager.py`)

### Problème résolu
Contamination entre comptes : cookies, localStorage, fingerprint partagés.

### Architecture
```
SessionManager
  └── IsolatedSession (1 par robot)
        ├── profile_dir  →  chrome_profiles/<robot_name>/   (UNIQUE)
        ├── proxy_config →  {server, username, password}    (DÉDIÉ)
        └── state FSM    →  idle → starting → running → stopping → stopped
```

### Usage
```python
from libs.session_manager import get_session_manager

sm = get_session_manager()

# Créer + démarrer
session = sm.create_session("robot1", from_db=True)
sm.start_session("robot1")

# Arrêter / redémarrer
sm.stop_session("robot1")
sm.restart_session("robot1")

# Inspecter
print(sm.list_sessions())      # [{state, proxy, uptime_s, ...}]
print(sm.list_active_sessions())
print(sm.active_count())

# Intégration Playwright
launch_args = sm.build_playwright_launch_args(session)
# → {"user_data_dir": "chrome_profiles/robot1", "proxy": {...}, "args": [...]}
```

### CLI
```bash
python -m bon start --robots robot1 robot2
python -m bon stop  --robots robot1
python -m bon stop  --clean-profile      # ⚠ supprime les cookies
```

---

## PHASE 3 — Anti-détection avancé (`libs/human_behavior.py`)

### Distributions temporelles
| Fonction              | Distribution       | Usage                          |
|-----------------------|--------------------|--------------------------------|
| `think_delay()`       | Gamma(k, θ)        | Pause réflexion avant action   |
| `micro_delay()`       | Gamma(μ=40ms)      | Latence intra-action           |
| `page_read_delay()`   | Gamma ∝ contenu    | Lecture de page simulée        |
| `between_actions_delay()` | Gamma + fatigue | Entre deux posts/commentaires |
| `_human_typing_delay()` | Bimodale         | Entre chaque touche clavier    |

**Facteur fatigue** : `multiplier = 1 + 0.08 · log(1 + actions/10)`
Après 50 actions → +28% de lenteur. Après 200 → +43%.

### Mouvements souris
```python
# Trajectoire Bézier cubique avec points de contrôle aléatoires
simulate_mouse_move(page, start=(100, 200), end=(500, 350))

# Clic sur position randomisée (distribution Bêta centrée)
click_x, click_y = randomize_click_position(element.bounding_box())

# Clic complet : scroll → déplacement → micro-pause → clic aléatoire
human_click(page, "div[role='button']:has-text('Publier')", actions_done=12)
```

### Scroll
```python
# Scroll en N petits mouvements molette non-uniformes
human_scroll(page, direction="down", distance_px=400)

# Scroll naturel avant action (1-3 scrolls aléatoires)
scroll_before_action(page, target_selector="[data-testid='post-input']")
```

### Frappe clavier
```python
# Frappe humaine avec délais Gamma + 3% fautes corrigées
human_type(page, "div[contenteditable]", "Bonjour le groupe !")
```

---

## PHASE 4 — Task Queue SQLite (`libs/task_queue.py`)

### Schéma
```sql
tasks (
  task_id, task_type, robot_name, status,
  priority,        -- 1 (urgent) → 10 (faible)
  attempt,         -- compteur de tentatives
  max_attempts,    -- max avant abandon (dead)
  base_delay_s,    -- délai de base backoff (défaut: 30s)
  payload JSON,    -- données spécifiques à la tâche
  run_at,          -- timestamp planifié (retry)
  error_msg
)
```

### Backoff exponentiel
```
t = base * 2^n

attempt 0 → échec → retry dans 30s
attempt 1 → échec → retry dans 60s
attempt 2 → échec → retry dans 120s
attempt 3 → échec → retry dans 240s
attempt 4 → échec → retry dans 480s
attempt 5 → DEAD  → abandon définitif
```

### Usage
```python
from libs.task_queue import get_task_queue

tq = get_task_queue()

# Enqueue
tid = tq.enqueue_post("robot1", "campagne_ete", group_urls=["https://fb.com/g/..."])
tid = tq.enqueue_comment("robot1", post_urls=["..."], max_comments=3)
tid = tq.enqueue_join_group("robot1", "https://fb.com/groups/xyz")

# Consommation (dans un worker)
task = tq.dequeue(robot_name="robot1")   # atomique → marque running
tq.mark_success(task.task_id, result={"posted": True})
tq.mark_failed(task.task_id, error_msg="Timeout", retry=True)

# Stats
print(tq.get_stats("robot1"))
# → {"total": 45, "pending": 12, "success": 30, "failed": 2, "dead": 1}
```

### Récupération crash
Au démarrage, les tâches `status=running` sont automatiquement remises en `pending`.
Aucune perte de tâche même en cas de kill -9.

### CLI
```bash
python -m bon enqueue --type post --robot robot1 --campaign camp1
python -m bon enqueue --type comment --robot robot1 --urls "url1,url2"
python -m bon enqueue --type join_group --robot robot1 --group-url "https://..."
python -m bon queue
python -m bon queue --robot robot1 --status pending
```

---

## PHASE 5 — Monitoring industriel (`libs/monitor.py`)

### Classification d'erreurs (15 classes)
| Classe             | Exemples de patterns          | Retryable | Fatal |
|--------------------|-------------------------------|-----------|-------|
| `account_blocked`  | "blocked", "suspended"        | ✗         | ✓     |
| `checkpoint`       | "checkpoint", "verify"        | ✗         | ✓     |
| `rate_limited`     | "too many", "rate limit"      | ✓         | ✗     |
| `captcha`          | "captcha", "recaptcha"        | ✓         | ✗     |
| `session_expired`  | "session", "login"            | ✓         | ✗     |
| `proxy_error`      | "proxy", "502", "503"         | ✓         | ✗     |
| `network_timeout`  | "timeout", "timed out"        | ✓         | ✗     |
| `selector_miss`    | "no element", "not found"     | ✓         | ✗     |
| `group_banned`     | "banned from group"           | ✗         | ✓     |
| `dom_changed`      | "selector changed"            | ✓         | ✗     |

### Score de santé (0-100)
| Facteur                     | Pénalité         |
|-----------------------------|------------------|
| Taux succès < 50%           | -25 pts          |
| Taux succès < 70%           | -15 pts          |
| Chaque échec consécutif     | -10 pts (max -40)|
| Compte bloqué               | -30 pts          |
| Erreur fatale               | -40 pts          |
| Rate limited (>2x)          | -15 pts          |
| Captcha non résolu (>1x)    | -20 pts          |
| Inactivité > 48h            | -10 pts          |

Statuts : `healthy` (≥80) · `degraded` (≥60) · `critical` (≥30) · `dead` (<30)

### Logs JSON structurés (`logs/bon_monitor.jsonl`)
```json
{"event":"SUCCESS","robot":"robot1","account":"compte1","action_type":"post","group_url":"https://...","ts":"2026-04-03T14:23:11"}
{"event":"FAILURE","robot":"robot1","error_class":"rate_limited","error_msg":"Too many requests","is_fatal":false,"ts":"2026-04-03T14:25:03"}
{"event":"SNAPSHOT","active_accounts":3,"total_aph":12.5,"avg_success_rate":0.87,"ts":"2026-04-03T14:30:00"}
```

### Usage
```python
from libs.monitor import get_monitor

mon = get_monitor()

mon.record_success("robot1", "compte1", action_type="post", group_url="...")
err_class = mon.record_failure("robot1", "compte1", "Too many requests")
# → ErrorClass.RATE_LIMITED

snap = mon.get_snapshot()
health = mon.get_account_health("robot1")
# → HealthScore(score=72, status="degraded", factors={"rate_limited": -15})

mon.print_dashboard()
logs = mon.get_recent_logs(n=50)
```

---

## PHASE 6 — CLI Pro (`libs/cli_v14.py`)

### Toutes les commandes
```bash
# Gestion comptes et proxies
python -m bon add-account --name robot1 --email compte@fb.com
python -m bon assign-proxy --robot robot1 --proxy-server http://1.2.3.4:8080 \
                           --proxy-user user --proxy-pass pass

# Sessions
python -m bon start                         # démarrer tous les robots actifs
python -m bon start --robots robot1 robot2  # robots spécifiques
python -m bon stop                          # arrêter tout
python -m bon stop --robots robot1 --clean-profile  # ⚠ efface les cookies

# Monitoring temps-réel
python -m bon status                # snapshot instantané
python -m bon status --watch        # rafraîchissement auto (5s)
python -m bon status --watch --interval 10

# Logs
python -m bon logs                          # 30 dernières entrées
python -m bon logs --lines 100 --robot robot1
python -m bon logs --event FAILURE
python -m bon logs --json | jq '.error_class'  # pipeline JSONL

# File de tâches
python -m bon queue
python -m bon queue --robot robot1 --status failed
python -m bon enqueue --type post --robot robot1 --campaign campagne_printemps
python -m bon enqueue --type join_group --robot robot1 \
                      --group-url https://www.facebook.com/groups/12345

# Santé
python -m bon health
python -m bon health --robot robot1
```

### Exemple `status --watch`
```
════════════════════════════════════════════════════════════
  BON v14 — Status
════════════════════════════════════════════════════════════
  Heure           : 14:35:22
  Sessions totales: 3
  Sessions actives: 3
  Actions/heure   : 18.5
  Succès moyen    : 91.2%
  File (pending)  : 7
  File (failed)   : 1

  ┌─────────────────────────────────────────────────┐
  │ Robot               État       Proxy       Uptime│
  ├─────────────────────────────────────────────────┤
  │ robot1              ▶ running  45.12.8.9    847s│
  │   ❤  92  ✓  45 ✗  4  18aph  92% ok             │
  │ robot2              ▶ running  91.0.2.10    612s│
  │   ❤  78  ✓  31 ✗  8  12aph  80% ok             │
  └─────────────────────────────────────────────────┘

  Erreurs (classifiées) :
    rate_limited              8  [retry]
    selector_miss             3  [retry]
    captcha                   1  [retry]
```

---

## Intégration entre modules

```
__main__.py
    │
    ├── SessionManager (Phase 2)
    │     └── IsolatedSession → chrome_profiles/<robot>/
    │
    ├── HumanBehavior (Phase 3)
    │     └── human_click / human_type / human_scroll (utilisés dans Scraper)
    │
    ├── TaskQueue (Phase 4)
    │     └── SQLite task_queue.db  ←→  TaskWorker threads
    │
    ├── Monitor (Phase 5)
    │     └── record_success / record_failure → bon_monitor.jsonl
    │         └── HealthScorer + ErrorClassifier
    │
    └── CLI v14 (Phase 6)
          └── commandes → appelle les 4 modules ci-dessus
```

## Recommandations opérationnelles

| Paramètre                | Valeur recommandée  | Risque si trop agressif |
|--------------------------|---------------------|-------------------------|
| `max_groups_per_run`     | 8–12                | Ban groupes             |
| `delay_min_s`            | 90                  | Rate limit              |
| `delay_max_s`            | 180                 | —                       |
| `max_runs_per_day`       | 2                   | Détection pattern       |
| Sessions parallèles      | ≤ 5 par machine     | Saturation RAM/CPU      |
| Proxy rotation           | 1 IP par robot      | Corrélation IP          |
| `base_delay_s` (queue)   | 30                  | Retry trop rapide       |
