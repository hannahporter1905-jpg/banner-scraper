# Agent Instructions

> This file is mirrored across CLAUDE.md, AGENTS.md, and GEMINI.md so the same instructions load in any AI environment.

## Project Overview: Banner Scraper

A **Playwright-based web scraper** that extracts banner/promotional images from casino and gaming websites. Uses stealth techniques + Oxylabs Web Unblocker proxy to bypass bot detection and geo-restrictions.

**Key Features:**
- Multi-page scraping (homepage → auto-discover promotions page)
- Geo-location targeting (10+ countries via proxy)
- Carousel detection (clicks through sliders to capture all banner variants)
- Background image extraction (CSS backgrounds + `<img>` tags)
- Three interfaces: CLI, Web UI, and API server

**Tech Stack:**
- **Backend**: Node.js + Python (Playwright)
- **Frontend**: Vanilla HTML/CSS/JS (responsive UI)
- **Proxy**: Oxylabs Web Unblocker (bypasses Cloudflare, Akamai, geo-blocks)
- **Deployment**: Docker, VPS, Oracle Cloud Free Tier, or split (Vercel frontend + VPS backend)

---

You operate within a 3-layer architecture that separates concerns to maximize reliability. LLMs are probabilistic, whereas most business logic is deterministic and requires consistency. This system fixes that mismatch.

## The 3-Layer Architecture

**Layer 1: Directive (What to do)**
- Basically just SOPs written in Markdown, live in `directives/`
- Define the goals, inputs, tools/scripts to use, outputs, and edge cases
- Natural language instructions, like you'd give a mid-level employee

**Layer 2: Orchestration (Decision making)**
- This is you. Your job: intelligent routing.
- Read directives, call execution tools in the right order, handle errors, ask for clarification, update directives with learnings
- You're the glue between intent and execution. E.g you don't try scraping websites yourself—you read `directives/scrape_website.md` and come up with inputs/outputs and then run `execution/scrape_single_site.py`

**Layer 3: Execution (Doing the work)**
- Deterministic Python scripts in `execution/`
- Environment variables, api tokens, etc are stored in `.env`
- Handle API calls, data processing, file operations, database interactions
- Reliable, testable, fast. Use scripts instead of manual work. Commented well.

**Why this works:** if you do everything yourself, errors compound. 90% accuracy per step = 59% success over 5 steps. The solution is push complexity into deterministic code. That way you just focus on decision-making.

## Operating Principles

**1. Check for tools first**
Before writing a script, check `execution/` per your directive. Only create new scripts if none exist.

**2. Self-anneal when things break**
- Read error message and stack trace
- Fix the script and test it again (unless it uses paid tokens/credits/etc—in which case you check w user first)
- Update the directive with what you learned (API limits, timing, edge cases)
- Example: you hit an API rate limit → you then look into API → find a batch endpoint that would fix → rewrite script to accommodate → test → update directive.

**3. Update directives as you learn**
Directives are living documents. When you discover API constraints, better approaches, common errors, or timing expectations—update the directive. But don't create or overwrite directives without asking unless explicitly told to. Directives are your instruction set and must be preserved (and improved upon over time, not extemporaneously used and then discarded).

## Self-annealing loop

Errors are learning opportunities. When something breaks:
1. Fix it
2. Update the tool
3. Test tool, make sure it works
4. Update directive to include new flow
5. System is now stronger

## Available Tools (Execution Scripts)

**Core Scraping:**
- `execution/scrape_with_playwright.py` - **CLI scraper** (interactive mode, prompts for URL/location/headless)
- `execution/scrape_api.py` - **API wrapper** (JSON output for backend server integration)

**Backend & Frontend:**
- `backend/server-playwright.js` - **Node.js API server** (spawns Python scraper, manages sessions)
- `frontend/index-v2.html` - **Web UI** (modern responsive interface)
- `frontend/script-v2.js` - **Frontend logic** (progress polling, results rendering)
- `frontend/config.js` - **Backend URL config** (for split deployment)

**Core Logic (Directives):**
- `directives/scrape_banners_stealth.py` - **Main scraping engine** (stealth mode, proxy, geo-targeting)
  - `scrape_website_banners_stealth()` - Single-page scraper
  - `scrape_site_full()` - Multi-page scraper (homepage + promotions)
  - `_click_promo_link()` - Auto-discovers and clicks promotion links
  - `_scrape_current_page()` - Extracts banners from current page

## Common Issues & Solutions

### 1. **"Page.evaluate: Target page, context or browser has been closed"**
**Cause:** Website detects automation and closes/redirects the page during scraping.

**Solutions:**
- **Website-specific issue** - Try a different test site first to verify scraper works
- **Aggressive bot detection** - Some sites (e.g., novadreams.com) have strong anti-bot measures
- **Proxy IP blocked** - Try changing location or contact Oxylabs for fresh IPs
- **Add error handling** - Wrap `page.evaluate()` calls in try-catch blocks to handle gracefully

**Test sites (less aggressive):**
- `https://www.casinomeister.com/`
- `https://www.askgamblers.com/`
- `https://www.casinobonusca.com/`

### 2. **Location Mapping Errors**
**Cause:** Frontend sends integer (1-10), but scraper expects country code string (US, UK, etc.)

**Solution:** Already fixed in `execution/scrape_api.py` with location_map dictionary:
```python
location_map = {1: 'US', 2: 'UK', 3: 'CA', 4: 'AU', 5: 'DE', ...}
```

### 3. **Proxy Authentication Failures**
**Cause:** Invalid Oxylabs credentials in `.env`

**Solution:**
1. Verify credentials: `curl -k -x https://unblock.oxylabs.io:60000 -U 'user:pass' 'https://ip.oxylabs.io/location'`
2. Check `.env` format:
   ```env
   PROXY_HOST=unblock.oxylabs.io
   PROXY_PORT=60000
   PROXY_USER=your_username
   PROXY_PASS=your_password
   PROXY_SCHEME=https
   ```
3. Ensure no spaces around `=` signs

### 4. **Playwright Not Installed**
**Cause:** Missing Playwright browsers

**Solution:**
```bash
pip install playwright
playwright install chromium
```

### 5. **JSON Parsing Errors in Backend**
**Cause:** Python script output includes non-JSON text before JSON object

**Solution:** Already fixed in `backend/server-playwright.js` - parses JSON from end of output.

## Testing Guidelines

**Before testing:**
1. Verify proxy credentials in `.env`
2. Check Playwright is installed: `playwright --version`
3. Test proxy connection: `curl -k -x https://unblock.oxylabs.io:60000 -U 'user:pass' 'https://ip.oxylabs.io/location'`

**Testing CLI scraper:**
```bash
# Interactive mode
python execution/scrape_with_playwright.py

# Command-line args
python execution/scrape_with_playwright.py https://example.com --visible --location US
```

**Testing API server:**
```bash
# Start server
npm start

# Open browser
http://localhost:3000
```

**Good test sites:**
- Low bot detection: `casinomeister.com`, `askgamblers.com`
- Medium bot detection: `casinobonusca.com`, `betway.com`
- High bot detection: `novadreams.com`, `bet365.com` (expect failures)

**Expected behavior:**
- Homepage scrapes first (1-10 banners typical)
- Auto-discovers promotion link (looks for "promo", "bonus", "offer" keywords)
- Clicks promotion link (real Playwright click, not page.goto)
- Scrapes promotions page (5-20 banners typical)
- Returns deduplicated results grouped by page

## Deployment Architecture

**Option 1: Single Server (Recommended for MVP)**
- Deploy everything on one VPS/Oracle Cloud instance
- Node.js + Python + Playwright all on same server
- Simplest setup, no CORS issues

**Option 2: Split Deployment**
- **Frontend**: Vercel/Netlify (static files)
- **Backend**: VPS/Oracle Cloud (Node.js + Python)
- Configure `frontend/config.js` with backend URL
- Requires CORS handling in backend

**Option 3: Docker**
- Use included `Dockerfile`
- Single container with Node.js + Python + Playwright
- Deploy to any Docker host (DigitalOcean, AWS, GCP, etc.)

**Important:** Vercel/Railway/Netlify **cannot run Playwright** (binary size, timeouts). Must use VPS/dedicated server for backend.

## File Organization

**Project Structure:**
```
banner-scraper/
├── execution/           # Layer 3: Python CLI scripts
│   ├── scrape_with_playwright.py  # Interactive CLI scraper
│   └── scrape_api.py               # API wrapper (JSON output)
├── directives/          # Layer 1: Core scraping logic
│   └── scrape_banners_stealth.py   # Main engine (stealth + proxy)
├── backend/             # Node.js API server
│   ├── server-playwright.js        # Spawns Python scraper
│   └── package.json                # Backend dependencies
├── frontend/            # Web UI (vanilla JS)
│   ├── index-v2.html               # Responsive UI
│   ├── script-v2.js                # Frontend logic
│   └── config.js                   # Backend URL config
├── .env                 # Proxy credentials (never commit)
├── .env.example         # Template for .env
├── Dockerfile           # Docker deployment
├── vercel.json          # Vercel config (frontend only)
├── package.json         # Root package file
├── requirements.txt     # Python dependencies
├── README.md            # User documentation
└── CLAUDE.md            # Agent instructions (this file)
```

**Key Files:**
- `.env` - **Oxylabs proxy credentials** (required for scraping)
- `directives/scrape_banners_stealth.py` - **Core scraping engine** (modify for banner detection improvements)
- `execution/scrape_with_playwright.py` - **CLI entry point** (unchanged since initial commit)
- `backend/server-playwright.js` - **API server** (handles sessions, spawns Python)

**Environment Variables (.env):**
```env
PORT=3000
PROXY_HOST=unblock.oxylabs.io
PROXY_PORT=60000
PROXY_USER=your_username
PROXY_PASS=your_password
PROXY_SCHEME=https
```

**Important:**
- **Never commit `.env`** - Contains proxy credentials
- **Test changes locally first** - Oxylabs charges per request
- **Check git status before committing** - Ensure no sensitive data included

## Best Practices & Considerations

### When Improving Banner Detection:
1. **Test with multiple sites** - Don't optimize for just one website
2. **Preserve existing logic** - Add new patterns, don't remove working ones
3. **Document changes** - Update comments explaining why new keywords/rules added
4. **Consider false positives** - Banner detection balance: too loose = noise, too strict = missing banners

### When Fixing Errors:
1. **Identify if it's code or runtime** - Check git history first (`git diff HEAD`)
2. **Test with simple sites first** - Isolate if issue is website-specific
3. **Check proxy connection** - `curl` test before blaming code
4. **Add graceful error handling** - Wrap risky operations in try-catch
5. **Update this file** - Document new error patterns discovered

### When Adding Features:
1. **Follow 3-layer architecture** - Directives (logic) → Execution (CLI) → Backend (API)
2. **Update all interfaces** - CLI + API + Web UI must all support new features
3. **Add command-line args** - Make features toggleable (e.g., `--include-small-images`)
4. **Test backwards compatibility** - Ensure existing workflows still work

### Proxy Usage:
- **Costs money** - Every request goes through Oxylabs (pay per GB)
- **Test locally first** - Use `--visible` mode to debug without wasting requests
- **Respect rate limits** - Add delays between requests
- **Monitor usage** - Check Oxylabs dashboard regularly

### Git Workflow:
1. **Test locally** before committing
2. **Clear commit messages** - Describe what changed and why
3. **One feature per commit** - Makes rollbacks easier
4. **Never commit `.env`** - Already in `.gitignore`
5. **Push to GitHub after testing** - Keep remote in sync

## Summary

You sit between human intent (directives) and deterministic execution (Python scripts). Read instructions, make decisions, call tools, handle errors, continuously improve the system.

**Your role in this project:**
- **Orchestrate** scraping workflows using existing tools
- **Debug** runtime issues (proxy, website changes, Playwright errors)
- **Improve** banner detection logic when needed
- **Document** learnings in this file and code comments
- **Test** changes thoroughly before committing

**When scraping fails:**
1. Check if code changed (`git diff HEAD`)
2. Test with known-good website
3. Verify proxy credentials
4. Check if website added bot detection
5. Add error handling if needed
6. Document pattern in "Common Issues" section

Be pragmatic. Be reliable. Self-anneal.

---

**Last Updated:** 2026-02-13
**Version:** 1.1 (Added project-specific details and troubleshooting)


