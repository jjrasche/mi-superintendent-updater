from typing import Dict, Optional

from utils.html_parser import parse_html_to_text
from utils.llm import build_extraction_prompt, call_llm


def extract_superintendent(html: str, district_name: str) -> Dict:
    """
    Extract superintendent info from HTML using LLM.
    
    Args:
        html: Raw HTML
        district_name: District name for context
    
    Returns:
        {
            'name': str | None,
            'title': str | None,
            'email': str | None,
            'phone': str | None,
            'extracted_text': str,  # What was sent to LLM
            'llm_reasoning': str,
            'is_empty': bool
        }
        
    Process:
        1. Parse HTML to text using parse_html_to_text()
        2. Build LLM prompt with instructions
        3. Call Groq API with llama-3.1-8b-instant
        4. Parse JSON response
        5. Return structured extraction
        
    LLM Instructions:
        - Look for SUPERINTENDENT only (not assistants, principals, etc)
        - Extract name, title, email, phone
        - Explain reasoning
        - Mark is_empty=True if nothing found
    
    Assumptions:
        - HTML parsing preserves semantic meaning
        - LLM can extract from cleaned text
        - LLM reasoning is NOT a reliable confidence score
    """
    # Parse HTML to clean text
    cleaned_text = parse_html_to_text(html)
    
    # Build prompts
    system_prompt, user_prompt = build_extraction_prompt(cleaned_text, district_name)
    
    # Call LLM
    try:
        result = call_llm(system_prompt, user_prompt)
        
        return {
            'name': result.get('name'),
            'title': result.get('title'),
            'email': result.get('email'),
            'phone': result.get('phone'),
            'extracted_text': cleaned_text,
            'llm_reasoning': result.get('reasoning', ''),
            'is_empty': result.get('is_empty', False)
        }
    except Exception as e:
        # If LLM fails, return error state
        return {
            'name': None,
            'title': None,
            'email': None,
            'phone': None,
            'extracted_text': cleaned_text,
            'llm_reasoning': f'LLM extraction failed: {str(e)}',
            'is_empty': True
        }