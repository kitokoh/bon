"""
__main__.py v14 — Point d'entrée BON
Délègue toutes les commandes au nouveau module CLI (cli_v14.py)
"""
import sys

try:
    from check_license import is_license_valid
    if not is_license_valid():
        print("\n✗ Licence invalide ou expirée.\n", file=sys.stderr)
        sys.exit(1)
except Exception as _e:
    pass

try:
    from playwright.sync_api import sync_playwright  # noqa
except ImportError:
    print("\n✗ Playwright non installé. Lancez : python install.py\n", file=sys.stderr)
    sys.exit(1)

from libs.cli_v14 import run_cli

if __name__ == "__main__":
    run_cli()
