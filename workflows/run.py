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
    
    Returns:
        {
            'district_id': int,
            'mode': str,
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
        
        print(f"\n{'='*60}")
        print(f"Checking {district.name} ({district.domain})")
        print(f"{'='*60}")
        
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
                print(f"\n[DISCOVERY COMPLETE] Found {len(all_urls)} total URLs")
                
                # Print first 15 URLs for inspection
                print("\nSample of discovered URLs:")
                for i, url in enumerate(all_urls[:15], 1):
                    print(f"  {i}. {url}")
                if len(all_urls) > 15:
                    print(f"  ... and {len(all_urls) - 15} more")
                
                urls_to_check, llm_reasoning = filter_urls(all_urls, district.name, district.domain)
                print(f"\n[FILTERING COMPLETE] Selected {len(urls_to_check)} URLs")
                
                if llm_reasoning:
                    print(f"\nLLM Reasoning:")
                    print(f"  {llm_reasoning}")
                
                print("\nFinal selected URLs:")
                for i, url in enumerate(urls_to_check, 1):
                    print(f"  {i}. {url}")
                
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
            
            print("\nURLs to monitor:")
            for i, url in enumerate(urls_to_check, 1):
                print(f"  {i}. {url}")
        
        # Counters
        pages_fetched = 0
        successful_extractions = 0
        empty_extractions = 0
        errors = 0
        
        # 4. Fetch and extract from each URL
        print(f"\n{'='*60}")
        print("Processing URLs...")
        print(f"{'='*60}")
        
        for idx, url in enumerate(urls_to_check, 1):
            print(f"\n[{idx}/{len(urls_to_check)}] Processing: {url}")
            
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
                    district.name,
                    url  # Pass URL for logging
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
                    if extraction_result['llm_reasoning']:
                        print(f"     Reason: {extraction_result['llm_reasoning'][:100]}")
                else:
                    successful_extractions += 1
                    print(f"  → ✓ Found: {extraction_result['name']}")
                    print(f"     Title: {extraction_result['title']}")
                    print(f"     Email: {extraction_result['email']}")
            else:
                errors += 1
                print(f"  → ✗ Fetch failed: {fetch_result['error_message']}")
        
        # 6. Update district
        district.last_checked_at = datetime.utcnow()
        
        # Commit all changes
        session.commit()
        
        print(f"\n{'='*60}")
        print(f"Check complete for {district.name}")
        print(f"{'='*60}")
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