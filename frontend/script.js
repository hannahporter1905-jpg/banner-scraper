const API_URL = 'http://localhost:3000/api/scrape';

const urlInput = document.getElementById('urlInput');
const searchBtn = document.getElementById('searchBtn');
const errorDiv = document.getElementById('error');
const loadingDiv = document.getElementById('loading');
const resultsDiv = document.getElementById('results');

searchBtn.addEventListener('click', findBanners);
urlInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') findBanners();
});

async function findBanners() {
    const url = urlInput.value.trim();
    
    // Reset UI
    errorDiv.classList.remove('show');
    errorDiv.textContent = '';
    resultsDiv.innerHTML = '';
    
    if (!url) {
        showError('Please enter a URL');
        return;
    }
    
    // Validate URL
    try {
        new URL(url);
    } catch {
        showError('Please enter a valid URL');
        return;
    }
    
    // Show loading
    loadingDiv.classList.add('show');
    searchBtn.disabled = true;
    
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to scrape website');
        }
        
        displayResults(data.banners);
        
    } catch (error) {
        showError(error.message);
    } finally {
        loadingDiv.classList.remove('show');
        searchBtn.disabled = false;
    }
}

function showError(message) {
    errorDiv.textContent = message;
    errorDiv.classList.add('show');
}

function displayResults(banners) {
    if (banners.length === 0) {
        resultsDiv.innerHTML = '<div class="banner-card"><div class="banner-info"><p>No banner images found on this website.</p></div></div>';
        return;
    }
    
    resultsDiv.innerHTML = banners.map((banner, index) => `
        <div class="banner-card">
            <img src="${banner.src}" alt="${banner.alt}" onerror="this.src='https://via.placeholder.com/1200x400?text=Image+Load+Error'">
            <div class="banner-info">
                <h3>${banner.type}</h3>
                <p>Dimensions: ${banner.width} × ${banner.height}</p>
                <a href="${banner.src}" target="_blank" download class="download-btn">
                    Download Image
                </a>
            </div>
        </div>
    `).join('');
}