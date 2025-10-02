# tasks/discovery.py
from prefect import task
from utils.sitemap import get_sitemap_urls
from utils.llm import llm_pick_best_urls
from utils.fetcher import fetch_with_render_fallback
from bs4 import BeautifulSoup


@task(retries=2, retry_delay_seconds=5)
def get_candidate_urls(district_name: str, domain: str) -> list[str]:
    """Get candidate URLs via sitemap, then intelligently pick best ones"""
    print(f"Getting candidate URLs for {domain}...")
    
    # Get sitemap URLs
    sitemap_urls = get_sitemap_urls(domain)
    
    if not sitemap_urls:
        print("  No sitemap found, trying homepage navigation...")
        return discover_from_homepage(domain)
    
    print(f"  Found {len(sitemap_urls)} URLs in sitemap")
    
    # Quick filter for obviously relevant URLs
    keywords = ['admin', 'leadership', 'superintendent', 'staff', 'director', 'about', 'contact']
    bad_keywords = ['news', 'calendar', 'lunch', 'menu', 'sports', 'athletics', 'event', 'student', 'parent']
    
    filtered = [
        url for url in sitemap_urls 
        if any(kw in url.lower() for kw in keywords)
        and not any(bad in url.lower() for bad in bad_keywords)
    ][:20]  # Limit to top 20
    
    if not filtered:
        filtered = sitemap_urls[:20]
    
    print(f"  Pre-filtered to {len(filtered)} candidates")
    print(f"  Fetching page titles and headings...")
    
    # Fetch lightweight content (just titles/headings) from each candidate
    url_contexts = []
    for url in filtered:
        try:
            html = fetch_lightweight(url)
            soup = BeautifulSoup(html, 'html.parser')
            
            title = soup.title.string if soup.title else ""
            headings = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])[:5]]
            
            url_contexts.append({
                'url': url,
                'title': title,
                'headings': headings
            })
        except:
            continue
    
    print(f"  Successfully fetched {len(url_contexts)} page contexts")
    
    # Now let LLM pick the best ones based on actual content
    return llm_pick_best_urls(district_name, url_contexts)


def fetch_lightweight(url: str) -> str:
    """Quick fetch without rendering - just need headers"""
    import requests
    response = requests.get(url, timeout=5, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    })
    return response.text


def discover_from_homepage(domain: str) -> list[str]:
    """Fallback: extract links from homepage and pick best"""
    # Implementation for homepage navigation
    return [
        f"https://{domain}/administration",
        f"https://{domain}/about/superintendent",
        f"https://{domain}/staff",
        f"https://{domain}/contact",
        f"https://{domain}/district/leadership"
    ]