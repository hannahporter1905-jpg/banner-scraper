const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');
const axios = require('axios');
const { HttpsProxyAgent } = require('https-proxy-agent');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, '../frontend')));

// Store active scraping sessions
const sessions = new Map();

// Location mapping
const LOCATIONS = {
  1: 'US',
  2: 'UK',
  3: 'CA',
  4: 'AU',
  5: 'DE',
  6: 'FR',
  7: 'JP',
  8: 'BR',
  9: 'IN',
  10: 'SG'
};

/**
 * POST /api/scrape
 * Start a new scraping session
 * Body: { url, location (1-10), headless (true/false) }
 */
app.post('/api/scrape', async (req, res) => {
  const { url, location = 1, headless = true } = req.body;

  if (!url) {
    return res.status(400).json({ error: 'URL is required' });
  }

  // Validate URL
  try {
    new URL(url);
  } catch {
    return res.status(400).json({ error: 'Invalid URL format' });
  }

  // Validate location
  if (!LOCATIONS[location]) {
    return res.status(400).json({ error: 'Invalid location (must be 1-10)' });
  }

  const sessionId = Date.now().toString();
  const session = {
    id: sessionId,
    url,
    location: LOCATIONS[location],
    headless,
    status: 'running',
    progress: [],
    results: null,
    error: null,
    startTime: new Date()
  };

  sessions.set(sessionId, session);

  // Start Python scraper in background
  const pythonScript = path.join(__dirname, '../execution/scrape_api.py');
  const args = [
    pythonScript,
    '--url', url,
    '--location', location.toString(),
    '--headless', headless ? 'true' : 'false',
    '--json'
  ];

  console.log(`[${sessionId}] Starting scrape: ${url} (${LOCATIONS[location]})`);

  const pythonProcess = spawn('python', args, {
    cwd: path.join(__dirname, '..')
  });

  let outputBuffer = '';
  let errorBuffer = '';

  pythonProcess.stdout.on('data', (data) => {
    const output = data.toString();
    outputBuffer += output;

    // Parse progress updates (lines starting with [*], [+], [-])
    const lines = output.split('\n').filter(l => l.trim());
    lines.forEach(line => {
      if (line.match(/^\[[\*\+\-]\]/)) {
        session.progress.push({
          timestamp: new Date(),
          message: line
        });
      }
    });
  });

  pythonProcess.stderr.on('data', (data) => {
    errorBuffer += data.toString();
    console.error(`[${sessionId}] Error: ${data}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`[${sessionId}] Process closed with code ${code}`);

    if (code === 0) {
      try {
        // Find the JSON output (last occurrence of valid JSON object)
        const lines = outputBuffer.split('\n');
        let jsonStr = null;

        // Look for JSON starting from the end (most recent output)
        for (let i = lines.length - 1; i >= 0; i--) {
          const line = lines[i].trim();
          if (line.startsWith('{')) {
            // Try to parse from this line onwards
            const remainingLines = lines.slice(i).join('\n');
            try {
              const parsed = JSON.parse(remainingLines);
              if (parsed.homepage !== undefined) {
                jsonStr = remainingLines;
                break;
              }
            } catch (e) {
              continue;
            }
          }
        }

        if (jsonStr) {
          session.results = JSON.parse(jsonStr);
          session.status = 'completed';
          console.log(`[${sessionId}] Completed: ${session.results.homepage?.length || 0} homepage + ${session.results.promotions?.length || 0} promo banners`);
        } else {
          session.status = 'error';
          session.error = 'No valid JSON results found in output';
          console.error(`[${sessionId}] Output: ${outputBuffer.substring(0, 500)}`);
        }
      } catch (err) {
        session.status = 'error';
        session.error = 'Failed to parse results: ' + err.message;
        console.error(`[${sessionId}] Parse error:`, err);
      }
    } else {
      session.status = 'error';
      session.error = errorBuffer || `Python script exited with code ${code}`;
      console.error(`[${sessionId}] Failed with code ${code}`);
      console.error(`[${sessionId}] Error output: ${errorBuffer}`);
    }
  });

  // Return session ID immediately
  res.json({
    success: true,
    sessionId,
    message: 'Scraping started'
  });
});

/**
 * GET /api/scrape/:sessionId
 * Get status and results of a scraping session
 */
app.get('/api/scrape/:sessionId', (req, res) => {
  const session = sessions.get(req.params.sessionId);

  if (!session) {
    return res.status(404).json({ error: 'Session not found' });
  }

  res.json({
    id: session.id,
    url: session.url,
    location: session.location,
    status: session.status,
    progress: session.progress,
    results: session.results,
    error: session.error,
    duration: session.status === 'completed'
      ? new Date() - session.startTime
      : null
  });
});

/**
 * GET /api/locations
 * Get available location options
 */
app.get('/api/locations', (req, res) => {
  res.json(Object.entries(LOCATIONS).map(([id, code]) => ({
    id: parseInt(id),
    code,
    name: getLocationName(code)
  })));
});

function getLocationName(code) {
  const names = {
    'US': 'United States',
    'UK': 'United Kingdom',
    'CA': 'Canada',
    'AU': 'Australia',
    'DE': 'Germany',
    'FR': 'France',
    'JP': 'Japan',
    'BR': 'Brazil',
    'IN': 'India',
    'SG': 'Singapore'
  };
  return names[code] || code;
}

/**
 * GET /api/download
 * Proxy-download a banner image through the server (bypasses CORS + geo-restriction).
 * Query params: url (required), filename (optional, e.g. "PromoMob-Sun.jpg")
 *
 * Strategy: try direct fetch first (saves proxy credits).
 * If direct returns non-image content (e.g. geo-block HTML page) or errors,
 * retry via Oxylabs Web Unblocker.
 */
app.get('/api/download', async (req, res) => {
  const { url, filename } = req.query;
  if (!url) return res.status(400).json({ error: 'url param required' });

  const dlFilename = filename || 'banner.jpg';
  const fetchOpts = {
    responseType: 'arraybuffer',
    timeout: 30000,
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
      'Referer': new URL(url).origin,
    }
  };

  // Direct axios fetch (no proxy) — works for public CDN images
  async function fetchDirect() {
    return axios.get(url, fetchOpts);
  }

  // Proxy fetch via Python urllib — more reliable than Node.js https-proxy-agent for HTTPS
  // proxies like Oxylabs Web Unblocker (avoids TLS cert chain issues in Cloud Run).
  // Python urllib handles CONNECT tunneling and SSL verification correctly.
  function fetchViaProxy() {
    return new Promise((resolve, reject) => {
      const host = process.env.PROXY_HOST;
      const port = process.env.PROXY_PORT;
      const user = process.env.PROXY_USER;
      const pass = process.env.PROXY_PASS;
      const scheme = process.env.PROXY_SCHEME || 'https';
      if (!host || !user) { reject(new Error('No proxy configured')); return; }

      // Inline Python script: downloads image via Oxylabs proxy, outputs binary to stdout
      // and content-type header to first line of stderr.
      const pyScript = [
        'import sys, os, urllib.request, ssl, urllib.parse',
        'url = sys.argv[1]',
        'u = os.getenv("PROXY_USER", ""); p = os.getenv("PROXY_PASS", "")',
        'h = os.getenv("PROXY_HOST", ""); port = os.getenv("PROXY_PORT", "")',
        'sc = os.getenv("PROXY_SCHEME", "https")',
        'proxy_url = f"{sc}://{urllib.parse.quote(u)}:{urllib.parse.quote(p)}@{h}:{port}"',
        'ctx = ssl.create_default_context()',
        'ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE',
        'ph = urllib.request.ProxyHandler({"https": proxy_url, "http": proxy_url})',
        'opener = urllib.request.build_opener(ph, urllib.request.HTTPSHandler(context=ctx))',
        'req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Chrome/120.0.0.0", "Accept": "image/*,*/*"})',
        'with opener.open(req, timeout=30) as r:',
        '    sys.stderr.write(r.headers.get("Content-Type","image/jpeg") + "\\n")',
        '    sys.stdout.buffer.write(r.read())',
      ].join('\n');

      const python = spawn('python', ['-c', pyScript, url], {
        env: process.env,
        cwd: path.join(__dirname, '..'),
      });

      const chunks = [];
      let stderrOut = '';
      python.stdout.on('data', chunk => chunks.push(chunk));
      python.stderr.on('data', d => { stderrOut += d.toString(); });
      python.on('close', code => {
        if (code === 0 && chunks.length > 0) {
          const contentType = stderrOut.split('\n')[0].trim() || 'image/jpeg';
          resolve({ data: Buffer.concat(chunks), headers: { 'content-type': contentType } });
        } else {
          reject(new Error(stderrOut.trim() || 'Python proxy download failed'));
        }
      });
      python.on('error', reject);
    });
  }

  function isImageContent(contentType) {
    return contentType && contentType.startsWith('image/');
  }

  try {
    let response;
    try {
      response = await fetchDirect();
      const ct = response.headers['content-type'] || '';
      // If server returned HTML (geo-block page instead of image), retry via proxy
      if (!isImageContent(ct)) {
        console.log(`[download] Direct got ${ct}, retrying via proxy...`);
        response = await fetchViaProxy();
      }
    } catch (directErr) {
      console.log(`[download] Direct failed (${directErr.message}), retrying via proxy...`);
      response = await fetchViaProxy();
    }

    const finalContentType = response.headers['content-type'] || 'image/jpeg';
    res.setHeader('Content-Type', finalContentType);
    res.setHeader('Content-Disposition', `attachment; filename="${dlFilename}"`);
    res.setHeader('Cache-Control', 'no-store');
    res.send(Buffer.from(response.data));

  } catch (err) {
    console.error('[download] Failed:', err.message);
    res.status(502).json({ error: 'Failed to download image: ' + err.message });
  }
});

// Health check — update VERSION string on every deploy to confirm latest code is live
const VERSION = '2026-02-25-v11-smart-block-detect';

app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    version: VERSION,
    activeSessions: sessions.size,
    timestamp: new Date()
  });
});

// Serve frontend (use v2 by default)
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend/index-v2.html'));
});

app.listen(PORT, () => {
  console.log(`✓ Banner Scraper API running on http://localhost:${PORT}`);
  console.log(`✓ Frontend available at http://localhost:${PORT}`);
  console.log(`✓ Using Playwright stealth scraper with Oxylabs proxy`);
});
