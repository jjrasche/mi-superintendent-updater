from pydantic import BaseModel, Field
from typing import Optional

class SuperintendentExtraction(BaseModel):
    """Superintendent contact information extracted from webpage"""
    name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    reasoning: str
    is_empty: bool

class URLFilterResult(BaseModel):
    """Filtered URLs likely to contain superintendent info"""
    urls: list[str]
    reasoning: str

class TransparencyLinkResult(BaseModel):
    """Budget/Salary transparency link identified from homepage"""
    url: Optional[str] = None
    reasoning: str

class HealthPlanData(BaseModel):
    """Individual health insurance plan"""
    plan_name: str
    provider: str
    plan_type: str = Field(..., description="Medical|Dental|Vision|Disability|Life Insurance|Long-Term Care|Other")
    coverage_details: Optional[str] = None
    source_url: Optional[str] = None
    is_empty: bool = False

class HealthPlanExtraction(BaseModel):
    """Collection of health plans extracted from transparency page"""
    plans: list[HealthPlanData]
    reasoning: str
