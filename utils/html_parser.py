from bs4 import BeautifulSoup, NavigableString, Tag
from typing import Optional
from urllib.parse import urljoin
from config import MAX_TEXT_LENGTH

# Link handling helpers
_DOC_EXTENSIONS = ('.pdf', '.doc', '.docx', '.xlsx', '.xls')
_make_absolute = lambda href, base_url: (urljoin(base_url, href)
                                         if base_url and not href.startswith(('http://', 'https://', 'mailto:', 'tel:', 'javascript:', '#'))
                                         else href)

def _format_link_text(href: str, text: str, preserve_document_links: bool) -> Optional[str]:
    """Format link text based on href type"""
    if href.startswith('mailto:'):
        email = href.replace('mailto:', '').strip()
        return f"{text} (Email: {email})" if text and text.lower() != email.lower() else f"Email: {email}"
    elif href.startswith('tel:'):
        phone = href.replace('tel:', '').strip()
        return f"{text} (Phone: {phone})" if text else f"Phone: {phone}"
    elif preserve_document_links and any(href.lower().endswith(ext) for ext in _DOC_EXTENSIONS):
        return f"{text} (URL: {href})" if text else f"Document: {href}"
    return text if text else None

def parse_html_to_text(html: str, preserve_document_links: bool = False, base_url: str = None) -> str:
    """
    Convert raw HTML to structured text for LLM.
    
    Args:
        html: Raw HTML string
        preserve_document_links: If True, preserve PDF/doc links in format "text (URL: link)"
        base_url: Base URL for converting relative links to absolute
    
    Returns:
        Cleaned text preserving headings and structure
    """
    # Detect if this is XML content
    html_lower = html[:200].lower()
    is_xml = (
        html.strip().startswith('<?xml') or 
        '<urlset' in html_lower or 
        '<rss' in html_lower or
        '<sitemap' in html_lower
    )
    
    soup = BeautifulSoup(html, 'xml' if is_xml else 'html.parser')
    
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
        
        # Handle links
        if element.name == 'a':
            href = _make_absolute(element.get('href', ''), base_url)
            text = element.get_text(strip=True)
            formatted = _format_link_text(href, text, preserve_document_links)
            if formatted:
                current_section.append(formatted)
            return
        
        # Handle headings
        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            if current_section:
                sections.append(' '.join(current_section))
                current_section.clear()
            
            # Process heading content recursively to catch mailto links
            def _process_heading_child(child):
                if isinstance(child, NavigableString):
                    return str(child).strip() or None
                if isinstance(child, Tag):
                    if child.name == 'a':
                        href = _make_absolute(child.get('href', ''), base_url)
                        return _format_link_text(href, child.get_text(strip=True), preserve_document_links)
                    elif child.name == 'br':
                        return ' '
                    return child.get_text(strip=True) or None
                return None

            heading_parts = [part for child in element.children if (part := _process_heading_child(child))]
            
            if heading_parts:
                current_section.append(f"## {' '.join(heading_parts)}")
        
        # Handle paragraphs and divs
        elif element.name in ['p', 'div', 'article', 'section', 'main']:
            for child in element.children:
                process_element(child, depth + 1)
            if element.name in ['p', 'article', 'section']:
                if current_section and current_section[-1] != '':
                    current_section.append('')
        
        # Handle lists
        elif element.name == 'ul' or element.name == 'ol':
            for li in element.find_all('li', recursive=False):
                li_parts = []
                
                def process_li_content(elem):
                    """Process list item content recursively"""
                    if isinstance(elem, NavigableString):
                        text = str(elem).strip()
                        if text:
                            li_parts.append(text)
                    elif isinstance(elem, Tag):
                        if elem.name == 'a':
                            href = elem.get('href', '')
                            text = elem.get_text(strip=True)
                            
                            # Convert relative URL to absolute
                            if href and base_url and not href.startswith(('http://', 'https://', 'mailto:', 'tel:', 'javascript:', '#')):
                                href = urljoin(base_url, href)
                            
                            if preserve_document_links and href and any(href.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.xlsx', '.xls']):
                                if text:
                                    li_parts.append(f"{text} (URL: {href})")
                                else:
                                    li_parts.append(f"Document: {href}")
                            elif text:
                                li_parts.append(text)
                        else:
                            # Recurse into nested tags (like <p> inside <li>)
                            for child in elem.children:
                                process_li_content(child)
                
                for child in li.children:
                    process_li_content(child)
                
                if li_parts:
                    current_section.append(f"• {' '.join(li_parts)}")
        
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