# libs/__init__.py — API publique du package libs (v12)
#
# Modules actifs :
#   database          -- SQLite thread-safe (RLock, WAL, FK, health_score adaptatif)
#   playwright_engine -- Moteur navigateur Playwright
#   scraper           -- Logique metier Facebook (groupes, marketplace, commentaires)
#   stealth_profile   -- Fingerprinting anti-detection natif CDP (0 dependance externe)
#   circuit_breaker   -- Circuit breaker par robot (CLOSED/OPEN/HALF-OPEN, persiste en DB)
#   rest_api          -- API Flask avec rate limiting et filtres date
#   bon_scheduler     -- Planificateur APScheduler + persistance SQLite
#   captcha_solver    -- 2captcha avec cle par robot (DB) ou globale (env)
#
# Dependances optionnelles (non bloquantes au demarrage) :
#   flask            -- API REST (pip install flask>=3.0.0)
#   flask-limiter    -- Rate limiting API (pip install flask-limiter)
#   apscheduler      -- Planificateur cron (pip install apscheduler>=3.10.0)
#   openpyxl         -- Export XLSX (pip install openpyxl>=3.1.0)
#
# Verifier les dependances optionnelles :
#   from libs import check_optional_deps; check_optional_deps()


def check_optional_deps() -> dict:
    """Verifie les dependances optionnelles et retourne leur statut.

    Usage :
        from libs import check_optional_deps
        status = check_optional_deps()
        # {"flask": True, "flask_limiter": False, "apscheduler": True, "openpyxl": True}
    """
    deps = {
        "flask": False,
        "flask_limiter": False,
        "apscheduler": False,
        "openpyxl": False,
    }
    for dep in deps:
        try:
            __import__(dep)
            deps[dep] = True
        except ImportError:
            pass
    return deps


def print_deps_status() -> None:
    """Affiche un tableau de statut des dependances optionnelles."""
    status = check_optional_deps()
    labels = {
        "flask":        ("API REST", "pip install flask>=3.0.0"),
        "flask_limiter":("Rate limiting API", "pip install flask-limiter"),
        "apscheduler":  ("Planificateur cron", "pip install apscheduler>=3.10.0"),
        "openpyxl":     ("Export XLSX", "pip install openpyxl>=3.1.0"),
    }
    print("\nDependances optionnelles BON v12 :")
    for dep, ok in status.items():
        label, install = labels[dep]
        mark = "OK" if ok else "MANQUANT"
        hint = "" if ok else f"  -> {install}"
        print(f"  [{mark:8s}] {dep:<15} {label}{hint}")
    print()
