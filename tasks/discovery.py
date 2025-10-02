from prefect import task
from utils.sitemap import get_sitemap_urls
from utils.llm import llm_rank_urls
from utils.fetcher import fetch_with_render_fallback


@task(retries=2, retry_delay_seconds=5)
def get_candidate_urls(district_name: str, domain: str) -> list[str]:
    """Get candidate URLs via sitemap or fallback"""
    print(f"Getting candidate URLs for {domain}...")
    
    # Try sitemap first
    sitemap_urls = get_sitemap_urls(domain)
    
    if sitemap_urls:
        print(f"  Found {len(sitemap_urls)} URLs in sitemap")
        # Filter by keywords
        keywords = ['administration', 'leadership', 'superintendent', 'staff', 'directory', 'about', 'district']
        bad_keywords = ['news', 'calendar', 'lunch', 'sports', 'athletics', 'event']
        
        filtered = [
            url for url in sitemap_urls 
            if any(kw in url.lower() for kw in keywords)
            and not any(bad in url.lower() for bad in bad_keywords)
        ]
        
        print(f"  Filtered to {len(filtered)} relevant URLs")
        
        if filtered and len(filtered) > 5:
            # Use LLM to rank if we have many candidates
            print(f"  Using LLM to rank candidates...")
            return llm_rank_urls(district_name, filtered)
        elif filtered:
            return filtered[:5]
    
    # Fallback: common paths
    print("  No sitemap found, using common paths...")
    return [
        f"https://{domain}/administration",
        f"https://{domain}/district/leadership",
        f"https://{domain}/about/superintendent",
        f"https://{domain}/staff/directory",
        f"https://{domain}/contact"
    ]


@task(retries=3, retry_delay_seconds=10)
def fetch_page(url: str) -> dict:
    """Fetch page content and screenshot"""
    print(f"Fetching: {url}")
    html, screenshot = fetch_with_render_fallback(url)
    
    return {
        "url": url,
        "html": html,
        "screenshot": screenshot,
        "html_length": len(html)
    }
