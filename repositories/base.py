from contextlib import contextmanager
from models.database import get_session

class BaseRepository:
    """Base repository with session management"""

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
