from bs4 import BeautifulSoup, NavigableString, Tag
from urllib.parse import urljoin
from config import MAX_TEXT_LENGTH

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
            href = element.get('href', '')
            text = element.get_text(strip=True)
            
            # Convert relative URL to absolute if base_url provided
            if href and base_url and not href.startswith(('http://', 'https://', 'mailto:', 'tel:', 'javascript:', '#')):
                href = urljoin(base_url, href)
            
            # Extract email from mailto links
            if href.startswith('mailto:'):
                email = href.replace('mailto:', '').strip()
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
            # Preserve document links (PDFs, docs, etc.) if requested
            elif preserve_document_links and href and any(href.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.xlsx', '.xls']):
                if text:
                    current_section.append(f"{text} (URL: {href})")
                else:
                    current_section.append(f"Document: {href}")
            # Regular links - just keep the text
            elif text:
                current_section.append(text)
            return
        
        # Handle headings
        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            if current_section:
                sections.append(' '.join(current_section))
                current_section.clear()
            
            # Process heading content recursively to catch mailto links
            heading_parts = []
            for child in element.children:
                if isinstance(child, NavigableString):
                    text = str(child).strip()
                    if text:
                        heading_parts.append(text)
                elif isinstance(child, Tag):
                    if child.name == 'a':
                        href = child.get('href', '')
                        text = child.get_text(strip=True)
                        
                        # Convert relative URL to absolute
                        if href and base_url and not href.startswith(('http://', 'https://', 'mailto:', 'tel:', 'javascript:', '#')):
                            href = urljoin(base_url, href)
                        
                        if href.startswith('mailto:'):
                            email = href.replace('mailto:', '').strip()
                            if text and text.lower() != email.lower():
                                heading_parts.append(f"{text} (Email: {email})")
                            else:
                                heading_parts.append(f"Email: {email}")
                        elif href.startswith('tel:'):
                            phone = href.replace('tel:', '').strip()
                            if text:
                                heading_parts.append(f"{text} (Phone: {phone})")
                            else:
                                heading_parts.append(f"Phone: {phone}")
                        elif preserve_document_links and href and any(href.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.xlsx', '.xls']):
                            if text:
                                heading_parts.append(f"{text} (URL: {href})")
                            else:
                                heading_parts.append(f"Document: {href}")
                        elif text:
                            heading_parts.append(text)
                    elif child.name == 'br':
                        heading_parts.append(' ')
                    else:
                        text = child.get_text(strip=True)
                        if text:
                            heading_parts.append(text)
            
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