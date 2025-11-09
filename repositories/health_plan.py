from datetime import datetime
from typing import List, Dict
from models.database import HealthPlan
from .base import BaseRepository

class HealthPlanRepository(BaseRepository):
    """Health plan data operations"""

    # Queries
    get_by_district = lambda self, district_id: (
        self.session.query(HealthPlan)
        .filter_by(district_id=district_id)
        .all()
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

    # Composite operation
    def save_extracted_plans(self, district_id: int, plans_data: List[Dict], source_url: str) -> List[HealthPlan]:
        """Create and save all plans from extraction result"""
        return self.save_plans([
            self.create_plan(district_id, plan_data, source_url)
            for plan_data in plans_data
        ])
