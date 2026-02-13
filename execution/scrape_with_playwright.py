import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from directives.scrape_banners_stealth import scrape_site_full

def main():
    """Main execution function — full site scrape (homepage + promotions)"""

    # Get URL from command-line arg or prompt the user
    if len(sys.argv) >= 2:
        url = sys.argv[1]
        headless = '--visible' not in sys.argv
        location = 'US'
        if '--location' in sys.argv:
            try:
                idx = sys.argv.index('--location')
                if idx + 1 < len(sys.argv):
                    location = sys.argv[idx + 1].upper()
            except (ValueError, IndexError):
                pass
    else:
        print("\n" + "=" * 60)
        print("        Banner Image Scraper (Full Site)")
        print("=" * 60)

        url = input("\nEnter website URL: ").strip()
        if not url:
            print("Error: URL cannot be empty")
            sys.exit(1)

        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        print("\nAvailable Locations:")
        print("  1. US    2. UK    3. DE    4. FR    5. JP")
        print("  6. AU    7. CA    8. BR    9. IN   10. SG")

        location_input = input("\nSelect location (1-10, default: 1): ").strip().upper()
        location_map = {
            '1': 'US', '2': 'UK', '3': 'DE', '4': 'FR', '5': 'JP',
            '6': 'AU', '7': 'CA', '8': 'BR', '9': 'IN', '10': 'SG'
        }
        if location_input in location_map:
            location = location_map[location_input]
        elif location_input in location_map.values():
            location = location_input
        else:
            location = 'US'

        visible_input = input("\nShow browser window? (y/n, default: n): ").strip().lower()
        headless = visible_input not in ['y', 'yes']

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    print("\n" + "=" * 60)
    print("        Banner Image Scraper (Full Site)")
    print("=" * 60)
    print(f"\nTarget: {url}")
    print(f"Location: {location} | Mode: {'Headless' if headless else 'Visible'}")
    print(f"Flow: Homepage -> Promotions (auto-discover)")
    print("=" * 60 + "\n")

    try:
        results = scrape_site_full(url, headless=headless, location=location)

        # Print results grouped by page
        total = 0
        for page_name, banners in results.items():
            if not banners:
                continue
            total += len(banners)
            print(f"\n{'=' * 60}")
            print(f"  {page_name.upper()} — {len(banners)} banner(s)")
            print(f"{'=' * 60}\n")

            for i, b in enumerate(banners, 1):
                print(f"  {i}. [{b['type']}]")
                print(f"     URL: {b['src']}")
                print(f"     Alt: {b['alt']}")
                print(f"     Size: {b['width']} x {b['height']}px")
                print()

        if total == 0:
            print("\n[-] No banners found on homepage or promotions page.")
        else:
            print(f"\n[+] Total: {total} banner(s) across {len([k for k,v in results.items() if v])} page(s)")

        print("=" * 60 + "\n")

    except KeyboardInterrupt:
        print("\n\nScraping cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[-] Error occurred: {e}")
        print("\nMake sure Playwright is installed:")
        print("  py -m pip install playwright")
        print("  py -m playwright install chromium")
        sys.exit(1)

if __name__ == "__main__":
    main()
