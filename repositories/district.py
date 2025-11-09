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
    def mark_checked(self, district: District) -> District:
        """Mark district as checked now"""
        district.last_checked_at = datetime.utcnow()
        return district

    def set_transparency_url(self, district: District, url: str) -> District:
        """Set transparency URL for district"""
        district.transparency_url = url
        return district
