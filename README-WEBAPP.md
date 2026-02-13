# Banner Scraper - Web Application

Modern web UI for the banner scraper with Playwright stealth mode and Oxylabs proxy integration.

## Features

✨ **Multi-Page Scraping** - Automatically scrapes homepage + promotions page
🌍 **Geo-Targeting** - 10 country locations (US, UK, CA, AU, DE, FR, JP, BR, IN, SG)
🕵️ **Stealth Mode** - Anti-detection with Playwright + random user agents
🚀 **Real-Time Progress** - Live updates as scraping progresses
📊 **Organized Results** - Banners grouped by page (homepage/promotions)
🎨 **Modern UI** - Clean, responsive design with dark mode support

## Quick Start

### 1. Install Dependencies

**Backend (Node.js):**
```bash
cd backend
npm install
```

**Python Scraper:**
```bash
pip install playwright python-dotenv
playwright install chromium
```

### 2. Configure Proxy

Create a `.env` file in the project root:
```env
PORT=3000

# Oxylabs Web Unblocker (required for geo-bypass)
PROXY_HOST=unblock.oxylabs.io
PROXY_PORT=60000
PROXY_USER=your_username
PROXY_PASS=your_password
PROXY_SCHEME=https
```

### 3. Start the Server

```bash
cd backend
node server-playwright.js
```

Server will start at: `http://localhost:3000`

### 4. Open the Web UI

Visit `http://localhost:3000` in your browser.

## Usage

1. **Enter URL** - Input the website URL to scrape
2. **Select Location** - Choose geo-location (affects proxy routing)
3. **Toggle Headless** - Enable/disable headless browser mode
4. **Start Scraping** - Click the button and watch real-time progress
5. **View Results** - See banners grouped by page with download options

## How It Works

### Architecture

```
Frontend (HTML/CSS/JS)
    ↓
Express API Server (Node.js)
    ↓
Python Scraper (Playwright + Stealth)
    ↓
Oxylabs Proxy → Target Website
```

### API Endpoints

**POST /api/scrape**
- Start a new scraping session
- Body: `{ url, location (1-10), headless (boolean) }`
- Returns: `{ sessionId }`

**GET /api/scrape/:sessionId**
- Check status and get results
- Returns: `{ status, progress, results, error }`

**GET /api/locations**
- List available geo-locations

**GET /api/health**
- Server health check

### Banner Detection

The scraper identifies banners using:
- Wide aspect ratio (>2:1) + width >600px
- Large width (>1000px)
- Parent elements with banner keywords (`banner`, `hero`, `slider`, `carousel`, `promo`)
- Background images with wide dimensions
- Carousel/slider images (including hidden slides)

## Project Structure

```
banner-scraper/
├── backend/
│   ├── server.js              # Original Cheerio-based server
│   ├── server-playwright.js   # New Playwright integration server
│   └── package.json
├── frontend/
│   ├── index-v2.html          # Modern UI
│   ├── style-v2.css           # Modern styles
│   └── script-v2.js           # Frontend logic
├── execution/
│   ├── scrape_api.py          # CLI wrapper for API
│   └── scrape_with_playwright.py  # Interactive scraper
├── directives/
│   ├── scrape_banners_stealth.py  # Core Playwright logic
│   └── scrape_banners.md      # SOP directive
├── .env                       # Proxy credentials (gitignored)
└── README-WEBAPP.md           # This file
```

## Development

### Run in Development Mode

**Backend:**
```bash
cd backend
nodemon server-playwright.js
```

**Frontend:**
Served automatically by Express at `http://localhost:3000`

### Testing the Python Scraper Directly

```bash
python execution/scrape_api.py --url "https://example.com" --location 1 --headless true --json
```

## Troubleshooting

**"Module not found" error:**
```bash
cd backend
npm install express cors
```

**Python import errors:**
```bash
pip install playwright python-dotenv
playwright install chromium
```

**Proxy connection fails:**
- Check `.env` credentials
- Verify Oxylabs account is active
- Test with: `python execution/test_proxy.py`

**No banners found:**
- Site may block automated scraping (check browser console)
- Try different location
- Disable headless mode to see what's happening

## Credits

Built with:
- [Playwright](https://playwright.dev/) - Browser automation
- [Express.js](https://expressjs.com/) - Web server
- [Oxylabs](https://oxylabs.io/) - Proxy service
- 3-Layer Architecture (Directives → Orchestration → Execution)

---

Co-Authored-By: Claude Sonnet 4.5
