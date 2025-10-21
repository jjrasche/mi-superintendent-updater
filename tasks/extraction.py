from typing import Dict

from utils.html_parser import parse_html_to_text
from utils.llm import build_extraction_prompt, call_llm
from utils.debug_logger import get_logger

def extract_superintendent(html: str, district_name: str, url: str) -> Dict:
    """
    Extract superintendent info from HTML using LLM.
    
    Args:
        html: Raw HTML
        district_name: District name for context
        url: Source URL (for logging)
    
    Returns:
        {
            'name': str | None,
            'title': str | None,
            'email': str | None,
            'phone': str | None,
            'extracted_text': str,
            'llm_reasoning': str,
            'is_empty': bool
        }
    """
    logger = get_logger()
    
    # Parse HTML to clean text
    cleaned_text = parse_html_to_text(html)
    
    # Validation: If text is too short, return empty immediately
    if len(cleaned_text.strip()) < 50:
        empty_result = {
            'name': None,
            'title': None,
            'email': None,
            'phone': None,
            'extracted_text': cleaned_text,
            'llm_reasoning': 'Page content is empty or too short (less than 50 characters)',
            'is_empty': True
        }
        
        logger.log_page_fetch(
            district_name=district_name,
            url=url,
            raw_html=html,
            parsed_text=cleaned_text,
            extraction_result=empty_result
        )
        
        return empty_result
    
    # Build prompts
    system_prompt, user_prompt = build_extraction_prompt(cleaned_text, district_name)
    
    # Call LLM
    try:
        result = call_llm(system_prompt, user_prompt)
        
        # Validation: Check for invalid extractions
        is_empty = result.get('is_empty', False)
        name = result.get('name')
        title = result.get('title')
        
        # Force is_empty if name found but title doesn't contain "superintendent"
        if name and title and not is_empty:
            title_lower = title.lower()
            if 'superintendent' not in title_lower:
                result['name'] = None
                result['title'] = None
                result['email'] = None
                result['phone'] = None
                result['is_empty'] = True
                result['reasoning'] = f"Found '{title}' but title does not contain 'Superintendent'. Setting to empty."
        
        # Force is_empty if we have a name but empty text (hallucination)
        if name and len(cleaned_text.strip()) < 100 and not is_empty:
            result['name'] = None
            result['title'] = None
            result['email'] = None
            result['phone'] = None
            result['is_empty'] = True
            result['reasoning'] = "Detected potential hallucination: name found but text is too short. Setting to empty."
        
        extraction_result = {
            'name': result.get('name'),
            'title': result.get('title'),
            'email': result.get('email'),
            'phone': result.get('phone'),
            'extracted_text': cleaned_text,
            'llm_reasoning': result.get('reasoning', ''),
            'is_empty': result.get('is_empty', False)
        }
        
        # Log everything for debugging
        logger.log_page_fetch(
            district_name=district_name,
            url=url,
            raw_html=html,
            parsed_text=cleaned_text,
            extraction_result=extraction_result
        )
        
        return extraction_result
        
    except Exception as e:
        # If LLM fails, return error state
        error_result = {
            'name': None,
            'title': None,
            'email': None,
            'phone': None,
            'extracted_text': cleaned_text,
            'llm_reasoning': f'LLM extraction failed: {str(e)}',
            'is_empty': True
        }
        
        # Still log the attempt
        logger.log_page_fetch(
            district_name=district_name,
            url=url,
            raw_html=html,
            parsed_text=cleaned_text,
            extraction_result=error_result
        )
        
        return error_result