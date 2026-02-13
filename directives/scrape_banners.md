# Directive: Scrape Banner Images from a Website

## Goal
Given a base URL, automatically scrape banner images from the homepage and promotions page.

## Inputs
- `url` (string, required): The base URL of the website (e.g. `https://example.com`)

## Process (Full Site Scrape — `scrape_site_full()`)
1. User inputs just the URL + location
2. **Homepage scrape**: Navigate to the base URL, scroll, cycle carousels, extract banners
3. **Promo page navigation**: **Actually click** the promotions link like a real user (using Playwright locators), not href extraction + goto. Scans for links matching promo keywords (`promo`, `bonus`, `offer`, `deal`, `reward`, etc.) and clicks the first match.
4. **Promo page scrape**: After clicking and waiting for navigation, repeat scrolling + carousel cycling + extraction
5. Return results grouped by page: `{ homepage: [...], promotions: [...] }`

### Banner Detection Criteria
- `<img>` tags with wide aspect ratio (>2:1) and width >600px
- `<img>` tags with width >1000px
- `<img>` tags whose parent elements contain banner keywords: `banner`, `hero`, `slider`, `carousel`, `header`, `promo`
- Images inside carousel/slider containers (included even if hidden)
- Elements with `background-image` CSS styles (width >800px or aspect ratio >2:1)

## Tools / Scripts

| Script | Purpose |
|--------|---------|
| `execution/scrape_single_site.py` | Basic scraper (requests + BeautifulSoup). Fast, no JS support. |
| `execution/scrape_with_playwright.py` | **Primary scraper.** Playwright + stealth + Oxylabs proxy. Handles JS, lazy-loading, geo-bypass. |
| `execution/scrape_playwright_proxy.py` | Standalone Playwright with manual proxy input. |
| `execution/scrape_stealth.py` | Stealth variant with JSON output. |
| `backend/server.js` | Express API exposing `POST /api/scrape` (basic Cheerio). |
| `directives/scrape_banners_stealth.py` | Core Playwright logic — `scrape_website_banners_stealth()`. |
| `directives/scrape_banners.py` | Core requests logic — `scrape_website_banners()`. |

## Proxy Configuration
- **Oxylabs Web Unblocker** (`unblock.oxylabs.io:60000`) — bypasses Cloudflare, Akamai, and other bot protection
- Credentials stored in `.env` (root): `PROXY_HOST`, `PROXY_PORT`, `PROXY_USER`, `PROXY_PASS`, `PROXY_SCHEME`
- Country targeting via `x-oxylabs-geo-location` HTTP header (set automatically based on location selection)
- Requires `--ignore-certificate-errors` in Chromium args and `ignore_https_errors: True` in context (self-signed cert)
- Proxy is loaded automatically by `get_proxy_from_env()` in the stealth directive

## Outputs
- JSON array of banner objects with `src`, `alt`, `width`, `height`, `type`
- Intermediate scraped HTML stored in `.tmp/` if needed for debugging

## Edge Cases & Learnings
- **Windows cp1252 encoding**: Python `print()` crashes on emojis/unicode chars on Windows. Use ASCII-safe markers like `[+]`, `[-]`, `[*]` instead.
- Some sites block non-browser User-Agents; use a realistic UA string
- Relative URLs (e.g. `/images/banner.jpg`) must be resolved against the page origin
- Lazy-loaded images may use `data-src` or `data-lazy` attributes instead of `src` — check `data-src`, `data-lazy-src`, and `currentSrc`
- Sites with heavy JS rendering (SPAs) won't yield images via Cheerio alone; use the Playwright scraper instead
- **`networkidle` vs `domcontentloaded`**: Use `networkidle` for JS-heavy sites. Wrap in try/except since some sites never fully idle.
- **Scroll to load**: Scroll in 5 steps (20% increments) with 1-2s random delays to trigger lazy-loaded images and appear human-like.
- **Web Unblocker vs datacenter proxies**: Oxylabs Web Unblocker (`unblock.oxylabs.io`) handles Cloudflare/Akamai automatically. Datacenter proxies (`dc.oxylabs.io`) are cheaper but get blocked by aggressive bot protection. Web Unblocker successfully bypasses DraftKings (Akamai) — confirmed working.
- Timeout set to 45s for Playwright (vs 10s for requests) to allow JS rendering time
- **Carousel/slider images**: Inactive slides are hidden (`display:none`, `width:0`), so a visibility-only filter will miss them. Fix: detect carousel containers (`.slick`, `.swiper`, `.owl`, `.carousel`, etc.), click next-buttons to cycle all slides, and include hidden images inside carousel parents. Also check `data-original`, `srcset` as additional src fallbacks.
- **Click-based navigation vs URL extraction**: For multi-page scraping, **actually click** links using Playwright locators (`.click()`) instead of extracting hrefs and using `page.goto()`. This mimics real user behavior, triggers event handlers, respects navigation guards, and appears more natural to anti-bot systems. Use `page.evaluate()` to find matching links, then `page.locator().click()` with navigation wait.
