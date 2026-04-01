# BON — Feuille de route & suivi qualité

> Dernière mise à jour : **version 7** (améliorations critiques post-v6)

---

## ✅ Améliorations appliquées dans cette version (v7)

### 🔴 Sécurité anti-détection (P1 résolu définitivement)

| # | Fichier | Amélioration |
|---|---------|-------------|
| E1 | `libs/stealth_profile.py` *(nouveau)* | Fingerprinting anti-détection natif via CDP Playwright — **0 dépendance externe**. Techniques : `navigator.webdriver → undefined`, Canvas 2D noise par session, WebGL vendor/renderer spoofing, plugins réalistes, `deviceMemory`/`hardwareConcurrency` cohérents, `window.chrome` injecté, `navigator.languages` sync locale, headers HTTP `Sec-Ch-Ua`. Pool de 7 profils matériels + 7 user-agents Chromium 122-124. |
| E2 | `libs/scraper.py` | `StealthProfile.apply(page)` appelé automatiquement dans `Scraper.open()` après création de la page, **avant toute navigation**. |
| E3 | `libs/session_manager.py` | `DEFAULT_SESSION_CONFIG` : `"platform": "windows"` pour cohérence matérielle du fingerprint. |

### 🔴 Résilience multi-comptes (nouveau)

| # | Fichier | Amélioration |
|---|---------|-------------|
| F1 | `libs/circuit_breaker.py` *(nouveau)* | Circuit breaker par compte, pattern CLOSED → OPEN → HALF-OPEN. `failure_threshold=3`, `recovery_timeout_s=900`, `half_open_max_ok=2`. Thread-safe, singleton. |
| F2 | `libs/scraper.py` | Circuit breaker vérifié en tête de boucle. `record_success/failure` à chaque groupe. Erreurs critiques ouvrent le circuit immédiatement. |

### 🟠 Alertes push Telegram (P5 résolu)

| # | Fichier | Amélioration |
|---|---------|-------------|
| G1 | `libs/notifier.py` *(nouveau)* | Alertes Telegram via `urllib.request` stdlib — **0 dépendance externe**. Messages HTML pour blocage, session expirée, CAPTCHA, circuit ouvert, résumé run, health bas. Envoi async (daemon thread), **jamais bloquant**. |
| G2 | `libs/notifier.py` | Config : vars env `BON_TELEGRAM_TOKEN/CHAT_ID` > champ `"telegram"` session > `logs/telegram.json`. |
| G3 | `libs/scraper.py` | `notify_critical()` dans les except critiques. `notify_run_summary()` + alerte health en fin de boucle. |

### 🟡 Health score adaptatif + warmup progressif

| # | Fichier | Amélioration |
|---|---------|-------------|
| H1 | `libs/database.py` | Colonne `consecutive_failures` + migration idempotente. `record_publication` success → `health_score+2`, failure → `health_score-5`. |
| H2 | `libs/database.py` | `mark_warmup_completed()` + `get_health_score()`. |
| I1 | `libs/scraper.py` | Nouveaux comptes (`warmup_completed=0`) : run bridé à 3 groupes / 2 par heure automatiquement. |
| I2 | `libs/scraper.py` | 1er succès → `mark_warmup_completed()` → limites normales au prochain run. |

### 🟡 CDN sélecteurs amélioré (P3 partiellement résolu)

| # | Fichier | Amélioration |
|---|---------|-------------|
| J1 | `libs/selector_registry.py` | Fallback GitHub Releases automatique si `BON_SELECTORS_CDN_URL` non défini. |
| J2 | `libs/selector_registry.py` | Vérification d'âge du fichier local avant requête. `SELECTORS_MAX_AGE_DAYS` : 30 → **7 jours**. |

---

## 📊 Récapitulatif par version

| Version | Points clés | Fichiers modifiés |
|---------|-------------|-------------------|
| v3 | Bugs critiques fondateurs (deadlock DB, crash JS) | 8 |
| v4 | Proxy par contexte, anti_block unifié | 6 |
| v5 | Validation config, locale/timezone, CDN sélecteurs | 5 |
| v6 | Architecture legacy, rate-limit DB unifié, rotation logs | 12 |
| **v7** | **Stealth CDP, circuit breaker, Telegram, health score adaptatif, warmup** | **7** |

---

## ⚠️ Problèmes restants

### 🟠 P4 — Résolution CAPTCHA automatique
Détection OK, alerte Telegram OK. Résolution nécessite une intégration tierce.

```bash
pip install 2captcha-python
export TWOCAPTCHA_API_KEY="votre_clé"
```

### 🟠 P6 — Tests E2E (couverture 0%)
41 tests unitaires solides. Flux complet non testé. Dépendances : `pytest-playwright` + mock Facebook.

### 🟡 P7 — URL CDN production à configurer
Le fallback GitHub pointe vers un dépôt exemple. Pour production :

```bash
export BON_SELECTORS_CDN_URL="https://github.com/votre-org/bon/releases/latest/download/selectors.json"
```

### 🟢 Améliorations futures (non bloquantes)

| # | Idée | Complexité |
|---|------|-----------|
| K1 | Rotation de proxies résidentiels entre groupes | Moyenne |
| K2 | Dashboard Flask/FastAPI monitoring health scores | Haute |
| K3 | Export CSV/Excel des stats de publication | Faible |
| K4 | Scheduler intégré (`apscheduler`) | Moyenne |
