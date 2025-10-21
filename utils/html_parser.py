from bs4 import BeautifulSoup, NavigableString, Tag
from config import MAX_TEXT_LENGTH


def parse_html_to_text(html: str) -> str:
    """
    Convert raw HTML to structured text for LLM.
    
    Args:
        html: Raw HTML string
    
    Returns:
        Cleaned text preserving headings and structure
    """
    # Detect if this is XML content (sitemap, RSS, etc.)
    html_lower = html[:200].lower()
    is_xml = (
        html.strip().startswith('<?xml') or 
        '<urlset' in html_lower or 
        '<rss' in html_lower or
        '<sitemap' in html_lower
    )
    
    # Use appropriate parser
    if is_xml:
        soup = BeautifulSoup(html, 'xml')
    else:
        soup = BeautifulSoup(html, 'html.parser')
    
    # Remove unwanted elements
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe', 'noscript']):
        tag.decompose()
    
    sections = []
    current_section = []
    
    def process_element(element, depth=0):
        """Recursively process HTML elements"""
        if isinstance(element, NavigableString):
            text = str(element).strip()
            if text:
                current_section.append(text)
            return
        
        if not isinstance(element, Tag):
            return
        
        # Handle links - CRITICAL for email/phone extraction
        if element.name == 'a':
            href = element.get('href', '')
            text = element.get_text(strip=True)
            
            # Extract email from mailto links
            if href.startswith('mailto:'):
                email = href.replace('mailto:', '').strip()
                # Include both the name and explicit email
                if text and text.lower() != email.lower():
                    current_section.append(f"{text} (Email: {email})")
                else:
                    current_section.append(f"Email: {email}")
            # Extract phone from tel links
            elif href.startswith('tel:'):
                phone = href.replace('tel:', '').strip()
                if text:
                    current_section.append(f"{text} (Phone: {phone})")
                else:
                    current_section.append(f"Phone: {phone}")
            # Regular links - just keep the text
            elif text:
                current_section.append(text)
            return  # Don't process children, we already got the text
        
        # Handle headings
        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            text = element.get_text(strip=True)
            if text:
                # Start new section if we have content
                if current_section:
                    sections.append(' '.join(current_section))
                    current_section.clear()
                current_section.append(f"## {text}")
        
        # Handle paragraphs and divs
        elif element.name in ['p', 'div', 'article', 'section', 'main']:
            # Process children recursively instead of getting all text at once
            for child in element.children:
                process_element(child, depth + 1)
            # Add spacing after paragraph-like elements
            if element.name in ['p', 'article', 'section']:
                if current_section and current_section[-1] != '':
                    current_section.append('')
        
        # Handle lists
        elif element.name == 'ul' or element.name == 'ol':
            for li in element.find_all('li', recursive=False):
                text = li.get_text(strip=True)
                if text:
                    current_section.append(f"• {text}")
        
        # Handle tables
        elif element.name == 'table':
            for row in element.find_all('tr'):
                cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                if cells:
                    current_section.append(' | '.join(cells))
        
        # Recurse for other elements
        else:
            for child in element.children:
                process_element(child, depth + 1)
    
    # Process the body or entire document
    body = soup.find('body') or soup
    process_element(body)
    
    # Add any remaining content
    if current_section:
        sections.append(' '.join(current_section))
    
    # Join sections with separator
    full_text = '\n---\n'.join(sections)
    
    # Clean up whitespace
    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
    full_text = '\n\n'.join(lines)
    
    # Limit to max length
    if len(full_text) > MAX_TEXT_LENGTH:
        full_text = full_text[:MAX_TEXT_LENGTH] + "\n\n[Text truncated...]"
    
    return full_text