import requests
import time

def test_proxy(proxy_url, test_url="https://www.novadreams.com/promotions"):
    """
    Test if a proxy works for accessing a specific site
    
    Args:
        proxy_url: Proxy in format "http://ip:port"
        test_url: Website to test access
    
    Returns:
        bool: True if proxy works
    """
    
    proxies = {
        'http': proxy_url,
        'https': proxy_url
    }
    
    try:
        print(f"Testing: {proxy_url}...", end=" ")
        
        response = requests.get(
            test_url,
            proxies=proxies,
            timeout=10,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        
        if response.status_code == 200:
            print(f"✅ WORKS! (Status: {response.status_code})")
            return True
        elif response.status_code == 403:
            print(f"❌ Blocked (403)")
            return False
        else:
            print(f"⚠️  Status: {response.status_code}")
            return False
            
    except requests.Timeout:
        print("❌ Timeout")
        return False
    except requests.ConnectionError:
        print("❌ Connection failed")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)[:50]}")
        return False

def get_github_proxies():
    """Fetch fresh proxies from GitHub"""
    
    proxy_sources = [
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt"
    ]
    
    all_proxies = []
    
    print("📥 Fetching fresh proxies from GitHub...\n")
    
    for source in proxy_sources:
        try:
            response = requests.get(source, timeout=10)
            if response.status_code == 200:
                proxies = response.text.strip().split('\n')
                proxies = [f"http://{p.strip()}" for p in proxies if p.strip()]
                all_proxies.extend(proxies[:10])  # Get first 10 from each source
                print(f"✅ Got {len(proxies[:10])} proxies from {source.split('/')[-2]}")
        except:
            print(f"❌ Failed to get proxies from {source.split('/')[-2]}")
    
    return all_proxies

def main():
    """Test proxies and find working ones"""
    
    print("\n" + "=" * 70)
    print("  🔍 Free Proxy Tester for NovaDreams")
    print("=" * 70 + "\n")
    
    # Option 1: Use GitHub proxies
    use_github = input("Fetch fresh proxies from GitHub? (y/n): ").strip().lower()
    
    if use_github == 'y':
        proxies = get_github_proxies()
        print(f"\n📊 Total proxies to test: {len(proxies)}\n")
    else:
        # Manual list
        print("\nUsing pre-defined proxy list...\n")
        proxies = [
            "http://103.152.112.162:80",
            "http://20.206.106.192:80",
            "http://43.134.68.153:3128",
            "http://47.243.177.210:8080",
            "http://195.201.34.206:80",
        ]
    
    print("=" * 70)
    print("  🧪 TESTING PROXIES")
    print("=" * 70 + "\n")
    
    working_proxies = []
    
    for proxy in proxies[:20]:  # Test first 20
        if test_proxy(proxy):
            working_proxies.append(proxy)
            
        time.sleep(0.5)  # Small delay between tests
    
    print("\n" + "=" * 70)
    print("  📊 RESULTS")
    print("=" * 70 + "\n")
    
    if working_proxies:
        print(f"✅ Found {len(working_proxies)} working proxy/proxies!\n")
        
        for i, proxy in enumerate(working_proxies, 1):
            print(f"{i}. {proxy}")
        
        # Save to file
        with open('working_proxies.txt', 'w') as f:
            for proxy in working_proxies:
                f.write(proxy + '\n')
        
        print(f"\n💾 Saved to: working_proxies.txt")
        print(f"\nUse any of these in your Playwright scraper!")
        
    else:
        print("❌ No working proxies found")
        print("\n💡 Suggestions:")
        print("  • Try again (proxy lists update frequently)")
        print("  • Use a paid proxy service (WebShare, Bright Data)")
        print("  • Use a VPN instead")
    
    print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    main()