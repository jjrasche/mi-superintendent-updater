from typing import Optional, List, Dict
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import requests

from config import USER_AGENT, REQUEST_TIMEOUT
from utils.llm import build_link_identification_prompt, call_llm


def find_transparency_link(domain: str) -> Optional[str]:
    """
    Find Budget/Salary Transparency link on district homepage.
    
    Args:
        domain: District domain (e.g., "exampledistrict.edu")
    
    Returns:
        URL of transparency page, or None if not found
    """
    # Ensure domain has protocol
    if not domain.startswith(('http://', 'https://')):
        domain = f'https://{domain}'
    
    print(f"\n[TRANSPARENCY DISCOVERY] Searching homepage: {domain}")
    
    try:
        # Fetch homepage
        response = requests.get(
            domain, 
            headers={'User-Agent': USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            verify=False
        )
        response.raise_for_status()
        
        # Extract all links
        links = _extract_links_from_homepage(response.text, domain)
        print(f"[TRANSPARENCY DISCOVERY] Found {len(links)} links on homepage: {', '.join(link['href'] for link in links)}")
        
        if not links:
            return None
        # Fall back to LLM
        llm_match = _llm_identify_transparency_link(links)
        
        if llm_match:
            print(f"[TRANSPARENCY DISCOVERY] LLM found: {llm_match}")
        else:
            print(f"[TRANSPARENCY DISCOVERY] No transparency link identified")
        
        return llm_match
        
    except requests.RequestException as e:
        print(f"[TRANSPARENCY DISCOVERY] Failed to fetch homepage: {str(e)}")
        return None


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


def _pattern_match_transparency_link(links: List[Dict]) -> Optional[str]:
    """
    Try to find transparency link using pattern matching.
    
    Args:
        links: List of link dicts
    
    Returns:
        URL if found, None otherwise
    """
    transparency_keywords = [
        'budget transparency',
        'salary transparency',
        'compensation transparency',
        'budget & salary',
        'budget and salary',
        'budget/salary',
        'financial transparency',
        'transparency reporting'
    ]
    
    for link in links:
        text_lower = link['text'].lower()
        href_lower = link['href'].lower()
        
        # Check for exact phrase matches in text
        for keyword in transparency_keywords:
            if keyword in text_lower:
                return link['href']
        
        # Check for keyword combinations in URL
        if 'transparency' in href_lower and any(
            word in href_lower for word in ['budget', 'salary', 'compensation']
        ):
            return link['href']
    
    return None


def _llm_identify_transparency_link(links: List[Dict]) -> Optional[str]:
    """
    Use LLM to identify transparency link.
    
    Args:
        links: List of link dicts
    
    Returns:
        URL if identified, None otherwise
    """
    # Limit to first 50 links to avoid token limits
    links_subset = links[:50]
    
    system_prompt, user_prompt = build_link_identification_prompt(links_subset)
    
    try:
        result = call_llm(system_prompt, user_prompt)
        
        identified_url = result.get('url')
        reasoning = result.get('reasoning', '')
        
        print(f"[TRANSPARENCY DISCOVERY] LLM reasoning: {reasoning[:150]}...")
        
        # Validate that returned URL is actually in our list
        if identified_url:
            valid_urls = {link['href'] for link in links_subset}
            if identified_url in valid_urls:
                return identified_url
            else:
                print(f"[TRANSPARENCY DISCOVERY] LLM returned invalid URL")
                return None
        
        return None
        
    except Exception as e:
        print(f"[TRANSPARENCY DISCOVERY] LLM identification failed: {str(e)}")
        return None