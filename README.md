# 🎯 Banner Scraper

[![Playwright](https://img.shields.io/badge/Playwright-Enabled-green?logo=playwright)](https://playwright.dev/)
[![Oxylabs](https://img.shields.io/badge/Oxylabs-Proxy-blue)](https://oxylabs.io/)
[![Node.js](https://img.shields.io/badge/Node.js-Express-brightgreen?logo=node.js)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Intelligent banner image scraper with **Playwright stealth mode** and **Oxylabs proxy** integration. Multi-page scraping with geo-targeting support.

---

## ✨ Features

- 🎭 **Stealth Mode** - Anti-detection with Playwright + random user agents
- 🌍 **Geo-Targeting** - 10 country locations (US, UK, CA, AU, DE, FR, JP, BR, IN, SG)
- 📄 **Multi-Page Scraping** - Automatically scrapes homepage + promotions page
- 🎠 **Carousel Detection** - Cycles through sliders to capture hidden slides
- 🚀 **Real-Time Progress** - Live updates as scraping progresses
- 🎨 **Modern Web UI** - Clean, responsive interface with grouped results
- 🔄 **Click-Based Navigation** - Mimics real user behavior for better success rates
- 🛡️ **Proxy Integration** - Oxylabs Web Unblocker bypasses Cloudflare/Akamai

---

## 🏗️ Architecture

This project follows a **3-layer architecture** for maximum reliability:

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Directives (What to do)                           │
│  📋 Markdown SOPs in directives/ define goals & edge cases  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Orchestration (Decision making)                   │
│  🧠 AI reads directives, calls tools, handles errors        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Execution (Doing the work)                        │
│  ⚙️  Deterministic Python scripts in execution/             │
└─────────────────────────────────────────────────────────────┘
```

**Why this works:** AI is probabilistic, business logic is deterministic. Separating them ensures consistency.

---

## 🚀 Quick Start

### Prerequisites

- Node.js 14+ and npm
- Python 3.8+
- Oxylabs account ([Get credentials](https://oxylabs.io/))

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/Kels-69/banner-scraper.git
cd banner-scraper
```

**2. Install dependencies**

```bash
# Backend
cd backend
npm install

# Python scraper
cd ..
pip install playwright python-dotenv
playwright install chromium
```

**3. Configure proxy**

Create a `.env` file in the project root:

```env
PORT=3000

PROXY_HOST=unblock.oxylabs.io
PROXY_PORT=60000
PROXY_USER=your_username
PROXY_PASS=your_password
PROXY_SCHEME=https
```

**4. Start the server**

```bash
cd backend
node server-playwright.js
```

Open your browser: **http://localhost:3000**

---

## 📖 Usage

### Web Interface

1. **Enter URL** - Input the website to scrape (e.g., `https://www.draftkings.com`)
2. **Select Location** - Choose geo-location for proxy routing (default: US)
3. **Toggle Headless** - Enable to run browser invisibly, disable to watch
4. **Start Scraping** - Click and monitor real-time progress
5. **View Results** - Banners grouped by page (Homepage | Promotions)
6. **Download** - Save individual images or export all URLs

### Command Line

Test the Python scraper directly:

```bash
python execution/scrape_api.py \
  --url "https://www.draftkings.com" \
  --location 1 \
  --headless true \
  --json
```

### API Usage

**Start scraping:**

```bash
curl -X POST http://localhost:3000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.draftkings.com",
    "location": 1,
    "headless": true
  }'
```

**Check results:**

```bash
curl http://localhost:3000/api/scrape/SESSION_ID
```

---

## 🎯 How It Works

### Banner Detection

The scraper identifies banners using multiple criteria:

- ✅ Wide aspect ratio (>2:1) + width >600px
- ✅ Large width (>1000px)
- ✅ Parent elements with keywords: `banner`, `hero`, `slider`, `carousel`, `promo`
- ✅ CSS background images with wide dimensions
- ✅ Carousel/slider images (including hidden slides)

### Multi-Page Scraping Flow

```
1. Load homepage → Scrape banners
2. Find promotions link (keywords: promo, bonus, offer, deal, reward)
3. Actually CLICK the link (mimics real user)
4. Wait for page load (networkidle)
5. Scrape promotions page
6. Return results grouped by page
```

**Why click instead of goto?** Clicking triggers event handlers, respects navigation guards, and appears more natural to anti-bot systems.

### Proxy & Geo-Targeting

- Uses **Oxylabs Web Unblocker** to bypass Cloudflare, Akamai, and bot protection
- Sets `x-oxylabs-geo-location` header for country-specific content
- Handles self-signed certificates with `--ignore-certificate-errors`

---

## 📂 Project Structure

```
banner-scraper/
├── backend/
│   ├── server.js                  # Original Cheerio server
│   ├── server-playwright.js       # Playwright integration (main)
│   └── package.json
├── frontend/
│   ├── index-v2.html              # Modern UI
│   ├── style-v2.css               # Responsive styles
│   └── script-v2.js               # Real-time progress polling
├── execution/
│   ├── scrape_api.py              # CLI wrapper for API
│   ├── scrape_with_playwright.py  # Interactive scraper
│   └── test_proxy.py              # Proxy connectivity test
├── directives/
│   ├── scrape_banners_stealth.py  # Core Playwright logic
│   ├── scrape_banners.md          # SOP directive
│   └── __init__.py
├── .env                           # Proxy config (gitignored)
├── .env.example                   # Template for credentials
├── CLAUDE.md                      # 3-layer architecture guide
├── QUICKSTART.md                  # Fast setup guide
└── README.md                      # This file
```

---

## 🧪 Testing

### Test Sites

These sites work well for testing:

- **https://www.draftkings.com** - Has promotions page, good carousel examples
- **https://www.fanduel.com** - Multi-page with banners
- **https://www.bet365.com** - Geo-restricted content
- **https://httpbin.org/html** - Simple test page

### Troubleshooting

**"Cannot read properties of undefined"**
- ✅ Fixed in latest version (location mapping bug)
- Update: `git pull origin main`

**Proxy errors**
```bash
python execution/test_proxy.py
```

**Python not found**
```bash
which python   # or: which python3
```

**Server won't start**
```bash
cd backend
npm install express cors
```

---

## 🛠️ Development

### Run in Dev Mode

```bash
# Backend with auto-restart
cd backend
nodemon server-playwright.js

# Frontend is served automatically
```

### Modify Banner Detection

Edit `directives/scrape_banners_stealth.py`:

```python
def is_banner_image(img_data):
    # Add custom detection logic here
    pass
```

### Add New Locations

Update both files:
1. `execution/scrape_api.py` - location_map
2. `backend/server-playwright.js` - LOCATIONS

---

## 📊 API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/scrape` | Start scraping session |
| `GET` | `/api/scrape/:sessionId` | Get session status & results |
| `GET` | `/api/locations` | List available geo-locations |
| `GET` | `/api/health` | Server health check |

### Response Format

```json
{
  "homepage": [
    {
      "src": "https://example.com/banner.jpg",
      "alt": "Banner image",
      "width": "1920",
      "height": "600",
      "type": "Banner Image"
    }
  ],
  "promotions": [...]
}
```

---

## 🎓 Learn More

- **3-Layer Architecture** - See [CLAUDE.md](CLAUDE.md)
- **Quick Setup** - See [QUICKSTART.md](QUICKSTART.md)
- **Web App Guide** - See [README-WEBAPP.md](README-WEBAPP.md)
- **Directives** - See [directives/scrape_banners.md](directives/scrape_banners.md)

---

## 🤝 Contributing

Contributions welcome! Please follow the 3-layer architecture:

1. **Directives** - Update SOPs for new features
2. **Orchestration** - AI decision-making logic
3. **Execution** - Deterministic Python scripts

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🙏 Credits

Built with:
- [Playwright](https://playwright.dev/) - Browser automation
- [Express.js](https://expressjs.com/) - Web server
- [Oxylabs](https://oxylabs.io/) - Proxy service

**Co-Authored-By:** Claude Sonnet 4.5

---

## ⭐ Star This Repo

If you find this project helpful, please consider giving it a star! ⭐

---

**Questions?** Open an issue on [GitHub](https://github.com/Kels-69/banner-scraper/issues)
