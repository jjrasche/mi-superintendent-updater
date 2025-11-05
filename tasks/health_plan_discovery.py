from typing import Optional, List, Dict
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from config import USER_AGENT, REQUEST_TIMEOUT
from utils.llm import build_link_identification_prompt, call_llm


def find_transparency_link(domain: str, district_name: str = None) -> Dict:
    """
    Find Budget/Salary Transparency link on district homepage using Playwright.
    
    Args:
        domain: District domain (e.g., "exampledistrict.edu")
        district_name: Optional district name for context
    
    Returns:
        {
            'url': str | None,
            'reasoning': str,
            'all_links': List[Dict]
        }
    """
    # Ensure domain has protocol
    if not domain.startswith(('http://', 'https://')):
        domain = f'https://{domain}'
    
    print(f"\n[TRANSPARENCY DISCOVERY] Searching homepage with Playwright: {domain}")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=USER_AGENT,
                ignore_https_errors=True
            )
            page = context.new_page()
            
            # Navigate and wait for network to be idle
            page.goto(domain, timeout=REQUEST_TIMEOUT * 1000, wait_until='networkidle')
            
            # Get the rendered HTML
            html = page.content()
            browser.close()
        
        # Extract all links from rendered HTML
        links = _extract_links_from_homepage(html, domain)
        print(f"[TRANSPARENCY DISCOVERY] Found {len(links)} links on homepage")
        
        if not links:
            return {
                'url': None,
                'reasoning': 'No links found on homepage',
                'all_links': []
            }
        
        # Use LLM to identify transparency link
        llm_result = _llm_identify_transparency_link(links, district_name)
        
        if llm_result['url']:
            print(f"[TRANSPARENCY DISCOVERY] LLM found: {llm_result['url']}")
        else:
            print(f"[TRANSPARENCY DISCOVERY] No transparency link identified")
        
        return {
            'url': llm_result['url'],
            'reasoning': llm_result['reasoning'],
            'all_links': links
        }
        
    except PlaywrightTimeout:
        print(f"[TRANSPARENCY DISCOVERY] Timeout loading homepage")
        return {
            'url': None,
            'reasoning': f'Timeout loading homepage after {REQUEST_TIMEOUT}s',
            'all_links': []
        }
    except Exception as e:
        print(f"[TRANSPARENCY DISCOVERY] Failed to fetch homepage: {str(e)}")
        return {
            'url': None,
            'reasoning': f'Failed to fetch homepage: {str(e)}',
            'all_links': []
        }


def _extract_links_from_homepage(html: str, base_domain: str) -> List[Dict]:
    """
    Extract all links from homepage HTML.
    
    Args:
        html: Raw HTML content
        base_domain: Base domain URL for resolving relative links
    
    Returns:
        List of {'text': str, 'href': str} dicts
    """
    soup = BeautifulSoup(html, 'html.parser')
    links = []
    
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        href = a['href']
        
        # Skip empty links
        if not href or href.strip() in ['#', '']:
            continue
        
        # Convert to absolute URL
        absolute_url = urljoin(base_domain, href)
        
        # Skip non-http links
        if not absolute_url.startswith(('http://', 'https://')):
            continue
        
        # Include alt text from images inside links
        img = a.find('img')
        if img and img.get('alt'):
            text = f"{text} {img['alt']}".strip()
        
        # Skip if no meaningful text and not a PDF/document link
        if not text and not any(absolute_url.lower().endswith(ext) 
                               for ext in ['.pdf', '.doc', '.docx', '.xlsx']):
            continue
        
        links.append({
            'text': text or '[No text]',
            'href': absolute_url
        })
    
    return links


def _llm_identify_transparency_link(links: List[Dict], district_name: str = None) -> Dict:
    """
    Use LLM to identify transparency link.
    
    Args:
        links: List of link dicts
        district_name: Optional district name for context
    
    Returns:
        {
            'url': str | None,
            'reasoning': str
        }
    """
    # Limit to first 50 links to avoid token limits
    links_subset = links[:50]
    
    system_prompt, user_prompt = build_link_identification_prompt(links_subset, district_name)
    
    try:
        result = call_llm(system_prompt, user_prompt)
        
        identified_url = result.get('url')
        reasoning = result.get('reasoning', '')
        
        print(f"[TRANSPARENCY DISCOVERY] LLM reasoning: {reasoning[:150]}...")
        
        # Validate that returned URL is actually in our list
        if identified_url:
            valid_urls = {link['href'] for link in links_subset}
            if identified_url in valid_urls:
                return {
                    'url': identified_url,
                    'reasoning': reasoning
                }
            else:
                print(f"[TRANSPARENCY DISCOVERY] LLM returned invalid URL")
                return {
                    'url': None,
                    'reasoning': f'LLM returned invalid URL: {reasoning}'
                }
        
        return {
            'url': None,
            'reasoning': reasoning
        }
        
    except Exception as e:
        print(f"[TRANSPARENCY DISCOVERY] LLM identification failed: {str(e)}")
        return {
            'url': None,
            'reasoning': f'LLM identification failed: {str(e)}'
        }