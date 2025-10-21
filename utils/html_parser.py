from bs4 import BeautifulSoup, NavigableString, Tag
from config import MAX_TEXT_LENGTH


def parse_html_to_text(html: str) -> str:
    """
    Convert raw HTML to structured text for LLM.
    
    Args:
        html: Raw HTML string
    
    Returns:
        Cleaned text preserving headings and structure
        
    Process:
        1. Parse with BeautifulSoup
        2. Remove <script>, <style>, <nav>, <footer>, <header>
        3. Extract text preserving headings (mark with ##)
        4. Separate sections with ---
        5. Limit to 4000 chars
        
    Output Format:
        ## Heading 1
        Paragraph text here
        
        ## Heading 2
        More text
        ---
        ## Another Section
        ...
    """
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
        elif element.name in ['p', 'div', 'article', 'section']:
            text = element.get_text(separator=' ', strip=True)
            if text:
                current_section.append(text)
        
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