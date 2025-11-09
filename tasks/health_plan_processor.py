from typing import Dict, List
from models.database import District
from models.enums import FetchStatus, ExtractionStatus
from .health_plan_discovery import find_transparency_link
from .health_plan_extraction import extract_health_plans
from .fetcher import fetch_with_playwright
from utils.html_parser import parse_html_to_text
from utils.pdf_parser import extract_text_from_pdf
from utils.debug_logger import get_logger


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

    transparency_result = find_transparency_link(district.domain, district.name)
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

    fetch_result = fetch_with_playwright(transparency_url)
    if fetch_result['status'] != FetchStatus.SUCCESS.value:
        print(f"✗ Failed to fetch: {fetch_result['error_message']}")
        return {
            'transparency_url': transparency_url,
            'plans': [],
            'status': ExtractionStatus.ERROR.value,
            'error_message': fetch_result['error_message']
        }
    print("✓ Successfully fetched page")

    content_type = fetch_result.get('content_type', 'html')
    raw_content = fetch_result['html']

    if content_type == 'html':
        text_content = parse_html_to_text(raw_content, preserve_document_links=True, base_url=transparency_url)
    else:
        text_content = extract_text_from_pdf(raw_content)

    plans = extract_health_plans(text_content, district.name)
    valid_plans = [p for p in plans if not p.get('is_empty', True)]

    if valid_plans:
        for plan in valid_plans:
            repo.upsert_plan(district.id, plan, transparency_url)
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
