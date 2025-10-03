from bs4 import BeautifulSoup

def clean_html_to_text(html: str, max_chars: int = 8000) -> str:
    """Convert HTML to clean text, removing noise and limiting length"""
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe', 'noscript']):
        tag.decompose()
    text = soup.get_text(separator='\n', strip=True)
    text = '\n'.join(line for line in text.split('\n') if line.strip()) # Remove empty lines and limit length
    return text[:max_chars]