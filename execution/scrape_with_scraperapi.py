import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os

def is_banner_image(img, soup):
    """Determine if an image is likely a banner"""
    width = img.get('width', '0')
    height = img.get('height', '0')
    src = img.get('src', '')
    
    try:
        width = int(str(width).replace('px', ''))
        height = int(str(height).replace('px', ''))
    except (ValueError, TypeError):
        width = 0
        height = 0
    
    if width > 0 and height > 0:
        aspect_ratio = width / height
        if aspect_ratio > 2 and width > 600:
            return True
    
    banner_keywords = [
        'banner', 'hero', 'slider', 'carousel', 
        'header', 'jumbotron', 'masthead'
    ]
    
    parent = img.parent
    if parent:
        parent_class = ' '.join(parent.get('class', [])).lower()
        parent_id = parent.get('id', '').lower()
        
        for keyword in banner_keywords:
            if keyword in parent_class or keyword in parent_id or keyword in src.lower():
                return True
    
    if width > 1000:
        return True
    
    return False

def scrape_with_scraperapi(url, api_key, country_code='us'):
    """
    Scrape using ScraperAPI - bypasses geo-restrictions and bot detection.
    
    Sign up at: https://www.scraperapi.com (1,000 free requests/month)
    
    Args:
        url: Target website URL
        api_key: Your ScraperAPI key
        country_code: Country code (us, uk, ca, de, fr, jp, au, etc.)
    
    Returns:
        list: Banner images found
    """
    
    banners = []
    
    # ScraperAPI endpoint
    api_url = 'http://api.scraperapi.com'
    
    params = {
        'api_key': api_key,
        'url': url,
        'country_code': country_code,
        'render': 'true',  # Enable JavaScript rendering
        'premium': 'true'  # Use premium proxies (costs more credits but more reliable)
    }
    
    print(f"\n🌐 Sending request through ScraperAPI...")
    print(f"📍 Country: {country_code.upper()}")
    print(f"⏳ Please wait (this may take 10-30 seconds)...\n")
    
    try:
        response = requests.get(api_url, params=params, timeout=60)
        response.raise_for_status()
        
        print("✅ Successfully retrieved page!")
        print(f"📊 Page size: {len(response.content)} bytes\n")
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find images
        images = soup.find_all('img')
        print(f"🔍 Found {len(images)} total images")
        
        for img in images:
            if is_banner_image(img, soup):
                src = img.get('src', '')
                
                if src and not src.startswith('data:'):
                    if not src.startswith('http'):
                        src = urljoin(url, src)
                    
                    banners.append({
                        'src': src,
                        'alt': img.get('alt', 'Banner image'),
                        'width': img.get('width', 'auto'),
                        'height': img.get('height', 'auto'),
                        'type': 'Banner Image'
                    })
        
        # Check background images
        elements_with_bg = soup.find_all(
            lambda tag: tag.get('style') and 'background-image' in tag.get('style', '')
        )
        
        for elem in elements_with_bg:
            style = elem.get('style', '')
            if 'url(' in style:
                start = style.find('url(') + 4
                end = style.find(')', start)
                
                if end > start:
                    bg_url = style[start:end].strip('\'"')
                    
                    if bg_url and not bg_url.startswith('data:'):
                        if not bg_url.startswith('http'):
                            bg_url = urljoin(url, bg_url)
                        
                        banners.append({
                            'src': bg_url,
                            'alt': 'Background banner',
                            'width': 'auto',
                            'height': 'auto',
                            'type': 'Background Banner'
                        })
        
        print(f"✅ Found {len(banners)} banner images\n")
        return banners
        
    except requests.RequestException as e:
        print(f"❌ Error: {e}")
        return []

def main():
    """Interactive ScraperAPI scraper"""
    
    print("\n" + "=" * 70)
    print("  🔑 ScraperAPI Banner Scraper (Premium - Bypasses Everything)")
    print("=" * 70)
    print("\n📝 Get your FREE API key at: https://www.scraperapi.com")
    print("   (1,000 free requests per month)\n")
    
    # Get API key
    api_key = input("🔑 Enter your ScraperAPI key: ").strip()
    
    if not api_key:
        print("\n❌ API key is required!")
        print("   Sign up at: https://www.scraperapi.com")
        sys.exit(1)
    
    # Get URL
    url = input("\n🌐 Enter website URL: ").strip()
    
    if not url:
        print("❌ URL cannot be empty")
        sys.exit(1)
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Get country
    print("\n📍 Available Countries:")
    print("  us, uk, ca, au, de, fr, jp, sg, br, in, and more...")
    
    country = input("\n🗺️  Enter country code (default: us): ").strip().lower()
    if not country:
        country = 'us'
    
    print("\n" + "=" * 70)
    
    # Scrape
    banners = scrape_with_scraperapi(url, api_key, country)
    
    # Display results
    print("=" * 70)
    print("  📊 RESULTS")
    print("=" * 70 + "\n")
    
    if banners:
        print(f"✅ SUCCESS! Found {len(banners)} banner(s)\n")
        
        for i, banner in enumerate(banners, 1):
            print(f"Banner #{i}: {banner['type']}")
            print(f"  🔗 {banner['src'][:100]}{'...' if len(banner['src']) > 100 else ''}")
            print(f"  📐 {banner['width']} x {banner['height']}")
            print()
    else:
        print("❌ No banners found")
    
    print("=" * 70 + "\n")

if __name__ == "__main__":
    import sys
    main()