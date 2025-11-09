from datetime import datetime
from typing import List, Dict, Optional
from models.database import HealthPlan, District
from .base import BaseRepository

class HealthPlanRepository(BaseRepository):
    """Health plan data operations"""

    # Queries
    get_district = lambda self, district_id: (
        self.session.query(District).filter_by(id=district_id).first()
    )

    get_by_district = lambda self, district_id: (
        self.session.query(HealthPlan)
        .filter_by(district_id=district_id)
        .all()
    )

    get_existing_plan = lambda self, district_id, plan_name, provider, plan_type: (
        self.session.query(HealthPlan).filter_by(
            district_id=district_id,
            plan_name=plan_name,
            provider=provider,
            plan_type=plan_type
        ).first()
    )

    # Factory
    create_plan = lambda self, district_id, plan_data, source_url: HealthPlan(
        district_id=district_id,
        plan_name=plan_data['plan_name'],
        provider=plan_data['provider'],
        plan_type=plan_data['plan_type'],
        coverage_details=plan_data.get('coverage_details'),
        source_url=source_url,
        extracted_at=datetime.utcnow()
    )

    # Saves
    def save_plan(self, plan: HealthPlan) -> HealthPlan:
        """Save health plan"""
        self.session.add(plan)
        return plan

    def save_plans(self, plans: List[HealthPlan]) -> List[HealthPlan]:
        """Save multiple health plans"""
        self.session.add_all(plans)
        return plans

    # Composite operations
    def save_extracted_plans(self, district_id: int, plans_data: List[Dict], source_url: str) -> List[HealthPlan]:
        """Create and save all plans from extraction result"""
        return self.save_plans([
            self.create_plan(district_id, plan_data, source_url)
            for plan_data in plans_data
        ])

    def upsert_plan(self, district_id: int, plan_data: Dict, transparency_url: str) -> HealthPlan:
        """Update existing plan or create new one"""
        existing = self.get_existing_plan(
            district_id,
            plan_data['plan_name'],
            plan_data['provider'],
            plan_data['plan_type']
        )

        if existing:
            if plan_data.get('source_url') and not existing.source_url:
                existing.source_url = plan_data['source_url']
            existing.extracted_at = datetime.utcnow()
            return existing
        else:
            return self.save_plan(self.create_plan(district_id, plan_data, transparency_url))

    def update_transparency_url(self, district: District, url: str) -> District:
        """Update district transparency URL"""
        district.transparency_url = url
        return district
