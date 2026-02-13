import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import sys
import time

def extract_all_banners(soup, base_url):
    """Extract ALL banner images"""
    banners = []
    seen_urls = set()
    
    print("🔍 Analyzing page content...\n")
    
    # Find ALL images with Rails storage
    rails_images = soup.find_all('img', src=re.compile(r'/cms/rails/active_storage'))
    print(f"📦 Rails storage images: {len(rails_images)}")
    
    for img in rails_images:
        src = img.get('src', '')
        if src and src not in seen_urls:
            seen_urls.add(src)
            if not src.startswith('http'):
                src = urljoin(base_url, src)
            
            alt = img.get('alt', 'Banner')
            banners.append({
                'src': src,
                'alt': alt,
                'type': 'Promotion Banner'
            })
    
    # Find promotion cards
    cards = soup.find_all('div', class_='promotions-card')
    print(f"🎴 Promotion cards: {len(cards)}")
    
    for card in cards:
        title = card.find('h4', class_='promotions-card__title')
        title_text = title.text.strip() if title else 'Promo'
        
        img = card.find('img')
        if img:
            src = img.get('src', '')
            if src and src not in seen_urls:
                seen_urls.add(src)
                if not src.startswith('http'):
                    src = urljoin(base_url, src)
                
                banners.append({
                    'src': src,
                    'alt': title_text,
                    'type': 'Promotion Card'
                })
        else:
            print(f"  ⚠️  Empty card: {title_text}")
    
    # Hero banner
    hero = soup.find('img', class_='casino-promotions__background')
    if hero:
        src = hero.get('src', '')
        if src and src not in seen_urls:
            seen_urls.add(src)
            if not src.startswith('http'):
                src = urljoin(base_url, src)
            banners.append({
                'src': src,
                'alt': 'Hero Banner',
                'type': 'Hero'
            })
    
    return banners

def scrape_simple(url, api_key, country='us'):
    """Simple, reliable ScraperAPI scraping"""
    
    api_url = 'http://api.scraperapi.com'
    
    # SIMPLIFIED parameters - more reliable
    params = {
        'api_key': api_key,
        'url': url,
        'country_code': country,
        'render': 'true',
        'timeout': 30000,  # 30 seconds timeout
    }
    
    print(f"\n{'='*70}")
    print(f"  🌐 ScraperAPI Simple & Reliable")
    print(f"{'='*70}\n")
    print(f"🎯 URL: {url}")
    print(f"📍 Country: {country.upper()}")
    print(f"⏳ Fetching with JavaScript rendering...\n")
    
    try:
        response = requests.get(api_url, params=params, timeout=60)
        response.raise_for_status()
        
        print(f"✅ Success! Status: {response.status_code}")
        print(f"📊 Size: {len(response.content):,} bytes\n")
        
        # Save HTML
        with open('scraperapi_final.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"💾 Saved: scraperapi_final.html\n")
        
        # Parse
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print(f"{'='*70}")
        print(f"  🔍 EXTRACTING BANNERS")
        print(f"{'='*70}\n")
        
        banners = extract_all_banners(soup, url)
        
        print(f"\n{'='*70}")
        print(f"✅ Found {len(banners)} banners")
        print(f"{'='*70}\n")
        
        return banners
        
    except requests.HTTPError as e:
        if e.response.status_code == 500:
            print(f"❌ ScraperAPI Error 500 - Their server had an issue")
            print(f"   This usually means:")
            print(f"   • The target site is very difficult to scrape")
            print(f"   • Try again in a few minutes")
            print(f"   • Try a different country code")
        elif e.response.status_code == 403:
            print(f"❌ Error 403 - Website blocked the request")
            print(f"   Even ScraperAPI couldn't bypass this site's protection")
        else:
            print(f"❌ HTTP Error: {e}")
        return []
    except requests.Timeout:
        print(f"❌ Timeout - Request took too long")
        return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def main():
    print("\n" + "=" * 70)
    print("  🎯 ScraperAPI Final Version (Simple & Reliable)")
    print("=" * 70)
    print("\nSimplified version - removes problematic parameters")
    print("=" * 70 + "\n")
    
    api_key = input("🔑 ScraperAPI key: ").strip()
    if not api_key:
        print("❌ API key required")
        sys.exit(1)
    
    url = input("🌐 Website URL: ").strip()
    if not url:
        print("❌ URL required")
        sys.exit(1)
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    print("\n📍 Countries: us, uk, ca, au, de, fr, jp, sg")
    country = input("🗺️  Country (default: ca): ").strip().lower() or 'ca'
    
    print("\n" + "=" * 70)
    
    # Scrape
    banners = scrape_simple(url, api_key, country)
    
    # Results
    print("=" * 70)
    print("  📊 RESULTS")
    print("=" * 70 + "\n")
    
    if banners:
        print(f"✅ SUCCESS! Found {len(banners)} banners\n")
        
        for i, b in enumerate(banners, 1):
            print(f"{i}. {b['type']}: {b['alt']}")
            print(f"   {b['src'][:70]}...")
            print()
        
        # Save
        with open('banners.txt', 'w', encoding='utf-8') as f:
            f.write(f"Banners from {url}\n")
            f.write(f"Country: {country}\n")
            f.write(f"Total: {len(banners)}\n\n")
            for i, b in enumerate(banners, 1):
                f.write(f"{i}. {b['alt']}\n")
                f.write(f"   {b['src']}\n\n")
        
        print(f"💾 Saved to: banners.txt")
        
    else:
        print("❌ No banners found")
        print("\n💡 Check scraperapi_final.html to see what was captured")
    
    print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    main()