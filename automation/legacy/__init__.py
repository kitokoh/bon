"""
automation/legacy/ — Code archivé, non utilisé en production.

Ces fichiers (engine.py, playwright_engine.py, selenium_engine.py) constituaient
une tentative de façade unifiée qui n'a jamais été branchée dans le flux réel.
La décision architecturale v5 est : libs/playwright_engine.py + libs/scraper.py
sont le pipeline unique. automation/ ne contient plus que les outils actifs :
  - anti_block.py
  - selector_health.py
  - selector_tester.py

Conservés ici pour référence / future réutilisation potentielle.
Ne pas importer depuis ce dossier en production.
"""
