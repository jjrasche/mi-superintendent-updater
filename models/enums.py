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

class ContentType(str, Enum):
    """Content type for fetched pages"""
    HTML = "html"
    PDF = "pdf"

class FileExtension(str, Enum):
    """Common file extensions"""
    PDF = ".pdf"
    DOC = ".doc"
    DOCX = ".docx"
    XLS = ".xls"
    XLSX = ".xlsx"
    PPT = ".ppt"
    PPTX = ".pptx"
    ZIP = ".zip"
    RAR = ".rar"
