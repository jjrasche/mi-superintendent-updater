from datetime import datetime
from typing import List, Dict, Optional
from models.database import FetchedPage, District, SuperintendentContact
from models.enums import WorkflowMode, FetchStatus
from .base import BaseRepository

class SuperintendentRepository(BaseRepository):
    """Superintendent extraction data operations"""

    # Queries
    get_district = lambda self, district_id: (
        self.session.query(District).filter_by(id=district_id).first()
    )

    get_monitoring_urls = lambda self, district_id: [
        row[0] for row in self.session.query(FetchedPage.url)
        .filter_by(district_id=district_id, mode=WorkflowMode.MONITORING.value, status=FetchStatus.SUCCESS.value)
        .all()
    ]

    get_latest_contact = lambda self, district_id: (
        self.session.query(SuperintendentContact)
        .filter_by(district_id=district_id)
        .order_by(SuperintendentContact.extracted_at.desc())
        .first()
    )

    # Domain-specific factories
    create_contact = lambda self, district_id, result, extraction_id=None: SuperintendentContact(
        district_id=district_id,
        extraction_id=extraction_id,
        name=result.get('name'),
        title=result.get('title'),
        email=result.get('email'),
        phone=result.get('phone'),
        extracted_at=datetime.utcnow()
    )

    # Domain-specific saves
    def save_contact(self, contact: SuperintendentContact) -> SuperintendentContact:
        """Save superintendent contact"""
        self.session.add(contact)
        return contact

    # District updates
    def update_last_checked(self, district: District) -> District:
        """Update district last_checked_at timestamp"""
        district.last_checked_at = datetime.utcnow()
        return district
