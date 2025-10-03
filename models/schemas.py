from dataclasses import dataclass
from typing import Optional


@dataclass
class SuperintendentContact:
    name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    

@dataclass
class PageCandidate:
    url: str
    html: str
    screenshot: Optional[str] = None
    discovery_score: float = 0.0
    extraction: Optional[SuperintendentContact] = None
    confidence: float = 0.0
