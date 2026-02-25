from playwright.sync_api import sync_playwright
from urllib.parse import urljoin, urlparse
import time
import random
import os
from dotenv import load_dotenv

# playwright-stealth works on Python <=3.11 (pkg_resources dependency).
# On Python 3.12+ locally it may fail — inline JS stealth below always runs regardless.
try:
    from playwright_stealth import stealth_sync
    _STEALTH_PKG = True
except Exception:
    _STEALTH_PKG = False

# Comprehensive inline stealth JS — patches the fingerprint vectors casino sites check.
# Runs always, regardless of whether the playwright-stealth package is available.
_STEALTH_JS = """
// 1. Remove webdriver flag
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 2. Realistic plugins (Chrome)
Object.defineProperty(navigator, 'plugins', { get: () => {
    const arr = [
        { name: 'Chrome PDF Plugin',  filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
        { name: 'Chrome PDF Viewer',  filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
        { name: 'Native Client',      filename: 'internal-nacl-plugin', description: '' }
    ];
    arr.item = i => arr[i]; arr.namedItem = n => arr.find(p => p.name === n);
    return arr;
}});

// 3. Languages
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });

// 4. Chrome runtime API (missing in headless)
window.chrome = {
    runtime: {
        onMessage: { addListener: () => {} },
        connect: () => ({ onMessage: { addListener: () => {} }, onDisconnect: { addListener: () => {} } })
    },
    loadTimes: () => ({}),
    csi: () => ({})
};

// 5. Permissions API (headless returns denied for notifications)
try {
    const origQuery = window.navigator.permissions.query.bind(navigator.permissions);
    window.navigator.permissions.query = (p) =>
        p.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : origQuery(p);
} catch(_) {}

// 6. WebGL vendor/renderer (headless shows SwiftShader — a known bot signal)
try {
    const handler = {
        apply(target, ctx, args) {
            if (args[0] === 37445) return 'Intel Inc.';
            if (args[0] === 37446) return 'Intel Iris OpenGL Engine';
            return Reflect.apply(target, ctx, args);
        }
    };
    WebGLRenderingContext.prototype.getParameter =
        new Proxy(WebGLRenderingContext.prototype.getParameter, handler);
    WebGL2RenderingContext.prototype.getParameter =
        new Proxy(WebGL2RenderingContext.prototype.getParameter, handler);
} catch(_) {}

// 7. Outer dimensions (headless defaults differ from real browser)
Object.defineProperty(window, 'outerWidth',  { get: () => window.innerWidth });
Object.defineProperty(window, 'outerHeight', { get: () => window.innerHeight + 85 });

// 8. Screen color/pixel depth
Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
Object.defineProperty(screen, 'pixelDepth',  { get: () => 24 });
"""

# Load proxy config from .env at project root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


def get_proxy_from_env(country='US'):
    """Build proxy config from .env variables. Supports country override.

    Oxylabs Web Unblocker geo-targeting requires the country to be encoded
    in the username: e.g. myuser-country-CA. The x-oxylabs-geo-location header
    is kept as a secondary signal.
    """
    host = os.getenv('PROXY_HOST')
    port = os.getenv('PROXY_PORT')
    user = os.getenv('PROXY_USER', '')
    password = os.getenv('PROXY_PASS', '')
    scheme = os.getenv('PROXY_SCHEME', 'http')

    if not host or not port:
        return None

    # Oxylabs Web Unblocker: country is targeted via x-oxylabs-geo-location header,
    # NOT via username suffix. Plain username required or proxy returns 401.
    return {
        'server': f'{scheme}://{host}:{port}',
        'username': user,
        'password': password,
        'country': country,
    }

def is_page_blocked(page, target_url=None):
    """
    Detect geo-restriction / access-denied pages before scraping them.

    Checks:
    1. Page title and body text for known block phrases
    2. ISP redirect: if the loaded domain differs from the target domain, the ISP
       intercepted the request and served its own block page (e.g. PAGCOR in PH).

    Returns True if blocked, False if the page looks like the real site.
    """
    block_phrases = [
        # Generic geo-block language
        'restricted region', 'not available in your region',
        'not available in your country', 'not available in your area',
        'geographic restriction', 'geo restriction',
        'access denied', 'access is not available',
        'blocked in your country', 'country is not supported',
        'not accessible from your location', 'region not supported',
        'this site is not available', 'unavailable in your country',
        'this content is not available', 'service not available in your region',
        # ISP / government block pages (e.g. Philippines PAGCOR, CICC)
        'prohibited site', 'this site is blocked', 'site has been blocked',
        'access to this site', 'internet access to this',
        'blocked by', 'access is blocked', 'page is blocked',
        'access restricted', 'restricted access',
        'this page is restricted', 'site is restricted',
        # Regulator / ISP identifiers that only appear on block pages
        'pagcor', 'cicc.gov', 'sbmd',
        # Common block page titles
        'forbidden', 'access forbidden',
        # Cloudflare / CAPTCHA walls
        'just a moment', 'checking your browser', 'please wait',
        'enable javascript and cookies',
        # Age / jurisdiction gates
        'not available in your jurisdiction', 'not licensed in your region',
        'your country is not', 'unfortunately.*not available',
    ]
    try:
        title = (page.title() or '').lower()
        body_text = page.evaluate(
            "() => (document.body && document.body.innerText || '').toLowerCase().slice(0, 3000)"
        )
        combined = title + ' ' + body_text
        if any(phrase in combined for phrase in block_phrases):
            return True

        # ISP redirect detection: loaded domain ≠ target domain
        # (e.g., navigating to stake.com but ending up on blocked.sbmd.cicc.gov.ph)
        if target_url:
            target_domain = urlparse(target_url).netloc.lower().lstrip('www.')
            loaded_domain = urlparse(page.url).netloc.lower().lstrip('www.')
            if target_domain and loaded_domain and loaded_domain != target_domain:
                print(f"[!] ISP redirect: {target_domain} → {loaded_domain}")
                return True

        return False
    except Exception:
        return False


def get_random_user_agent():
    """Return a random realistic user agent"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    ]
    return random.choice(user_agents)

def is_banner_image(img_data, in_carousel=False):
    """
    Detect promotional banner images. Two-stage check:
    1. Exclude known non-banner patterns (logos, icons, badges, nav elements)
       — always applied, even for carousel images
    2. Include by aspect ratio, size, or promotional keywords
       — relaxed thresholds when in_carousel=True

    in_carousel=True relaxes Stage 2 size requirements (promo cards can be
    smaller than full-width hero banners) but still requires minimum width and
    aspect ratio to exclude square game tiles (380x380 etc.).
    """
    width = img_data.get('width', 0)
    height = img_data.get('height', 0)
    src = img_data.get('src', '').lower()
    alt = img_data.get('alt', '').lower()
    classes = img_data.get('class', '').lower()
    parent_classes = img_data.get('parent_class', '').lower()

    all_text = f"{src} {alt} {classes} {parent_classes}"

    # Reject broken image references: if dimensions are both zero AND the src URL
    # has no image file extension, it's a placeholder or a failed lazy-load reference.
    _IMG_EXTS = ('.jpg', '.jpeg', '.webp', '.png', '.gif', '.avif', '.svg')
    if width == 0 and height == 0 and not any(ext in src for ext in _IMG_EXTS):
        return False

    # --- STAGE 1: Exclude non-banner images (always runs, even for carousel) ---
    # Logos, icons, flags, badges, compliance images
    exclude_keywords = [
        'logo', 'icon', 'badge', 'seal', 'flag', 'avatar', 'thumbnail',
        'favicon', 'sprite', 'rating', 'star', 'review', 'award',
        'certificate', 'certified', 'responsible', 'therapy', 'aware',
        'gambling-therapy', 'begambleaware', 'gamcare', 'gamstop',
        'payment', 'visa', 'mastercard', 'paypal', 'trustly', 'skrill',
        'lang', 'language', 'country-flag', 'social', 'twitter', 'facebook',
        # Game tiles (alt text often ends in "game tile")
        'game tile',
        # Mini-game section thumbnails (game category images, not promo banners)
        'mini-game',
        # Popup / modal overlay images
        'pop-up', 'popup', 'modal',
        # Game list / game section background images
        'game-list', 'game_list',
    ]
    # Exclude structural/nav parent containers
    exclude_parents = ['nav', 'navbar', 'footer', 'header-logo', 'site-logo']

    if any(kw in all_text for kw in exclude_keywords):
        return False
    if any(kw in parent_classes for kw in exclude_parents):
        return False
    # Skip SVGs that are clearly logos (small, square-ish, in header)
    if src.endswith('.svg') and (width < 600 or (width > 0 and height > 0 and width / height < 2)):
        return False

    # --- STAGE 2: Include by positive signals ---
    banner_keywords = [
        'banner', 'hero', 'slider', 'carousel', 'slideshow',
        'jumbotron', 'masthead', 'cover', 'featured',
        'promo', 'promotion', 'landing', 'splash', 'billboard',
        'spotlight', 'showcase', 'highlight', 'campaign', 'offer',
        'bonus', 'deposit', 'welcome', 'free-spin',
    ]

    if in_carousel:
        # In the carousel branch, only check keywords against src/alt/own-class.
        # parent_classes always contain "carousel"/"slider" (that's how in_carousel was
        # detected), so using all_text would falsely match those same words against
        # banner_keywords and admit every game tile in every carousel.
        content_text = f"{src} {alt} {classes}"

        # Size/ratio check: excludes square game tiles (380×380 → ratio 1.0, width 380)
        if width > 0 and height > 0:
            aspect_ratio = width / height
            if aspect_ratio > 1.3 and width > 600:
                return True
        if width > 1000:
            return True
        # Promotional keyword in the image's own src/alt/class (not container classes)
        for keyword in banner_keywords:
            if keyword in content_text:
                return True
        return False

    # Standard aspect ratio: genuinely wide promotional images (not logos)
    if width > 0 and height > 0:
        aspect_ratio = width / height
        if aspect_ratio > 2.5 and width > 600:      # ultra-wide banners (5:2+)
            return True
        if aspect_ratio > 1.8 and width > 900:      # widescreen at full-column width
            return True
        if aspect_ratio > 1.5 and width > 950:      # promo cards (3:2, 16:10, etc.)
            return True                              # width > 950 to skip article thumbnails

    # Very large images (full-width hero banners regardless of ratio)
    if width > 1200:
        return True

    # Promotional keywords in src/alt/class
    for keyword in banner_keywords:
        if keyword in all_text:
            return True

    return False

def scrape_website_banners_stealth(url, headless=True, location='US', proxy=None, use_env_proxy=True):
    """
    Advanced scraper with stealth mode and better detection evasion.

    Args:
        url: The website URL to scrape
        headless: Run browser in headless mode (True) or visible mode (False)
        location: Geolocation code (US, UK, DE, FR, JP, AU, CA, BR, IN, SG)
        proxy: Optional proxy dict (format: {'server': ..., 'username': ..., 'password': ...})
        use_env_proxy: If True and no proxy passed, load Oxylabs proxy from .env

    Returns:
        list: List of dictionaries containing banner information
    """
    banners = []
    
    # Geolocation presets
    geolocations = {
        'US': {'latitude': 37.7749, 'longitude': -122.4194, 'locale': 'en-US', 'timezone': 'America/Los_Angeles'},
        'UK': {'latitude': 51.5074, 'longitude': -0.1278, 'locale': 'en-GB', 'timezone': 'Europe/London'},
        'DE': {'latitude': 52.5200, 'longitude': 13.4050, 'locale': 'de-DE', 'timezone': 'Europe/Berlin'},
        'FR': {'latitude': 48.8566, 'longitude': 2.3522, 'locale': 'fr-FR', 'timezone': 'Europe/Paris'},
        'JP': {'latitude': 35.6762, 'longitude': 139.6503, 'locale': 'ja-JP', 'timezone': 'Asia/Tokyo'},
        'AU': {'latitude': -33.8688, 'longitude': 151.2093, 'locale': 'en-AU', 'timezone': 'Australia/Sydney'},
        'CA': {'latitude': 43.6532, 'longitude': -79.3832, 'locale': 'en-CA', 'timezone': 'America/Toronto'},
        'BR': {'latitude': -23.5505, 'longitude': -46.6333, 'locale': 'pt-BR', 'timezone': 'America/Sao_Paulo'},
        'IN': {'latitude': 28.6139, 'longitude': 77.2090, 'locale': 'en-IN', 'timezone': 'Asia/Kolkata'},
        'SG': {'latitude': 1.3521, 'longitude': 103.8198, 'locale': 'en-SG', 'timezone': 'Asia/Singapore'},
    }
    
    geo = geolocations.get(location.upper(), geolocations['US'])
    
    print(f"[*] Launching stealth browser (location={location})...")
    
    with sync_playwright() as p:
        try:
            # Launch browser with specific args to avoid detection
            browser = p.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--ignore-certificate-errors',
                ]
            )
            
            # Build context options
            extra_headers = {
                'Accept-Language': f"{geo['locale']},en;q=0.9",
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }

            context_options = {
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': get_random_user_agent(),
                'locale': geo['locale'],
                'timezone_id': geo['timezone'],
                'geolocation': {'latitude': geo['latitude'], 'longitude': geo['longitude']},
                'permissions': ['geolocation'],
                'ignore_https_errors': True,
            }

            # Add proxy: explicit proxy > env proxy > direct connection
            proxy_country = None
            if proxy:
                proxy_cfg = proxy if isinstance(proxy, dict) else {'server': proxy}
                proxy_country = proxy_cfg.pop('country', None)
                context_options['proxy'] = proxy_cfg
            elif use_env_proxy:
                env_proxy = get_proxy_from_env(country=location)
                if env_proxy:
                    proxy_country = env_proxy.pop('country', None)
                    context_options['proxy'] = env_proxy
                    print(f"   Using Oxylabs Web Unblocker ({proxy_country or location})")

            # Set geo-location header for Web Unblocker country targeting
            if proxy_country:
                extra_headers['x-oxylabs-geo-location'] = proxy_country

            context_options['extra_http_headers'] = extra_headers
            
            context = browser.new_context(**context_options)
            
            # Add stealth scripts to avoid detection
            context.add_init_script("""
                // Overwrite the `navigator.webdriver` property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Overwrite the `plugins` property
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Overwrite the `languages` property
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                // Remove automation indicators
                window.chrome = {
                    runtime: {}
                };
            """)
            
            page = context.new_page()
            
            print(f"[*] Navigating to {url}...")

            # Random delay before navigation (human-like behavior)
            time.sleep(random.uniform(0.5, 1.5))

            # Navigate and wait for network to settle (catches JS-rendered content)
            try:
                page.goto(url, wait_until='networkidle', timeout=45000)
            except Exception:
                # Fallback: some sites never fully idle, just continue
                print("    (network didn't fully idle, continuing...)")

            # Wait for page to settle after initial load
            print("[*] Waiting for content to render...")
            time.sleep(random.uniform(3, 5))

            # Scroll in steps to trigger lazy-loaded images (human-like)
            print("[*] Scrolling to load all images...")
            for i in range(5):
                scroll_pct = (i + 1) * 20  # 20%, 40%, 60%, 80%, 100%
                page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {scroll_pct / 100})")
                time.sleep(random.uniform(1, 2))

            # Scroll back to top and let any final images load
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(2)

            # Click through carousels/sliders to load all slides
            print("[*] Cycling through carousels...")
            page.evaluate("""
                () => {
                    // Common carousel next-button selectors
                    const nextSelectors = [
                        '.slick-next', '.swiper-button-next', '.carousel-control-next',
                        '.owl-next', '[data-slide="next"]', '.next-arrow', '.arrow-right',
                        '.slider-next', '.bx-next', '.flex-next', '.glide__arrow--right',
                        'button[aria-label="Next"]', 'button[aria-label="next"]',
                        '.splide__arrow--next', '.flickity-prev-next-button.next'
                    ];
                    for (const sel of nextSelectors) {
                        const btn = document.querySelector(sel);
                        if (btn) {
                            // Click multiple times to cycle through all slides
                            for (let i = 0; i < 10; i++) {
                                btn.click();
                            }
                            break;
                        }
                    }
                }
            """)
            time.sleep(3)

            print("[*] Extracting images...")

            # Extract ALL images — including hidden carousel slides
            images_data = page.evaluate("""
                () => {
                    const images = [];
                    const imgElements = document.querySelectorAll('img');

                    imgElements.forEach(img => {
                        const rect = img.getBoundingClientRect();
                        const computedStyle = window.getComputedStyle(img);
                        const parent = img.parentElement;

                        // Get all parent classes up to 3 levels
                        let parentClasses = '';
                        let currentParent = parent;
                        for (let i = 0; i < 3 && currentParent; i++) {
                            parentClasses += ' ' + (currentParent.className || '');
                            currentParent = currentParent.parentElement;
                        }

                        // Grab src from multiple possible attributes
                        const src = img.currentSrc
                            || img.src
                            || img.getAttribute('data-src')
                            || img.getAttribute('data-lazy-src')
                            || img.getAttribute('data-original')
                            || '';

                        // Also check srcset for high-res version
                        const srcset = img.getAttribute('srcset') || '';
                        const srcsetUrl = srcset ? srcset.split(',')[0].trim().split(' ')[0] : '';

                        const isVisible = computedStyle.display !== 'none'
                            && computedStyle.visibility !== 'hidden'
                            && rect.width > 0 && rect.height > 0;

                        // Check if this image sits inside a carousel/slider container
                        const inCarousel = parentClasses.match(
                            /slider|carousel|swiper|slick|owl|splide|glide|flickity|banner|promo/i
                        ) || (img.className || '').match(
                            /slider|carousel|swiper|slick|owl|splide|glide|flickity|banner|promo/i
                        );

                        images.push({
                            src: src || srcsetUrl,
                            alt: img.alt || '',
                            width: Math.max(rect.width, img.naturalWidth, img.width) || 0,
                            height: Math.max(rect.height, img.naturalHeight, img.height) || 0,
                            class: img.className || '',
                            parent_class: parentClasses.trim(),
                            visible: isVisible,
                            in_carousel: !!inCarousel
                        });
                    });

                    return images;
                }
            """)
            
            print(f"[*] Found {len(images_data)} total images")
            
            # Filter for banner images (include hidden carousel slides)
            banner_count = 0
            for img_data in images_data:
                if not img_data['src'] or img_data['src'].startswith('data:'):
                    continue

                # Include if visible OR if it's inside a carousel container
                if not img_data['visible'] and not img_data.get('in_carousel'):
                    continue

                if is_banner_image(img_data, in_carousel=img_data.get('in_carousel', False)):
                    banners.append({
                        'src': img_data['src'],
                        'alt': img_data['alt'] or 'Banner image',
                        'width': int(img_data['width']),
                        'height': int(img_data['height']),
                        'type': 'Carousel Banner' if img_data.get('in_carousel') else 'Banner Image'
                    })
                    banner_count += 1
            
            print(f"[+] Identified {banner_count} banner images from <img> tags")
            
            # Extract CSS background images
            print("[*] Checking for background images...")
            bg_images = page.evaluate("""
                () => {
                    const bgImages = [];
                    const elements = document.querySelectorAll('*');
                    
                    elements.forEach(el => {
                        const style = window.getComputedStyle(el);
                        const bgImage = style.backgroundImage;
                        
                        if (bgImage && bgImage !== 'none' && !bgImage.includes('gradient')) {
                            const urlMatch = bgImage.match(/url\\(["']?([^"']*)["']?\\)/);
                            if (urlMatch && urlMatch[1] && !urlMatch[1].startsWith('data:')) {
                                const rect = el.getBoundingClientRect();
                                const className = el.className || '';
                                const id = el.id || '';
                                
                                bgImages.push({
                                    src: urlMatch[1],
                                    width: rect.width,
                                    height: rect.height,
                                    class: className,
                                    id: id,
                                    visible: style.display !== 'none' && rect.width > 0 && rect.height > 0
                                });
                            }
                        }
                    });
                    
                    return bgImages;
                }
            """)
            
            # Filter background images
            bg_count = 0
            for bg_data in bg_images:
                if not bg_data['visible']:
                    continue
                
                width = bg_data['width']
                height = bg_data['height']
                
                # Check if it looks like a banner
                if width > 800 or (width > 0 and height > 0 and width / height > 2):
                    banners.append({
                        'src': bg_data['src'],
                        'alt': 'Background banner image',
                        'width': int(width),
                        'height': int(height),
                        'type': 'Background Banner'
                    })
                    bg_count += 1
            
            print(f"[+] Identified {bg_count} background banner images")
            
            # Close browser
            browser.close()
            
            # Remove duplicates
            seen_urls = set()
            unique_banners = []
            for banner in banners:
                if banner['src'] not in seen_urls:
                    seen_urls.add(banner['src'])
                    unique_banners.append(banner)
            
            return unique_banners
            
        except Exception as e:
            print(f"[-] Error during scraping: {e}")
            if 'browser' in locals():
                browser.close()
        return []


# Keywords used to find promotion/bonus pages in nav links
PROMO_KEYWORDS = [
    'promo', 'promotion', 'bonus', 'offer', 'deal',
    'reward', 'campaign', 'special', 'incentive',
    'welcome', 'deposit', 'cashback', 'free-bet', 'freebet',
]


def _click_promo_link(page, base_url):
    """
    Find and click a promotions link on the current page like a real user.
    Returns True if a promo link was found and clicked, False otherwise.
    """
    base_domain = urlparse(base_url).netloc
    keywords_pattern = '|'.join(PROMO_KEYWORDS)

    # Score every anchor and pick the best promotions link.
    # Scoring: URL path match (+10) >> exact text match (+5) >> partial text match (+2)
    # Game category paths (/games/, /slots/, bonus-buy, etc.) are excluded first.
    clicked = page.evaluate("""
        (args) => {
            const promoPathKws  = args.promoPathKws;
            const promoTextKws  = args.promoTextKws;
            const gamePathPats  = args.gamePathPats;
            const baseDomain    = args.baseDomain;
            const anchors       = document.querySelectorAll('a[href]');

            let best = null;
            let bestScore = -1;

            for (const a of anchors) {
                const href = a.href || '';
                const text = (a.textContent || '').trim().toLowerCase();
                let path = '';

                try {
                    const u = new URL(href, document.location.origin);
                    const linkDomain = u.hostname;
                    if (linkDomain && linkDomain !== baseDomain) continue;
                    path = u.pathname.toLowerCase();
                } catch(e) { continue; }

                // Skip game category / non-promo pages
                if (gamePathPats.some(p => path.includes(p))) continue;

                let score = 0;
                // Strong signal: promo keyword appears in the URL path itself
                if (promoPathKws.some(kw => path.includes(kw))) score += 10;
                // Medium signal: link text is exactly a promo word
                if (promoTextKws.some(kw => text === kw)) score += 5;
                // Weak signal: link text contains a promo word
                else if (promoTextKws.some(kw => text.includes(kw))) score += 2;

                if (score > 0 && score > bestScore) {
                    bestScore = score;
                    best = { text: text, href: href };
                }
            }

            if (!best) return { found: false };
            return { found: true, text: best.text, href: best.href };
        }
    """, {
        'promoPathKws': ['promo', 'promotion', 'offer', 'bonus', 'reward', 'deal',
                         'cashback', 'free-spin', 'freebet', 'free-bet', 'campaign'],
        'promoTextKws': ['promo', 'promotion', 'promotions', 'bonus', 'bonuses',
                         'offer', 'offers', 'reward', 'rewards', 'deal', 'campaign'],
        'gamePathPats': ['/games/', '/slots/', '/live-casino/', '/table-games/',
                         '/jackpots/', 'bonus-buy', '/casino-games/'],
        'baseDomain': base_domain,
    })

    if not clicked['found']:
        return False

    print(f"[+] Found promo link: \"{clicked['text']}\" -> {clicked['href']}")

    try:
        # Get current URL before click to detect navigation
        old_url = page.url

        # Actually click it using Playwright's click (handles SPA navigation, overlays, etc.)
        try:
            href = clicked['href']
            link = page.locator(f'a[href="{href}"]').first
            link.click(timeout=5000)
        except Exception:
            # Fallback: navigate directly to the href we already scored and selected
            try:
                page.goto(clicked['href'], wait_until='domcontentloaded', timeout=20000)
            except Exception:
                pass

        # Wait for navigation / page transition
        print("[*] Waiting for promotions page to load...")
        time.sleep(3)

        # Check if URL changed (navigation occurred)
        try:
            new_url = page.url
            if new_url != old_url:
                print(f"    Navigation detected: {new_url}")
        except Exception:
            pass

        # Wait for page to stabilize after navigation
        try:
            page.wait_for_load_state('domcontentloaded', timeout=15000)
        except Exception:
            print(f"    (domcontentloaded timed out, continuing)")
        # Short networkidle grace — casino promo pages rarely reach full idle
        try:
            page.wait_for_load_state('networkidle', timeout=8000)
        except Exception:
            pass

        time.sleep(random.uniform(1.5, 2.5))
        return True

    except Exception as e:
        print(f"[-] Error during promo link click/navigation: {e}")
        return False


def _dismiss_overlays(page):
    """
    Try to dismiss cookie consent banners, GDPR notices, and age-gate overlays.

    These overlays intercept pointer events so carousel buttons can't be clicked
    and lazy-load images never reveal themselves. We try to dismiss them before
    any scrolling or carousel interaction.

    Returns True if something was clicked, False otherwise.
    """
    try:
        dismissed = page.evaluate("""
            () => {
                const selectors = [
                    // ── OneTrust (very widely deployed) ──────────────────────────
                    '#onetrust-accept-btn-handler',
                    '#onetrust-reject-all-handler',
                    // ── Cookiebot ────────────────────────────────────────────────
                    '#CybotCookiebotDialogBodyButtonAccept',
                    '#CybotCookiebotDialogBodyLevelButtonAcceptAll',
                    // ── Cookie Consent JS library ────────────────────────────────
                    '.cc-accept', '.cc-allow', '.cc-dismiss',
                    // ── TrustArc / TRUSTe ────────────────────────────────────────
                    '.truste_popframe .pdynamicbutton a',
                    // ── Generic accept / agree patterns ─────────────────────────
                    'button[id*="accept-all" i]',
                    'button[id*="acceptAll" i]',
                    'button[id*="accept-cookies" i]',
                    'button[id*="acceptcookies" i]',
                    'button[class*="accept-all" i]',
                    'button[class*="acceptAll" i]',
                    '[data-action="accept"]',
                    '[data-testid*="accept" i]',
                    '[aria-label*="accept all" i]',
                    '[class*="cookie-accept" i]',
                    '[class*="CookieConsent"] button[class*="accept" i]',
                    '[class*="cookie-banner"] button:first-of-type',
                    '[class*="cookie-notice"] button:first-of-type',
                    '[id*="cookie-banner"] button:first-of-type',
                    // ── Age verification / enter-site gates ─────────────────────
                    '[class*="age-gate"] button:first-of-type',
                    '[id*="age-gate"] button:first-of-type',
                    '[class*="age-verification"] button:first-of-type',
                    '[id*="age-verification"] button:first-of-type',
                    '[class*="ageGate"] button:first-of-type',
                    '[class*="age_gate"] button:first-of-type',
                    '[data-age-gate] button:first-of-type',
                    '.enter-site-button',
                ];
                for (const sel of selectors) {
                    try {
                        const el = document.querySelector(sel);
                        // offsetParent === null means the element is hidden (display:none)
                        if (el && el.offsetParent !== null) {
                            el.click();
                            return sel;
                        }
                    } catch (_) {}
                }
                return null;
            }
        """)
        if dismissed:
            print(f"    [*] Dismissed overlay: {dismissed}")
            return True
    except Exception:
        pass
    return False


def _scrape_current_page(page, page_label):
    """Extract banners from the currently loaded page. Returns list of banner dicts."""
    banners = []

    # Wait for page content to be ready.
    # Wait for the React/SPA nav to mount, then give the app time to fetch
    # promo data and render content images.
    #
    # Why NOT wait for large images (>300px) here:
    #   On sites like spinjo.com, banner images are below the fold so their
    #   getBoundingClientRect().width is 0 until scrolled into view. Waiting
    #   for large images would time out and skip the rendering window.
    #
    # Why NOT wait for body text (>200 chars) alone:
    #   Some casino sites have minimal text and all content is images.
    #
    # Best signal: wait for navigation links (>5) — fires the moment the React
    # app mounts its nav bar (~1-3s for a direct connection, ~5-10s through proxy).
    # Then sleep to let the React component tree finish fetching promo API data.
    print(f"[*] Waiting for {page_label} to render...")
    # Step 1: Wait for the React/SPA nav to mount — confirms JS has run and
    # the app is hydrated. Links > 5 fires first (nav); text > 200 is a fallback
    # for server-rendered pages that don't have many nav links.
    try:
        page.wait_for_function(
            "() => document.body && ("
            "  document.querySelectorAll('a[href]:not([href=\"\"])').length > 5 ||"
            "  document.body.innerText.trim().length > 200"
            ")",
            timeout=20000
        )
    except Exception:
        pass

    # Step 2: Wait for hero/banner-sized images to finish downloading.
    # Threshold is 600px wide — game thumbnails are typically 300-400px, hero
    # sliders and promotional banners are 800px+ wide. This prevents scrolling
    # before the above-fold banner content has actually loaded.
    # 15s timeout covers slow proxy connections (each JS bundle + API call
    # goes through the proxy, adding several seconds of latency).
    print(f"[*] Waiting for banner images on {page_label}...")
    try:
        page.wait_for_function(
            "() => Array.from(document.querySelectorAll('img[src]:not([src=\"\"])')).some("
            "  img => img.naturalWidth > 600"
            ")",
            timeout=15000
        )
    except Exception:
        # No banner-sized img tags found — either a CSS-background-only site, or
        # React hasn't finished its API fetches yet. Sleep to let the app settle.
        time.sleep(5)

    # Dismiss cookie consent banners and age-gate overlays before any interaction.
    # These block pointer events — carousels can't be clicked and lazy images won't load.
    _dismiss_overlays(page)
    time.sleep(0.8)

    # Scroll to load lazy images. Guard against null document.body (can happen
    # when the page is a bot-wall that hasn't rendered yet).
    print(f"[*] Scrolling {page_label}...")
    for i in range(4):
        scroll_pct = (i + 1) * 25
        try:
            page.evaluate(
                f"() => {{ if (document.body) window.scrollTo(0, document.body.scrollHeight * {scroll_pct / 100}); }}"
            )
        except Exception:
            pass
        time.sleep(random.uniform(0.8, 1.5))

    try:
        page.evaluate("() => { if (document.body) window.scrollTo(0, 0); }")
    except Exception:
        pass
    time.sleep(1.5)

    # Cycle ALL carousels on the page (not just the first match).
    # Uses a WeakSet so the same button element is never double-clicked even if
    # it matches multiple selectors.
    print(f"[*] Cycling carousels on {page_label}...")
    page.evaluate("""
        () => {
            const nextSelectors = [
                '.slick-next', '.swiper-button-next', '.carousel-control-next',
                '.owl-next', '[data-slide="next"]', '.next-arrow', '.arrow-right',
                '.slider-next', '.bx-next', '.flex-next', '.glide__arrow--right',
                'button[aria-label="Next"]', 'button[aria-label="next"]',
                '.splide__arrow--next', '.flickity-prev-next-button.next',
                '[data-direction="next"]', '[data-action="next"]',
                '.carousel__arrow--next', '.hero-slider__btn--next',
                '.js-next', '[class*="arrow-next"]', '[class*="next-btn"]',
            ];
            const clicked = new WeakSet();
            for (const sel of nextSelectors) {
                try {
                    for (const btn of document.querySelectorAll(sel)) {
                        // offsetParent null = hidden element, skip it
                        if (!clicked.has(btn) && btn.offsetParent !== null) {
                            for (let i = 0; i < 8; i++) btn.click();
                            clicked.add(btn);
                        }
                    }
                } catch (_) {}
            }
        }
    """)
    time.sleep(3)

    # Second scroll pass — carousel cycling reveals new slides whose lazy images
    # haven't loaded yet. Scroll the page again to trigger their load.
    for i in range(2):
        scroll_pct = (i + 1) * 50
        try:
            page.evaluate(
                f"() => {{ if (document.body) window.scrollTo(0, document.body.scrollHeight * {scroll_pct / 100}); }}"
            )
        except Exception:
            pass
        time.sleep(0.8)
    try:
        page.evaluate("() => { if (document.body) window.scrollTo(0, 0); }")
    except Exception:
        pass
    time.sleep(0.5)

    # Wait for lazy-loaded images to arrive after scrolling.
    # Scrolling fires IntersectionObserver which triggers network requests for
    # banner images. We wait up to 8s for the first large image (>300px) to
    # finish downloading. Without this, extraction runs before images arrive.
    try:
        page.wait_for_function(
            "() => Array.from(document.querySelectorAll('img[src]:not([src=\"\"])')).some("
            "  img => img.naturalWidth > 300"
            ")",
            timeout=8000
        )
    except Exception:
        pass  # No large images (CSS-background-only site) — still scrape backgrounds
    time.sleep(1)

    # Extract images
    print(f"[*] Extracting images from {page_label}...")
    images_data = page.evaluate("""
        () => {
            const images = [];
            document.querySelectorAll('img').forEach(img => {
                const rect = img.getBoundingClientRect();
                const cs = window.getComputedStyle(img);
                let parentClasses = '';
                let p = img.parentElement;
                for (let i = 0; i < 3 && p; i++) {
                    parentClasses += ' ' + (p.className || '');
                    p = p.parentElement;
                }
                const src = img.currentSrc || img.src
                    || img.getAttribute('data-src')
                    || img.getAttribute('data-lazy-src')
                    || img.getAttribute('data-original')
                    || img.getAttribute('data-lazy')
                    || img.getAttribute('data-image')
                    || img.getAttribute('data-original-src')
                    || '';
                // Prefer the largest srcset URL (usually last entry with biggest w descriptor)
                const srcsetRaw = img.getAttribute('srcset') || img.getAttribute('data-srcset') || '';
                let srcsetUrl = '';
                if (srcsetRaw) {
                    const parts = srcsetRaw.split(',').map(s => {
                        const p = s.trim().split(/[ \\t]+/);
                        const w = p[1] && p[1].endsWith('w') ? parseInt(p[1]) : 0;
                        return { url: p[0], w };
                    }).filter(p => p.url);
                    parts.sort((a, b) => b.w - a.w);
                    srcsetUrl = (parts[0] && parts[0].url) || '';
                }
                const isVisible = cs.display !== 'none' && cs.visibility !== 'hidden'
                    && rect.width > 0 && rect.height > 0;
                const inCarousel = !!(parentClasses + ' ' + (img.className || '')).match(
                    /slider|carousel|swiper|slick|owl|splide|glide|flickity|banner|promo/i
                );
                images.push({
                    src: src || srcsetUrl, alt: img.alt || '',
                    width: Math.max(rect.width, img.naturalWidth, img.width) || 0,
                    height: Math.max(rect.height, img.naturalHeight, img.height) || 0,
                    class: img.className || '', parent_class: parentClasses.trim(),
                    visible: isVisible, in_carousel: inCarousel
                });
            });
            return images;
        }
    """)

    print(f"[*] Found {len(images_data)} total images on {page_label}")

    for img in images_data:
        if not img['src'] or img['src'].startswith('data:'):
            continue
        if not img['visible'] and not img.get('in_carousel'):
            continue
        if is_banner_image(img, in_carousel=img.get('in_carousel', False)):
            banners.append({
                'src': img['src'],
                'alt': img['alt'] or 'Banner image',
                'width': int(img['width']),
                'height': int(img['height']),
                'type': 'Carousel Banner' if img.get('in_carousel') else 'Banner Image',
                'page': page_label,
            })

    # Background images — two sources:
    # 1. Computed CSS background-image (current active backgrounds)
    # 2. data-bg / data-background / data-background-image attributes (lazy-loaded,
    #    not yet applied to CSS — still contain the real image URL)
    bg_images = page.evaluate("""
        () => {
            const bgImages = [];
            const seen = new Set();
            document.querySelectorAll('*').forEach(el => {
                // Source 1: computed CSS background-image
                const style = window.getComputedStyle(el);
                const bgImage = style.backgroundImage;
                if (bgImage && bgImage !== 'none' && !bgImage.includes('gradient')) {
                    const m = bgImage.match(/url\\(["']?([^"'\\)]+)["']?\\)/);
                    if (m && m[1] && !m[1].startsWith('data:') && !seen.has(m[1])) {
                        seen.add(m[1]);
                        const rect = el.getBoundingClientRect();
                        bgImages.push({
                            src: m[1], width: rect.width, height: rect.height,
                            visible: style.display !== 'none' && rect.width > 0 && rect.height > 0
                        });
                    }
                }
                // Source 2: data-bg / data-background attributes (lazy-load pattern)
                const dataAttrs = ['data-bg', 'data-background', 'data-background-image',
                                   'data-lazy-background', 'data-lazy-bg'];
                for (const attr of dataAttrs) {
                    const val = el.getAttribute(attr);
                    if (val && !val.startsWith('data:') && !seen.has(val)) {
                        seen.add(val);
                        const rect = el.getBoundingClientRect();
                        bgImages.push({
                            src: val, width: rect.width, height: rect.height,
                            visible: rect.width > 0 && rect.height > 0
                        });
                        break;
                    }
                }
            });
            return bgImages;
        }
    """)

    for bg in bg_images:
        if not bg['visible']:
            continue
        w, h = bg['width'], bg['height']
        if w > 800 or (w > 0 and h > 0 and w / h > 2):
            banners.append({
                'src': bg['src'], 'alt': 'Background banner image',
                'width': int(w), 'height': int(h),
                'type': 'Background Banner', 'page': page_label,
            })

    # Deduplicate within this page (carousels sometimes clone slides)
    seen_page = set()
    unique_banners = []
    for b in banners:
        try:
            p = urlparse(b['src'])
            key = p._replace(query='', fragment='').geturl()
        except Exception:
            key = b['src']
        if key not in seen_page:
            seen_page.add(key)
            unique_banners.append(b)

    print(f"[+] {len(unique_banners)} banners from {page_label}")
    return unique_banners


def _scrape_with_connection(url, headless, location, proxy, use_env_proxy):
    """
    Internal helper: performs the actual scraping with given connection settings.
    Returns dict with 'homepage' and 'promotions' results.
    """
    results = {'homepage': [], 'promotions': []}

    geolocations = {
        'US': {'latitude': 37.7749, 'longitude': -122.4194, 'locale': 'en-US', 'timezone': 'America/Los_Angeles'},
        'UK': {'latitude': 51.5074, 'longitude': -0.1278, 'locale': 'en-GB', 'timezone': 'Europe/London'},
        'DE': {'latitude': 52.5200, 'longitude': 13.4050, 'locale': 'de-DE', 'timezone': 'Europe/Berlin'},
        'FR': {'latitude': 48.8566, 'longitude': 2.3522, 'locale': 'fr-FR', 'timezone': 'Europe/Paris'},
        'JP': {'latitude': 35.6762, 'longitude': 139.6503, 'locale': 'ja-JP', 'timezone': 'Asia/Tokyo'},
        'AU': {'latitude': -33.8688, 'longitude': 151.2093, 'locale': 'en-AU', 'timezone': 'Australia/Sydney'},
        'CA': {'latitude': 43.6532, 'longitude': -79.3832, 'locale': 'en-CA', 'timezone': 'America/Toronto'},
        'BR': {'latitude': -23.5505, 'longitude': -46.6333, 'locale': 'pt-BR', 'timezone': 'America/Sao_Paulo'},
        'IN': {'latitude': 28.6139, 'longitude': 77.2090, 'locale': 'en-IN', 'timezone': 'Asia/Kolkata'},
        'SG': {'latitude': 1.3521, 'longitude': 103.8198, 'locale': 'en-SG', 'timezone': 'Asia/Singapore'},
    }

    geo = geolocations.get(location.upper(), geolocations['US'])

    print(f"\n[*] Full site scrape: {url}")
    print(f"[*] Location: {location}\n")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=headless,
                args=[
                    # Anti-detection
                    '--disable-blink-features=AutomationControlled',
                    # Stability in Docker / Cloud Run (Linux only flags)
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-gpu',
                    # NOTE: --single-process is Linux-only; causes navigation failure on Windows
                    # Rendering
                    '--window-size=1920,1080',
                    '--hide-scrollbars',
                    '--mute-audio',
                    # Network
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--ignore-certificate-errors',
                ]
            )

            extra_headers = {
                'Accept-Language': f"{geo['locale']},en;q=0.9",
                # NOTE: Do NOT override Accept or Accept-Encoding here.
                # Playwright sets them correctly per request type (HTML nav vs XHR vs image).
                # Overriding globally breaks React SPAs that make JSON API calls — the
                # server receives Accept:text/html for XHR and returns HTML instead of JSON,
                # causing the app to render with no banner images (only 7 static images vs 337).
                'DNT': '1', 'Connection': 'keep-alive', 'Upgrade-Insecure-Requests': '1'
            }

            context_options = {
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': get_random_user_agent(),
                'locale': geo['locale'],
                'timezone_id': geo['timezone'],
                'geolocation': {'latitude': geo['latitude'], 'longitude': geo['longitude']},
                'permissions': ['geolocation'],
                'ignore_https_errors': True,
            }

            proxy_country = None
            if proxy:
                proxy_cfg = proxy if isinstance(proxy, dict) else {'server': proxy}
                proxy_country = proxy_cfg.pop('country', None)
                context_options['proxy'] = proxy_cfg
            elif use_env_proxy:
                env_proxy = get_proxy_from_env(country=location)
                if env_proxy:
                    proxy_country = env_proxy.pop('country', None)
                    context_options['proxy'] = env_proxy
                    print(f"[*] Using Oxylabs Web Unblocker ({proxy_country or location})")

            if proxy_country:
                extra_headers['x-oxylabs-geo-location'] = proxy_country
            context_options['extra_http_headers'] = extra_headers

            context = browser.new_context(**context_options)

            page = context.new_page()

            # Layer 1: inline JS stealth (always runs, works on all Python versions)
            context.add_init_script(_STEALTH_JS)

            # Layer 2: playwright-stealth package (additional patches, when available)
            if _STEALTH_PKG:
                stealth_sync(page)
                print("[*] Stealth: inline JS + playwright-stealth package")
            else:
                print("[*] Stealth: inline JS only (playwright-stealth unavailable locally)")

            # --- STEP 1: Homepage ---
            print("=" * 60)
            print("[*] STEP 1: Scraping homepage...")
            print("=" * 60)

            # Navigation strategy:
            #
            # Phase 1 — commit: fires on first HTTP byte, fast fail for empty shells
            # Phase 2 — domcontentloaded: wait for HTML parse (handles Cloudflare
            #   challenge redirects — don't bail early, let the redirect complete)
            # Phase 3 — JS render wait: React/Vue/Next.js CSR apps render content
            #   AFTER domcontentloaded, so we explicitly wait for real content to appear
            commit_fired = False
            try:
                page.goto(url, wait_until='commit', timeout=30000)
                commit_fired = True
            except Exception as e:
                print(f"    (connection timed out: {type(e).__name__})")

            # Immediate shell-size check right after first byte.
            # If tiny (<= 200 bytes) the proxy returned nothing useful — bail fast.
            if commit_fired:
                try:
                    immediate_len = page.evaluate("() => document.documentElement.outerHTML.length")
                    if immediate_len <= 200:
                        print(f"[!] Empty shell (html_len={immediate_len}) — proxy blocked by site")
                        results['blocked'] = True
                        browser.close()
                        return results
                except Exception:
                    pass

            # Phase 2: wait for domcontentloaded.
            # Do NOT bail early on timeout — Cloudflare challenge pages redirect mid-flight
            # and can push the real domcontentloaded event past the timeout window.
            try:
                page.wait_for_load_state('domcontentloaded', timeout=30000)
            except Exception:
                print(f"    (domcontentloaded timed out — may be Cloudflare challenge, continuing)")

            # Short networkidle grace (casino SPAs rarely reach full idle)
            try:
                page.wait_for_load_state('networkidle', timeout=8000)
            except Exception:
                pass

            # Phase 3: for React/Vue/Next.js CSR apps, content renders after
            # domcontentloaded. Extended to 20s because proxy adds latency to
            # every JS bundle / API request the app makes during render.
            # Three early-exit signals (fastest to slowest):
            #   1. links > 5   — nav bar mounts (React hydration complete)
            #   2. naturalWidth > 600 — a hero/banner image downloaded
            #      (600px threshold skips small thumbnails/icons that load first)
            #   3. text > 200  — substantial text rendered (server-rendered pages)
            try:
                page.wait_for_function(
                    "() => document.body && ("
                    "  document.querySelectorAll('a[href]:not([href=\"\"])').length > 5 ||"
                    "  Array.from(document.querySelectorAll('img[src]:not([src=\"\"])')).some("
                    "    img => img.naturalWidth > 600"
                    "  ) ||"
                    "  document.body.innerText.trim().length > 200"
                    ")",
                    timeout=20000
                )
            except Exception:
                pass  # Not a CSR app, or truly nothing loaded

            # Debug: log what page actually loaded
            try:
                loaded_url = page.url
                loaded_title = page.title()
                print(f"[*] Loaded: {loaded_url}")
                print(f"[*] Title:  {loaded_title}")
            except Exception:
                loaded_url = ''

            # Bail out if navigation never completed at all
            if not loaded_url or loaded_url in ('about:blank', '') or loaded_url.startswith('chrome-error://'):
                print("[-] Navigation failed — proxy could not reach the target site")
                browser.close()
                return results

            # Detect empty/useless page after all waiting:
            #   a) Bare HTML shell (html_len < 1000) — proxy returned nothing real
            #   b) JS ran but produced nothing (no title + no images + no text)
            try:
                html_len      = page.evaluate("() => document.documentElement.outerHTML.length")
                img_count     = page.evaluate("() => document.querySelectorAll('img[src]:not([src=\"\"])').length")
                body_text_len = page.evaluate(
                    "() => (document.body && document.body.innerText || '').trim().length"
                )
                link_count    = page.evaluate("() => document.querySelectorAll('a[href]:not([href=\"\"])').length")
                print(f"[*] html_len={html_len}  real_imgs={img_count}  text_len={body_text_len}  links={link_count}")

                empty_shell = html_len < 1000
                no_content  = (not loaded_title.strip()) and img_count == 0 and body_text_len < 100

                if empty_shell or no_content:
                    print(f"[!] Page has no usable content — proxy blocked or site unreachable")
                    results['blocked'] = True
                    browser.close()
                    return results
            except Exception:
                pass

            # Detect geo-block / access-denied pages BEFORE scraping.
            # Pass target url so domain-mismatch (ISP redirect) is also detected.
            if is_page_blocked(page, target_url=url):
                print(f"[!] Geo-restriction detected on homepage — not the real site")
                results['blocked'] = True
                browser.close()
                return results

            results['homepage'] = _scrape_current_page(page, 'Homepage')

            # --- STEP 2: Navigate to promotions page ---
            print("\n" + "=" * 60)
            print("[*] STEP 2: Looking for promotions page...")
            print("=" * 60)

            # Actually click the promo link like a real user
            if _click_promo_link(page, url):
                # Link was clicked, page has navigated, now scrape
                try:
                    results['promotions'] = _scrape_current_page(page, 'Promotions')
                except Exception as e:
                    print(f"[-] Error scraping promotions page: {e}")
                    print("    (Homepage results still available)")
            else:
                print("[-] No promotions link found on page")

            browser.close()

            # Deduplicate across both pages using normalised URL as the key.
            # Normalisation strips query-string + fragment so that the same image
            # at different resolutions (e.g. banner.jpg?w=1920 vs ?w=800) counts
            # as one entry — but the original URL is preserved in the output.
            def _norm(src):
                try:
                    p = urlparse(src)
                    return p._replace(query='', fragment='').geturl()
                except Exception:
                    return src

            seen = set()
            for key in ('homepage', 'promotions'):
                unique = []
                for b in results.get(key, []):
                    key_url = _norm(b['src'])
                    if key_url not in seen:
                        seen.add(key_url)
                        unique.append(b)
                results[key] = unique

            return results

        except Exception as e:
            print(f"[-] Error during full scrape: {e}")
            if 'browser' in locals():
                browser.close()
            return results


def scrape_site_full(url, headless=True, location='US', proxy=None, use_env_proxy=True, skip_proxy=False):
    """
    Full site scrape with automatic proxy fallback.

    Strategy:
    1. Try direct connection first (faster, free)
    2. If blocked/failed (0 images found) -> automatically retry with proxy
    3. Returns best results (proxy or direct)

    Args:
        url: Base URL of the site (e.g. "https://example.com")
        headless: Run browser headless
        location: Geo location code
        proxy: Optional proxy dict
        use_env_proxy: Load proxy from .env if True (default)
        skip_proxy: If True, only use direct connection — never use proxy

    Returns:
        dict with keys 'homepage' and 'promotions', each a list of banner dicts
    """

    if skip_proxy:
        print("=" * 60)
        print("[*] STRATEGY: Direct connection only (no proxy)...")
        print("=" * 60)
        return _scrape_with_connection(url, headless, location, proxy=None, use_env_proxy=False)

    # STEP 1: Try direct connection (no proxy)
    print("=" * 60)
    print("[*] STRATEGY: Try direct connection first...")
    print("=" * 60)

    results = _scrape_with_connection(url, headless, location, proxy=None, use_env_proxy=False)

    # Check if direct connection worked
    # Blocked = geo-restriction page detected (don't trust any banners found on it)
    # Zero = page loaded but no banners matched (also retry with proxy)
    total_found = len(results.get('homepage', [])) + len(results.get('promotions', []))
    is_blocked = results.get('blocked', False)

    if total_found > 0 and not is_blocked:
        print("\n" + "=" * 60)
        print(f"[+] SUCCESS: Direct connection worked! Found {total_found} banner(s)")
        print("[*] No proxy needed - saved proxy bandwidth!")
        print("=" * 60 + "\n")
        return results

    # STEP 2: Direct connection geo-blocked or returned nothing → retry with proxy
    print("\n" + "=" * 60)
    if is_blocked:
        print("[!] Direct connection: geo-restricted. Retrying with proxy...")
    else:
        print("[!] Direct connection: 0 banners found. Retrying with proxy...")
    print("=" * 60 + "\n")

    if not use_env_proxy and not proxy:
        print("[-] No proxy available. Returning empty results.")
        return results

    # Retry with proxy
    results = _scrape_with_connection(url, headless, location, proxy, use_env_proxy=True)

    total_found = len(results.get('homepage', [])) + len(results.get('promotions', []))

    if total_found > 0:
        print("\n" + "=" * 60)
        print(f"[+] SUCCESS: Proxy connection worked! Found {total_found} banner(s)")
        print("=" * 60 + "\n")
    else:
        print("\n" + "=" * 60)
        print("[!] Site blocked even with proxy. May need residential proxy.")
        print("=" * 60 + "\n")

    return results