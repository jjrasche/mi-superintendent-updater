from datetime import datetime
from typing import List, Dict, Optional
from models.database import FetchedPage, Extraction
from .base import BaseRepository

class SuperintendentRepository(BaseRepository):
    """Superintendent extraction data operations"""

    # Queries
    get_monitoring_urls = lambda self, district_id: [
        row[0] for row in self.session.query(FetchedPage.url)
        .filter_by(district_id=district_id, mode='monitoring', status='success')
        .all()
    ]

    get_latest_extraction = lambda self, district_id: (
        self.session.query(Extraction)
        .join(FetchedPage)
        .filter(FetchedPage.district_id == district_id)
        .order_by(Extraction.extracted_at.desc())
        .first()
    )

    # Factories (single-expression builders)
    create_page = lambda self, district_id, url, mode, status, error=None: FetchedPage(
        district_id=district_id,
        url=url,
        mode=mode,
        status=status,
        error_message=error,
        fetched_at=datetime.utcnow()
    )

    create_extraction = lambda self, page_id, result: Extraction(
        fetched_page_id=page_id,
        name=result.get('name'),
        title=result.get('title'),
        email=result.get('email'),
        phone=result.get('phone'),
        extracted_text=result.get('extracted_text'),
        llm_reasoning=result.get('llm_reasoning'),
        is_empty=result.get('is_empty', False),
        extracted_at=datetime.utcnow()
    )

    # Chainable saves
    def save_page(self, page: FetchedPage) -> FetchedPage:
        """Save page and flush to get ID"""
        self.session.add(page)
        self.session.flush()
        return page

    def save_extraction(self, extraction: Extraction) -> Extraction:
        """Save extraction"""
        self.session.add(extraction)
        return extraction

    # Composite operations (full workflow steps)
    def save_fetch_result(self, district_id: int, url: str, mode: str, fetch_result: Dict) -> FetchedPage:
        """Create and save fetched page from fetch result"""
        return self.save_page(self.create_page(
            district_id, url, mode,
            fetch_result['status'],
            fetch_result.get('error_message')
        ))

    def save_extraction_result(self, page_id: int, extraction_result: Dict) -> Extraction:
        """Create and save extraction from extraction result"""
        return self.save_extraction(self.create_extraction(page_id, extraction_result))
