# tasks/discovery.py
from prefect import task
from urllib.parse import urljoin, urlparse
from utils.sitemap import get_sitemap_urls
from utils.llm import llm_pick_best_urls
from utils.fetcher import fetch_with_render_fallback
from bs4 import BeautifulSoup
import requests

@task(retries=2, retry_delay_seconds=5)
def get_candidate_urls(district_name: str, domain: str) -> list[str]:
    """Get candidate URLs via sitemap, then intelligently pick best ones"""    
    sitemap_urls = get_sitemap_urls(domain) or discover_from_homepage(url)
    print(f"  Found {len(sitemap_urls)} URLs in sitemap")
    url_contexts = [getPageContext(url) for url in sitemap_urls]
    return llm_pick_best_urls(district_name, url_contexts)

def getPageContext(url: str) -> dict:
    try:
        soup = getSoup(url)
        title = soup.title.string or "No title"
        headings = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])[:5]]
        return { 'url': url, 'title': title, 'headings': headings }
    except:
        return { 'url': url, 'title': "Error", 'headings': [] }

def getSoup(url: str) -> BeautifulSoup:
    html = requests.get(url, timeout=5, headers={ 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' }).text
    return BeautifulSoup(html, 'html.parser')

def discover_from_homepage(url: str) -> list[str]:
    """Fallback: extract links from homepage and pick best"""
    soup = getSoup(url)
    links = set()
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        full_url = urljoin(url, href) # Convert relative URLs to absolute
        if urlparse(full_url).netloc == urlparse(url).netloc: # Only keep links from the same domain
            links.add(full_url)
    return links