import requests
from typing import Dict
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from models.enums import FetchStatus, ContentType, FileExtension
from config import REQUEST_TIMEOUT, USER_AGENT


# Helper functions for DRY
_success_result = lambda url, content, content_type: {
    'url': url, 'html': content, 'content_type': content_type.value,
    'status': FetchStatus.SUCCESS.value, 'error_message': None
}

_error_result = lambda url, content_type, status, message: {
    'url': url, 'html': '', 'content_type': content_type.value,
    'status': status.value, 'error_message': message
}

_is_pdf_url = lambda url: url.lower().endswith(FileExtension.PDF.value)
_is_pdf_content = lambda content_type, url: 'application/pdf' in content_type.lower() or _is_pdf_url(url)
_has_valid_content = lambda text: text and len(text.strip()) > 100

def _process_response(response, url, is_pdf):
    """Process HTTP response and return result dict"""
    content_type = response.headers.get('Content-Type', '').lower()
    is_pdf_response = _is_pdf_content(content_type, url)

    if is_pdf_response:
        return _success_result(url, response.content, ContentType.PDF)
    elif _has_valid_content(response.text):
        return _success_result(url, response.text, ContentType.HTML)
    return None

def _try_requests(url, verify=True):
    """Try fetching with requests library"""
    try:
        response = requests.get(url, headers={'User-Agent': USER_AGENT},
                              timeout=REQUEST_TIMEOUT, verify=verify)
        response.raise_for_status()
        return _process_response(response, url, _is_pdf_url(url))
    except requests.exceptions.SSLError:
        return None if verify else False  # None = retry without verify, False = failed
    except (requests.Timeout, requests.RequestException):
        return False

def _try_playwright(url):
    """Try fetching with Playwright for JS-rendered content"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=USER_AGENT, ignore_https_errors=True)
            page = context.new_page()
            page.goto(url, timeout=REQUEST_TIMEOUT * 1000, wait_until='networkidle')
            html = page.content()
            browser.close()

            return (_success_result(url, html, ContentType.HTML) if _has_valid_content(html)
                   else _error_result(url, ContentType.HTML, FetchStatus.ERROR, 'Empty page content'))
    except PlaywrightTimeout:
        return _error_result(url, ContentType.HTML, FetchStatus.TIMEOUT,
                           f'Page load timeout after {REQUEST_TIMEOUT}s')
    except Exception as e:
        return _error_result(url, ContentType.HTML, FetchStatus.ERROR, str(e))

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
    is_pdf = _is_pdf_url(url)

    # Try requests with SSL verification
    result = _try_requests(url, verify=True)
    if result: return result

    # Retry without SSL verification if SSL error
    if result is None:
        result = _try_requests(url, verify=False)
        if result: return result

    # Fall back to Playwright for HTML (not PDF)
    if not is_pdf:
        result = _try_playwright(url)
        if result: return result

    # All methods failed
    return _error_result(url, ContentType.PDF if is_pdf else ContentType.HTML,
                        FetchStatus.ERROR, 'Failed to fetch content')


fetch_with_playwright = lambda url: _try_playwright(url)