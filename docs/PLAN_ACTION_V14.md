# BON — Plan d'action d'amélioration (v14)

Document de synthèse : **vision produit**, **audit ami** (`BON_Audit_v11.pdf`), **implémentation réelle v14** dans ce dépôt, et **priorités** pour la suite.

---

## 1. Vision et besoins métier

- **Automatiser** la publication dans des groupes Facebook de façon **prudente** (délais, circuit breaker, variants, anti-doublon SQL).
- **Piloter plusieurs comptes** (robots) avec **traçabilité** (publications, erreurs, CAPTCHA, health).
- **S'intégrer** à un écosystème d'outils (n8n, Make, dashboard maison) via **API** et **exports**.
- **S'adapter** aux changements de DOM Facebook (sélecteurs versionnés, CDN optionnel, santé des sélecteurs).
- **Limiter les risques** : respect des CGU Facebook à la charge de l'exploitant ; le logiciel vise la **résilience technique**, pas la contournement « garanti » des politiques plateforme.

---

## 2. Alignement audit ami ↔ code v14 (honnêteté technique)

| Sujet | Document d'audit (cible) | Ce dépôt (réalité v14) |
|--------|---------------------------|-------------------------|
| CAPTCHA | SDK `2captcha-python`, `detect_captcha_on_page`, clé par robot en DB | Client HTTP dans `libs/captcha_solver.py`, clé **`BON_2CAPTCHA_KEY`**, résolution auto si **`BON_AUTO_SOLVE_CAPTCHA=1`** ; table **`captcha_solve_log`** |
| Scheduler | `schedule start` / `--daemon`, fichier `scheduler/scheduler.py` | **`python -m bon schedule daemon`**, logique dans **`libs/bon_scheduler.py`** |
| API | 12+ routes sous `/api/v1/...` | Routes **`/v1/...` et `/api/v1/...`** (alias) ; export CSV/XLSX via **`GET .../publications/export`** |
| CDN | `BON_USE_CDN=1` par défaut + GitHub Releases | **`BON_USE_CDN` désactivé par défaut** + URL **obligatoire** si activation (pas d'URL fictive) |
| Export | CSV + XLSX, filtres date | **CSV + XLSX** (CLI `export` + API) ; filtres date **implémentés v14** |
| Config robot | `robot config --set max_groups_per_run=3` (tous champs) | **CLI Pro v14** complète : `add-account`, `assign-proxy`, `status --watch`, `logs --json`, `queue`, `health` |
| Tests | ~30 tests dont stealth dédiés | **`tests/test_v10.py`** + **`tests/test_v11.py`** + **`tests/test_smoke.py`** ; **pas** de suite E2E navigateur |
| PostgreSQL | Prévu v12 | **Non** (SQLite uniquement) |
| Session Management | Non spécifié | **SessionManager v14** : isolation complète avec `chrome_profiles/` |
| Human Behavior | Non spécifié | **HumanBehavior v14** : mouvements Bézier, délais Gamma, fatigue adaptative |
| Task Queue | Non spécifié | **TaskQueue v14** : file SQLite avec backoff exponentiel |
| Monitor | Non spécifié | **Monitor v14** : classification 15 classes d'erreurs, score santé 0-100 |

**Score** : l'audit fixe une cible « ~98/100 » ; une estimation **conservatrice** pour le dépôt actuel est **114/120**, les écarts principaux étant **E2E**, **PostgreSQL**, **dashboard web complet**.

---

## 3. Plan d'action par priorité (v15)

### Priorité haute

| ID | Action | Effort | Critère de succès |
|----|--------|--------|-------------------|
| **V15-P1** | **Tests E2E DOM synthétique** (Playwright sur HTML mock + CI) | 2–3 sem. | Régression sur sélecteurs clés sans compte FB réel |
| **V15-P2** | **Dashboard web** (Flask/FastAPI + graphiques 7 jours) | 4–5 sem. | Vue lecture/écriture minimale robots & stats |
| **V15-P3** | **Adaptateur PostgreSQL** (`BON_DB_URL`, migration depuis SQLite) | 3–4 sem. | 10+ robots en écriture concurrente sans contention majeure |

### Priorité normale

| ID | Action | Effort |
|----|--------|--------|
| **V15-K1** | Multi-provider CAPTCHA (fallback AntiCaptcha / CapMonster) | 1 sem. |
| **V15-K2** | Pool de proxies + rotation liée au circuit breaker | 2–3 sem. |
| **V15-K3** | Warmup guidé (étapes J1/J7/J14) stockées en DB | 2 sem. |
| **V15-K4** | **`GET /metrics`** (Prometheus) | 1 sem. |
| **V15-K5** | Webhooks **Slack / Discord** en parallèle de Telegram | 1 sem. |

### Priorité future

- Docker Compose (BON + Postgres + option Redis pour files).
- WebSocket logs temps réel.
- Module autre réseau social (hors périmètre court terme).

---

## 4. Mesures de solidité immédiates (v14)

1. **Verrouiller la prod** : `BON_API_TOKEN` fort, API non exposée sur `0.0.0.0` sans reverse-proxy TLS.
2. **CDN** : définir une URL de sélecteurs **contrôlée par l'équipe** ; activer `BON_USE_CDN=1` seulement si cette URL est stable.
3. **Surveiller** : consulter `status --watch`, `health`, `logs --json`, et API `/v1/dashboard`.
4. **Mettre à jour** : `python -m bon update-ua` régulièrement ; surveiller `SELECTORS_STALE` dans les logs.
5. **Monitor** : utiliser `queue` pour suivre les tâches et `health` pour score santé 0-100.

---

## 5. Réalisations v14 (consolidées)

### ✅ Architecture industrielle
- **SessionManager** : isolation complète par robot
- **HumanBehavior** : anti-détection avancé
- **TaskQueue** : file avec backoff exponentiel
- **Monitor** : classification erreurs + score santé
- **CLI Pro** : monitoring temps réel

### ✅ Fonctionnalités opérationnelles
- `status --watch` : rafraîchissement automatique
- `logs --json` : logs structurés filtrables
- `queue` : gestion tâches avec retry
- `health` : score santé par robot
- `enqueue` : ajout tâches (post/comment/join_group)

---

*Dernière mise à jour : avril 2026 — alignée sur BON v14 avec architecture consolidée.*
