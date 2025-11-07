from typing import Dict, List
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from models.database import get_session, District
from tasks.health_plan_discovery import find_transparency_link
from tasks.health_plan_extraction import extract_health_plans
from utils.html_parser import parse_html_to_text
from utils.pdf_parser import extract_text_from_pdf
from utils.debug_logger import get_logger
from config import USER_AGENT, REQUEST_TIMEOUT
from utils.logging import print_header


def _fetch_transparency_page_with_playwright(url: str) -> Dict:
    """
    Fetch transparency page using Playwright to handle JavaScript-rendered content.
    
    Args:
        url: URL to fetch
    
    Returns:
        {
            'url': str,
            'html': str,
            'content_type': str,
            'status': str,
            'error_message': str | None
        }
    """
    print(f"[FETCH] Using Playwright for: {url}")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=USER_AGENT,
                ignore_https_errors=True
            )
            page = context.new_page()
            
            # Navigate and wait for network to be idle (JavaScript loaded)
            page.goto(url, timeout=REQUEST_TIMEOUT * 1000, wait_until='networkidle')
            
            # Additional wait for any lazy-loaded content
            page.wait_for_timeout(2000)
            
            html = page.content()
            browser.close()
            
            if html and len(html.strip()) > 100:
                return {
                    'url': url,
                    'html': html,
                    'content_type': 'html',
                    'status': 'success',
                    'error_message': None
                }
            else:
                return {
                    'url': url,
                    'html': '',
                    'content_type': 'html',
                    'status': 'error',
                    'error_message': 'Empty page content'
                }
                
    except PlaywrightTimeout:
        return {
            'url': url,
            'html': '',
            'content_type': 'html',
            'status': 'timeout',
            'error_message': f'Page load timeout after {REQUEST_TIMEOUT}s'
        }
    except Exception as e:
        return {
            'url': url,
            'html': '',
            'content_type': 'html',
            'status': 'error',
            'error_message': str(e)
        }


def extract_district_health_plans(district_id: int) -> Dict:
    session, logger = get_session(), get_logger()
    try:
        # 1. Get district
        district = session.query(District).filter_by(id=district_id).first()
        if not district: raise ValueError(f"District {district_id} not found")
        print_header(f"HEALTH PLAN CHECK: {district.name} ({district.domain})")
        # 2. Find transparency link on homepage 
        transparency_result = find_transparency_link(district.domain, district.name)
        logger.log_transparency_discovery(district.name,district.domain,transparency_result['url'], transparency_result.get('all_links', []),transparency_result.get('reasoning'))
        if not transparency_result['url']:
            print("✗ No transparency link found on homepage")
            return { 'district_id': district_id, 'district_name': district.name, 'transparency_url': None, 'plans_found': 0, 'plans': [], 'status': 'no_link' }
        transparency_url = transparency_result['url']
        print(f"✓ Found transparency page: {transparency_url}")
        # 3. Fetch transparency page with Playwright
        fetch_result = _fetch_transparency_page_with_playwright(transparency_url)
        if fetch_result['status'] != 'success':
            print(f"✗ Failed to fetch: {fetch_result['error_message']}")
            return { 'district_id': district_id, 'district_name': district.name, 'transparency_url': transparency_url, 'plans_found': 0, 'plans': [], 'status': 'fetch_error', 'error_message': fetch_result['error_message'] }
        print(f"✓ Successfully fetched page")
        # 4. Determine content type and parse
        print("\n[STEP 3] Parsing content...")
        content_type = fetch_result.get('content_type', 'html')
        raw_content = fetch_result['html']
        text_content = content_type == 'html' and parse_html_to_text(raw_content) or extract_text_from_pdf(raw_content)
        # 5. Extract health plans
        print("\n[STEP 4] Extracting health plans...")
        plans = extract_health_plans(text_content, district.name)
        valid_plans = [p for p in plans if not p.get('is_empty', True)]
        print(f"✓ Found {len(valid_plans)} health plan(s):\n")
        extraction_result = { 'plans': plans, 'reasoning': plans[0].get('reasoning', '') if plans else '' }
        logger.log_health_plan_fetch( district.name, transparency_url, raw_content, text_content, extraction_result, content_type )
        return { 'district_id': district_id, 'district_name': district.name, 'transparency_url': transparency_url, 'plans_found': len(valid_plans), 'plans': valid_plans if valid_plans else plans, 'status': 'success' }
    except Exception as e:
        print(f"\n✗ Error during health plan check: {str(e)}")
        district_name = district.name if 'district' in locals() and district is not None else 'Unknown'
        return { 'district_id': district_id, 'district_name': district_name, 'transparency_url': transparency_url if 'transparency_url' in locals() else None, 'plans_found': 0, 'plans': [], 'status': 'error', 'error_message': str(e) }
    finally:
        session.close()


def run_bulk_health_plan_check(district_ids: List[int]) -> List[Dict]:
    """
    Run health plan checks for multiple districts.
    
    Args:
        district_ids: List of district IDs
    
    Returns:
        List of result dicts from run_health_plan_check
    """
    logger = get_logger()
    results = []
    
    print(f"\n{'='*60}")
    print(f"BULK HEALTH PLAN CHECK - {len(district_ids)} districts")
    print(f"{'='*60}")
    print(f"Debug logs will be saved to: {logger.run_dir}")
    print(f"{'='*60}\n")
    
    for idx, district_id in enumerate(district_ids, 1):
        print(f"\n[{idx}/{len(district_ids)}] Processing district {district_id}...")
        
        try:
            result = extract_district_health_plans(district_id)
            results.append(result)
        except Exception as e:
            print(f"✗ Failed to check district {district_id}: {str(e)}")
            results.append({
                'district_id': district_id,
                'district_name': 'Unknown',
                'transparency_url': None,
                'plans_found': 0,
                'plans': [],
                'status': 'error',
                'error_message': str(e)
            })
    
    # Print summary
    print(f"\n\n{'='*60}")
    print("BULK CHECK SUMMARY")
    print(f"{'='*60}")
    
    total_districts = len(results)
    successful = sum(1 for r in results if r['status'] == 'success' and r['plans_found'] > 0)
    no_link = sum(1 for r in results if r['status'] == 'no_link')
    no_plans = sum(1 for r in results if r['status'] == 'success' and r['plans_found'] == 0)
    errors = sum(1 for r in results if r['status'] in ['error', 'fetch_error', 'extraction_error'])
    
    print(f"Total districts checked: {total_districts}")
    print(f"  ✓ Found plans: {successful}")
    print(f"  - No transparency link: {no_link}")
    print(f"  - Link found but no plans: {no_plans}")
    print(f"  ✗ Errors: {errors}")
    
    total_plans = sum(r['plans_found'] for r in results)
    print(f"\nTotal plans extracted: {total_plans}")
    
    print(f"{'='*60}")
    print(f"\nDebug logs saved to: {logger.run_dir}")
    print("Check the logs for detailed HTML and extraction information")
    print(f"{'='*60}\n")
    
    return results