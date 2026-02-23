# Agent Instructions

> Mirrored across CLAUDE.md, AGENTS.md, and GEMINI.md so the same instructions load in any AI environment.

## Project Overview

A Playwright-based scraper that extracts banner/promotional images from casino and gaming websites. Uses stealth browser fingerprinting + Oxylabs Web Unblocker proxy to bypass bot detection and geo-restrictions.

**What it does:**
- Scrapes homepage banners, then auto-discovers and scrapes the promotions page
- Clicks through carousels/sliders to capture all banner variants
- Extracts both `<img>` tags and CSS background images
- Targets content from a specific geo-location via proxy (10 countries supported)

**Interfaces:** CLI (`scrape_with_playwright.py`), Web UI (`frontend/`), REST API (`backend/server-playwright.js`)

**Tech stack:** Python + Playwright (scraping), Node.js (API server), Vanilla JS (frontend), Oxylabs Web Unblocker (proxy)

---

## Architecture: 3 Layers

| Layer | Role | Location |
|-------|------|----------|
| **Directive** | What to do — SOPs, goals, edge cases | `directives/` |
| **Orchestration** | Decision-making — that's you | (this file) |
| **Execution** | Deterministic scripts that do the work | `execution/` |

**Why this matters:** LLMs are probabilistic; business logic must be deterministic. Push complexity into scripts, keep your job to routing and decisions.

**Your job as orchestrator:**
1. Read the relevant directive before acting
2. Call execution scripts in the right order
3. Handle errors — fix, test, update directive, move on
4. Don't scrape sites yourself; run the scripts

---

## File Map

```
banner-scraper/
├── directives/                          # Layer 1: Logic + SOPs
│   ├── scrape_banners.md                # Markdown SOP (human-readable spec)
│   ├── scrape_banners_stealth.py        # ★ MAIN ENGINE (stealth + proxy + geo)
│   ├── scrape_banners_playwright.py     # Older Playwright version (reference)
│   ├── scrape_banners.py                # Oldest version (reference)
│   └── __init__.py
│
├── execution/                           # Layer 3: CLI entry points
│   ├── scrape_with_playwright.py        # ★ Interactive CLI scraper
│   ├── scrape_api.py                    # ★ JSON wrapper (called by Node.js backend)
│   ├── test_proxy.py                    # Utility: test free/Oxylabs proxy connectivity
│   ├── scrape_playwright_proxy.py       # Experimental variants (reference only)
│   ├── scrape_stealth.py
│   ├── scrape_single_site.py
│   └── scrape_with_scraperapi.py (+ variants)
│
├── backend/
│   ├── server-playwright.js             # ★ Node.js API server (spawns scrape_api.py)
│   ├── server.js                        # Older server version (reference)
│   └── package.json
│
├── frontend/
│   ├── index-v2.html                    # ★ Current Web UI
│   ├── script-v2.js                     # ★ Current frontend logic
│   ├── style-v2.css                     # ★ Current styles
│   ├── config.js                        # Backend URL config (split deployment)
│   ├── index.html / script.js / style.css  # Older versions (reference)
│
├── .env                                 # Proxy credentials — NEVER COMMIT
├── .env.example                         # Template
├── requirements.txt                     # Python deps
├── Dockerfile                           # Container deployment
├── vercel.json                          # Frontend-only Vercel config
└── package.json                         # Root (starts backend server)
```

**Active files (★):** `directives/scrape_banners_stealth.py`, `execution/scrape_with_playwright.py`, `execution/scrape_api.py`, `backend/server-playwright.js`, `frontend/index-v2.*`

---

## Key Functions in the Main Engine

`directives/scrape_banners_stealth.py`:

| Function | What it does |
|----------|-------------|
| `scrape_site_full(url, headless, location)` | Full scrape: homepage → auto-discover promo page |
| `scrape_website_banners_stealth(url, ...)` | Scrapes a single page for banners |
| `_click_promo_link(page, base_url)` | Finds and clicks promotion/bonus link |
| `_scrape_current_page(page, base_url)` | Extracts banners from whatever page is loaded |
| `is_banner_image(img_data)` | Filters images: aspect ratio + keyword heuristics |
| `get_proxy_from_env(country)` | Builds Oxylabs proxy config from `.env` |

**Banner detection logic** (`is_banner_image`): checks width/height aspect ratio (wide = likely banner), src/alt/class keywords (`banner`, `hero`, `slider`, `promo`, `carousel`, etc.), and parent element classes.

---

## Environment Variables (`.env`)

```env
PORT=3000
PROXY_HOST=unblock.oxylabs.io
PROXY_PORT=60000
PROXY_USER=your_username
PROXY_PASS=your_password
PROXY_SCHEME=https
```

No spaces around `=`. Never commit this file.

**Location codes** (used by `scrape_api.py`):
`1=US, 2=UK, 3=CA, 4=AU, 5=DE, 6=FR, 7=JP, 8=BR, 9=IN, 10=SG`

---

## Running the Scraper

**CLI (interactive):**
```bash
python execution/scrape_with_playwright.py
# or with args:
python execution/scrape_with_playwright.py https://casinomeister.com --visible --location US
```

**Web UI + API server:**
```bash
npm start                  # starts backend/server-playwright.js on PORT 3000
# open http://localhost:3000
```

**Verify proxy before scraping:**
```bash
curl -k -x https://unblock.oxylabs.io:60000 -U 'user:pass' https://ip.oxylabs.io/location
```

**Test free proxies (no Oxylabs cost):**
```bash
python execution/test_proxy.py
```

---

## Test Sites (by bot detection level)

| Level | Sites |
|-------|-------|
| Low | `casinomeister.com`, `askgamblers.com` |
| Medium | `casinobonusca.com`, `betway.com` |
| High (expect failures) | `novadreams.com`, `bet365.com` |

**Expected results per scrape:** 1–10 homepage banners, 5–20 promotions banners, deduplicated and grouped by page.

---

## Common Errors & Fixes

### "Page.evaluate: Target page, context or browser has been closed"
**Cause:** Site detected the bot and killed the page.
- Test on a low-detection site first to confirm scraper itself works
- Try a different geo location (proxy IP may be flagged)
- Wrap `page.evaluate()` calls in try/catch

### Proxy auth failure (407 / connection refused)
- Run the `curl` verification command above
- Check `.env` has no spaces, correct credentials

### Location code error (integer vs string mismatch)
- Already fixed in `scrape_api.py` via `location_map` dict
- If you see it again: ensure frontend sends integer 1–10, not a string like "US"

### JSON parse error in backend
- Already fixed in `server-playwright.js` — parses JSON from the *end* of Python stdout
- If it recurs: check Python script isn't printing extra non-JSON lines after the JSON block

### Playwright not installed
```bash
pip install playwright && playwright install chromium
```

---

## Operating Principles

**1. Check before creating.** Look in `execution/` first. Only write a new script if nothing fits.

**2. Self-anneal on errors:**
1. Read the full error + stack trace
2. Fix the script
3. Test it (check w/ user first if it costs proxy credits)
4. Update the relevant directive with what you learned

**3. Directives are living documents.** When you discover new edge cases, API limits, or better patterns — update the directive. Don't overwrite directives without asking; improve them incrementally.

**4. Proxy costs money.** Every request through Oxylabs costs bandwidth. Use `--visible` to debug locally, and only run full scrapes to verify a fix works.

---

## Deployment Options

| Option | Setup | Notes |
|--------|-------|-------|
| **Single VPS** | Node.js + Python + Playwright on one server | Simplest, no CORS issues |
| **Split** | Frontend → Vercel, Backend → VPS | Set backend URL in `frontend/config.js` |
| **Docker** | `docker build + run` | Included `Dockerfile`, deploy anywhere |

Vercel/Netlify/Railway **cannot run Playwright** — binary size and timeout limits. Always use a VPS or dedicated server for the backend.

---

## When Scraping Fails (Checklist)

1. `git diff HEAD` — did something change?
2. Test on `casinomeister.com` — is the scraper itself broken?
3. `curl` test — is the proxy working?
4. Is it a new site with stronger bot detection?
5. Add try/catch around the failing call
6. Document the pattern in "Common Errors" above

---

**Last updated:** 2026-02-23
**Version:** 1.2 (Accurate file map, cleaned up structure, added test_proxy.py)
