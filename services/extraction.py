"""
Thin service layer for LLM-based extractions.

Each function is a single-expression lambda that delegates to LLM client
with appropriate template and response model.
"""

from utils.llm_client import get_client
from models.extraction_results import (
    SuperintendentExtraction,
    URLFilterResult,
    TransparencyLinkResult,
    HealthPlanExtraction
)

# Superintendent extraction
extract_superintendent = lambda text, district_name: get_client().call(
    'superintendent_extraction',
    SuperintendentExtraction,
    text=text,
    district_name=district_name
)

# URL filtering
filter_urls = lambda urls, district_name: get_client().call(
    'url_filtering',
    URLFilterResult,
    urls=urls,
    district_name=district_name
)

# Transparency link identification
identify_transparency_link = lambda links, district_name=None: get_client().call(
    'link_identification',
    TransparencyLinkResult,
    links=links,
    district_name=district_name
)

# Health plan extraction
extract_health_plans = lambda text, district_name: get_client().call(
    'health_plan_extraction',
    HealthPlanExtraction,
    text=text,
    district_name=district_name
)
