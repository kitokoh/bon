# BON — Feuille de route

## État actuel : **v14** (avril 2026)

### Livré en v14
- **SessionManager** : isolation complète par robot avec `chrome_profiles/`
- **HumanBehavior** : mouvements souris Bézier, délais Gamma, fatigue adaptative
- **TaskQueue** : file SQLite avec backoff exponentiel et retry automatique
- **Monitor** : classification 15 classes d'erreurs, score santé 0-100
- **CLI Pro** : `status --watch`, `logs --json`, `queue`, `health` en temps réel
- **Architecture consolidée** : modules v14 intégrés, score 114/120

### Livré en v11 (précédent)
- **CDN sélecteurs** : plus d'URL GitHub fictive ; `BON_USE_CDN=1` + `BON_SELECTORS_CDN_URL` ou `config set selectors_cdn_url` ; cache TTL `BON_SELECTORS_CACHE_TTL_S`.
- **Proxy CLI** : `robot create --proxy-server …`, `robot config set|show|clear-proxy`, `post --validate-proxy`, login création avec proxy contexte Playwright.
- **Export CSV** : `python -m bon export --out … [--robot …]` + pagination DB `get_publications_paginated`.
- **2captcha** : `libs/captcha_solver.py`, `python -m bon captcha test`, journal `captcha_solve_log` ; résolution auto optionnelle dans `check_page_state` si `BON_AUTO_SOLVE_CAPTCHA=1` + `BON_2CAPTCHA_KEY`.
- **Scheduler** : table `scheduler_jobs`, `schedule add|list|remove|daemon` (APScheduler).
- **API REST** : `python -m bon api` — Flask, `BON_API_TOKEN`, `/v1/*` (robots, dashboard, publications, run).
- **Cross-robot variants** : `BON_CROSS_ROBOT_VARIANT_EXCLUSION=1` + `pick_variant(..., exclude_cross_robot=True)`.
- **Tests** : `tests/test_v10.py` (ex-v9), `tests/test_v11.py`.

### Suite possible (v15)
- Tests E2E DOM synthétique, dashboard web complet, adaptateur PostgreSQL, `robot config` étendu, `/metrics`, multi-provider CAPTCHA.

### Synthèse audit (`BON_Audit_v11.pdf`) ↔ dépôt
L’audit décrit une cible « plateforme 24/7 » très proche de cette base. **Écarts documentés** : pas de SDK `2captcha-python` (HTTP natif), pas de colonnes `captcha_*` par robot (clé globale `BON_2CAPTCHA_KEY`), CDN **opt-in** (pas d’URL GitHub imposée), scheduler sous **`schedule daemon`** (pas `schedule start`). **Renforts dépôt** : alias API `/api/v1/*`, export **XLSX** (`openpyxl`), endpoints **campaigns**, **groups**, **errors**, **publications/export**.

**Plan d'action détaillé** : [docs/PLAN_ACTION_V14.md](docs/PLAN_ACTION_V14.md).

---

## Archive : v10 (avril 2026)

### ✅ Réalisé (v3 → v10)

**Fondations (v3–v6)**
- Correction deadlock SQLite (RLock)
- Crash JS selector tester corrigé
- Boucle infinie scroll bornée
- Injection URL encodée
- Détection CAPTCHA corrigée
- Proxy par contexte Playwright
- Locale/timezone configurable
- Architecture nettoyée (code mort supprimé)

**Anti-détection (v7)**
- Stealth CDP natif (10 vecteurs, 0 dépendance externe)
- navigator.webdriver → undefined
- Canvas noise unique par session
- WebGL vendor/renderer spoofing
- Plugins, deviceMemory, screen cohérents
- window.chrome injecté
- Permissions API normalisée

**Résilience (v7–v8)**
- Circuit breaker CLOSED→OPEN→HALF-OPEN
- État CB persisté en DB (survit aux redémarrages)
- Alertes Telegram async (8 types)
- Health score adaptatif par compte
- Warmup progressif nouveaux comptes

**Architecture SQL (v8–v9)**
- Zéro JSON métier (tout en SQLite)
- 20 tables : robots, campaigns, variants, media, comments, dm_queue, subscriptions...
- Modèle Robot (robot1..N) = 1 compte Facebook
- Anti-doublon publications : was_published_recently()
- Media assets avec captcha optionnel
- Pool commentaires SQL + RANDOM()
- Circuit breaker persisté en DB
- 8 factories de test (niveau industriel)
- Migration idempotente v8→v9

**Actions sociales (v9)**
- subscribe_to_group() — multi-sélecteurs DOM
- comment_on_post() — pool SQL
- browse_and_comment() — navigation naturelle
- send_dm() — texte + image/vidéo
- process_dm_queue() — file planifiée
- simulate_natural_browse() — mouvements souris

**Qualité v10**
- UA Chrome mis à jour : 130–134 (depuis 122–124)
- user_agents.json externalisé (mise à jour sans code)
- `python -m bon update-ua` — commande dédiée
- Alerte au démarrage si UA obsolètes
- Sélection intelligente de variants (anti-répétition 30j par groupe)
- Bug Telegram corrigé (get_telegram_config inexistante)
- configure_from_robot() vs configure_from_session()
- requirements.txt nettoyé (v10, playwright>=1.50)
- ROADMAP.md à jour (ce fichier)

---

## Backlog historique (référence) — items v10 largement couverts en v11

| ID | Thème | Statut v11 |
|----|--------|----------------|
| P1 | CDN sélecteurs | Fait (URL explicite, pas de repo fictif) |
| P2 | Proxy par robot | Fait (CLI + DB + validation optionnelle) |
| P3 | Tests E2E DOM | **À faire** (v15) |
| P4 | CAPTCHA 2captcha | Fait (client + journal + **auto** si `BON_AUTO_SOLVE_CAPTCHA=1`) |
| K1 | Scheduler | Fait (`schedule add` / `daemon`) |
| K2 | Dashboard web | Partiel (API REST + CLI `dashboard` ; pas de graphes 7j) |
| K3 | Export CSV | Fait (`bon export`) |
| K4 | API REST | Fait (`bon api`, Bearer token) |
| F3 | Cross-robots variants | Fait (`BON_CROSS_ROBOT_VARIANT_EXCLUSION`) |

---

## Score de santé par version

| Version | Score | Highlight |
|---------|-------|-----------|
| v3 | 20/100 | Prototype instable |
| v7 | 87/100 | Stealth + Circuit breaker |
| v8 | 95/100 | Tout-SQL |
| v9 | 95/100 | Modèle Robot + factories |
| v10 | **96/100** | UA à jour + bug Telegram + rotation variants |
| **v11** | **97/100** | Proxy + CDN explicite + export + scheduler + API + CAPTCHA auto optionnel |
| **v14** | **114/120** | SessionManager + HumanBehavior + TaskQueue + Monitor + CLI Pro |

**Objectif v15** — Tests E2E DOM + dashboard web enrichi + PostgreSQL optionnel
