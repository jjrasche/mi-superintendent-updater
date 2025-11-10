from enum import Enum

class WorkflowMode(str, Enum):
    """Workflow execution modes"""
    DISCOVERY = "discovery"
    MONITORING = "monitoring"
    HEALTH_PLAN = "health_plan"
    HOMEPAGE_DISCOVERY = "homepage_discovery"

class FetchStatus(str, Enum):
    """Page fetch status"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"

class ExtractionStatus(str, Enum):
    """Health plan extraction status"""
    NO_LINK = "no_link"
    ERROR = "error"
    SUCCESS = "success"

class ExtractionType(str, Enum):
    """Type of LLM extraction operation"""
    SUPERINTENDENT = "superintendent"
    HEALTH_PLAN = "health_plan"
    URL_FILTERING = "url_filtering"
    LINK_IDENTIFICATION = "link_identification"
