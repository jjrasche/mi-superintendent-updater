from typing import Dict

from utils.html_parser import parse_html_to_text
from services.extraction import extract_superintendent as llm_extract
from utils.debug_logger import get_logger

def extract_superintendent(html: str, district_name: str, url: str) -> Dict:
    """Extract superintendent info from HTML using LLM."""
    logger = get_logger()
    
    # Parse HTML to clean text
    cleaned_text = parse_html_to_text(html)
    
    # Quick validation: empty content
    if len(cleaned_text.strip()) < 50:
        return _empty_result(
            cleaned_text, 
            'Page content too short (less than 50 characters)',
            logger, district_name, url, html
        )
    
    # Call LLM extraction service
    try:
        result = llm_extract(cleaned_text, district_name)

        # Post-validation: title must contain "superintendent"
        if not result.is_empty and result.title:
            title_lower = result.title.lower()
            if 'superintendent' not in title_lower:
                return _empty_result(
                    cleaned_text,
                    f"Title '{result.title}' does not contain 'Superintendent'",
                    logger, district_name, url, html
                )

        # Log and return
        extraction_result = {
            'name': result.name,
            'title': result.title,
            'email': result.email,
            'phone': result.phone,
            'extracted_text': cleaned_text,
            'llm_reasoning': result.reasoning,
            'is_empty': result.is_empty
        }

        logger.log_page_fetch(district_name, url, html, cleaned_text, extraction_result)
        return extraction_result

    except Exception as e:
        return _empty_result(
            cleaned_text,
            f'LLM extraction failed: {str(e)}',
            logger, district_name, url, html
        )


def _empty_result(text: str, reason: str, logger, district_name: str, url: str, html: str) -> Dict:
    """Helper to create empty result"""
    result = {
        'name': None,
        'title': None,
        'email': None,
        'phone': None,
        'extracted_text': text,
        'llm_reasoning': reason,
        'is_empty': True
    }
    logger.log_page_fetch(district_name, url, html, text, result)
    return result