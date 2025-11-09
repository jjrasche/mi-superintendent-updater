from datetime import datetime
from typing import Optional
from models.database import District
from .base import BaseRepository

class DistrictRepository(BaseRepository):
    """District data operations"""

    # Queries
    get = lambda self, district_id: self.session.query(District).filter_by(id=district_id).first()
    get_by_domain = lambda self, domain: self.session.query(District).filter_by(domain=domain).first()
    all = lambda self: self.session.query(District).all()

    # Updates
    mark_checked = lambda self, district: setattr(district, 'last_checked_at', datetime.utcnow()) or district
    set_transparency_url = lambda self, district, url: setattr(district, 'transparency_url', url) or district

    # Chainable operations
    def update_and_flush(self, district) -> District:
        """Update district and flush to get ID"""
        self.session.add(district)
        self.session.flush()
        return district
