"""
automation/__init__.py — Package automation moderne

Ce package fournit une architecture moderne pour l'automatisation Facebook:
- Interface unifiée (engine.py)
- Sélecteurs centralisés multi-langue
- Fallback automatique
- Gestion de santé des sélecteurs
- Anti-blocage intelligent
"""

from automation.engine import AutomationEngine
from automation.playwright_engine import PlaywrightWrapper
from automation.selenium_engine import SeleniumEngine
from automation.selector_tester import test_selector
from automation.selector_health import SelectorHealthManager, get_health_manager
from automation.anti_block import AntiBlockManager, get_anti_block_manager

__all__ = [
    "AutomationEngine",
    "PlaywrightWrapper",
    "SeleniumEngine",
    "test_selector",
    "SelectorHealthManager",
    "get_health_manager",
    "AntiBlockManager",
    "get_anti_block_manager",
]

__version__ = "5.0.0"
__author__ = "BON Team"
