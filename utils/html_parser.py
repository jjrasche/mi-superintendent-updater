from bs4 import BeautifulSoup, NavigableString, Tag
from urllib.parse import urljoin
from config import MAX_TEXT_LENGTH

""" Recommendation: Consider using a library like trafilatura or readability-lxml for cleaner extraction."""
def parse_html_to_text(html: str, preserve_document_links: bool = False, base_url: str = None) -> str:
    """
    Convert raw HTML to structured text for LLM.
    
    Args:
        html: Raw HTML string
        preserve_document_links: If True, preserve PDF/doc links in format "text (URL: link)"
    
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
        
        # Handle links - CRITICAL for email/phone/document extraction
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
            # Preserve document links (PDFs, docs, etc.) if requested
            elif preserve_document_links and href and any(href.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.xlsx', '.xls']):
                absolute_href = urljoin(base_url, href) if base_url else href
                print(f"[DEBUG] Found document link: '{text}' -> {absolute_href}")
                if text:
                    current_section.append(f"{text} (URL: {absolute_href})")
                else:
                    current_section.append(f"Document: {absolute_href}")
            # Regular links - just keep the text
            elif text:
                current_section.append(text)
            return  # Don't process children, we already got the text
        
        # Handle headings
        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            # Start new section if we have content
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
                # Process list items recursively to catch links
                li_parts = []
                for child in li.children:
                    if isinstance(child, NavigableString):
                        text = str(child).strip()
                        if text:
                            li_parts.append(text)
                    elif isinstance(child, Tag):
                        if child.name == 'a':
                            href = child.get('href', '')
                            text = child.get_text(strip=True)
                            
                            if preserve_document_links and href and any(href.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.xlsx', '.xls']):
                                if text:
                                    li_parts.append(f"{text} (URL: {href})")
                                else:
                                    li_parts.append(f"Document: {href}")
                            elif text:
                                li_parts.append(text)
                        else:
                            text = child.get_text(strip=True)
                            if text:
                                li_parts.append(text)
                
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