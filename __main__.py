"""
__main__.py — Entry point for the Facebook Groups Post Bot.

Run with:
    python -m bon
"""

from __future__ import annotations

import sys


def _banner() -> None:
    print(
        "\n"
        "╔══════════════════════════════════════════╗\n"
        "║     Facebook Groups Post Bot  v2.0       ║\n"
        "╚══════════════════════════════════════════╝\n"
    )


def _menu() -> None:
    print(
        "  1) Save groups (search by keyword)\n"
        "  2) Post in groups  (single image)\n"
        "  3) Post in groups  (multi-image)\n"
        "  4) Exit\n"
    )


def main() -> None:
    _banner()

    # Import lazily so startup errors surface cleanly.
    try:
        from libs.scraper import Scraper
    except Exception as exc:
        print(f"[FATAL] Could not import Scraper: {exc}")
        sys.exit(1)

    scraper: Scraper | None = None

    try:
        scraper = Scraper()

        while True:
            _menu()
            choice = input("Option: ").strip()

            if choice == "1":
                keyword = input("Enter keyword: ").strip()
                if keyword:
                    links = scraper.save_groups(keyword)
                    print(f"  → {len(links)} groups saved.\n")
                else:
                    print("  Keyword cannot be empty.\n")

            elif choice == "2":
                print("  Starting single-image posting …\n")
                scraper.post_in_groups()

            elif choice == "3":
                print("  Starting multi-image posting …\n")
                scraper.post_in_groupsx()

            elif choice == "4":
                print("  Bye!\n")
                break

            else:
                print("  Invalid option — please enter 1, 2, 3 or 4.\n")

    except KeyboardInterrupt:
        print("\n  Interrupted by user.")

    finally:
        if scraper is not None:
            scraper.browser.quit()


if __name__ == "__main__":
    main()
