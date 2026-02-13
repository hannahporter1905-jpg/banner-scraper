# Quick Start Guide

## 🚀 Get Up and Running in 3 Steps

### Step 1: Install Dependencies

**Backend:**
```bash
cd backend
npm install
```

**Python:**
```bash
pip install playwright python-dotenv
playwright install chromium
```

### Step 2: Configure Proxy

Make sure your `.env` file is set up in the project root:
```env
PORT=3000
PROXY_HOST=unblock.oxylabs.io
PROXY_PORT=60000
PROXY_USER=aqaq1_xZnFG
PROXY_PASS=a7i9q_zSAjmlSy3
PROXY_SCHEME=https
```

### Step 3: Start the Server

```bash
cd backend
node server-playwright.js
```

You should see:
```
✓ Banner Scraper API running on http://localhost:3000
✓ Frontend available at http://localhost:3000
✓ Using Playwright stealth scraper with Oxylabs proxy
```

### Step 4: Use the Web App

1. Open browser: http://localhost:3000
2. Enter a website URL (e.g., `https://www.draftkings.com`)
3. Select location (default: US)
4. Toggle headless mode if needed
5. Click "Start Scraping"
6. Watch real-time progress
7. View results grouped by page

## 🧪 Testing

**Test the Python scraper directly:**
```bash
python execution/scrape_api.py --url "https://www.draftkings.com" --location 1 --headless true --json
```

**Test the API:**
```bash
# Start scraping
curl -X POST http://localhost:3000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.draftkings.com", "location": 1, "headless": true}'

# Check results (use sessionId from above)
curl http://localhost:3000/api/scrape/YOUR_SESSION_ID
```

## 🐛 Troubleshooting

**"Cannot read properties of undefined":**
- Fixed! Update to latest commit
- Was caused by location mapping bug

**"Python not found":**
```bash
# Try python3 instead
which python
which python3
```

**Server won't start:**
```bash
cd backend
npm install express cors
```

**Proxy errors:**
- Check `.env` credentials
- Test proxy: `python execution/test_proxy.py`

## 📁 Project Structure

```
banner-scraper/
├── backend/
│   └── server-playwright.js   ← Start this
├── frontend/
│   ├── index-v2.html          ← Modern UI
│   ├── style-v2.css
│   └── script-v2.js
├── execution/
│   └── scrape_api.py          ← Called by backend
└── .env                       ← Proxy config
```

## 🎯 Example URLs to Test

- https://www.draftkings.com
- https://www.fanduel.com
- https://www.bet365.com
- https://www.betmgm.com

---

Need help? Check [README-WEBAPP.md](README-WEBAPP.md) for full documentation.
