from datetime import datetime
from typing import Dict

from models.database import get_session, District, FetchedPage, Extraction
from tasks.fetcher import fetch_page
from tasks.extraction import extract_superintendent


def run_monitoring_for_district(district_id: int, url: str) -> Dict:
    """
    Quick check: fetch one known-good URL and extract.
    
    Steps:
        1. Fetch single page
        2. Extract superintendent
        3. Save FetchedPage + Extraction with mode="monitoring"
        4. Update district.last_checked_at
        5. Return extraction
    
    Returns:
        Extraction dict with keys:
        {
            'name': str | None,
            'title': str | None,
            'email': str | None,
            'phone': str | None,
            'url': str,
            'fetched_at': datetime,
            'status': str,
            'is_empty': bool
        }
    """
    session = get_session()
    
    try:
        # Get district
        district = session.query(District).filter_by(id=district_id).first()
        if not district:
            raise ValueError(f"District {district_id} not found")
        
        print(f"Monitoring {district.name} at {url}")
        
        # Fetch page
        fetch_result = fetch_page(url)
        
        # Create FetchedPage record
        fetched_page = FetchedPage(
            district_id=district_id,
            url=fetch_result['url'],
            mode='monitoring',
            status=fetch_result['status'],
            error_message=fetch_result['error_message'],
            fetched_at=datetime.utcnow()
        )
        session.add(fetched_page)
        session.flush()
        
        # Extract if fetch succeeded
        result = {
            'url': url,
            'fetched_at': fetched_page.fetched_at,
            'status': fetch_result['status']
        }
        
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
            
            result.update({
                'name': extraction_result['name'],
                'title': extraction_result['title'],
                'email': extraction_result['email'],
                'phone': extraction_result['phone'],
                'is_empty': extraction_result['is_empty']
            })
            
            if extraction_result['is_empty']:
                print(f"  → No superintendent found")
            else:
                print(f"  → Found: {extraction_result['name']}")
        else:
            result.update({
                'name': None,
                'title': None,
                'email': None,
                'phone': None,
                'is_empty': True
            })
            print(f"  → Fetch failed: {fetch_result['error_message']}")
        
        # Update district
        district.last_checked_at = datetime.utcnow()
        
        session.commit()
        
        return result
        
    except Exception as e:
        session.rollback()
        print(f"Monitoring failed: {str(e)}")
        raise
    finally:
        session.close()