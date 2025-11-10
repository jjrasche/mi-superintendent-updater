from contextlib import contextmanager
from datetime import datetime
from typing import Dict
from models.database import get_session, FetchedPage
from utils.html_compressor import compress_html

class BaseRepository:
    """Base repository with session management and common FetchedPage operations"""

    def __init__(self, session):
        self.session = session

    @classmethod
    @contextmanager
    def transaction(cls):
        """Context manager for transactional operations"""
        session = get_session()
        try:
            yield cls(session)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # Common FetchedPage operations (used by all domain repos)
    create_page = lambda self, district_id, url, mode, status, error=None, raw_html=None, content_type=None: FetchedPage(
        district_id=district_id,
        url=url,
        mode=mode,
        status=status,
        error_message=error,
        raw_html=compress_html(raw_html) if raw_html else None,
        content_type=content_type,
        fetched_at=datetime.utcnow()
    )

    def save_page(self, page: FetchedPage) -> FetchedPage:
        """Save page and flush to get ID"""
        self.session.add(page)
        self.session.flush()
        return page

    def save_fetch_result(self, district_id: int, url: str, mode: str, fetch_result: Dict) -> FetchedPage:
        """Create and save fetched page from fetch result"""
        return self.save_page(self.create_page(
            district_id, url, mode,
            fetch_result['status'],
            fetch_result.get('error_message'),
            fetch_result.get('html'),
            fetch_result.get('content_type', 'html')
        ))
