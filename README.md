# Facebook Groups Post Bot — v2.0

Automation tool for posting content to Facebook Groups using Selenium.

## Architecture

```
bon-v2/
├── __main__.py          # CLI entry point  →  python -m bon
├── .env.example         # Configuration template
├── data.json            # Groups + posts (single image)
├── data1.json           # Posts (multi-image)
├── requirements.txt
├── config/
│   └── selectors.json   # Multi-language CSS selectors
├── libs/
│   ├── browser.py       # BrowserEngine — pure Selenium primitives
│   └── scraper.py       # Scraper       — Facebook business logic
├── logs/                # Auto-created — daily log files
└── screenshots/         # Auto-created — error screenshots
```

### Layer responsibilities

| File | What it does |
|------|--------------|
| `browser.py` | Manages Chrome lifecycle, provides `click / type_text / find_one / …` |
| `scraper.py` | Facebook-specific logic: open composer, upload images, submit, wait |
| `__main__.py` | Interactive CLI menu |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set CHROME_FOLDER to your Chrome profile path
```

## Run

```bash
python -m bon
```

## Key robustness improvements (v2 vs v1)

| Area | v1 | v2 |
|------|----|----|
| Browser engine | Duplicated in `automate.py` + `automate3.py` | Single `browser.py` |
| Error handling | Mixed raise/silent | Every step returns bool; failed groups never crash the run |
| Retries | None | `_with_retries()` with exponential back-off for Stale/Timeout |
| Image upload | Parallel threads (race conditions) | Sequential — safe with Facebook's dialog |
| Screenshots on error | Manual | Automatic on every failure |
| Logging | Single file, mixed print/logger | Rotating daily log + console; structured format |
| Path resolution | Hardcoded Windows paths | `_resolve_path()` handles absolute + relative |
| Config validation | None | Warns at startup for missing groups/posts |
| Context manager | None | `with Scraper() as s:` — browser always cleaned up |
