import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def is_banner_image(img, soup):
    """
    Determine if an image element is likely a banner image.
    
    Args:
        img: BeautifulSoup img tag element
        soup: BeautifulSoup object of the entire page
    
    Returns:
        bool: True if image appears to be a banner, False otherwise
    """
    
    # Get image attributes
    width = img.get('width', '0')
    height = img.get('height', '0')
    src = img.get('src', '')
    alt = img.get('alt', '').lower()
    
    # Convert dimensions to integers
    try:
        width = int(str(width).replace('px', ''))
        height = int(str(height).replace('px', ''))
    except (ValueError, TypeError):
        width = 0
        height = 0
    
    # Check aspect ratio (wide images are often banners)
    if width > 0 and height > 0:
        aspect_ratio = width / height
        if aspect_ratio > 2 and width > 600:
            return True
    
    # Check for banner-related keywords
    banner_keywords = [
        'banner', 'hero', 'slider', 'carousel', 
        'header', 'jumbotron', 'masthead', 'cover'
    ]
    
    # Check in source URL
    for keyword in banner_keywords:
        if keyword in src.lower():
            return True
    
    # Check in alt text
    for keyword in banner_keywords:
        if keyword in alt:
            return True
    
    # Check parent element classes and IDs
    parent = img.parent
    if parent:
        parent_class = ' '.join(parent.get('class', [])).lower()
        parent_id = parent.get('id', '').lower()
        
        for keyword in banner_keywords:
            if keyword in parent_class or keyword in parent_id:
                return True
    
    # Check if image is very wide (common for banners)
    if width > 1000:
        return True
    
    # Check if image has data attributes suggesting it's a banner
    data_attrs = [key for key in img.attrs.keys() if key.startswith('data-')]
    for attr in data_attrs:
        attr_value = str(img.get(attr, '')).lower()
        for keyword in banner_keywords:
            if keyword in attr_value:
                return True
    
    return False


def extract_background_images(soup, base_url):
    """
    Extract background images from CSS styles.
    
    Args:
        soup: BeautifulSoup object
        base_url: Base URL for resolving relative paths
    
    Returns:
        list: List of background image dictionaries
    """
    bg_images = []
    
    # Find elements with inline background-image styles
    elements_with_bg = soup.find_all(
        lambda tag: tag.get('style') and 'background-image' in tag.get('style', '')
    )
    
    for elem in elements_with_bg:
        style = elem.get('style', '')
        
        # Extract URL from CSS url() function
        if 'url(' in style:
            start = style.find('url(') + 4
            end = style.find(')', start)
            
            if end > start:
                bg_url = style[start:end].strip('\'"')
                
                # Skip data URIs and very small images
                if bg_url.startswith('data:') or len(bg_url) < 5:
                    continue
                
                # Resolve relative URLs
                if not bg_url.startswith('http'):
                    bg_url = urljoin(base_url, bg_url)
                
                # Check if parent has banner-related classes
                classes = ' '.join(elem.get('class', [])).lower()
                elem_id = elem.get('id', '').lower()
                
                banner_keywords = ['banner', 'hero', 'slider', 'header']
                is_likely_banner = any(
                    keyword in classes or keyword in elem_id 
                    for keyword in banner_keywords
                )
                
                if is_likely_banner or elem.name in ['header', 'section']:
                    bg_images.append({
                        'src': bg_url,
                        'alt': 'Background banner image',
                        'width': 'auto',
                        'height': 'auto',
                        'type': 'Background Banner'
                    })
    
    return bg_images


def scrape_website_banners(url):
    """
    Scrape a website and extract all banner images.
    
    Args:
        url: The website URL to scrape
    
    Returns:
        list: List of dictionaries containing banner information
    """
    
    banners = []
    
    try:
        # Configure request headers to better mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'DNT': '1'
        }
        
        # Create a session to maintain cookies
        session = requests.Session()
        session.headers.update(headers)
        
        # Send GET request
        print("Fetching webpage...")
        response = session.get(url, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        # Parse HTML with BeautifulSoup
        print("Parsing HTML content...")
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all <img> tags
        print("Analyzing images...")
        images = soup.find_all('img')
        
        found_count = 0
        for img in images:
            if is_banner_image(img, soup):
                src = img.get('src', '')
                
                # Skip empty sources and data URIs
                if not src or src.startswith('data:'):
                    continue
                
                # Handle relative URLs
                if not src.startswith('http'):
                    src = urljoin(url, src)
                
                banners.append({
                    'src': src,
                    'alt': img.get('alt', 'Banner image'),
                    'width': img.get('width', 'auto'),
                    'height': img.get('height', 'auto'),
                    'type': 'Banner Image'
                })
                found_count += 1
        
        print(f"Found {found_count} banner <img> tags")
        
        # Extract CSS background images
        print("Checking for background images...")
        bg_images = extract_background_images(soup, url)
        banners.extend(bg_images)
        print(f"Found {len(bg_images)} background banner images")
        
        # Remove duplicates based on src URL
        seen_urls = set()
        unique_banners = []
        for banner in banners:
            if banner['src'] not in seen_urls:
                seen_urls.add(banner['src'])
                unique_banners.append(banner)
        
        return unique_banners
        
    except requests.Timeout:
        print("Error: Request timed out. The website took too long to respond.")
        return []
    except requests.ConnectionError:
        print("Error: Could not connect to the website. Check your internet connection.")
        return []
    except requests.HTTPError as e:
        print(f"Error: HTTP error occurred: {e}")
        return []
    except requests.RequestException as e:
        print(f"Error: An error occurred while fetching the website: {e}")
        return []
    except Exception as e:
        print(f"Error: An unexpected error occurred: {e}")
        return []