# libs/__init__.py — API publique du package libs (v7)
#
# Modules actifs :
#   database        — SQLite thread-safe (RLock, WAL, FK, health_score adaptatif)
#   playwright_engine — Moteur navigateur Playwright
#   scraper         — Logique métier Facebook (groupes, marketplace, commentaires)
#   stealth_profile — Fingerprinting anti-détection natif CDP (v7, 0 dépendance)
#   circuit_breaker — Circuit breaker par compte (CLOSED/OPEN/HALF-OPEN)
