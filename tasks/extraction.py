from typing import Optional
from utils.html_parser import parse_html_to_text
from services.extraction import extract_superintendent as llm_extract
from utils.debug_logger import get_logger
from repositories.extraction import ExtractionRepository
from models.enums import ExtractionType
from models.database import SuperintendentContact

def extract_superintendent(
    html: str,
    district_name: str,
    url: str,
    district_id: int,
    repo,
    fetched_page
) -> Optional[SuperintendentContact]:
    """
    Extract superintendent info from HTML using LLM.
    Saves both generic Extraction tracking and SuperintendentContact result.

    Args:
        html: Raw HTML content
        district_name: District name for context
        url: Source URL (for logging)
        district_id: District ID
        repo: SuperintendentRepository instance
        fetched_page: FetchedPage object (already saved)

    Returns:
        SuperintendentContact object (or None if extraction completely failed)
    """
    logger = get_logger()

    # Parse HTML to clean text
    cleaned_text = parse_html_to_text(html)

    # Quick validation: empty content
    if len(cleaned_text.strip()) < 50:
        reasoning = 'Page content too short (less than 50 characters)'
        _save_empty_extraction(fetched_page.id, repo, cleaned_text, reasoning, logger, district_name, url, html)
        return _save_empty_contact(district_id, repo, reasoning)

    # Call LLM extraction service
    try:
        result = llm_extract(cleaned_text, district_name)

        # Post-validation: title must contain "superintendent"
        if not result.is_empty and result.title:
            title_lower = result.title.lower()
            if 'superintendent' not in title_lower:
                reasoning = f"Title '{result.title}' does not contain 'Superintendent'"
                _save_empty_extraction(fetched_page.id, repo, cleaned_text, reasoning, logger, district_name, url, html)
                return _save_empty_contact(district_id, repo, reasoning)

        # Track extraction (HTML→Text→LLM pipeline)
        extraction_repo = ExtractionRepository(repo.session)
        extraction = extraction_repo.create_extraction(
            fetched_page_id=fetched_page.id,
            extraction_type=ExtractionType.SUPERINTENDENT.value,
            parsed_text=cleaned_text,
            parsing_method='html_parser',
            llm_prompt_template='superintendent_extraction',
            llm_reasoning=result.reasoning,
            is_empty=result.is_empty
        )
        extraction_repo.save_extraction(extraction)

        # Save domain-specific contact
        contact_data = {
            'name': result.name,
            'title': result.title,
            'email': result.email,
            'phone': result.phone
        }
        contact = repo.create_contact(district_id, contact_data, extraction.id)
        repo.save_contact(contact)

        # Log for debugging
        extraction_result = {**contact_data, 'llm_reasoning': result.reasoning, 'is_empty': result.is_empty}
        logger.log_page_fetch(district_name, url, html, cleaned_text, extraction_result)

        return contact

    except Exception as e:
        reasoning = f'LLM extraction failed: {str(e)}'
        _save_empty_extraction(fetched_page.id, repo, cleaned_text, reasoning, logger, district_name, url, html)
        return _save_empty_contact(district_id, repo, reasoning)


def _save_empty_extraction(fetched_page_id: int, repo, text: str, reason: str, logger, district_name: str, url: str, html: str):
    """Save empty extraction tracking"""
    extraction_repo = ExtractionRepository(repo.session)
    extraction = extraction_repo.create_extraction(
        fetched_page_id=fetched_page_id,
        extraction_type=ExtractionType.SUPERINTENDENT.value,
        parsed_text=text,
        parsing_method='html_parser',
        llm_prompt_template='superintendent_extraction',
        llm_reasoning=reason,
        is_empty=True
    )
    extraction_repo.save_extraction(extraction)

    # Log for debugging
    result = {'name': None, 'title': None, 'email': None, 'phone': None, 'llm_reasoning': reason, 'is_empty': True}
    logger.log_page_fetch(district_name, url, html, text, result)
    return extraction


def _save_empty_contact(district_id: int, repo, reason: str) -> SuperintendentContact:
    """Save empty superintendent contact"""
    contact_data = {'name': None, 'title': None, 'email': None, 'phone': None}
    contact = repo.create_contact(district_id, contact_data, extraction_id=None)
    repo.save_contact(contact)
    return contact