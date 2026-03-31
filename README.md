# BON — Facebook Groups Publisher

Module autonome de publication automatisée dans des groupes Facebook.  
**Version 4.0** — Distribution Ready — Migration Playwright · Stabilité Sélecteurs · Cross-OS · Logs PyQt

## Changelog v4.0 — Distribution Ready

- **Fix C-08** : `check_license.py` réécrit — MAC lue dynamiquement (plus de valeur hardcodée), `get_serial_number()` utilise PowerShell en priorité (compatible Windows 11 22H2+), fallback UUID universel macOS/Linux.
- **Fix C-06** : `SELECTORS_CDN_URL` configurable via variable d'environnement `BON_SELECTORS_CDN_URL`. Alerte automatique si les sélecteurs dépassent `BON_SELECTORS_MAX_AGE_DAYS` (défaut : 30 jours).
- **Fix C-09** : `examples/pyqt_integration.py` ajouté — exemple complet de lancement subprocess, lecture logs JSONL temps réel, arrêt propre SIGTERM.
- **Fix C-07** : `tests/test_smoke.py` ajouté — 41 tests unitaires (resolve_media_path, DEFAULT_SESSION_CONFIG, timing limits, data files, license parsing). Sans Playwright ni réseau.
- **Fix C-02** : Avertissement automatique si `storage_state` manquant au démarrage (session expirée) avec hint de commande.
- **Fix C-06b** : Check Playwright au démarrage dans `__main__.py` — message d'erreur clair + redirection vers `install.py`.

## Changelog v3.1

- **Fix critique** : `resolve_media_path()` gère maintenant correctement les chemins Windows legacy (antislash) sur Linux et macOS — les images des utilisateurs Windows ne sont plus perdues silencieusement sur les autres OS.
- **Fix** : `DEFAULT_SESSION_CONFIG` complété avec les champs manquants (`add_comments`, `comments`, `marketplace`, `cooldown_between_runs_s`).
- **Fix** : `run_login()` délègue désormais à `SessionManager.create_session()` — suppression du code dupliqué.
- **Sécurité** : `data.json` et `data1.json` remplacés par des exemples neutres — suppression des chemins personnels Windows exposés.
- **Ajout** : `check_license.py` réintégré (absent de v3).

---

---

## Architecture

Le module tourne **en autonome** dans son propre venv.  
L'app PyQt ne l'intègre pas directement — elle le **configure, le planifie, et lit ses logs**.

```
PyQt App
  └─ subprocess.run("python -m bon post --session compte1")
  └─ tail(LOGS_DIR/activity.jsonl)   ← logs JSON Lines temps réel
  └─ os.kill(pid, SIGTERM)           ← arrêt propre après groupe en cours
```

---

## Installation

```bash
python install.py
```

Crée un venv `.venv/`, installe les dépendances, et télécharge Chromium via Playwright (~300MB).

---

## Utilisation

### 1. Créer une session (login manuel une fois)

```bash
python -m bon login --session compte1
```

Une fenêtre Chrome s'ouvre. Connectez-vous à Facebook manuellement, puis appuyez sur Entrée.  
La session est sauvegardée dans `~/.config/bon/sessions/compte1_state.json`.

### 2. Configurer les posts et groupes

Éditez `~/.config/bon/sessions/compte1.json` :

```json
{
    "session_name": "compte1",
    "storage_state": "~/.config/bon/sessions/compte1_state.json",
    "max_groups_per_run": 10,
    "delay_between_groups": [60, 120],
    "max_runs_per_day": 2,
    "posts": [
        {
            "text": "Votre texte de publication",
            "image": "mon_image.jpg",
            "weight": 1
        }
    ],
    "groups": [
        "https://www.facebook.com/groups/123456789/"
    ]
}
```

Placez vos images dans : `~/.config/bon/media/compte1/`

### 3. Publier

```bash
python -m bon post --session compte1
# ou en mode invisible :
python -m bon post --session compte1 --headless
```

### 4. Rechercher des groupes

```bash
python -m bon save-groups --session compte1 --keyword "machines hydrauliques"
```

### 5. Lister les sessions

```bash
python -m bon list-sessions
```

---

## Migration depuis l'ancienne version

Si vous avez un ancien `data.json`, utilisez l'outil de migration :

```bash
python migrate_data.py --data data.json --session mon_compte
python migrate_data.py --data data1.json --session mon_compte
```

---

## Structure du projet

```
bon/
├── __main__.py              # Point d'entrée CLI
├── install.py               # Script d'installation venv + Playwright
├── migrate_data.py          # Migration depuis l'ancien format
├── requirements.txt         # Dépendances avec versions fixées
│
├── libs/
│   ├── playwright_engine.py # Moteur Playwright (remplace Selenium)
│   ├── scraper.py           # Logique métier (publication, sauvegarde groupes)
│   ├── session_manager.py   # Gestion des sessions par compte
│   ├── selector_registry.py # Sélecteurs multi-fallback + CDN
│   ├── config_manager.py    # Chemins cross-platform
│   ├── config_validator.py  # Validation config au démarrage
│   ├── timing_humanizer.py  # Délais humains, limites de fréquence
│   ├── log_emitter.py       # Logs JSON Lines lisibles par PyQt
│   └── error_handlers.py    # Retry, détection états bloquants
│
├── config/
│   └── selectors.json       # Sélecteurs multi-fallback versionnés
│
└── conception/
    ├── analyse_bon_module.pdf
    ├── plan_action_bon_v2.pdf
    └── robustness_ideas.md
```

---

## Logs — Interface PyQt

Les logs sont écrits en JSON Lines dans `~/.config/bon/logs/activity.jsonl`.

Format de chaque ligne :
```json
{"ts": "2026-03-31T14:32:11", "level": "INFO", "event": "SESSION_START", "compte": "compte1"}
{"ts": "2026-03-31T14:32:22", "level": "SUCCESS", "event": "POST_PUBLISHED", "compte": "compte1", "groupe": "https://..."}
{"ts": "2026-03-31T14:33:01", "level": "ERROR", "event": "SESSION_EXPIRED", "compte": "compte1"}
```

Niveaux : `DEBUG` · `INFO` · `SUCCESS` · `WARN` · `ERROR`

### Lecture temps réel depuis PyQt

```python
class LogWatcher(QThread):
    new_line = pyqtSignal(dict)

    def run(self):
        log_path = pathlib.Path.home() / ".config/bon/logs/activity.jsonl"
        with open(log_path, "r") as f:
            f.seek(0, 2)  # aller à la fin
            while self.running:
                line = f.readline()
                if line.strip():
                    self.new_line.emit(json.loads(line))
                else:
                    time.sleep(0.3)
```

### Savoir si le module tourne

```python
import os, pathlib, signal

pid_file = pathlib.Path.home() / ".config/bon/logs/running.pid"
if pid_file.exists():
    pid = int(pid_file.read_text())
    # Arrêt propre :
    os.kill(pid, signal.SIGTERM)  # Linux/Mac
```

---

## Sélecteurs — Mise à jour

Les sélecteurs Facebook changent régulièrement. Pour mettre à jour :

1. **Automatiquement** : le module vérifie le CDN à chaque démarrage (configurer `SELECTORS_CDN_URL` dans `selector_registry.py`)
2. **Manuellement** : éditer `config/selectors.json` — format v2 avec liste de fallbacks :

```json
{
    "version": "2026-03",
    "selectors": {
        "submit": {
            "selectors": [
                "[aria-label*=\"Post\"][role=\"button\"]",
                "[data-testid='react-composer-post-button']"
            ]
        }
    }
}
```

---

## Limites recommandées (anti-détection)

| Paramètre | Valeur recommandée |
|---|---|
| Groupes par session | 10–15 max |
| Délai entre groupes | 60–120 secondes |
| Sessions par jour | 2–3 max |
| Cooldown entre sessions | 2 heures minimum |

---

## Compatibilité

| OS | Statut |
|---|---|
| Windows 10/11 | ✓ Supporté |
| Ubuntu 20+ | ✓ Supporté |
| macOS 12+ | ✓ Supporté |

---

## Dépendances principales

| Package | Version | Rôle |
|---|---|---|
| playwright | 1.42.0 | Moteur navigateur |
| python-dotenv | 1.0.1 | Variables d'environnement |
| requests | 2.31.0 | Mise à jour sélecteurs CDN |
| pyarmor | 8.4.0 | Obfuscation code |
| pycryptodome | 3.20.0 | Cryptographie |

---

*BON v2.0 — Mars 2026 — Document de travail interne*
