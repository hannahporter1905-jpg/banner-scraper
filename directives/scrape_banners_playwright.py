from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
import time

def is_banner_image(img_data):
    """
    Determine if an image is likely a banner based on its properties.
    
    Args:
        img_data: Dictionary containing image attributes
    
    Returns:
        bool: True if image appears to be a banner
    """
    width = img_data.get('width', 0)
    height = img_data.get('height', 0)
    src = img_data.get('src', '').lower()
    alt = img_data.get('alt', '').lower()
    classes = img_data.get('class', '').lower()
    parent_classes = img_data.get('parent_class', '').lower()
    
    # Banner keywords to look for
    banner_keywords = [
        'banner', 'hero', 'slider', 'carousel', 
        'header', 'jumbotron', 'masthead', 'cover',
        'featured', 'promo'
    ]
    
    # Check aspect ratio (wide images)
    if width > 0 and height > 0:
        aspect_ratio = width / height
        if aspect_ratio > 2.5 and width > 600:
            return True
    
    # Check for very wide images
    if width > 1000:
        return True
    
    # Check keywords in various attributes
    for keyword in banner_keywords:
        if (keyword in src or 
            keyword in alt or 
            keyword in classes or 
            keyword in parent_classes):
            return True
    
    return False


def scrape_website_banners_playwright(url, headless=True, location='US'):
    """
    Scrape a website using Playwright and extract banner images.
    Works better with JavaScript-heavy sites and sites that block simple scrapers.
    
    Args:
        url: The website URL to scrape
        headless: Run browser in headless mode (True) or visible mode (False)
        location: Geolocation code (US, UK, DE, FR, JP, AU, etc.)
    
    Returns:
        list: List of dictionaries containing banner information
    """
    banners = []
    
    # Geolocation presets for different countries
    geolocations = {
        'US': {'latitude': 37.7749, 'longitude': -122.4194, 'locale': 'en-US', 'timezone': 'America/Los_Angeles'},  # San Francisco
        'UK': {'latitude': 51.5074, 'longitude': -0.1278, 'locale': 'en-GB', 'timezone': 'Europe/London'},  # London
        'DE': {'latitude': 52.5200, 'longitude': 13.4050, 'locale': 'de-DE', 'timezone': 'Europe/Berlin'},  # Berlin
        'FR': {'latitude': 48.8566, 'longitude': 2.3522, 'locale': 'fr-FR', 'timezone': 'Europe/Paris'},  # Paris
        'JP': {'latitude': 35.6762, 'longitude': 139.6503, 'locale': 'ja-JP', 'timezone': 'Asia/Tokyo'},  # Tokyo
        'AU': {'latitude': -33.8688, 'longitude': 151.2093, 'locale': 'en-AU', 'timezone': 'Australia/Sydney'},  # Sydney
        'CA': {'latitude': 43.6532, 'longitude': -79.3832, 'locale': 'en-CA', 'timezone': 'America/Toronto'},  # Toronto
        'BR': {'latitude': -23.5505, 'longitude': -46.6333, 'locale': 'pt-BR', 'timezone': 'America/Sao_Paulo'},  # São Paulo
        'IN': {'latitude': 28.6139, 'longitude': 77.2090, 'locale': 'en-IN', 'timezone': 'Asia/Kolkata'},  # New Delhi
        'SG': {'latitude': 1.3521, 'longitude': 103.8198, 'locale': 'en-SG', 'timezone': 'Asia/Singapore'},  # Singapore
    }
    
    geo = geolocations.get(location.upper(), geolocations['US'])
    
    print(f"Launching browser (headless={headless}, location={location})...")
    
    with sync_playwright() as p:
        try:
            # Launch browser (Chromium is most compatible)
            browser = p.chromium.launch(headless=headless)
            
            # Create a new browser context with realistic settings and geolocation
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale=geo['locale'],
                timezone_id=geo['timezone'],
                geolocation={'latitude': geo['latitude'], 'longitude': geo['longitude']},
                permissions=['geolocation']
            )
            
            # Create a new page
            page = context.new_page()
            
            print(f"Navigating to {url}...")
            
            # Navigate to the URL with timeout
            page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Wait a bit for dynamic content to load
            print("Waiting for page to fully load...")
            time.sleep(2)
            
            # Scroll down to trigger lazy-loaded images
            print("Scrolling to load lazy images...")
            page.evaluate("""
                window.scrollTo(0, document.body.scrollHeight / 2);
            """)
            time.sleep(1)
            page.evaluate("""
                window.scrollTo(0, 0);
            """)
            time.sleep(1)
            
            print("Extracting images...")
            
            # Extract all images using JavaScript
            images_data = page.evaluate("""
                () => {
                    const images = [];
                    const imgElements = document.querySelectorAll('img');
                    
                    imgElements.forEach(img => {
                        const rect = img.getBoundingClientRect();
                        const computedStyle = window.getComputedStyle(img);
                        const parent = img.parentElement;
                        const parentClasses = parent ? parent.className : '';
                        
                        images.push({
                            src: img.src || img.getAttribute('data-src') || '',
                            alt: img.alt || '',
                            width: rect.width || img.naturalWidth || 0,
                            height: rect.height || img.naturalHeight || 0,
                            class: img.className || '',
                            parent_class: parentClasses,
                            visible: computedStyle.display !== 'none' && computedStyle.visibility !== 'hidden'
                        });
                    });
                    
                    return images;
                }
            """)
            
            print(f"Found {len(images_data)} total images")
            
            # Filter for banner images
            for img_data in images_data:
                # Skip invisible images and data URIs
                if not img_data['visible'] or not img_data['src']:
                    continue
                    
                if img_data['src'].startswith('data:'):
                    continue
                
                # Check if it's a banner
                if is_banner_image(img_data):
                    banners.append({
                        'src': img_data['src'],
                        'alt': img_data['alt'] or 'Banner image',
                        'width': int(img_data['width']),
                        'height': int(img_data['height']),
                        'type': 'Banner Image'
                    })
            
            # Extract CSS background images
            print("Checking for background images...")
            bg_images = page.evaluate("""
                () => {
                    const bgImages = [];
                    const elements = document.querySelectorAll('*');
                    
                    elements.forEach(el => {
                        const style = window.getComputedStyle(el);
                        const bgImage = style.backgroundImage;
                        
                        if (bgImage && bgImage !== 'none') {
                            const urlMatch = bgImage.match(/url\\(["']?([^"']*)["']?\\)/);
                            if (urlMatch && urlMatch[1]) {
                                const rect = el.getBoundingClientRect();
                                bgImages.push({
                                    src: urlMatch[1],
                                    width: rect.width,
                                    height: rect.height,
                                    class: el.className || '',
                                    visible: style.display !== 'none'
                                });
                            }
                        }
                    });
                    
                    return bgImages;
                }
            """)
            
            # Filter background images for banners
            for bg_data in bg_images:
                if not bg_data['visible'] or bg_data['src'].startswith('data:'):
                    continue
                
                width = bg_data['width']
                height = bg_data['height']
                
                # Check if it looks like a banner
                if (width > 800 and height > 200) or (width > 0 and height > 0 and width / height > 2):
                    banners.append({
                        'src': bg_data['src'],
                        'alt': 'Background banner image',
                        'width': int(width),
                        'height': int(height),
                        'type': 'Background Banner'
                    })
            
            print(f"Found {len(banners)} banner images")
            
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
            print(f"Error during scraping: {e}")
            if 'browser' in locals():
                browser.close()
            return []