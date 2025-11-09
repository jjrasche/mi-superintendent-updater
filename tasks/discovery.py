import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import List

from config import REQUEST_TIMEOUT, USER_AGENT, MAX_URLS_TO_FILTER
from services.extraction import filter_urls as llm_filter_urls


def discover_urls(domain: str) -> List[str]:
    """
    Get all URLs from sitemap.xml or homepage links.
    
    Args:
        domain: School district domain (e.g., "exampledistrict.edu")
    
    Returns:
        List of URLs found (may be 100+)
    """
    # Ensure domain has protocol
    if not domain.startswith(('http://', 'https://')):
        domain = f'https://{domain}'
    
    urls = set()
    headers = {'User-Agent': USER_AGENT}
    base_netloc = urlparse(domain).netloc
    
    print(f"\n[DISCOVERY] Starting URL discovery for {domain}")
    print(f"[DISCOVERY] Base netloc: {base_netloc}")
    
    # Try sitemap.xml first
    sitemap_url = urljoin(domain, '/sitemap.xml')
    print(f"[DISCOVERY] Trying sitemap: {sitemap_url}")
    
    try:
        response = requests.get(sitemap_url, headers=headers, timeout=REQUEST_TIMEOUT, verify=False)
        print(f"[DISCOVERY] Sitemap status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'xml')
            loc_tags = soup.find_all('loc')
            print(f"[DISCOVERY] Found {len(loc_tags)} <loc> tags in sitemap")
            
            for loc in loc_tags:
                url = loc.text.strip()
                if url and _is_valid_url(url, base_netloc):
                    urls.add(url)
                else:
                    if url:
                        print(f"[DISCOVERY] Rejected sitemap URL: {url}")
            
            if urls:
                print(f"[DISCOVERY] Sitemap yielded {len(urls)} valid URLs")
                return list(urls)
            else:
                print(f"[DISCOVERY] Sitemap had no valid URLs, falling back to homepage")
    except Exception as e:
        print(f"[DISCOVERY] Sitemap fetch failed: {str(e)}")
    
    # Fall back to homepage scraping
    print(f"[DISCOVERY] Scraping homepage: {domain}")
    try:
        response = requests.get(domain, headers=headers, timeout=REQUEST_TIMEOUT, verify=False)
        response.raise_for_status()
        print(f"[DISCOVERY] Homepage status: {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract all links
        all_links = soup.find_all('a', href=True)
        print(f"[DISCOVERY] Found {len(all_links)} <a> tags on homepage")
        
        for link in all_links:
            href = link['href']
            
            # Convert to absolute URL
            absolute_url = urljoin(domain, href)
            
            # Validate and clean
            if _is_valid_url(absolute_url, base_netloc):
                urls.add(absolute_url)
            else:
                # Log first 10 rejections to understand what's being filtered
                if len(urls) < 10:
                    print(f"[DISCOVERY] Rejected link: {href} → {absolute_url}")
        
        print(f"[DISCOVERY] Homepage scraping yielded {len(urls)} valid URLs")
        
        # If still no URLs, try common paths
        if not urls:
            print(f"[DISCOVERY] No valid URLs found, trying common paths...")
            common_paths = [
                '/about', '/administration', '/contact', '/contact-us',
                '/staff', '/leadership', '/board', '/superintendent'
            ]
            for path in common_paths:
                test_url = urljoin(domain, path)
                try:
                    r = requests.head(test_url, headers=headers, timeout=5, verify=False)
                    if r.status_code == 200:
                        print(f"[DISCOVERY] Common path exists: {test_url}")
                        urls.add(test_url)
                except:
                    pass
        
        if not urls:
            raise ConnectionError(f"No URLs found on {domain}")
        
        return list(urls)
        
    except requests.RequestException as e:
        raise ConnectionError(f"Failed to reach {domain}: {str(e)}")

def _normalize_domain(domain: str) -> str:
    """Normalize domain for comparison (remove www, lowercase)."""
    domain = domain.lower()
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain

def _is_valid_url(url: str, expected_netloc: str) -> bool:
    """Validate that URL is usable."""
    try:
        # Check for common non-URL patterns
        if not url or url.strip() == '':
            return False
        
        # Reject email addresses (sometimes parsed as URLs)
        if '@' in url and not url.startswith(('http://', 'https://')):
            return False
        
        # Reject mailto/tel/javascript
        if url.startswith(('mailto:', 'tel:', 'javascript:', 'data:', '#')):
            return False
        
        parsed = urlparse(url)
        if _normalize_domain(parsed.netloc) != _normalize_domain(expected_netloc):
            return False
        # Must be http/https
        if parsed.scheme not in ('http', 'https'):
            return False
        
        # Must have netloc (not relative)
        if not parsed.netloc:
            return False
        
        # Must be same domain
        if parsed.netloc != expected_netloc:
            return False
        
        # No fragments
        if parsed.fragment:
            return False
        
        # Reject file extensions we don't want
        path_lower = parsed.path.lower()
        bad_extensions = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                         '.zip', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.mp4', 
                         '.mp3', '.wav', '.avi', '.css', '.js', '.xml', '.rss'}
        if any(path_lower.endswith(ext) for ext in bad_extensions):
            return False
        
        return True
    except:
        return False


def filter_urls(urls: List[str], district_name: str, domain: str = None) -> tuple[List[str], str]:
    """
    Use LLM to pick top 10 URLs most likely to have superintendent info.
    
    Returns:
        (filtered_urls, llm_reasoning)
    """
    from utils.debug_logger import get_logger
    logger = get_logger()
    
    print(f"\n[FILTER] Starting URL filtering")
    print(f"[FILTER] Input: {len(urls)} URLs")
    
    # Pre-filter out non-HTML pages
    html_urls = []
    excluded_extensions = {'.xml', '.rss', '.pdf', '.doc', '.docx', '.xls', '.xlsx', 
                          '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.zip'}
    
    excluded_count = 0
    excluded_examples = []
    
    for url in urls:
        # Check if URL ends with excluded extension
        parsed = urlparse(url)
        path_lower = parsed.path.lower()
        
        # Check extensions
        excluded = False
        for ext in excluded_extensions:
            if path_lower.endswith(ext):
                excluded = True
                if len(excluded_examples) < 5:
                    excluded_examples.append(f"{url} (extension: {ext})")
                break
        
        if excluded:
            excluded_count += 1
            continue
        
        # Skip if URL contains these keywords (often non-content pages)
        skip_keywords = ['sitemap', 'feed', 'rss', 'calendar', 'event']
        if any(keyword in path_lower for keyword in skip_keywords):
            excluded_count += 1
            if len(excluded_examples) < 5:
                excluded_examples.append(f"{url} (keyword filter)")
            continue
        
        html_urls.append(url)
    
    print(f"[FILTER] Pre-filter removed {excluded_count} URLs")
    if excluded_examples:
        print(f"[FILTER] Examples of excluded URLs:")
        for ex in excluded_examples:
            print(f"[FILTER]   - {ex}")
    print(f"[FILTER] Remaining: {len(html_urls)} HTML URLs")
    
    # If we have fewer than max after filtering, return all
    if len(html_urls) <= MAX_URLS_TO_FILTER:
        reasoning = f"No LLM filtering needed - only {len(html_urls)} URLs after pre-filtering"
        print(f"[FILTER] {reasoning}")
        
        if domain:
            logger.log_discovery(district_name, domain, urls, html_urls, reasoning)
        
        return html_urls, reasoning
    
    # Call LLM to filter URLs
    print(f"[FILTER] Calling LLM to select top {MAX_URLS_TO_FILTER} URLs...")
    result = llm_filter_urls(html_urls, district_name)

    # Extract filtered URLs and reasoning
    filtered_urls = result.urls
    llm_reasoning = result.reasoning
    
    print(f"[FILTER] LLM returned {len(filtered_urls)} URLs")
    print(f"[FILTER] LLM reasoning: {llm_reasoning[:150]}...")
    
    # Ensure we return valid URLs that were in the original list
    valid_filtered = [url for url in filtered_urls if url in html_urls]
    
    print(f"[FILTER] Final selection: {len(valid_filtered)} valid URLs")
    
    # Log the discovery
    if domain:
        logger.log_discovery(district_name, domain, urls, valid_filtered, llm_reasoning)
    
    # Return up to MAX_URLS_TO_FILTER
    return valid_filtered[:MAX_URLS_TO_FILTER], llm_reasoning