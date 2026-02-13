import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sys
import os

def scrape_with_scraperapi_debug(url, api_key, country_code='us'):
    """
    Debug version - shows you exactly what ScraperAPI returns
    """
    
    api_url = 'http://api.scraperapi.com'
    
    params = {
        'api_key': api_key,
        'url': url,
        'country_code': country_code,
        'render': 'true',  # Enable JavaScript rendering
    }
    
    print(f"\n🌐 Sending request through ScraperAPI...")
    print(f"📍 Country: {country_code.upper()}")
    print(f"🔗 Target: {url}")
    print(f"⏳ Please wait (this may take 10-30 seconds)...\n")
    
    try:
        response = requests.get(api_url, params=params, timeout=90)
        response.raise_for_status()
        
        print("✅ Successfully retrieved page!")
        print(f"📊 Status Code: {response.status_code}")
        print(f"📊 Page size: {len(response.content)} bytes")
        print(f"📊 Content Type: {response.headers.get('Content-Type', 'unknown')}\n")
        
        # Save the HTML to a file so you can inspect it
        debug_filename = 'scraperapi_debug.html'
        with open(debug_filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"💾 Saved raw HTML to: {debug_filename}")
        print(f"   → You can open this file in a browser to see what was retrieved\n")
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Show page title
        title = soup.find('title')
        print(f"📄 Page Title: {title.text if title else 'No title found'}\n")
        
        # Show first 500 characters of text
        page_text = soup.get_text()[:500]
        print(f"📝 First 500 characters of page text:")
        print(f"{'='*70}")
        print(page_text)
        print(f"{'='*70}\n")
        
        # Find ALL images (not just banners)
        all_images = soup.find_all('img')
        print(f"🖼️  Total <img> tags found: {len(all_images)}\n")
        
        if all_images:
            print("📸 All images found:")
            print(f"{'='*70}")
            for i, img in enumerate(all_images[:20], 1):  # Show first 20
                src = img.get('src', 'NO SRC')
                alt = img.get('alt', 'NO ALT')
                width = img.get('width', 'auto')
                height = img.get('height', 'auto')
                classes = img.get('class', [])
                
                print(f"\n  Image #{i}:")
                print(f"    SRC: {src[:100]}{'...' if len(src) > 100 else ''}")
                print(f"    ALT: {alt[:60]}{'...' if len(alt) > 60 else ''}")
                print(f"    SIZE: {width} x {height}")
                print(f"    CLASSES: {', '.join(classes) if classes else 'none'}")
            
            if len(all_images) > 20:
                print(f"\n  ... and {len(all_images) - 20} more images")
            print(f"{'='*70}\n")
        else:
            print("❌ No <img> tags found on the page!\n")
            print("🔍 Checking for background images in CSS...")
        
        # Check for background images
        bg_elements = soup.find_all(style=lambda x: x and 'background-image' in x)
        print(f"🎨 Elements with background-image: {len(bg_elements)}\n")
        
        if bg_elements:
            print("Background images found:")
            print(f"{'='*70}")
            for i, elem in enumerate(bg_elements[:10], 1):
                style = elem.get('style', '')
                print(f"\n  BG Image #{i}:")
                print(f"    STYLE: {style[:100]}{'...' if len(style) > 100 else ''}")
                print(f"    TAG: <{elem.name}>")
                print(f"    CLASSES: {elem.get('class', [])}")
            print(f"{'='*70}\n")
        
        # Check for common banner containers
        print("🔍 Checking for common banner containers:")
        print(f"{'='*70}")
        banner_selectors = [
            ('header', soup.find_all('header')),
            ('.hero', soup.select('.hero')),
            ('.banner', soup.select('.banner')),
            ('.slider', soup.select('.slider')),
            ('.carousel', soup.select('.carousel')),
            ('#hero', soup.select('#hero')),
        ]
        
        for selector, elements in banner_selectors:
            if elements:
                print(f"  ✅ Found {len(elements)} element(s) matching '{selector}'")
                for elem in elements[:3]:
                    imgs_inside = elem.find_all('img')
                    print(f"      → Contains {len(imgs_inside)} images")
            else:
                print(f"  ❌ No elements matching '{selector}'")
        
        print(f"{'='*70}\n")
        
        # Check if page looks like a redirect or error
        if len(response.text) < 5000:
            print("⚠️  WARNING: Page content is very small!")
            print("   This might be a redirect, login page, or error page.\n")
        
        # Look for common blocking messages
        blocking_keywords = ['captcha', 'access denied', 'forbidden', 'blocked', 'cloudflare', 'robot']
        found_blocks = []
        for keyword in blocking_keywords:
            if keyword in response.text.lower():
                found_blocks.append(keyword)
        
        if found_blocks:
            print(f"🚫 Possible blocking detected! Found keywords: {', '.join(found_blocks)}\n")
        
        return all_images
        
    except requests.RequestException as e:
        print(f"❌ Error: {e}")
        return []

def main():
    """Interactive debug scraper"""
    
    print("\n" + "=" * 70)
    print("  🔍 ScraperAPI DEBUG Mode - See Exactly What Was Retrieved")
    print("=" * 70)
    print("\nThis version shows you:")
    print("  • The actual HTML content retrieved")
    print("  • All images found (not just banners)")
    print("  • Page structure and containers")
    print("  • Potential blocking issues")
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
    
    # Scrape and debug
    images = scrape_with_scraperapi_debug(url, api_key, country)
    
    print("=" * 70)
    print("  ✅ DEBUG COMPLETE")
    print("=" * 70)
    print(f"\n📁 Check the file 'scraperapi_debug.html' to see the actual page")
    print(f"   Right-click the file → Open with → Your Browser\n")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()