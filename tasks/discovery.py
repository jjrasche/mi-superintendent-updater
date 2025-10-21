import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import List

from config import REQUEST_TIMEOUT, USER_AGENT, MAX_URLS_TO_FILTER
from utils.llm import build_url_filtering_prompt, call_llm


def discover_urls(domain: str) -> List[str]:
    """
    Get all URLs from sitemap.xml or homepage links.
    
    Args:
        domain: School district domain (e.g., "exampledistrict.edu")
    
    Returns:
        List of URLs found (may be 100+)
        
    Process:
        1. Try GET domain/sitemap.xml
        2. If 404, fall back to homepage scraping
        3. Extract all <a href> tags from homepage
        4. Return absolute URLs only (filter out anchors, mailto:, etc)
    
    Raises:
        ConnectionError: If domain unreachable
    """
    # Ensure domain has protocol
    if not domain.startswith(('http://', 'https://')):
        domain = f'https://{domain}'
    
    urls = set()
    headers = {'User-Agent': USER_AGENT}
    
    # Try sitemap.xml first
    sitemap_url = urljoin(domain, '/sitemap.xml')
    try:
        response = requests.get(sitemap_url, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'xml')
            for loc in soup.find_all('loc'):
                url = loc.text.strip()
                if url:
                    urls.add(url)
            
            if urls:
                return list(urls)
    except Exception:
        pass  # Fall through to homepage scraping
    
    # Fall back to homepage scraping
    try:
        response = requests.get(domain, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract all links
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Convert to absolute URL
            absolute_url = urljoin(domain, href)
            
            # Filter out non-http URLs and anchors
            parsed = urlparse(absolute_url)
            if parsed.scheme in ('http', 'https') and not parsed.fragment:
                # Only keep URLs from the same domain
                if parsed.netloc == urlparse(domain).netloc:
                    # Remove query parameters for cleaner URLs
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    urls.add(clean_url)
        
        if not urls:
            raise ConnectionError(f"No URLs found on {domain}")
        
        return list(urls)
        
    except requests.RequestException as e:
        raise ConnectionError(f"Failed to reach {domain}: {str(e)}")


def filter_urls(urls: List[str], district_name: str) -> List[str]:
    """
    Use LLM to pick top 10 URLs most likely to have superintendent info.
    
    Args:
        urls: All URLs from discovery
        district_name: Name of district for context
    
    Returns:
        Top 10 URLs ranked by likelihood
        
    Process:
        1. Build prompt with URL paths only (not full HTML)
        2. Ask LLM to identify admin/leadership/superintendent pages
        3. Parse JSON response with ranked URLs
        4. Return top 10
    
    Assumptions:
        - URL path contains sufficient signal
        - LLM can infer page purpose from path
    """
    # If we have fewer than max, return all
    if len(urls) <= MAX_URLS_TO_FILTER:
        return urls
    
    # Build prompt and call LLM
    system_prompt, user_prompt = build_url_filtering_prompt(urls, district_name)
    result = call_llm(system_prompt, user_prompt)
    
    # Extract filtered URLs
    filtered_urls = result.get('urls', [])
    
    # Ensure we return valid URLs that were in the original list
    valid_filtered = [url for url in filtered_urls if url in urls]
    
    # Return up to MAX_URLS_TO_FILTER
    return valid_filtered[:MAX_URLS_TO_FILTER]