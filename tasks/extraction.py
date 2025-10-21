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
    
    # Build prompts
    system_prompt, user_prompt = build_extraction_prompt(cleaned_text, district_name)
    
    # Call LLM
    try:
        result = call_llm(system_prompt, user_prompt)
        
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