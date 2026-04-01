"""
automation/__init__.py — Package automation BON v5

Décision architecturale v5 :
  - Le pipeline de publication est : libs/scraper.py → libs/playwright_engine.py
  - Ce package contient uniquement les outils transverses actifs :
      · anti_block   : limite horaire + déduplication images (monitoring)
      · selector_health : taux de succès des sélecteurs
      · selector_tester : outil de debug CLI interactif

Les anciennes tentatives de façade (engine.py, PlaywrightWrapper, SeleniumEngine)
sont archivées dans automation/legacy/ — ne pas importer depuis ce dossier.
"""

from automation.selector_health import SelectorHealthManager, get_health_manager
from automation.anti_block import AntiBlockManager, get_anti_block_manager
from automation.selector_tester import test_selector

__all__ = [
    "SelectorHealthManager",
    "get_health_manager",
    "AntiBlockManager",
    "get_anti_block_manager",
    "test_selector",
]

__version__ = "5.1.0"
