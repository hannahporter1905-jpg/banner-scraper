from playwright.sync_api import sync_playwright
from urllib.parse import urljoin, urlparse
import time
import random
import os
from dotenv import load_dotenv

# Load proxy config from .env at project root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


def get_proxy_from_env(country='US'):
    """Build proxy config from .env variables. Supports country override."""
    host = os.getenv('PROXY_HOST')
    port = os.getenv('PROXY_PORT')
    user = os.getenv('PROXY_USER', '')
    password = os.getenv('PROXY_PASS', '')
    scheme = os.getenv('PROXY_SCHEME', 'http')

    if not host or not port:
        return None

    return {
        'server': f'{scheme}://{host}:{port}',
        'username': user,
        'password': password,
        'country': country,
    }

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

def is_banner_image(img_data):
    """Improved banner detection logic"""
    width = img_data.get('width', 0)
    height = img_data.get('height', 0)
    src = img_data.get('src', '').lower()
    alt = img_data.get('alt', '').lower()
    classes = img_data.get('class', '').lower()
    parent_classes = img_data.get('parent_class', '').lower()
    
    # Expanded banner keywords
    banner_keywords = [
        'banner', 'hero', 'slider', 'carousel', 'slideshow',
        'header', 'jumbotron', 'masthead', 'cover', 'featured',
        'promo', 'promotion', 'landing', 'splash', 'billboard',
        'spotlight', 'showcase', 'highlight', 'campaign'
    ]
    
    # Check aspect ratio (wide images are typically banners)
    if width > 0 and height > 0:
        aspect_ratio = width / height
        # Common banner aspect ratios: 16:9, 3:1, 4:1, etc.
        if (aspect_ratio > 2.0 and width > 500) or (aspect_ratio > 1.5 and width > 800):
            return True
    
    # Very wide images are almost always banners
    if width > 1200:
        return True
    
    # Check keywords in various attributes
    for keyword in banner_keywords:
        if (keyword in src or keyword in alt or 
            keyword in classes or keyword in parent_classes):
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

                if is_banner_image(img_data) or img_data.get('in_carousel'):
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

    # Use Playwright locators to find and click a matching <a> link
    # Check all anchors on the page for promo keywords in text or href
    clicked = page.evaluate("""
        (args) => {
            const keywords = args.keywords;
            const baseDomain = args.baseDomain;
            const anchors = document.querySelectorAll('a[href]');

            for (const a of anchors) {
                const href = a.href || '';
                const text = (a.textContent || '').trim().toLowerCase();
                const path = (new URL(href, document.location.origin)).pathname.toLowerCase();

                // Skip external links
                try {
                    const linkDomain = new URL(href).hostname;
                    if (linkDomain && linkDomain !== baseDomain) continue;
                } catch(e) {}

                // Check if text or path matches any promo keyword
                const matches = keywords.some(kw => text.includes(kw) || path.includes(kw));
                if (matches) {
                    // Scroll the link into view and click it
                    a.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    return { found: true, text: text, href: href };
                }
            }
            return { found: false };
        }
    """, {'keywords': PROMO_KEYWORDS, 'baseDomain': base_domain})

    if not clicked['found']:
        return False

    print(f"[+] Found promo link: \"{clicked['text']}\" -> {clicked['href']}")

    # Actually click it using Playwright's click (handles SPA navigation, overlays, etc.)
    try:
        # Build a selector that matches the link we found
        href = clicked['href']
        # Try clicking by href match
        link = page.locator(f'a[href="{href}"]').first
        link.click(timeout=5000)
    except Exception:
        # Fallback: click via JS
        page.evaluate("""
            (args) => {
                const anchors = document.querySelectorAll('a[href]');
                for (const a of anchors) {
                    const text = (a.textContent || '').trim().toLowerCase();
                    const path = (new URL(a.href, document.location.origin)).pathname.toLowerCase();
                    if (args.keywords.some(kw => text.includes(kw) || path.includes(kw))) {
                        a.click();
                        break;
                    }
                }
            }
        """, {'keywords': PROMO_KEYWORDS})

    # Wait for navigation / page transition
    print("[*] Waiting for promotions page to load...")
    time.sleep(2)
    try:
        page.wait_for_load_state('networkidle', timeout=30000)
    except Exception:
        pass
    time.sleep(random.uniform(2, 4))

    return True


def _scrape_current_page(page, page_label):
    """Extract banners from the currently loaded page. Returns list of banner dicts."""
    banners = []

    # Wait for content to render
    print(f"[*] Waiting for {page_label} to render...")
    time.sleep(random.uniform(3, 5))

    # Scroll to load lazy images
    print(f"[*] Scrolling {page_label}...")
    for i in range(5):
        scroll_pct = (i + 1) * 20
        page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {scroll_pct / 100})")
        time.sleep(random.uniform(1, 2))

    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(2)

    # Cycle carousels
    print(f"[*] Cycling carousels on {page_label}...")
    page.evaluate("""
        () => {
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
                    for (let i = 0; i < 10; i++) { btn.click(); }
                    break;
                }
            }
        }
    """)
    time.sleep(3)

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
                    || img.getAttribute('data-original') || '';
                const srcset = img.getAttribute('srcset') || '';
                const srcsetUrl = srcset ? srcset.split(',')[0].trim().split(' ')[0] : '';
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
        if is_banner_image(img) or img.get('in_carousel'):
            banners.append({
                'src': img['src'],
                'alt': img['alt'] or 'Banner image',
                'width': int(img['width']),
                'height': int(img['height']),
                'type': 'Carousel Banner' if img.get('in_carousel') else 'Banner Image',
                'page': page_label,
            })

    # Background images
    bg_images = page.evaluate("""
        () => {
            const bgImages = [];
            document.querySelectorAll('*').forEach(el => {
                const style = window.getComputedStyle(el);
                const bgImage = style.backgroundImage;
                if (bgImage && bgImage !== 'none' && !bgImage.includes('gradient')) {
                    const m = bgImage.match(/url\\(["']?([^"']*)["']?\\)/);
                    if (m && m[1] && !m[1].startsWith('data:')) {
                        const rect = el.getBoundingClientRect();
                        bgImages.push({
                            src: m[1], width: rect.width, height: rect.height,
                            visible: style.display !== 'none' && rect.width > 0 && rect.height > 0
                        });
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

    print(f"[+] {len(banners)} banners from {page_label}")
    return banners


def scrape_site_full(url, headless=True, location='US', proxy=None, use_env_proxy=True):
    """
    Full site scrape: homepage first, then auto-discover and scrape the promotions page.

    Args:
        url: Base URL of the site (e.g. "https://example.com")
        headless: Run browser headless
        location: Geo location code
        proxy: Optional proxy dict
        use_env_proxy: Load proxy from .env if True

    Returns:
        dict with keys 'homepage' and 'promotions', each a list of banner dicts
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
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--ignore-certificate-errors',
                ]
            )

            extra_headers = {
                'Accept-Language': f"{geo['locale']},en;q=0.9",
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
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
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US','en'] });
                window.chrome = { runtime: {} };
            """)

            page = context.new_page()

            # --- STEP 1: Homepage ---
            print("=" * 60)
            print("[*] STEP 1: Scraping homepage...")
            print("=" * 60)

            try:
                page.goto(url, wait_until='networkidle', timeout=45000)
            except Exception:
                print("    (network didn't fully idle, continuing...)")

            results['homepage'] = _scrape_current_page(page, 'Homepage')

            # --- STEP 2: Navigate to promotions page ---
            print("\n" + "=" * 60)
            print("[*] STEP 2: Looking for promotions page...")
            print("=" * 60)

            # Actually click the promo link like a real user
            if _click_promo_link(page, url):
                # Link was clicked, page has navigated, now scrape
                results['promotions'] = _scrape_current_page(page, 'Promotions')
            else:
                print("[-] No promotions link found on page")

            browser.close()

            # Deduplicate across both pages
            seen = set()
            for key in results:
                unique = []
                for b in results[key]:
                    if b['src'] not in seen:
                        seen.add(b['src'])
                        unique.append(b)
                results[key] = unique

            return results

        except Exception as e:
            print(f"[-] Error during full scrape: {e}")
            if 'browser' in locals():
                browser.close()
            return results