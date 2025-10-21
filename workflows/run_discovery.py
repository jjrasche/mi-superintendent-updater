from datetime import datetime
from typing import Dict

from models.database import get_session, District, FetchedPage, Extraction
from tasks.discovery import discover_urls, filter_urls
from tasks.fetcher import fetch_page
from tasks.extraction import extract_superintendent


def run_discovery_for_district(district_id: int) -> Dict:
    """
    Full discovery workflow: find superintendent from scratch.
    
    Steps:
        1. Get district from DB
        2. Discover URLs from domain
        3. Filter to top 10 URLs via LLM
        4. Fetch all 10 pages (sequential)
        5. Extract from all 10 pages (sequential)
        6. Save all FetchedPages + Extractions to DB
        7. Update district.last_checked_at
        8. Return summary
    
    Returns:
        {
            'district_id': int,
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
        
        print(f"Starting discovery for {district.name} ({district.domain})")
        
        # 2. Discover URLs
        print("Discovering URLs...")
        try:
            all_urls = discover_urls(district.domain)
            print(f"Found {len(all_urls)} URLs")
        except Exception as e:
            print(f"URL discovery failed: {str(e)}")
            return {
                'district_id': district_id,
                'pages_fetched': 0,
                'successful_extractions': 0,
                'empty_extractions': 0,
                'errors': 1
            }
        
        # 3. Filter URLs
        print("Filtering URLs with LLM...")
        filtered_urls = filter_urls(all_urls, district.name)
        print(f"Selected {len(filtered_urls)} URLs for processing")
        
        # Counters
        pages_fetched = 0
        successful_extractions = 0
        empty_extractions = 0
        errors = 0
        
        # 4 & 5. Fetch and extract from each URL
        for url in filtered_urls:
            print(f"Processing: {url}")
            
            # Fetch page
            fetch_result = fetch_page(url)
            pages_fetched += 1
            
            # Create FetchedPage record
            fetched_page = FetchedPage(
                district_id=district_id,
                url=fetch_result['url'],
                mode='discovery',
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
        
        # 7. Update district
        district.last_checked_at = datetime.utcnow()
        
        # Commit all changes
        session.commit()
        
        print(f"\nDiscovery complete!")
        print(f"  Pages fetched: {pages_fetched}")
        print(f"  Successful extractions: {successful_extractions}")
        print(f"  Empty extractions: {empty_extractions}")
        print(f"  Errors: {errors}")
        
        return {
            'district_id': district_id,
            'pages_fetched': pages_fetched,
            'successful_extractions': successful_extractions,
            'empty_extractions': empty_extractions,
            'errors': errors
        }
        
    except Exception as e:
        session.rollback()
        print(f"Discovery failed: {str(e)}")
        raise
    finally:
        session.close()