from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import Session

from models.database import get_session, District, FetchedPage, Extraction


def get_current_superintendent(district_id: int) -> Optional[Dict]:
    """
    Get most recent successful extraction for district.
    
    Returns:
        {
            'name': str,
            'title': str,
            'email': str,
            'phone': str,
            'url': str,  # Source URL
            'fetched_at': datetime
        }
    """
    session = get_session()
    
    try:
        result = (
            session.query(Extraction, FetchedPage)
            .join(FetchedPage)
            .filter(
                FetchedPage.district_id == district_id,
                FetchedPage.status == 'success',
                Extraction.is_empty == False
            )
            .order_by(desc(FetchedPage.fetched_at))
            .first()
        )
        
        if not result:
            return None
        
        extraction, fetched_page = result
        
        return {
            'name': extraction.name,
            'title': extraction.title,
            'email': extraction.email,
            'phone': extraction.phone,
            'url': fetched_page.url,
            'fetched_at': fetched_page.fetched_at
        }
    finally:
        session.close()


def get_districts_with_conflicts(days: int = 1) -> List[Dict]:
    """
    Find districts where recent extractions have conflicting data.
    
    Returns list of:
        {
            'district_id': int,
            'district_name': str,
            'conflict_date': date,
            'extractions': [
                {'name': 'Dr. Smith', 'email': '...', 'count': 6},
                {'name': 'Dr. Jones', 'email': '...', 'count': 4}
            ]
        }
    
    Query:
        - Group FetchedPages by district_id and DATE(fetched_at)
        - Where mode='discovery' and fetched in last N days
        - Having COUNT(DISTINCT Extraction.name) > 1
    """
    session = get_session()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get districts with multiple distinct names in recent discovery
        conflicts = []
        
        # Find all districts with recent discovery runs
        districts_with_recent_discovery = (
            session.query(District.id, District.name, func.date(FetchedPage.fetched_at).label('date'))
            .join(FetchedPage)
            .filter(
                FetchedPage.mode == 'discovery',
                FetchedPage.fetched_at >= cutoff_date
            )
            .group_by(District.id, District.name, func.date(FetchedPage.fetched_at))
            .all()
        )
        
        # Check each district/date for conflicts
        for district_id, district_name, date in districts_with_recent_discovery:
            # Get all extractions for this district on this date
            extractions = (
                session.query(Extraction.name, Extraction.email, func.count().label('count'))
                .join(FetchedPage)
                .filter(
                    FetchedPage.district_id == district_id,
                    func.date(FetchedPage.fetched_at) == date,
                    FetchedPage.mode == 'discovery',
                    Extraction.is_empty == False,
                    Extraction.name.isnot(None)
                )
                .group_by(Extraction.name, Extraction.email)
                .all()
            )
            
            # If multiple distinct names, it's a conflict
            if len(extractions) > 1:
                conflicts.append({
                    'district_id': district_id,
                    'district_name': district_name,
                    'conflict_date': date,
                    'extractions': [
                        {'name': e.name, 'email': e.email, 'count': e.count}
                        for e in extractions
                    ]
                })
        
        return conflicts
    finally:
        session.close()


def get_districts_with_no_data(days: int = 7) -> List[Dict]:
    """
    Districts where all recent extractions returned empty.
    
    Returns list of:
        {
            'district_id': int,
            'district_name': str,
            'last_attempt': datetime,
            'pages_tried': int
        }
    
    Query:
        - Districts with FetchedPages in last N days
        - Where ALL Extractions have is_empty=True
    """
    session = get_session()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get districts with recent attempts
        districts_with_attempts = (
            session.query(
                District.id,
                District.name,
                func.max(FetchedPage.fetched_at).label('last_attempt'),
                func.count(FetchedPage.id).label('pages_tried')
            )
            .join(FetchedPage)
            .filter(FetchedPage.fetched_at >= cutoff_date)
            .group_by(District.id, District.name)
            .all()
        )
        
        no_data_districts = []
        
        for district_id, district_name, last_attempt, pages_tried in districts_with_attempts:
            # Check if ALL extractions are empty
            non_empty_count = (
                session.query(func.count(Extraction.id))
                .join(FetchedPage)
                .filter(
                    FetchedPage.district_id == district_id,
                    FetchedPage.fetched_at >= cutoff_date,
                    Extraction.is_empty == False
                )
                .scalar()
            )
            
            if non_empty_count == 0:
                no_data_districts.append({
                    'district_id': district_id,
                    'district_name': district_name,
                    'last_attempt': last_attempt,
                    'pages_tried': pages_tried
                })
        
        return no_data_districts
    finally:
        session.close()


def get_superintendent_changes(days: int = 30) -> List[Dict]:
    """
    Districts where superintendent changed recently.
    
    Returns list of:
        {
            'district_id': int,
            'district_name': str,
            'old_name': str,
            'old_email': str,
            'new_name': str,
            'new_email': str,
            'changed_at': datetime
        }
    
    Query:
        - Compare most recent 2 successful extractions per district
        - Where name OR email differs
        - Within last N days
    """
    session = get_session()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        changes = []
        
        # Get all districts
        districts = session.query(District).all()
        
        for district in districts:
            # Get two most recent successful extractions
            extractions = (
                session.query(Extraction, FetchedPage)
                .join(FetchedPage)
                .filter(
                    FetchedPage.district_id == district.id,
                    FetchedPage.status == 'success',
                    FetchedPage.fetched_at >= cutoff_date,
                    Extraction.is_empty == False,
                    Extraction.name.isnot(None)
                )
                .order_by(desc(FetchedPage.fetched_at))
                .limit(2)
                .all()
            )
            
            if len(extractions) >= 2:
                new_extraction, new_page = extractions[0]
                old_extraction, old_page = extractions[1]
                
                # Check if name or email changed
                if (new_extraction.name != old_extraction.name or 
                    new_extraction.email != old_extraction.email):
                    changes.append({
                        'district_id': district.id,
                        'district_name': district.name,
                        'old_name': old_extraction.name,
                        'old_email': old_extraction.email,
                        'new_name': new_extraction.name,
                        'new_email': new_extraction.email,
                        'changed_at': new_page.fetched_at
                    })
        
        return changes
    finally:
        session.close()


def get_stale_districts(days: int = 90) -> List[District]:
    """
    Districts not checked in N days.
    
    Query:
        District WHERE last_checked_at < NOW() - days 
        OR last_checked_at IS NULL
    """
    session = get_session()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        districts = (
            session.query(District)
            .filter(
                or_(
                    District.last_checked_at < cutoff_date,
                    District.last_checked_at.is_(None)
                )
            )
            .all()
        )
        
        return districts
    finally:
        session.close()


def get_extraction_history(district_id: int, limit: int = 10) -> List[Dict]:
    """
    Timeline of all extractions for a district.
    
    Returns:
        List of extractions with fetched_page info, ordered by date DESC
    """
    session = get_session()
    
    try:
        results = (
            session.query(Extraction, FetchedPage)
            .join(FetchedPage)
            .filter(FetchedPage.district_id == district_id)
            .order_by(desc(FetchedPage.fetched_at))
            .limit(limit)
            .all()
        )
        
        history = []
        for extraction, fetched_page in results:
            history.append({
                'name': extraction.name,
                'title': extraction.title,
                'email': extraction.email,
                'phone': extraction.phone,
                'url': fetched_page.url,
                'mode': fetched_page.mode,
                'status': fetched_page.status,
                'is_empty': extraction.is_empty,
                'fetched_at': fetched_page.fetched_at,
                'llm_reasoning': extraction.llm_reasoning
            })
        
        return history
    finally:
        session.close()


def get_discovery_results(district_id: int, date: str) -> List[Dict]:
    """
    All pages fetched during a discovery run.
    
    Args:
        district_id: District ID
        date: Date string "YYYY-MM-DD"
    
    Returns:
        List of FetchedPages + Extractions from that date
        
    Query:
        FetchedPages WHERE district_id=X 
        AND DATE(fetched_at)=date 
        AND mode='discovery'
        JOIN Extractions
    """
    session = get_session()
    
    try:
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
        
        results = (
            session.query(FetchedPage, Extraction)
            .outerjoin(Extraction)
            .filter(
                FetchedPage.district_id == district_id,
                func.date(FetchedPage.fetched_at) == target_date,
                FetchedPage.mode == 'discovery'
            )
            .all()
        )
        
        pages = []
        for fetched_page, extraction in results:
            page_data = {
                'url': fetched_page.url,
                'status': fetched_page.status,
                'error_message': fetched_page.error_message,
                'fetched_at': fetched_page.fetched_at
            }
            
            if extraction:
                page_data.update({
                    'name': extraction.name,
                    'title': extraction.title,
                    'email': extraction.email,
                    'phone': extraction.phone,
                    'is_empty': extraction.is_empty,
                    'llm_reasoning': extraction.llm_reasoning
                })
            
            pages.append(page_data)
        
        return pages
    finally:
        session.close()


def get_failed_fetches(days: int = 7) -> List[Dict]:
    """
    Recent page fetch failures.
    
    Returns list of:
        {
            'district_id': int,
            'district_name': str,
            'url': str,
            'error_message': str,
            'failed_at': datetime
        }
    
    Query:
        FetchedPages WHERE status='error' 
        AND fetched_at > NOW() - days
    """
    session = get_session()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        results = (
            session.query(FetchedPage, District)
            .join(District)
            .filter(
                FetchedPage.status == 'error',
                FetchedPage.fetched_at >= cutoff_date
            )
            .order_by(desc(FetchedPage.fetched_at))
            .all()
        )
        
        failures = []
        for fetched_page, district in results:
            failures.append({
                'district_id': district.id,
                'district_name': district.name,
                'url': fetched_page.url,
                'error_message': fetched_page.error_message,
                'failed_at': fetched_page.fetched_at
            })
        
        return failures
    finally:
        session.close()