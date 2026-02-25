// API URL configuration
// For split deployment: Set BACKEND_URL to your backend server
// For same-server deployment: Leave as window.location.origin
const BACKEND_URL = typeof window.BACKEND_URL !== 'undefined'
  ? window.BACKEND_URL
  : window.location.origin;
const API_URL = BACKEND_URL + '/api';

// DOM Elements
const urlInput = document.getElementById('urlInput');
const locationSelect = document.getElementById('locationSelect');
const headlessToggle = document.getElementById('headlessToggle');
const startBtn = document.getElementById('startBtn');

const progressSection = document.getElementById('progressSection');
const statusBadge = document.getElementById('statusBadge');
const progressLog = document.getElementById('progressLog');
const progressFill = document.getElementById('progressFill');

const resultsSection = document.getElementById('resultsSection');
const resultCount = document.getElementById('resultCount');
const downloadAllBtn = document.getElementById('downloadAllBtn');
const homepageSection = document.getElementById('homepageSection');
const homepageGrid = document.getElementById('homepageGrid');
const promotionsSection = document.getElementById('promotionsSection');
const promotionsGrid = document.getElementById('promotionsGrid');
const emptyState = document.getElementById('emptyState');

const errorSection = document.getElementById('errorSection');
const errorMessage = document.getElementById('errorMessage');

let currentSessionId = null;
let pollInterval = null;
let allBanners = [];

// Event Listeners
startBtn.addEventListener('click', startScraping);
urlInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') startScraping();
});
downloadAllBtn.addEventListener('click', downloadAllUrls);

// Update toggle label text to reflect current browser mode
const toggleText = document.querySelector('.toggle-text');
headlessToggle.addEventListener('change', () => {
    toggleText.textContent = headlessToggle.checked ? 'Headless' : 'Visible';
});

async function startScraping() {
    const url = urlInput.value.trim();
    const location = parseInt(locationSelect.value);
    const headless = headlessToggle.checked;

    console.log('Starting scrape:', { url, location, headless });

    // Reset UI
    hideAllSections();
    clearResults();

    // Validate URL
    if (!url) {
        showError('Please enter a website URL');
        return;
    }

    try {
        new URL(url);
    } catch {
        showError('Please enter a valid URL (include http:// or https://)');
        return;
    }

    // Disable button
    startBtn.disabled = true;
    startBtn.textContent = 'Starting...';

    try {
        console.log('Sending POST request to:', `${API_URL}/scrape`);
        // Start scraping session
        const response = await fetch(`${API_URL}/scrape`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, location, headless })
        });

        console.log('POST response status:', response.status, response.ok);
        const data = await response.json();
        console.log('POST response data:', data);

        if (!response.ok) {
            throw new Error(data.error || 'Failed to start scraping');
        }

        currentSessionId = data.sessionId;
        console.log(`Session started: ${currentSessionId}`);

        // Show progress section
        progressSection.classList.remove('hidden');
        statusBadge.textContent = 'Running...';
        statusBadge.className = 'status-badge running';
        progressFill.style.width = '30%';

        // Start polling for updates
        pollSession();

    } catch (error) {
        console.error('Start scraping error:', error);
        console.error('Error stack:', error.stack);
        showError(error.message);
        resetButton();
    }
}

function pollSession() {
    if (!currentSessionId) return;

    // Poll every 2 seconds
    pollInterval = setInterval(async () => {
        try {
            console.log(`Polling session: ${currentSessionId}`);
            const response = await fetch(`${API_URL}/scrape/${currentSessionId}`);
            console.log('Response status:', response.status, response.ok);

            const data = await response.json();
            console.log('Received data:', data);

            // Update progress log
            console.log('Progress items:', data.progress);
            updateProgressLog(data.progress);

            // Check status
            if (data.status === 'completed') {
                clearInterval(pollInterval);
                console.log('Scrape completed, calling handleCompletion');
                handleCompletion(data);
            } else if (data.status === 'error') {
                clearInterval(pollInterval);
                console.log('Scrape failed:', data.error);
                handleError(data.error);
            } else {
                // Still running
                console.log('Still running...');
                progressFill.style.width = '60%';
            }

        } catch (error) {
            console.error('Polling error:', error);
            console.error('Error stack:', error.stack);
            clearInterval(pollInterval);
            showError('Polling failed: ' + error.message);
            resetButton();
        }
    }, 2000);
}

function updateProgressLog(progressItems) {
    if (!progressItems || progressItems.length === 0) return;

    // Only add new items
    const currentCount = progressLog.children.length;
    const newItems = progressItems.slice(currentCount);

    newItems.forEach(item => {
        const div = document.createElement('div');
        div.className = 'progress-log-item';
        div.textContent = item.message;
        progressLog.appendChild(div);
    });

    // Auto-scroll to bottom
    progressLog.scrollTop = progressLog.scrollHeight;
}

function handleCompletion(data) {
    console.log('Scraping completed:', data);
    console.log('Results object:', data.results);
    console.log('Results type:', typeof data.results);

    progressFill.style.width = '100%';
    statusBadge.textContent = 'Completed';
    statusBadge.className = 'status-badge completed';

    // Display results
    try {
        displayResults(data.results);
    } catch (error) {
        console.error('Error displaying results:', error);
        console.error('Error stack:', error.stack);
        showError('Failed to display results: ' + error.message);
    }

    resetButton();
}

function handleError(error) {
    console.error('Scraping failed:', error);

    statusBadge.textContent = 'Failed';
    statusBadge.className = 'status-badge error';

    showError(error);
    resetButton();
}

function displayResults(results) {
    console.log('displayResults called with:', results);
    console.log('results type:', typeof results);

    if (!results) {
        console.error('No results provided');
        showError('No results returned from scraper');
        return;
    }

    console.log('results.homepage:', results.homepage);
    console.log('results.promotions:', results.promotions);

    const homepageBanners = results.homepage || [];
    const promotionsBanners = results.promotions || [];
    console.log('homepageBanners:', homepageBanners, 'length:', homepageBanners.length);
    console.log('promotionsBanners:', promotionsBanners, 'length:', promotionsBanners.length);

    allBanners = [...homepageBanners, ...promotionsBanners];
    console.log('allBanners:', allBanners, 'length:', allBanners.length);

    const totalCount = allBanners.length;

    if (totalCount === 0) {
        resultsSection.classList.remove('hidden');
        emptyState.classList.remove('hidden');
        homepageSection.classList.add('hidden');
        promotionsSection.classList.add('hidden');
        return;
    }

    // Show results section
    resultsSection.classList.remove('hidden');
    emptyState.classList.add('hidden');
    resultCount.textContent = `${totalCount} banner${totalCount === 1 ? '' : 's'} found`;

    // Display homepage banners
    if (homepageBanners.length > 0) {
        homepageSection.classList.remove('hidden');
        homepageGrid.innerHTML = homepageBanners.map((banner, idx) =>
            createBannerCard(banner, `homepage-${idx}`)
        ).join('');
    } else {
        homepageSection.classList.add('hidden');
    }

    // Display promotions banners
    if (promotionsBanners.length > 0) {
        promotionsSection.classList.remove('hidden');
        promotionsGrid.innerHTML = promotionsBanners.map((banner, idx) =>
            createBannerCard(banner, `promo-${idx}`)
        ).join('');
    } else {
        promotionsSection.classList.add('hidden');
    }
}

/**
 * Extract the human-readable filename from a banner URL.
 * e.g. ".../PromoMob-Sun.jpg" → "PromoMob-Sun"
 *      ".../eyJf...Q==/ND_HP_Desktop11_1.jpg" → "ND_HP_Desktop11_1"
 */
function getImageName(src) {
    try {
        const pathname = new URL(src).pathname;
        const raw = pathname.split('/').pop().split('?')[0]; // last path segment, no query
        return raw.replace(/\.[^.]+$/, '') || 'banner';      // strip extension
    } catch {
        return 'banner';
    }
}

function createBannerCard(banner, id) {
    const imgName = getImageName(banner.src);
    // Preserve the original extension for the downloaded file
    const extMatch = banner.src.match(/\.(jpg|jpeg|webp|png|gif|avif|svg)(\?|$)/i);
    const ext = extMatch ? extMatch[1].toLowerCase() : 'jpg';
    const dlFilename = `${imgName}.${ext}`;
    const downloadUrl = `${API_URL}/download?url=${encodeURIComponent(banner.src)}&filename=${encodeURIComponent(dlFilename)}`;

    return `
        <div class="banner-card" id="${id}">
            <img
                src="${banner.src}"
                alt="${banner.alt || imgName}"
                onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22400%22 height=%22200%22%3E%3Crect fill=%22%23ddd%22 width=%22400%22 height=%22200%22/%3E%3Ctext fill=%22%23999%22 x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22%3EImage Load Error%3C/text%3E%3C/svg%3E'"
            >
            <div class="banner-info">
                <h4 title="${banner.src}">${imgName}</h4>
                <p class="banner-url">${banner.src}</p>
                <a href="${downloadUrl}" class="banner-download" download="${dlFilename}">
                    Download Image
                </a>
            </div>
        </div>
    `;
}

function downloadAllUrls() {
    if (allBanners.length === 0) return;

    const urls = allBanners.map(b => b.src).join('\n');
    const blob = new Blob([urls], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `banner-urls-${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function showError(message) {
    errorSection.classList.remove('hidden');
    errorMessage.textContent = message;
}

function hideAllSections() {
    progressSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
    errorSection.classList.add('hidden');
}

function clearResults() {
    progressLog.innerHTML = '';
    progressFill.style.width = '0%';
    homepageGrid.innerHTML = '';
    promotionsGrid.innerHTML = '';
    allBanners = [];
}

function resetButton() {
    startBtn.disabled = false;
    startBtn.innerHTML = '<span class="btn-icon">🚀</span> Start Scraping';
}
