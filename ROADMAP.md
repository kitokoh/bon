# BON — Feuille de route

## État actuel : v10 (avril 2026)

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

## 🔄 En cours / Backlog v10

### Priorité HAUTE

| ID | Feature | Effort | Critère succès |
|----|---------|--------|----------------|
| P1 | CDN sélecteurs activé (GitHub Releases) | 1 semaine | BON_SELECTORS_CDN_URL configuré en prod |
| P2 | Proxies résidentiels par robot | 2 semaines | 1 proxy par robot, champs proxy_host/port/user/pass |
| P3 | Tests E2E DOM synthétique | 3 semaines | Flux post, session expirée, stealth testés |
| P4 | Résolution CAPTCHA auto (2captcha) | 1 semaine | 95%+ CAPTCHA résolus sans intervention |

### Priorité NORMALE

| ID | Feature | Effort | Notes |
|----|---------|--------|-------|
| K1 | Scheduler APScheduler | 2 semaines | `python -m bon schedule --robot r1 --cron "0 8 * * *"` |
| K2 | Dashboard Flask/FastAPI | 5 semaines | Health scores, CB states, graphes 7j |
| K3 | Export CSV/Excel publications | 1 semaine | openpyxl (déjà installé) |
| K4 | API REST légère | 4 semaines | GET /robots, POST /robots/{n}/run, auth par token |

### Priorité FUTURE (v11)

| ID | Feature | Effort | Notes |
|----|---------|--------|-------|
| F1 | PostgreSQL optionnel | 4 semaines | DatabaseAdapter SQLite/PG, BON_DB_URL |
| F2 | Interface web React | 15 semaines | Dashboard complet, gestion robots |
| F3 | Rotation campagnes cross-robots | 2 semaines | Éviter même variant même groupe entre robots |

---

## Score de santé par version

| Version | Score | Highlight |
|---------|-------|-----------|
| v3 | 20/100 | Prototype instable |
| v7 | 87/100 | Stealth + Circuit breaker |
| v8 | 95/100 | Tout-SQL |
| v9 | 95/100 | Modèle Robot + factories |
| v10 | **96/100** | UA à jour + bug Telegram + rotation variants |

**Objectif v11 : 9.5/10** — CDN actif + proxies + tests E2E
