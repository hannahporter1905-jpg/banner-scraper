import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
import time
import random

def is_banner_image(img_data):
    """Determine if image is a banner"""
    width = img_data.get('width', 0)
    height = img_data.get('height', 0)
    src = img_data.get('src', '').lower()
    alt = img_data.get('alt', '').lower()
    classes = img_data.get('class', '').lower()
    
    banner_keywords = [
        'banner', 'hero', 'slider', 'carousel', 'promo',
        'deposit', 'fortune', 'funday', 'wheel', 'spin'
    ]
    
    # Check aspect ratio
    if width > 0 and height > 0:
        aspect_ratio = width / height
        if aspect_ratio > 2.0 and width > 500:
            return True
    
    # Check width
    if width > 1000:
        return True
    
    # Check keywords
    for keyword in banner_keywords:
        if keyword in src or keyword in alt or keyword in classes:
            return True
    
    return False

def scrape_with_proxy(url, proxy_url=None, headless=True):
    """
    Scrape using Playwright with optional proxy support
    
    Args:
        url: Target website
        proxy_url: Proxy in format "http://username:password@proxy:port" or "http://proxy:port"
        headless: Run headless or visible
    
    Returns:
        list: Banner images found
    """
    
    banners = []
    
    print(f"\n{'='*70}")
    print(f"  🕵️  Playwright with Proxy Support")
    print(f"{'='*70}\n")
    
    if proxy_url:
        print(f"🔒 Using proxy: {proxy_url.split('@')[-1] if '@' in proxy_url else proxy_url}")
    else:
        print(f"⚠️  No proxy - direct connection (may be geo-blocked)")
    
    print(f"🎯 Target: {url}")
    print(f"👁️  Mode: {'Headless' if headless else 'Visible'}\n")
    
    with sync_playwright() as p:
        try:
            # Browser launch args
            launch_args = {
                'headless': headless,
                'args': [
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                ]
            }
            
            browser = p.chromium.launch(**launch_args)
            
            # Context options
            context_options = {
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
            
            # Add proxy if provided
            if proxy_url:
                # Parse proxy URL
                if '@' in proxy_url:
                    # Format: http://username:password@host:port
                    parts = proxy_url.split('@')
                    auth_part = parts[0].replace('http://', '').replace('https://', '')
                    host_part = parts[1]
                    
                    if ':' in auth_part:
                        username, password = auth_part.split(':', 1)
                        context_options['proxy'] = {
                            'server': f'http://{host_part}',
                            'username': username,
                            'password': password
                        }
                    else:
                        context_options['proxy'] = {'server': proxy_url}
                else:
                    # Format: http://host:port
                    context_options['proxy'] = {'server': proxy_url}
            
            context = browser.new_context(**context_options)
            
            # Anti-detection
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            page = context.new_page()
            
            print(f"🌐 Navigating to page...")
            page.goto(url, wait_until='domcontentloaded', timeout=45000)
            
            print(f"⏳ Waiting for content to load...")
            time.sleep(random.uniform(2, 3))
            
            # SCROLL to load lazy images
            print(f"📜 Scrolling to load ALL images...")
            for i in range(4):
                scroll_pos = (i + 1) * 25  # 25%, 50%, 75%, 100%
                page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {scroll_pos / 100})")
                print(f"   → Scrolled to {scroll_pos}%")
                time.sleep(random.uniform(1, 2))
            
            # Scroll back to top
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(1)
            
            print(f"\n🔍 Extracting images...")
            
            # Extract all images
            images_data = page.evaluate("""
                () => {
                    const images = [];
                    const imgElements = document.querySelectorAll('img');
                    
                    imgElements.forEach(img => {
                        const rect = img.getBoundingClientRect();
                        const style = window.getComputedStyle(img);
                        
                        images.push({
                            src: img.currentSrc || img.src || img.getAttribute('data-src') || '',
                            alt: img.alt || '',
                            width: Math.max(rect.width, img.naturalWidth, img.width) || 0,
                            height: Math.max(rect.height, img.naturalHeight, img.height) || 0,
                            class: img.className || '',
                            visible: style.display !== 'none' && style.visibility !== 'hidden'
                        });
                    });
                    
                    return images;
                }
            """)
            
            print(f"📊 Found {len(images_data)} total images\n")
            
            # Filter for banners
            for img_data in images_data:
                if not img_data['visible'] or not img_data['src']:
                    continue
                
                if img_data['src'].startswith('data:'):
                    continue
                
                if is_banner_image(img_data):
                    banners.append({
                        'src': img_data['src'],
                        'alt': img_data['alt'] or 'Banner',
                        'width': int(img_data['width']),
                        'height': int(img_data['height']),
                        'type': 'Banner Image'
                    })
            
            print(f"✅ Identified {len(banners)} banner images")
            
            browser.close()
            
            # Remove duplicates
            seen = set()
            unique = []
            for b in banners:
                if b['src'] not in seen:
                    seen.add(b['src'])
                    unique.append(b)
            
            return unique
            
        except Exception as e:
            print(f"❌ Error: {e}")
            if 'browser' in locals():
                browser.close()
            return []

def main():
    """Interactive Playwright with proxy"""
    
    print("\n" + "=" * 70)
    print("  🕵️  Playwright Banner Scraper with Proxy Support")
    print("=" * 70)
    print("\n✨ This version:")
    print("  • Uses Playwright for full browser control")
    print("  • Scrolls to load ALL images (including lazy-loaded)")
    print("  • Supports proxies to bypass geo-restrictions")
    print("=" * 70 + "\n")
    
    # Get URL
    url = input("🌐 Enter website URL: ").strip()
    if not url:
        print("❌ URL required")
        sys.exit(1)
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Get proxy
    print("\n🔒 Proxy Configuration:")
    print("  Formats supported:")
    print("    • http://proxy:port")
    print("    • http://username:password@proxy:port")
    print("    • https://proxy:port")
    print("\n  Free proxy sources:")
    print("    • https://www.webshare.io (10 free proxies)")
    print("    • https://proxyscrape.com (free list)")
    print("    • https://www.proxy-list.download/")
    
    proxy = input("\n🔗 Enter proxy URL (or press Enter to skip): ").strip()
    
    # Visible mode
    visible = input("\n👁️  Show browser? (y/n, default: n): ").strip().lower()
    headless = visible not in ['y', 'yes']
    
    print("\n" + "=" * 70)
    
    # Scrape
    banners = scrape_with_proxy(url, proxy if proxy else None, headless)
    
    # Results
    print("\n" + "=" * 70)
    print("  📊 RESULTS")
    print("=" * 70 + "\n")
    
    if banners:
        print(f"✅ SUCCESS! Found {len(banners)} banner(s)\n")
        
        for i, b in enumerate(banners, 1):
            print(f"📸 Banner #{i}")
            print(f"   Alt: {b['alt'][:50]}")
            print(f"   Size: {b['width']} x {b['height']}px")
            print(f"   URL: {b['src'][:70]}...")
            print()
        
        # Save
        with open('playwright_proxy_results.txt', 'w', encoding='utf-8') as f:
            f.write(f"Scraped from: {url}\n")
            f.write(f"Proxy used: {proxy if proxy else 'None (direct)'}\n")
            f.write(f"Total banners: {len(banners)}\n\n")
            
            for i, b in enumerate(banners, 1):
                f.write(f"Banner #{i}\n")
                f.write(f"  Alt: {b['alt']}\n")
                f.write(f"  Size: {b['width']} x {b['height']}px\n")
                f.write(f"  URL: {b['src']}\n\n")
        
        print(f"💾 Saved to: playwright_proxy_results.txt")
        
    else:
        print("❌ No banners found")
        print("\n💡 Troubleshooting:")
        print("  • Check if proxy is working")
        print("  • Try --visible mode to see what's happening")
        print("  • Try a different proxy")
    
    print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    main()