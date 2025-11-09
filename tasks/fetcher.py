import requests
from typing import Dict
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from models.enums import FetchStatus
from config import REQUEST_TIMEOUT, USER_AGENT


def fetch_page(url: str) -> Dict:
    """
    Fetch single webpage HTML or PDF.
    
    Returns:
        {
            'url': str,
            'html': str | bytes,  # str for HTML, bytes for PDF
            'content_type': str,  # 'html' or 'pdf'
            'status': str,  # "success" | "error" | "timeout"
            'error_message': str | None
        }
    """
    headers = {'User-Agent': USER_AGENT}
    
    # Check if URL is a PDF
    is_pdf = url.lower().endswith('.pdf')
    
    # Try requests first (faster)
    try:
        response = requests.get(
            url, 
            headers=headers, 
            timeout=REQUEST_TIMEOUT,
            verify=True  # Try with SSL verification first
        )
        response.raise_for_status()
        
        # Determine content type from response
        content_type = response.headers.get('Content-Type', '').lower()
        is_pdf_response = 'application/pdf' in content_type or is_pdf
        
        if is_pdf_response:
            # Return raw bytes for PDF
            return {
                'url': url,
                'html': response.content,  # bytes
                'content_type': 'pdf',
                'status': 'success',
                'error_message': None
            }
        else:
            # Return text for HTML
            if response.text and len(response.text.strip()) > 100:
                return {
                    'url': url,
                    'html': response.text,
                    'content_type': 'html',
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
            
            content_type = response.headers.get('Content-Type', '').lower()
            is_pdf_response = 'application/pdf' in content_type or is_pdf
            
            if is_pdf_response:
                return {
                    'url': url,
                    'html': response.content,
                    'content_type': 'pdf',
                    'status': 'success',
                    'error_message': None
                }
            else:
                if response.text and len(response.text.strip()) > 100:
                    return {
                        'url': url,
                        'html': response.text,
                        'content_type': 'html',
                        'status': 'success',
                        'error_message': None
                    }
        except Exception:
            pass  # Fall through to Playwright
    except requests.Timeout:
        pass  # Try Playwright
    except requests.RequestException:
        pass  # Try Playwright
    
    # Fall back to Playwright for dynamic content (HTML only, not PDF)
    if not is_pdf:
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
                        'content_type': 'html',
                        'status': 'success',
                        'error_message': None
                    }
                else:
                    return {
                        'url': url,
                        'html': '',
                        'content_type': 'html',
                        'status': 'error',
                        'error_message': 'Empty page content'
                    }
                    
        except PlaywrightTimeout:
            return {
                'url': url,
                'html': '',
                'content_type': 'html',
                'status': 'timeout',
                'error_message': f'Page load timeout after {REQUEST_TIMEOUT}s'
            }
        except Exception as e:
            return {
                'url': url,
                'html': '',
                'content_type': 'html',
                'status': 'error',
                'error_message': str(e)
            }
    
    # If we get here, all methods failed
    return {
        'url': url,
        'html': '',
        'content_type': 'pdf' if is_pdf else 'html',
        'status': 'error',
        'error_message': 'Failed to fetch content'
    }


def fetch_with_playwright(url: str) -> Dict:
    """
    Fetch page using Playwright to handle JavaScript-rendered content.

    Returns:
        {
            'url': str,
            'html': str,
            'content_type': str,
            'status': str,
            'error_message': str | None
        }
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=USER_AGENT,
                ignore_https_errors=True
            )
            page = context.new_page()
            page.goto(url, timeout=REQUEST_TIMEOUT * 1000, wait_until='networkidle')
            page.wait_for_timeout(2000)
            html = page.content()
            browser.close()

            if html and len(html.strip()) > 100:
                return {
                    'url': url,
                    'html': html,
                    'content_type': 'html',
                    'status': FetchStatus.SUCCESS.value,
                    'error_message': None
                }
            else:
                return {
                    'url': url,
                    'html': '',
                    'content_type': 'html',
                    'status': FetchStatus.ERROR.value,
                    'error_message': 'Empty page content'
                }

    except PlaywrightTimeout:
        return {
            'url': url,
            'html': '',
            'content_type': 'html',
            'status': FetchStatus.TIMEOUT.value,
            'error_message': f'Page load timeout after {REQUEST_TIMEOUT}s'
        }
    except Exception as e:
        return {
            'url': url,
            'html': '',
            'content_type': 'html',
            'status': FetchStatus.ERROR.value,
            'error_message': str(e)
        }