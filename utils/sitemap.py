import requests
from xml.etree import ElementTree

def get_sitemap_urls(domain: str) -> list[str]:
    """Try to fetch and parse sitemap"""
    sitemap_locations = [
        f"https://{domain}/sitemap.xml",
        f"https://{domain}/sitemap_index.xml",
        f"https://{domain}/sitemap-misc.xml",
    ]
    
    all_urls = []
    for sitemap_url in sitemap_locations:
        try:
            response = requests.get(sitemap_url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            })
            if response.status_code == 200:
                urls = parse_sitemap_xml(response.text)
                all_urls.extend(urls)
                if urls:
                    print(f"  Found {len(urls)} URLs in {sitemap_url}")
        except Exception as e:
            continue
    
    return all_urls


def parse_sitemap_xml(xml_content: str) -> list[str]:
    """Extract URLs from sitemap XML"""
    try:
        root = ElementTree.fromstring(xml_content)
        urls = []
        
        # Handle sitemap index (contains other sitemaps)
        for sitemap_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
            for loc in sitemap_elem.findall('{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
                urls.append(loc.text)
        
        # Handle URL set (actual pages)
        for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
            urls.append(url_elem.text)
        
        return list(set(urls))  # Remove duplicates
    except Exception as e:
        print(f"  Sitemap parse error: {e}")
        return []
