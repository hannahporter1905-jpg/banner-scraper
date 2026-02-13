import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from directives.scrape_banners import scrape_website_banners

def main():
    """Main execution function for scraping a single website"""
    
    # Get URL from command-line arg or prompt the user
    if len(sys.argv) >= 2:
        url = sys.argv[1]
    else:
        print("=" * 60)
        print("Banner Image Scraper")
        print("=" * 60)
        url = input("\nEnter website URL: ").strip()

    if not url:
        print("Error: No URL provided.")
        sys.exit(1)

    # Auto-add https:// if no scheme provided
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    print("\n" + "=" * 60)
    print("Banner Image Scraper")
    print("=" * 60)
    print(f"\nTarget URL: {url}")
    print("Scanning website for banner images...")
    print("-" * 60)
    
    # Scrape the website
    try:
        banners = scrape_website_banners(url)
        
        if banners:
            print(f"\n[+] Found {len(banners)} banner image(s)!\n")
            
            for i, banner in enumerate(banners, 1):
                print(f"{i}. {banner['type']}")
                print(f"   URL: {banner['src']}")
                print(f"   Alt Text: {banner['alt']}")
                print(f"   Dimensions: {banner['width']} x {banner['height']}")
                print()
        else:
            print("\n[-] No banner images found on this website.")
            print("\nPossible reasons:")
            print("  - The website has no banner images")
            print("  - The website blocks web scraping")
            print("  - Images are loaded dynamically with JavaScript")
        
        print("=" * 60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\nScraping cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[-] Error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()