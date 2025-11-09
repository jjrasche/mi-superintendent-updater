from enum import Enum

class WorkflowMode(str, Enum):
    """Workflow execution modes"""
    DISCOVERY = "discovery"
    MONITORING = "monitoring"

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
