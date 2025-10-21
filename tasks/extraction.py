from typing import Dict

from utils.html_parser import parse_html_to_text
from utils.llm import build_extraction_prompt, call_llm
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
    
    # Build prompts and call LLM
    system_prompt, user_prompt = build_extraction_prompt(cleaned_text, district_name)
    
    try:
        result = call_llm(system_prompt, user_prompt)
        
        # Post-validation: title must contain "superintendent"
        if not result.get('is_empty') and result.get('title'):
            title_lower = result['title'].lower()
            if 'superintendent' not in title_lower:
                result = _empty_result(
                    cleaned_text,
                    f"Title '{result['title']}' does not contain 'Superintendent'",
                    logger, district_name, url, html
                )
        
        # Log and return
        extraction_result = {
            'name': result.get('name'),
            'title': result.get('title'),
            'email': result.get('email'),
            'phone': result.get('phone'),
            'extracted_text': cleaned_text,
            'llm_reasoning': result.get('reasoning', ''),
            'is_empty': result.get('is_empty', False)
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