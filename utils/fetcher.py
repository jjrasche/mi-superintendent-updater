import requests
from playwright.sync_api import sync_playwright
from pathlib import Path

def http_fetch(url: str, timeout: int = 10) -> str:
    """Fetch HTML without rendering JS"""
    response = requests.get(url, timeout=timeout, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    response.raise_for_status()
    return response.text


def rendered_fetch(url: str) -> tuple[str, str]:
    """Fetch with Playwright, return (html, screenshot_path)"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until='networkidle', timeout=30000)
        html = page.content()
        
        # Create safe filename from URL
        safe_name = url.replace('https://', '').replace('http://', '').replace('/', '_').replace(':', '_')
        screenshot_path = str(Path('screenshots') / f"{safe_name}.png")
        page.screenshot(path=screenshot_path, full_page=True)
        browser.close()
        return html, screenshot_path


def fetch_with_render_fallback(url: str) -> tuple[str, str | None]:
    """Try cheap fetch first, render if needed"""
    try:
        html = http_fetch(url)
        # Check if likely JS-rendered (empty body)
        if len(html) < 500 or '<div id="root"></div>' in html or '<div id="app"></div>' in html:
            print(f"  Page seems JS-heavy, using Playwright...")
            return rendered_fetch(url)
        return html, None
    except Exception as e:
        print(f"  HTTP fetch failed ({e}), trying Playwright...")
        return rendered_fetch(url)
