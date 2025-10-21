from datetime import datetime
from typing import Dict, List

from models.database import get_session, District, FetchedPage, Extraction
from tasks.discovery import discover_urls, filter_urls
from tasks.fetcher import fetch_page
from tasks.extraction import extract_superintendent
from queries.superintendents import get_url_pool


def run_district_check(district_id: int) -> Dict:
    """
    Unified workflow: check district for superintendent info.
    
    Process:
        1. Get district from DB
        2. Get URL pool (URLs with successful extractions in last 3 attempts)
        3. IF pool is empty:
             → Run discovery: sitemap → LLM filter → get new URLs
             → mode = 'discovery'
           ELSE:
             → Use existing pool
             → mode = 'monitoring'
        4. Fetch + extract from all URLs
        5. Save FetchedPages + Extractions with appropriate mode
        6. Update district.last_checked_at
        7. Return summary
    
    Returns:
        {
            'district_id': int,
            'mode': str,  # 'discovery' or 'monitoring'
            'urls_checked': int,
            'pages_fetched': int,
            'successful_extractions': int,
            'empty_extractions': int,
            'errors': int
        }
    """
    session = get_session()
    
    try:
        # 1. Get district
        district = session.query(District).filter_by(id=district_id).first()
        if not district:
            raise ValueError(f"District {district_id} not found")
        
        print(f"Checking {district.name} ({district.domain})")
        
        # 2. Get URL pool
        print("Getting URL pool...")
        url_pool = get_url_pool(district_id)
        
        # 3. Determine mode and get URLs to check
        if not url_pool:
            # Discovery mode - need to find new URLs
            print("URL pool is empty - running discovery")
            mode = 'discovery'
            
            try:
                all_urls = discover_urls(district.domain)
                print(f"Found {len(all_urls)} URLs from discovery")
                urls_to_check = filter_urls(all_urls, district.name)
                print(f"Filtered to {len(urls_to_check)} URLs via LLM")
            except Exception as e:
                print(f"Discovery failed: {str(e)}")
                return {
                    'district_id': district_id,
                    'mode': 'discovery',
                    'urls_checked': 0,
                    'pages_fetched': 0,
                    'successful_extractions': 0,
                    'empty_extractions': 0,
                    'errors': 1
                }
        else:
            # Monitoring mode - check existing URLs
            print(f"URL pool has {len(url_pool)} valid URLs - running monitoring")
            mode = 'monitoring'
            urls_to_check = url_pool
        
        # Counters
        pages_fetched = 0
        successful_extractions = 0
        empty_extractions = 0
        errors = 0
        
        # 4. Fetch and extract from each URL
        for url in urls_to_check:
            print(f"Processing: {url}")
            
            # Fetch page
            fetch_result = fetch_page(url)
            pages_fetched += 1
            
            # Create FetchedPage record
            fetched_page = FetchedPage(
                district_id=district_id,
                url=fetch_result['url'],
                mode=mode,
                status=fetch_result['status'],
                error_message=fetch_result['error_message'],
                fetched_at=datetime.utcnow()
            )
            session.add(fetched_page)
            session.flush()  # Get the ID
            
            # If fetch succeeded, extract
            if fetch_result['status'] == 'success':
                extraction_result = extract_superintendent(
                    fetch_result['html'],
                    district.name
                )
                
                # Create Extraction record
                extraction = Extraction(
                    fetched_page_id=fetched_page.id,
                    name=extraction_result['name'],
                    title=extraction_result['title'],
                    email=extraction_result['email'],
                    phone=extraction_result['phone'],
                    extracted_text=extraction_result['extracted_text'],
                    llm_reasoning=extraction_result['llm_reasoning'],
                    is_empty=extraction_result['is_empty'],
                    extracted_at=datetime.utcnow()
                )
                session.add(extraction)
                
                if extraction_result['is_empty']:
                    empty_extractions += 1
                    print(f"  → No superintendent found")
                else:
                    successful_extractions += 1
                    print(f"  → Found: {extraction_result['name']}")
            else:
                errors += 1
                print(f"  → Fetch failed: {fetch_result['error_message']}")
        
        # 6. Update district
        district.last_checked_at = datetime.utcnow()
        
        # Commit all changes
        session.commit()
        
        print(f"\nCheck complete!")
        print(f"  Mode: {mode}")
        print(f"  URLs checked: {len(urls_to_check)}")
        print(f"  Pages fetched: {pages_fetched}")
        print(f"  Successful extractions: {successful_extractions}")
        print(f"  Empty extractions: {empty_extractions}")
        print(f"  Errors: {errors}")
        
        return {
            'district_id': district_id,
            'mode': mode,
            'urls_checked': len(urls_to_check),
            'pages_fetched': pages_fetched,
            'successful_extractions': successful_extractions,
            'empty_extractions': empty_extractions,
            'errors': errors
        }
        
    except Exception as e:
        session.rollback()
        print(f"District check failed: {str(e)}")
        raise
    finally:
        session.close()


def run_bulk_check(district_ids: List[int]) -> List[Dict]:
    """
    Run district checks for multiple districts.
    
    Args:
        district_ids: List of district IDs to check
    
    Returns:
        List of result dicts from run_district_check()
    """
    results = []
    
    for district_id in district_ids:
        try:
            result = run_district_check(district_id)
            results.append(result)
        except Exception as e:
            print(f"Failed to check district {district_id}: {str(e)}")
            results.append({
                'district_id': district_id,
                'mode': 'error',
                'urls_checked': 0,
                'pages_fetched': 0,
                'successful_extractions': 0,
                'empty_extractions': 0,
                'errors': 1
            })
    
    return results