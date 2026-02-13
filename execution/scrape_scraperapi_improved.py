import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import sys

def extract_banner_images(soup, base_url):
    """
    Extract ALL banner images including those with Rails storage paths
    and empty src attributes that load via JavaScript
    """
    banners = []
    
    # Method 1: Find images with Rails storage redirect URLs
    images_with_src = soup.find_all('img', src=re.compile(r'/cms/rails/active_storage'))
    
    print(f"🔍 Found {len(images_with_src)} images with Rails storage paths")
    
    for img in images_with_src:
        src = img.get('src', '')
        alt = img.get('alt', 'Banner image')
        
        if src:
            # Make sure it's an absolute URL
            if not src.startswith('http'):
                src = urljoin(base_url, src)
            
            banners.append({
                'src': src,
                'alt': alt,
                'width': 'auto',
                'height': 'auto',
                'type': 'Promotion Banner',
                'location': 'Rails Storage'
            })
    
    # Method 2: Find promotion cards (even with empty src)
    promo_cards = soup.find_all('div', class_='promotions-card')
    
    print(f"🎴 Found {len(promo_cards)} promotion cards")
    
    for card in promo_cards:
        # Get the title for better identification
        title_elem = card.find('h4', class_='promotions-card__title')
        title = title_elem.text.strip() if title_elem else 'Unknown Promotion'
        
        # Get the image
        img = card.find('img', class_='promotions-card__background')
        
        if img:
            src = img.get('src', '')
            alt = img.get('alt', title)
            
            # Even if src is empty, record it with the title
            if src:
                if not src.startswith('http'):
                    src = urljoin(base_url, src)
                
                # Check if not already added
                if not any(b['src'] == src for b in banners):
                    banners.append({
                        'src': src,
                        'alt': alt,
                        'title': title,
                        'width': 'auto',
                        'height': 'auto',
                        'type': 'Promotion Card',
                        'location': 'Promotion Block'
                    })
            else:
                # Empty src - record for debugging
                print(f"  ⚠️  Found card with empty image: {title}")
    
    # Method 3: Find the top banner (hero section)
    top_banner = soup.find('img', class_='casino-promotions__background')
    if top_banner:
        src = top_banner.get('src', '')
        if src and not src.startswith('data:'):
            if not src.startswith('http'):
                src = urljoin(base_url, src)
            
            banners.append({
                'src': src,
                'alt': 'Top Hero Banner',
                'title': 'Welcome Package Banner',
                'width': 'auto',
                'height': 'auto',
                'type': 'Hero Banner',
                'location': 'Top Section'
            })
            print(f"✅ Found hero banner")
    
    # Method 4: Find all images with specific alt text patterns
    all_imgs = soup.find_all('img')
    banner_keywords = ['deposit', 'promo', 'banner', 'fortune', 'funday', 'spin', 'wheel']
    
    for img in all_imgs:
        alt = img.get('alt', '').lower()
        src = img.get('src', '')
        
        if any(keyword in alt for keyword in banner_keywords):
            if src and not src.startswith('data:'):
                if not src.startswith('http'):
                    src = urljoin(base_url, src)
                
                # Check if not already added
                if not any(b['src'] == src for b in banners):
                    banners.append({
                        'src': src,
                        'alt': img.get('alt', 'Banner'),
                        'width': img.get('width', 'auto'),
                        'height': img.get('height', 'auto'),
                        'type': 'Promotional Image',
                        'location': 'Page Content'
                    })
    
    return banners

def scrape_with_scraperapi_improved(url, api_key, country_code='us'):
    """
    Improved scraper that finds ALL banner images including dynamically loaded ones
    """
    
    api_url = 'http://api.scraperapi.com'
    
    params = {
        'api_key': api_key,
        'url': url,
        'country_code': country_code,
        'render': 'true',  # Enable JavaScript rendering
        'wait_for': '5',   # Wait 5 seconds for JavaScript to load
    }
    
    print(f"\n🌐 Sending request through ScraperAPI...")
    print(f"📍 Country: {country_code.upper()}")
    print(f"⏳ Waiting for JavaScript to load (this takes longer but gets more images)...\n")
    
    try:
        response = requests.get(api_url, params=params, timeout=90)
        response.raise_for_status()
        
        print("✅ Successfully retrieved page!")
        print(f"📊 Status Code: {response.status_code}")
        print(f"📊 Page size: {len(response.content)} bytes\n")
        
        # Save debug HTML
        with open('scraperapi_improved_debug.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"💾 Saved HTML to: scraperapi_improved_debug.html\n")
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Show page title
        title = soup.find('title')
        print(f"📄 Page Title: {title.text if title else 'No title found'}\n")
        
        print("=" * 70)
        print("  🔍 EXTRACTING BANNER IMAGES")
        print("=" * 70 + "\n")
        
        # Extract all banner images using multiple methods
        banners = extract_banner_images(soup, url)
        
        print(f"\n{'='*70}")
        print(f"✅ Total unique banners found: {len(banners)}")
        print(f"{'='*70}\n")
        
        return banners
        
    except requests.RequestException as e:
        print(f"❌ Error: {e}")
        return []

def main():
    """Interactive improved scraper"""
    
    print("\n" + "=" * 70)
    print("  🎯 ScraperAPI IMPROVED - Finds ALL Banner Images")
    print("=" * 70)
    print("\n✨ Improvements:")
    print("  • Waits for JavaScript to fully load")
    print("  • Extracts Rails storage URLs")
    print("  • Finds promotion cards even with empty images")
    print("  • Multiple detection methods")
    print("=" * 70 + "\n")
    
    # Get API key
    api_key = input("🔑 Enter your ScraperAPI key: ").strip()
    
    if not api_key:
        print("\n❌ API key is required!")
        sys.exit(1)
    
    # Get URL
    url = input("\n🌐 Enter website URL: ").strip()
    
    if not url:
        print("❌ URL cannot be empty")
        sys.exit(1)
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Get country
    print("\n📍 Available Countries: us, uk, ca, au, de, fr, jp, sg, br, in")
    country = input("🗺️  Enter country code (default: us): ").strip().lower()
    if not country:
        country = 'us'
    
    print("\n" + "=" * 70)
    
    # Scrape
    banners = scrape_with_scraperapi_improved(url, api_key, country)
    
    # Display results
    print("=" * 70)
    print("  📊 DETAILED RESULTS")
    print("=" * 70 + "\n")
    
    if banners:
        print(f"✅ SUCCESS! Found {len(banners)} banner image(s)\n")
        
        for i, banner in enumerate(banners, 1):
            print(f"{'─'*70}")
            print(f"📸 Banner #{i}")
            print(f"{'─'*70}")
            print(f"  🏷️  Type: {banner['type']}")
            if 'title' in banner:
                print(f"  📝 Title: {banner['title']}")
            print(f"  💬 Alt Text: {banner['alt']}")
            print(f"  📍 Location: {banner.get('location', 'Unknown')}")
            print(f"  🔗 URL: {banner['src'][:100]}{'...' if len(banner['src']) > 100 else ''}")
            print(f"  📐 Size: {banner['width']} x {banner['height']}")
            print()
        
        # Save results to file
        print(f"{'='*70}")
        print("💾 Saving results to file...")
        
        with open('banner_results.txt', 'w', encoding='utf-8') as f:
            f.write("BANNER SCRAPING RESULTS\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Website: {url}\n")
            f.write(f"Total Banners: {len(banners)}\n\n")
            
            for i, banner in enumerate(banners, 1):
                f.write(f"\nBanner #{i}\n")
                f.write(f"  Type: {banner['type']}\n")
                if 'title' in banner:
                    f.write(f"  Title: {banner['title']}\n")
                f.write(f"  Alt: {banner['alt']}\n")
                f.write(f"  URL: {banner['src']}\n")
                f.write(f"  Size: {banner['width']} x {banner['height']}\n")
        
        print("✅ Results saved to: banner_results.txt")
        
    else:
        print("❌ No banners found")
        print("\n💡 Tip: Check scraperapi_improved_debug.html to see what was retrieved")
    
    print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    main()