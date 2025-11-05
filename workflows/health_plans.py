from typing import Dict, List

from models.database import get_session, District
from tasks.health_plan_discovery import find_transparency_link
from tasks.health_plan_extraction import extract_health_plans
from tasks.fetcher import fetch_page
from utils.html_parser import parse_html_to_text
from utils.pdf_parser import extract_text_from_pdf
from utils.debug_logger import get_logger


def run_health_plan_check(district_id: int) -> Dict:
    """
    Check district for employee health insurance plan data.
    
    Args:
        district_id: District ID to check
    
    Returns:
        {
            'district_id': int,
            'district_name': str,
            'transparency_url': str | None,
            'plans_found': int,
            'plans': List[Dict],
            'status': 'success' | 'no_link' | 'fetch_error' | 'extraction_error' | 'error'
        }
    """
    session = get_session()
    logger = get_logger()
    
    try:
        # 1. Get district
        district = session.query(District).filter_by(id=district_id).first()
        if not district:
            raise ValueError(f"District {district_id} not found")
        
        print(f"\n{'='*60}")
        print(f"HEALTH PLAN CHECK: {district.name} ({district.domain})")
        print(f"{'='*60}")
        
        # 2. Find transparency link on homepage
        print("\n[STEP 1] Finding transparency link...")
        transparency_result = find_transparency_link(district.domain, district.name)
        
        if not transparency_result['url']:
            print("✗ No transparency link found on homepage")
            return {
                'district_id': district_id,
                'district_name': district.name,
                'transparency_url': None,
                'plans_found': 0,
                'plans': [],
                'status': 'no_link'
            }
        
        transparency_url = transparency_result['url']
        print(f"✓ Found transparency page: {transparency_url}")
        
        # Log transparency discovery
        logger.log_transparency_discovery(
            district.name,
            district.domain,
            transparency_url,
            transparency_result.get('all_links', []),
            transparency_result.get('reasoning')
        )
        
        # 3. Fetch transparency page
        print("\n[STEP 2] Fetching transparency page...")
        fetch_result = fetch_page(transparency_url)
        
        if fetch_result['status'] != 'success':
            print(f"✗ Failed to fetch: {fetch_result['error_message']}")
            return {
                'district_id': district_id,
                'district_name': district.name,
                'transparency_url': transparency_url,
                'plans_found': 0,
                'plans': [],
                'status': 'fetch_error',
                'error_message': fetch_result['error_message']
            }
        
        print(f"✓ Successfully fetched page")
        
        # 4. Determine content type and parse
        print("\n[STEP 3] Parsing content...")
        content_type = fetch_result.get('content_type', 'html')
        raw_content = fetch_result['html']
        
        if content_type == 'pdf':
            print("Content type: PDF")
            text_content = extract_text_from_pdf(raw_content)
        else:
            print("Content type: HTML")
            text_content = parse_html_to_text(raw_content)
        
        print(f"✓ Parsed {len(text_content)} characters")
        
        # 5. Extract health plans
        print("\n[STEP 4] Extracting health plans...")
        plans = extract_health_plans(text_content, district.name)
        
        # Count non-empty plans
        valid_plans = [p for p in plans if not p.get('is_empty', True)]
        
        # Log health plan extraction
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
        
        # 6. Print results
        print(f"\n{'='*60}")
        print("RESULTS")
        print(f"{'='*60}")
        
        if valid_plans:
            print(f"✓ Found {len(valid_plans)} health plan(s):\n")
            for i, plan in enumerate(valid_plans, 1):
                print(f"{i}. {plan['plan_name']}")
                print(f"   Provider: {plan['provider']}")
                print(f"   Type: {plan['plan_type']}")
                if plan.get('coverage_details'):
                    print(f"   Details: {plan['coverage_details']}")
                print()
        else:
            print("✗ No health plans found")
            if plans and plans[0].get('reasoning'):
                print(f"   Reason: {plans[0]['reasoning']}")
        
        print(f"{'='*60}")
        
        return {
            'district_id': district_id,
            'district_name': district.name,
            'transparency_url': transparency_url,
            'plans_found': len(valid_plans),
            'plans': valid_plans if valid_plans else plans,
            'status': 'success'
        }
        
    except Exception as e:
        print(f"\n✗ Error during health plan check: {str(e)}")
        
        # Safely get district name
        district_name = 'Unknown'
        if 'district' in locals() and district is not None:
            district_name = district.name
        
        return {
            'district_id': district_id,
            'district_name': district_name,
            'transparency_url': transparency_url if 'transparency_url' in locals() else None,
            'plans_found': 0,
            'plans': [],
            'status': 'error',
            'error_message': str(e)
        }
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
            result = run_health_plan_check(district_id)
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