from typing import Dict, List
from models.database import District
from models.enums import FetchStatus, ExtractionStatus, ExtractionType
from .health_plan_discovery import find_transparency_link
from .health_plan_extraction import extract_health_plans
from .fetcher import fetch_with_playwright
from utils.html_parser import parse_html_to_text
from utils.pdf_parser import extract_text_from_pdf
from utils.debug_logger import get_logger
from repositories.extraction import ExtractionRepository


def process_health_plans(repo, district: District) -> Dict:
    """
    Process health plans: find transparency page, fetch, parse, extract, and save.

    Returns:
        {
            'transparency_url': str | None,
            'plans': List[Dict],
            'status': str,
            'error_message': str | None
        }
    """
    logger = get_logger()

    transparency_result = find_transparency_link(district.domain, district.name, district.id, repo)
    logger.log_transparency_discovery(
        district.name,
        district.domain,
        transparency_result['url'],
        transparency_result.get('all_links', []),
        transparency_result.get('reasoning')
    )

    if not transparency_result['url']:
        print("✗ No transparency link found on homepage")
        return {
            'transparency_url': None,
            'plans': [],
            'status': ExtractionStatus.NO_LINK.value,
            'error_message': None
        }

    transparency_url = transparency_result['url']
    print(f"✓ Found transparency page: {transparency_url}")

    # Check if this URL should be skipped
    # Skip if: (1) recent failure, OR (2) recent success with no plans extracted
    recent_failure = repo.get_recent_failed_fetch(district.id, transparency_url, days=30)
    if recent_failure:
        print(f"⊘ Skipping URL - failed recently on {recent_failure.fetched_at.strftime('%Y-%m-%d')} "
              f"(status: {recent_failure.status}, error: {recent_failure.error_message[:50] if recent_failure.error_message else 'N/A'})")
        return {
            'transparency_url': transparency_url,
            'plans': [],
            'status': ExtractionStatus.ERROR.value,
            'error_message': f"Skipped - failed recently ({recent_failure.status})"
        }

    recent_success = repo.get_recent_successful_fetch(district.id, transparency_url, days=30)
    if recent_success and not repo.has_plans_for_url(district.id, transparency_url):
        print(f"⊘ Skipping URL - fetched recently on {recent_success.fetched_at.strftime('%Y-%m-%d')} "
              f"but extracted 0 plans (likely 404/empty page)")
        return {
            'transparency_url': transparency_url,
            'plans': [],
            'status': ExtractionStatus.ERROR.value,
            'error_message': f"Skipped - no plans found on previous fetch"
        }

    # Fetch the transparency page
    fetch_result = fetch_with_playwright(transparency_url)

    # Save fetch result to track successes and failures
    fetched_page = repo.save_fetch_result(district.id, transparency_url, WorkflowMode.HEALTH_PLAN.value, fetch_result)

    if fetch_result['status'] != FetchStatus.SUCCESS.value:
        print(f"✗ Failed to fetch: {fetch_result['error_message']}")
        return {
            'transparency_url': transparency_url,
            'plans': [],
            'status': ExtractionStatus.ERROR.value,
            'error_message': fetch_result['error_message']
        }
    print("✓ Successfully fetched page")

    from models.enums import ContentType

    content_type = ContentType(fetch_result.get('content_type', ContentType.HTML.value))
    raw_content = fetch_result['html']

    # Parse HTML to text
    parsing_method = f'{content_type.value}_parser'
    text_content = (parse_html_to_text(raw_content, preserve_document_links=True, base_url=transparency_url)
                   if content_type == ContentType.HTML else extract_text_from_pdf(raw_content))

    # Extract health plans with LLM
    plans = extract_health_plans(text_content, district.name)

    # Track extraction (HTML→Text→LLM pipeline)
    # Note: raw_html is already stored in fetched_page via save_fetch_result
    extraction_repo = ExtractionRepository(repo.session)
    extraction = extraction_repo.create_extraction(
        fetched_page_id=fetched_page.id,
        extraction_type=ExtractionType.HEALTH_PLAN.value,
        parsed_text=text_content,
        parsing_method=parsing_method,
        llm_prompt_template='health_plan_extraction',
        llm_reasoning=plans[0].get('reasoning', '') if plans else '',
        is_empty=not any(not p.get('is_empty', True) for p in plans)
    )
    extraction_repo.save_extraction(extraction)
    valid_plans = [p for p in plans if not p.get('is_empty', True)]

    if valid_plans:
        for plan in valid_plans:
            repo.upsert_plan(district.id, plan, transparency_url, extraction.id)
        repo.update_transparency_url(district, transparency_url)

    extraction_result = {
        'plans': plans,
        'reasoning': plans[0].get('reasoning', '') if plans else ''
    }
    logger.log_health_plan_fetch(
        district.name,
        transparency_url,
        raw_content,
        text_content,
        extraction_result,
        content_type
    )

    print(f"✓ Found {len(valid_plans)} health plan(s)")

    return {
        'transparency_url': transparency_url,
        'plans': valid_plans if valid_plans else plans,
        'status': ExtractionStatus.SUCCESS.value,
        'error_message': None
    }
