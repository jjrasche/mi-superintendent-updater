from io import BytesIO
from typing import Union
import PyPDF2

from config import MAX_TEXT_LENGTH


def extract_text_from_pdf(pdf_content: Union[bytes, str]) -> str:
    """
    Extract text content from PDF.
    
    Args:
        pdf_content: Either bytes from PDF file or base64 string
    
    Returns:
        Extracted and cleaned text
    """
    print(f"\n[PDF PARSER] Extracting text from PDF...")
    
    try:
        # Handle different input types
        if isinstance(pdf_content, str):
            # If it's a string, assume it's the raw content from requests
            pdf_bytes = pdf_content.encode('latin-1')
        else:
            pdf_bytes = pdf_content
        
        # Create PDF reader
        pdf_file = BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        num_pages = len(pdf_reader.pages)
        print(f"[PDF PARSER] PDF has {num_pages} pages")
        
        # Extract text from all pages
        text_parts = []
        for page_num in range(num_pages):
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            
            if text and text.strip():
                text_parts.append(text)
        
        # Join all pages
        full_text = '\n\n--- PAGE BREAK ---\n\n'.join(text_parts)
        
        # Clean up the text
        full_text = _clean_pdf_text(full_text)
        
        print(f"[PDF PARSER] Extracted {len(full_text)} characters")
        
        # Limit to max length
        if len(full_text) > MAX_TEXT_LENGTH:
            full_text = full_text[:MAX_TEXT_LENGTH] + "\n\n[Text truncated...]"
            print(f"[PDF PARSER] Truncated to {MAX_TEXT_LENGTH} characters")
        
        return full_text
        
    except Exception as e:
        print(f"[PDF PARSER] Failed to extract text: {str(e)}")
        return f"[PDF parsing error: {str(e)}]"


def _clean_pdf_text(text: str) -> str:
    """
    Clean up extracted PDF text.
    
    Args:
        text: Raw extracted text
    
    Returns:
        Cleaned text
    """
    # Remove excessive whitespace
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if line:  # Skip empty lines
            cleaned_lines.append(line)
    
    # Join with single newlines
    cleaned = '\n'.join(cleaned_lines)
    
    # Remove repeated whitespace
    import re
    cleaned = re.sub(r' +', ' ', cleaned)
    
    # Remove page numbers (common pattern: standalone numbers)
    cleaned = re.sub(r'\n\d+\n', '\n', cleaned)
    
    return cleaned