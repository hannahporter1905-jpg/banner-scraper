import sys
import os
import json
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from directives.scrape_banners_stealth import scrape_website_banners_stealth

def save_results(url, banners, location):
    """Save scraping results to a JSON file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"banner_results_{timestamp}.json"
    
    data = {
        'url': url,
        'location': location,
        'timestamp': datetime.now().isoformat(),
        'total_banners': len(banners),
        'banners': banners
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to: {filename}")

def main():
    """Main execution function for stealth scraping"""
    
    # Interactive mode
    if len(sys.argv) < 2:
        print("\n" + "=" * 70)
        print("     🕵️  STEALTH Banner Image Scraper (Advanced Version)")
        print("=" * 70)
        
        # Get URL
        url = input("\n🌐 Enter website URL: ").strip()
        
        if not url:
            print("❌ Error: URL cannot be empty")
            sys.exit(1)
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Show locations
        print("\n📍 Available Locations:")
        print("  1. 🇺🇸 US - United States (San Francisco)")
        print("  2. 🇬🇧 UK - United Kingdom (London)")
        print("  3. 🇩🇪 DE - Germany (Berlin)")
        print("  4. 🇫🇷 FR - France (Paris)")
        print("  5. 🇯🇵 JP - Japan (Tokyo)")
        print("  6. 🇦🇺 AU - Australia (Sydney)")
        print("  7. 🇨🇦 CA - Canada (Toronto)")
        print("  8. 🇧🇷 BR - Brazil (São Paulo)")
        print("  9. 🇮🇳 IN - India (New Delhi)")
        print(" 10. 🇸🇬 SG - Singapore")
        
        location_input = input("\n🗺️  Select location (1-10 or country code, default: US): ").strip().upper()
        
        location_map = {
            '1': 'US', '2': 'UK', '3': 'DE', '4': 'FR', '5': 'JP',
            '6': 'AU', '7': 'CA', '8': 'BR', '9': 'IN', '10': 'SG'
        }
        
        if location_input in location_map:
            location = location_map[location_input]
        elif location_input in ['US', 'UK', 'DE', 'FR', 'JP', 'AU', 'CA', 'BR', 'IN', 'SG']:
            location = location_input
        else:
            location = 'US'
            print(f"ℹ️  Using default: US")
        
        # Browser visibility
        visible_input = input("\n👁️  Show browser window? (y/n, default: n): ").strip().lower()
        headless = visible_input not in ['y', 'yes']
        
        # Proxy option
        proxy_input = input("\n🔒 Use proxy? Enter proxy URL or press Enter to skip: ").strip()
        proxy = proxy_input if proxy_input else None
        
        # Save results option
        save_input = input("\n💾 Save results to file? (y/n, default: y): ").strip().lower()
        save_results_option = save_input not in ['n', 'no']
        
    else:
        print("Usage: Just run the script without arguments for interactive mode")
        print("Example: py execution\\scrape_stealth.py")
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("     🕵️  STEALTH Banner Image Scraper")
    print("=" * 70)
    print(f"\n🎯 Target URL: {url}")
    print(f"🗺️  Location: {location}")
    print(f"👁️  Mode: {'Visible Browser' if not headless else 'Headless (Hidden)'}")
    if proxy:
        print(f"🔒 Proxy: {proxy}")
    print("\n⏳ This may take 15-45 seconds depending on the website...")
    print("   Using advanced stealth techniques to avoid detection...")
    print("-" * 70 + "\n")
    
    # Scrape the website
    try:
        banners = scrape_website_banners_stealth(
            url, 
            headless=headless, 
            location=location,
            proxy=proxy
        )
        
        print("\n" + "=" * 70)
        
        if banners:
            print(f"\n✅ SUCCESS! Found {len(banners)} banner image(s)!\n")
            
            for i, banner in enumerate(banners, 1):
                print(f"📸 Banner #{i}: {banner['type']}")
                print(f"   🔗 URL: {banner['src'][:100]}{'...' if len(banner['src']) > 100 else ''}")
                print(f"   📝 Alt: {banner['alt'][:60]}{'...' if len(banner['alt']) > 60 else ''}")
                print(f"   📐 Size: {banner['width']} x {banner['height']}px")
                print()
            
            # Save results if requested
            if save_results_option:
                save_results(url, banners, location)
        else:
            print("\n⚠️  No banner images found on this website.\n")
            print("Possible reasons:")
            print("  • The website has no banner images")
            print("  • The website uses advanced bot detection")
            print("  • Images are loaded via complex JavaScript")
            print("  • Try using --visible mode to see what's happening")
            print("  • Try a different location")
        
        print("=" * 70 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Scraping cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print("\nTroubleshooting:")
        print("  1. Make sure Playwright is installed: py -m pip install playwright")
        print("  2. Make sure browsers are installed: py -m playwright install chromium")
        print("  3. Check your internet connection")
        print("  4. Try with --visible mode to debug")
        sys.exit(1)

if __name__ == "__main__":
    main()