import requests
from typing import Dict
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from config import REQUEST_TIMEOUT, USER_AGENT


def fetch_page(url: str) -> Dict:
    """
    Fetch single webpage HTML.
    
    Returns:
        {
            'url': str,
            'html': str,
            'status': str,  # "success" | "error" | "timeout"
            'error_message': str | None
        }
    """
    headers = {'User-Agent': USER_AGENT}
    
    # Try requests first (faster)
    try:
        response = requests.get(
            url, 
            headers=headers, 
            timeout=REQUEST_TIMEOUT,
            verify=True  # Try with SSL verification first
        )
        response.raise_for_status()
        
        if response.text and len(response.text.strip()) > 100:
            return {
                'url': url,
                'html': response.text,
                'status': 'success',
                'error_message': None
            }
    except requests.exceptions.SSLError:
        # Retry without SSL verification for self-signed certs
        try:
            response = requests.get(
                url, 
                headers=headers, 
                timeout=REQUEST_TIMEOUT,
                verify=False
            )
            response.raise_for_status()
            
            if response.text and len(response.text.strip()) > 100:
                return {
                    'url': url,
                    'html': response.text,
                    'status': 'success',
                    'error_message': None
                }
        except Exception:
            pass  # Fall through to Playwright
    except requests.Timeout:
        pass  # Try Playwright
    except requests.RequestException:
        pass  # Try Playwright
    
    # Fall back to Playwright (handles JavaScript)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=USER_AGENT,
                ignore_https_errors=True  # Handle SSL issues
            )
            page = context.new_page()
            
            page.goto(url, timeout=REQUEST_TIMEOUT * 1000, wait_until='networkidle')
            html = page.content()
            
            browser.close()
            
            if html and len(html.strip()) > 100:
                return {
                    'url': url,
                    'html': html,
                    'status': 'success',
                    'error_message': None
                }
            else:
                return {
                    'url': url,
                    'html': '',
                    'status': 'error',
                    'error_message': 'Empty page content'
                }
                
    except PlaywrightTimeout:
        return {
            'url': url,
            'html': '',
            'status': 'timeout',
            'error_message': f'Page load timeout after {REQUEST_TIMEOUT}s'
        }
    except Exception as e:
        return {
            'url': url,
            'html': '',
            'status': 'error',
            'error_message': str(e)
        }