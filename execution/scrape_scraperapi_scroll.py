import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import sys
import time

def extract_all_banners(soup, base_url):
    """Extract ALL banner images from the page"""
    banners = []
    seen_urls = set()
    
    print("🔍 Searching for banner images...\n")
    
    # Method 1: Find ALL images with Rails storage paths
    rails_images = soup.find_all('img', src=re.compile(r'/cms/rails/active_storage'))
    print(f"📦 Found {len(rails_images)} images with Rails storage paths")
    
    for img in rails_images:
        src = img.get('src', '')
        if src and src not in seen_urls:
            seen_urls.add(src)
            if not src.startswith('http'):
                src = urljoin(base_url, src)
            
            alt = img.get('alt', 'Promotion Banner')
            
            banners.append({
                'src': src,
                'alt': alt,
                'type': 'Promotion Banner',
                'source': 'Rails Storage'
            })
    
    # Method 2: Find ALL promotion cards (even with empty src)
    promo_cards = soup.find_all('div', class_='promotions-card')
    print(f"🎴 Found {len(promo_cards)} promotion card containers")
    
    for card in promo_cards:
        title_elem = card.find('h4', class_='promotions-card__title')
        title = title_elem.text.strip() if title_elem else 'Promotion'
        
        text_elem = card.find('p', class_='promotions-card__text')
        description = text_elem.text.strip() if text_elem else ''
        
        # Record even if no image (for debugging)
        img = card.find('img', class_='promotions-card__background')
        if img:
            src = img.get('src', '')
            if src and src not in seen_urls:
                seen_urls.add(src)
                if not src.startswith('http'):
                    src = urljoin(base_url, src)
                
                banners.append({
                    'src': src,
                    'alt': img.get('alt', title),
                    'title': title,
                    'description': description[:50],
                    'type': 'Promotion Card',
                    'source': 'Card Container'
                })
        else:
            print(f"  ⚠️  Card found but no image: {title}")
    
    # Method 3: Hero/Top banner
    hero_banner = soup.find('img', class_='casino-promotions__background')
    if hero_banner:
        src = hero_banner.get('src', '')
        if src and src not in seen_urls:
            seen_urls.add(src)
            if not src.startswith('http'):
                src = urljoin(base_url, src)
            
            banners.append({
                'src': src,
                'alt': 'Welcome Package Banner',
                'title': 'Hero Banner',
                'description': 'Top welcome banner',
                'type': 'Hero Banner',
                'source': 'Top Section'
            })
            print(f"✅ Found hero banner")
    
    # Method 4: Find ANY image with promotional keywords
    all_images = soup.find_all('img')
    promo_keywords = ['deposit', 'promo', 'banner', 'fortune', 'funday', 'spin', 'wheel', 'bonus', 'mob']
    
    for img in all_images:
        src = img.get('src', '')
        alt = img.get('alt', '').lower()
        
        if src and src not in seen_urls:
            # Check if src contains promo keywords
            src_lower = src.lower()
            if any(keyword in alt or keyword in src_lower for keyword in promo_keywords):
                seen_urls.add(src)
                if not src.startswith('http'):
                    src = urljoin(base_url, src)
                
                banners.append({
                    'src': src,
                    'alt': img.get('alt', 'Promotional Image'),
                    'type': 'Promotional Image',
                    'source': 'Keyword Match'
                })
    
    return banners

def scrape_with_scroll(url, api_key, country_code='us'):
    """
    ScraperAPI with extended wait time and JavaScript rendering
    to allow page to fully load including lazy-loaded images
    """
    
    api_url = 'http://api.scraperapi.com'
    
    # Extended parameters for better image loading
    params = {
        'api_key': api_key,
        'url': url,
        'country_code': country_code,
        'render': 'true',           # Enable JavaScript
        'wait_for_selector': 'img', # Wait for images to appear
        'session_number': '123',    # Use same session for consistency
    }
    
    print(f"\n{'='*70}")
    print(f"  🌐 ScraperAPI with Extended Loading")
    print(f"{'='*70}\n")
    print(f"🎯 Target: {url}")
    print(f"📍 Country: {country_code.upper()}")
    print(f"⏳ Using JavaScript rendering with image waiting...")
    print(f"   (This ensures lazy-loaded images have time to appear)\n")
    
    try:
        # Make request
        print("🚀 Sending request to ScraperAPI...")
        response = requests.get(api_url, params=params, timeout=120)
        response.raise_for_status()
        
        print(f"✅ Success! Status: {response.status_code}")
        print(f"📊 Page size: {len(response.content):,} bytes\n")
        
        # Save debug HTML
        with open('scraperapi_scroll_debug.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"💾 Saved HTML to: scraperapi_scroll_debug.html")
        print(f"   (Open this in a browser to see what was captured)\n")
        
        # Parse
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract banners
        print(f"{'='*70}")
        print(f"  🔍 ANALYZING PAGE CONTENT")
        print(f"{'='*70}\n")
        
        banners = extract_all_banners(soup, url)
        
        print(f"\n{'='*70}")
        print(f"✅ Extraction complete!")
        print(f"📊 Total unique banners found: {len(banners)}")
        print(f"{'='*70}\n")
        
        return banners
        
    except requests.Timeout:
        print("❌ Error: Request timed out (took longer than 2 minutes)")
        print("   The website might be very slow or blocking the request")
        return []
    except requests.RequestException as e:
        print(f"❌ Error: {e}")
        return []

def main():
    print("\n" + "=" * 70)
    print("  🎯 ScraperAPI Banner Scraper (Optimized for All Images)")
    print("=" * 70)
    print("\n✨ Features:")
    print("  • Uses ScraperAPI to bypass geo-restrictions")
    print("  • Waits for images to load with JavaScript rendering")
    print("  • wait_for_selector ensures images appear before scraping")
    print("  • Multiple detection methods for maximum coverage")
    print("=" * 70 + "\n")
    
    # Get API key
    api_key = input("🔑 Enter your ScraperAPI key: ").strip()
    if not api_key:
        print("\n❌ API key required!")
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
    print("\n📍 Countries: us, uk, ca, au, de, fr, jp, sg, br, in")
    country = input("🗺️  Country code (default: us): ").strip().lower() or 'us'
    
    print("\n" + "=" * 70)
    
    # Scrape
    start_time = time.time()
    banners = scrape_with_scroll(url, api_key, country)
    elapsed = time.time() - start_time
    
    # Results
    print("=" * 70)
    print("  📊 FINAL RESULTS")
    print("=" * 70 + "\n")
    
    if banners:
        print(f"✅ SUCCESS! Found {len(banners)} banner image(s)")
        print(f"⏱️  Time taken: {elapsed:.1f} seconds\n")
        
        for i, banner in enumerate(banners, 1):
            print(f"{'─'*70}")
            print(f"📸 Banner #{i}")
            print(f"{'─'*70}")
            if 'title' in banner:
                print(f"  🏷️  Title: {banner['title']}")
            if 'description' in banner and banner['description']:
                print(f"  📝 Description: {banner['description']}")
            print(f"  💬 Alt: {banner['alt']}")
            print(f"  🔖 Type: {banner['type']}")
            print(f"  📍 Source: {banner['source']}")
            print(f"  🔗 URL: {banner['src'][:80]}{'...' if len(banner['src']) > 80 else ''}")
            print()
        
        # Save to file
        print(f"{'='*70}")
        print("💾 Saving results...")
        
        with open('banner_results.txt', 'w', encoding='utf-8') as f:
            f.write("BANNER SCRAPING RESULTS\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Website: {url}\n")
            f.write(f"Country: {country.upper()}\n")
            f.write(f"Total Banners: {len(banners)}\n")
            f.write(f"Time Taken: {elapsed:.1f} seconds\n\n")
            
            for i, banner in enumerate(banners, 1):
                f.write(f"\nBanner #{i}\n")
                f.write(f"{'─'*70}\n")
                if 'title' in banner:
                    f.write(f"Title: {banner['title']}\n")
                if 'description' in banner:
                    f.write(f"Description: {banner['description']}\n")
                f.write(f"Alt: {banner['alt']}\n")
                f.write(f"Type: {banner['type']}\n")
                f.write(f"Source: {banner['source']}\n")
                f.write(f"URL: {banner['src']}\n")
        
        print("✅ Results saved to: banner_results.txt")
        print("✅ HTML saved to: scraperapi_scroll_debug.html")
        
    else:
        print("❌ No banners found")
        print("\n💡 Tips:")
        print("  • Check scraperapi_scroll_debug.html to see what was captured")
        print("  • Try a different country code")
        print("  • Some sites may still block even with ScraperAPI")
    
    print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    main()