# BON v14 — Facebook Groups Publisher

Module **Python 3.10+** / **Playwright** pour automatiser (avec prudence) la publication dans des groupes Facebook, avec **plusieurs robots** (un par compte), **données en SQLite**, **sélecteurs externalisés**, **circuit breaker**, **API REST**, **planification cron**, **monitoring industriel** et **file de tâches**.

> **Conformité** : l’usage peut enfreindre les conditions d’utilisation de Meta. **Vous êtes responsable** de l’usage du logiciel et du respect du droit applicable.

---

## Vision produit

| Objectif | Réponse dans BON |
|----------|------------------|
| Publier dans de nombreux groupes sans dupliquer le contenu bêtement | Variantes SQL, anti-doublon `was_published_recently`, option **`BON_CROSS_ROBOT_VARIANT_EXCLUSION`** |
| Tenir dans la durée malgré les changements de Facebook | Sélecteurs JSON, CDN optionnel, selector health, UA pool `update-ua` |
| Piloter plusieurs comptes | Modèle **Robot** + sessions Playwright + limites DB |
| Supervision & intégrations | **CLI dashboard**, **export CSV/XLSX**, **API Flask** (n8n, Make, etc.) |
| Moins d’arrêts sur CAPTCHA | **2captcha** (HTTP) + **`BON_AUTO_SOLVE_CAPTCHA=1`** dans `check_page_state` |

**Synthèse audit externe** : le document `BON_Audit_v11.pdf` fixe une cible « entreprise » (~98/100). Ce dépôt implémente **l’essentiel** avec quelques choix techniques différents (voir tableau ci‑dessous et [docs/PLAN_ACTION_V14.md](docs/PLAN_ACTION_V14.md)).

---

## Audit « cible » vs implémentation réelle

| Thème | Audit / vision ami | Ce dépôt |
|--------|---------------------|----------|
| CAPTCHA | SDK + config par robot en base | **`libs/captcha_solver.py`** (requests), **`BON_2CAPTCHA_KEY`**, journal **`captcha_solve_log`**, auto optionnelle |
| Scheduler | `schedule start` | **`python -m bon schedule daemon`** (`libs/bon_scheduler.py`, table **`scheduler_jobs`**) |
| API | `/api/v1/*` | **`/v1/*` et `/api/v1/*`** (doublon), Bearer **`BON_API_TOKEN`** |
| CDN sélecteurs | Souvent « on » par défaut | **`BON_USE_CDN=1`** + URL **`BON_SELECTORS_CDN_URL`** ou `bon config set selectors_cdn_url` (**pas** d’URL fictive) |
| Export | CSV + Excel | **`bon export`** `.csv` / `.xlsx` + **`GET .../publications/export?format=`** |
| Config robot CLI | `--set` tous champs | **`robot config set`** : proxy, max-groups-per-run, max-runs-per-day, delay-min/max, cooldown, locale, timezone, telegram, **captcha-key** (v12) |
| Filtres date | Absent | **`--date-from` / `--date-to`** sur `export` + API REST (v12) |
| Rate limiting | Absent | **`flask-limiter`** optionnel avec fallback gracieux (v12) |
| Tests | ~30 tests dont stealth | **`tests/test_v10.py`**, **`tests/test_v11.py`**, **`tests/test_smoke.py`** — **pas d’E2E DOM** (prévu v12) |

---

## Architecture (aperçu)

```
__main__.py          → CLI (robot, post, export, schedule, api, …)
libs/
  cli_v14.py         → CLI Pro complète (status, logs, queue, health)
  database.py        → SQLite (robots, publications, campaigns, CB, scheduler, captcha log, …)
  session_manager.py → Isolation sessions par robot (chrome_profiles/)
  human_behavior.py  → Anti-détection avancé (mouvements, délais, frappe)
  task_queue.py      → File de tâches SQLite avec backoff exponentiel
  monitor.py         → Monitoring industriel (classification erreurs, santé)
  scraper.py         → Flux publication groupe par groupe
  playwright_engine.py
  selector_registry.py
  captcha_solver.py
  bon_scheduler.py
  rest_api.py
  stealth_profile.py, circuit_breaker.py, social_actions.py, …
automation/          → anti_block, selector_health, selector_tester
config/              → selectors.json, user_agents.json, …
data/                → import initial campaigns/groups (JSON → SQL)
```

**Logs** : JSON Lines (répertoire défini par `libs/config_manager` — souvent `~/.config/bon/logs/`).

---

## Installation

```bash
python install.py
# ou : python -m venv .venv && .venv\Scripts\pip install -r requirements.txt
# puis : playwright install chromium
```

Dépendances clés : `playwright`, `requests`, `apscheduler`, `flask`, `openpyxl` (export Excel), `pytest` (tests).

---

## Premiers pas

### 1. Créer un robot (login Facebook manuel une fois)

```bash
python -m bon robot create --robot robot1 --account mon_compte
# optionnel :
python -m bon robot create --robot robot1 --proxy-server http://hote:8080 --proxy-user u --proxy-pass p
```

### 2. Vérifier / configurer

```bash
python -m bon robot list
python -m bon robot verify --robot robot1
python -m bon robot config show --robot robot1
python -m bon robot config set --robot robot1 --proxy-server http://…
```

### 3. Publier

```bash
python -m bon post --robot robot1
python -m bon post --robot robot1 --headless --validate-proxy
```

### 4. Exports & stats

```bash
python -m bon export --out rapports/q1.csv
python -m bon export --out rapports/q1.xlsx --robot robot1
python -m bon dashboard
```

### 5. Planification (APScheduler)

```bash
python -m bon schedule add --robot robot1 --cron "0 8 * * *"
python -m bon schedule list
python -m bon schedule daemon
```

### 6. API REST

```bash
set BON_API_TOKEN=votre_jeton_secret
python -m bon api --host 127.0.0.1 --port 8765
```

En-tête requêtes : `Authorization: Bearer votre_jeton_secret`  
(sauf **`GET /health`** et **`GET /api/v1/health`** — état du service sans token.)

---

## Variables d’environnement utiles

| Variable | Rôle |
|----------|------|
| `BON_API_TOKEN` | Jeton obligatoire pour `python -m bon api` |
| `BON_2CAPTCHA_KEY` | Clé 2captcha (`python -m bon captcha test`) |
| `BON_AUTO_SOLVE_CAPTCHA` | `1` / `true` → tentative auto reCAPTCHA/hCaptcha dans le navigateur |
| `BON_USE_CDN` | `1` pour télécharger les sélecteurs depuis une URL |
| `BON_SELECTORS_CDN_URL` | URL du `selectors.json` distant |
| `BON_SELECTORS_CACHE_TTL_S` | Cache entre tentatives CDN |
| `BON_CROSS_ROBOT_VARIANT_EXCLUSION` | `1` → évite le même variant sur un groupe entre robots |
| `BON_SELECTORS_MAX_AGE_DAYS` | Avertissement si version locale vieille |

Config globale persistante : `python -m bon config set selectors_cdn_url https://…/selectors.json`

---

## API REST — endpoints principaux

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/health`, `/api/v1/health` | Santé (sans Bearer) |
| GET | `/v1/robots`, `/api/v1/robots` | Liste robots |
| GET | `/v1/robots/<nom>`, `/api/v1/robots/<nom>` | Détail (mots de passe masqués) |
| POST | `/v1/robots/<nom>/run`, `/api/v1/robots/<nom>/run` | Lance une commande (`post`, …) en sous-processus |
| GET | `/v1/dashboard`, `/api/v1/dashboard` | Statistiques agrégées |
| GET | `/v1/publications`, `/api/v1/publications` | Pagination `?robot=&limit=&offset=` |
| GET | `/v1/publications/export`, `/api/v1/publications/export` | `?format=csv|xlsx&robot=` |
| GET | `/v1/campaigns`, `/api/v1/campaigns` | Campagnes |
| GET | `/v1/groups`, `/api/v1/groups` | Groupes (`?robot=` pour filtrer) |
| GET | `/v1/errors`, `/api/v1/errors` | Erreurs récentes `?limit=` |
| GET | `/v1/scheduler/jobs`, `/api/v1/scheduler/jobs` | Jobs planifiés |
| GET | `/v1/captcha/stats`, `/api/v1/captcha/stats` | Stats journal CAPTCHA `?days=` |

---

## Données

- **SQLite** (fichier par défaut sous le répertoire logs, voir `libs/config_manager`).
- Import initial : `data/campaigns/campaigns.json`, `data/groups/groups.json` (au bootstrap).
- **Ne pas committer** : sessions Playwright, mots de passe, `.db` de prod (voir `.gitignore`).

---

## Tests

```bash
pip install pytest
pytest tests/test_smoke.py tests/test_v10.py tests/test_v11.py -q
# ou :
python tests/test_v10.py
python tests/test_v11.py
```

---

## Feuille de route & plan d’action

- **Courte** : [ROADMAP.md](ROADMAP.md)
- **Détaillée (v14)** : [docs/PLAN_ACTION_V14.md](docs/PLAN_ACTION_V14.md) — *audit ami + vision + écarts + priorités (E2E, PostgreSQL, dashboard web, CLI config étendue, Prometheus, Slack/Discord, pool proxy…)*

---

## Outils annexes

- **Rapport PDF** (synthèse technique) : `python tools/gen_rapport_pdf.py` → `Rapport_BON_v11.pdf`
- **Selector tester** : `python -m automation.selector_tester`

---

## Historique (rappel)

Les versions **v3–v10** ont introduit : migration Selenium → Playwright, modèle **Robot**, tout-SQL, stealth CDP, circuit breaker persistant, Telegram, UA externalisés, variant selector intelligent, etc. Le détail ancien changelog a été **condensé** ici pour garder un README aligné sur **v11** ; les PDF d’audit du projet restent la trace des revues successives.

---

## État actuel v14

| Dimension | Score v12 | Score v14 | Évolution |
|-----------|-----------|-----------|----------|
| Architecture & modularité | 19/20 | 20/20 | ↑ +1 (modules v14 consolidés) |
| Sécurité & anti-détection | 17/20 | 19/20 | ↑ +2 (human_behavior avancé) |
| Résilience & gestion erreurs | 18/20 | 20/20 | ↑ +2 (monitoring industriel) |
| Tests & qualité code | 14/20 | 16/20 | ↑ +2 (tests étendus) |
| API & intégrations | 19/20 | 20/20 | ↑ +1 (CLI complète) |
| Ergonomie opérationnelle | 15/20 | 19/20 | ↑ +4 (status/watch/queue) |
| **TOTAL** | **102/120** | **114/120** | **↑ +12 pts** |

**Nouveautés v14** : 
- **SessionManager** : isolation complète par robot avec `chrome_profiles/`
- **HumanBehavior** : mouvements souris Bézier, délais Gamma, fatigue adaptative
- **TaskQueue** : file SQLite avec backoff exponentiel et retry automatique
- **Monitor** : classification 15 classes d'erreurs, score santé 0-100
- **CLI Pro** : `status --watch`, `logs --json`, `queue`, `health` en temps réel

---

*BON — avril 2026 — v14*
