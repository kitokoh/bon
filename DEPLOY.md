# BON v12 — Guide de déploiement & test rapide

> Temps estimé : **5–10 min** (hors téléchargement Playwright).

---

## Prérequis

| Outil | Version minimale |
|-------|-----------------|
| Python | 3.10+ |
| pip | 23+ |
| OS | Windows 10/11, macOS 12+, Ubuntu 22.04+ |

---

## 1. Installation

```bash
# Cloner / décompresser le projet puis entrer dans le dossier
cd bon-main

# Installation automatique (venv isolé + dépendances + Playwright Chromium)
python install.py
```

Puis activer le venv créé :

```bash
# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

Installation manuelle (alternative) :

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## 2. Configuration minimale

Aucun fichier de config à créer. Tout est en SQLite (auto-initialisé au premier lancement).

**Variables d'environnement optionnelles** (`.env` ou shell) :

```bash
# API REST (obligatoire si vous démarrez l'API)
export BON_API_TOKEN=mon-token-secret

# Résolution CAPTCHA automatique via 2captcha
export BON_2CAPTCHA_KEY=votre-clé-2captcha
export BON_AUTO_SOLVE_CAPTCHA=1

# CDN sélecteurs (pour mise à jour automatique des sélecteurs Facebook)
export BON_USE_CDN=1
export BON_SELECTORS_CDN_URL=https://votre-cdn.com/selectors.json

# URL de test proxy (défaut : https://www.google.com/generate_204)
export BON_PROXY_TEST_URL=https://httpbin.org/ip
```

---

## 3. Créer votre premier robot

```bash
# Ouvre un navigateur Chromium → connectez-vous à Facebook → appuyez Entrée
python -m bon robot create --robot robot1

# Avec un proxy
python -m bon robot create --robot robot1 \
  --proxy-server http://host:8080 \
  --proxy-user user --proxy-pass pass
```

> Le robot est enregistré en base SQLite avec sa session Playwright.

---

## 4. Préparer les données (campagnes & groupes)

Les fichiers JSON de démarrage sont déjà présents :

```
data/campaigns/campaigns.json   → campagnes et variantes de texte
data/groups/groups.json         → groupes Facebook cibles
```

Importez-les en base (fait automatiquement au démarrage, ou manuellement) :

```bash
python -m bon migrate --data
```

Assignez des groupes et une campagne au robot :

```bash
# Depuis la DB SQLite (logs/bon.db) ou via l'API
# Exemple rapide via Python
python3 -c "
from libs.database import get_database
db = get_database()
# Assigner tous les groupes au robot1
for g in db.get_all_groups():
    db.assign_group_to_robot('robot1', g['url'])
# Assigner la première campagne
camps = db.get_all_campaigns()
if camps:
    db.assign_campaign_to_robot('robot1', camps[0]['name'])
print('Assignations faites.')
"
```

---

## 5. Publier

```bash
# Mode headless (production)
python -m bon post --robot robot1 --headless

# Mode visible (debug)
python -m bon post --robot robot1
```

---

## 6. Commandes utiles

```bash
# Dashboard (état global)
python -m bon dashboard

# Lister les robots
python -m bon robot list

# Vérifier la session d'un robot (Facebook)
python -m bon robot verify --robot robot1

# Voir la config d'un robot
python -m bon robot config show --robot robot1

# Mettre à jour le pool User-Agents
python -m bon update-ua

# Exporter les publications
python -m bon export --out publications.csv
python -m bon export --out publications.xlsx

# Sauvegarder des groupes par mot-clé (scrape Facebook)
python -m bon save-groups --robot robot1 --keyword "immobilier france" --headless
```

---

## 7. API REST

```bash
# Démarrer l'API (BON_API_TOKEN requis)
BON_API_TOKEN=secret python -m bon api --host 127.0.0.1 --port 8765

# Tester
curl http://localhost:8765/health
curl -H "Authorization: Bearer secret" http://localhost:8765/api/v1/robots
curl -H "Authorization: Bearer secret" http://localhost:8765/api/v1/dashboard
curl -H "Authorization: Bearer secret" http://localhost:8765/api/v1/publications

# Déclencher un run via API
curl -X POST -H "Authorization: Bearer secret" \
  -H "Content-Type: application/json" \
  -d '{"command":"post","headless":true}' \
  http://localhost:8765/api/v1/robots/robot1/run
```

---

## 8. Planification cron

```bash
# Ajouter un job (tous les jours à 8h)
python -m bon schedule add --robot robot1 --cron "0 8 * * *"

# Voir les jobs
python -m bon schedule list

# Lancer le daemon planificateur
python -m bon schedule daemon
```

---

## 9. Lancer les tests

```bash
# Tests unitaires (sans Playwright ni connexion Facebook)
python -m pytest tests/ -v

# Tests rapides seulement
python -m pytest tests/test_smoke.py -v

# Tests base de données v10/v11
python -m pytest tests/test_v10.py tests/test_v11.py -v
```

---

## 10. Structure des fichiers de données

```
~/.config/bon/          (Linux)   — répertoire de données
~/Library/Application Support/bon/  (macOS)
%APPDATA%\bon\          (Windows)

├── logs/
│   ├── bon.db              → base SQLite (toutes les données)
│   └── activity.jsonl      → logs structurés JSON Lines
├── sessions/
│   └── robot1_state.json   → session Playwright chiffrée
├── media/
│   └── ...                 → médias assignés aux robots
└── config/
    └── selectors.json      → sélecteurs Facebook (mis à jour via CDN)
```

---

## Corrections apportées (v11-fixed)

| # | Fichier | Correction |
|---|---------|-----------|
| 1 | `libs/database.py` | Ajout `list_sessions()` (alias de `list_robot_names()`) — élimine l'`AttributeError` au runtime |
| 2 | `install.py` | Commandes post-install corrigées (`robot create` / `robot list`) — les anciennes (`login`, `list-sessions`) n'existaient pas |
| 3 | `libs/rest_api.py` | Subprocess corrigé : `python -m bon` au lieu de `python __main__.py` (le fichier n'est pas autonome) |
| 4 | `libs/bon_scheduler.py` | Même correction subprocess que rest_api |
| 5 | `tests/test_smoke.py` | `TestDefaultSessionConfig` migré vers `DEFAULT_ROBOT_CONFIG` (v11) — plus d'import du legacy `session_manager` |
| 6 | `libs/config_manager.py` | `list_sessions()` : fallback robuste avec `sorted()` correct |
| 7 | `libs/session_manager.py` | Réécriture complète : délègue à `RobotManager` — élimine les appels à `db.get_session()`, `db.upsert_session()`, `db.get_media_assets()` qui n'existent pas dans `BONDatabase` v11 |


---

## Nouveautés v12 (CLI étendue)

### `robot config set` — tous les paramètres configurables

```bash
# Proxy
python -m bon robot config set --robot robot1 --proxy http://host:8080

# Limites de publication
python -m bon robot config set --robot robot1 --max-groups-per-run 15
python -m bon robot config set --robot robot1 --max-runs-per-day 3
python -m bon robot config set --robot robot1 --delay-min 45 --delay-max 90
python -m bon robot config set --robot robot1 --cooldown 3600

# Localisation (fingerprinting anti-détection)
python -m bon robot config set --robot robot1 --locale fr-FR
python -m bon robot config set --robot robot1 --timezone Europe/Paris

# Notifications Telegram
python -m bon robot config set --robot robot1 --telegram-token TOK --telegram-chat-id 123456

# CAPTCHA automatique par robot (optionnel)
python -m bon robot config set --robot robot1 --captcha-key VOTRE_CLE_2CAPTCHA
python -m bon robot config set --robot robot1 --clear-captcha-key

# Voir la config actuelle
python -m bon robot config show --robot robot1
```

### Filtres date sur les exports et l'API

```bash
python -m bon export --out publications.csv --date-from 2026-01-01 --date-to 2026-03-31
python -m bon export --out q1.xlsx --date-from 2026-01-01 --date-to 2026-03-31
curl -H "Authorization: Bearer secret" \
  "http://localhost:8765/api/v1/publications?date_from=2026-01-01&date_to=2026-03-31"
```

### Installation v12 (deux niveaux)

```bash
# Usage minimal (publication seulement, 4 paquets)
pip install -r requirements-core.txt && playwright install chromium

# Usage complet (API, scheduler, Excel, tests)
python install.py --full
```

### CAPTCHA — comportement par défaut

BON ne résout **jamais** les CAPTCHAs automatiquement sans configuration explicite.

| Scénario | Comportement |
|----------|-------------|
| Pas de clé, pas de `BON_AUTO_SOLVE_CAPTCHA` | Log WARN → continue (non bloquant) |
| `BON_AUTO_SOLVE_CAPTCHA=1` sans clé | Log 'skipped — aucune clé' → continue |
| Clé robot en DB + `BON_AUTO_SOLVE_CAPTCHA=1` | Résolution auto avec la clé du robot |
| `BON_2CAPTCHA_KEY` global + `BON_AUTO_SOLVE_CAPTCHA=1` | Résolution auto avec la clé globale |
| Service 2captcha down | Timeout → log WARN → continue sans bloquer |

