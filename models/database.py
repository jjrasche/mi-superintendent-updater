from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    create_engine, String, Integer, DateTime, Boolean, Text, ForeignKey,
    Index, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from config import DB_URL


class Base(DeclarativeBase):
    pass


class District(Base):
    """School district to monitor"""
    __tablename__ = 'districts'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    state: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    transparency_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    fetched_pages: Mapped[List["FetchedPage"]] = relationship(
        "FetchedPage", back_populates="district", cascade="all, delete-orphan"
    )
    health_plans: Mapped[List["HealthPlan"]] = relationship(
        "HealthPlan", back_populates="district", cascade="all, delete-orphan"
    )
    superintendent_contacts: Mapped[List["SuperintendentContact"]] = relationship(
        "SuperintendentContact", back_populates="district", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index('idx_district_last_checked', 'last_checked_at'),
    )
    
    def __repr__(self):
        return f"<District(id={self.id}, name='{self.name}', domain='{self.domain}')>"


class FetchedPage(Base):
    """A webpage we retrieved and analyzed"""
    __tablename__ = 'fetched_pages'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_id: Mapped[int] = mapped_column(Integer, ForeignKey('districts.id'), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)  # "discovery" or "monitoring"
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # "success", "error", "timeout"
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Fetch result content
    raw_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Compressed HTML/content
    content_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # "html" or "pdf"

    # Relationships
    district: Mapped["District"] = relationship("District", back_populates="fetched_pages")
    extractions: Mapped[List["Extraction"]] = relationship(
        "Extraction", back_populates="fetched_page", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index('idx_fetched_page_district_date', 'district_id', 'fetched_at'),
        Index('idx_fetched_page_mode', 'mode'),
    )
    
    def __repr__(self):
        return f"<FetchedPage(id={self.id}, url='{self.url[:50]}...', status='{self.status}')>"


class Extraction(Base):
    """Generic LLM extraction - tracks HTML→Text→LLM pipeline"""
    __tablename__ = 'extractions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fetched_page_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('fetched_pages.id'), nullable=False
    )

    # Extraction metadata
    extraction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Types: "superintendent", "health_plan", "url_filtering", "link_identification"

    # HTML → Text parsing stage (FRAGILE POINT #1)
    # Note: raw_html is stored in FetchedPage, not here
    parsed_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Text extracted from HTML for LLM processing
    parsing_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # Method: "html_parser", "pdf_parser", "playwright_render"

    # LLM extraction stage (FRAGILE POINT #2)
    llm_prompt_template: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Template name: "superintendent_extraction", "health_plan_extraction", etc.
    llm_input: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Full prompt sent to LLM (may be large)
    llm_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Raw JSON response from LLM
    llm_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Extracted reasoning field from LLM response

    # Result metadata
    is_empty: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    extracted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    fetched_page: Mapped["FetchedPage"] = relationship("FetchedPage", back_populates="extractions")

    __table_args__ = (
        Index('idx_extraction_type', 'extraction_type'),
        Index('idx_extraction_page', 'fetched_page_id'),
        Index('idx_extraction_empty', 'is_empty'),
    )

    def __repr__(self):
        return f"<Extraction(id={self.id}, type='{self.extraction_type}', is_empty={self.is_empty})>"


class SuperintendentContact(Base):
    """Superintendent contact information (domain-specific extraction result)"""
    __tablename__ = 'superintendent_contacts'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_id: Mapped[int] = mapped_column(Integer, ForeignKey('districts.id'), nullable=False)
    extraction_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('extractions.id'), nullable=True)

    # Contact fields
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Metadata
    extracted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    district: Mapped["District"] = relationship("District", back_populates="superintendent_contacts")
    extraction: Mapped[Optional["Extraction"]] = relationship("Extraction")

    __table_args__ = (
        Index('idx_superintendent_district', 'district_id'),
        Index('idx_superintendent_extraction', 'extraction_id'),
    )

    def __repr__(self):
        return f"<SuperintendentContact(id={self.id}, name='{self.name}')>"


class HealthPlan(Base):
    """Employee health insurance plan"""
    __tablename__ = 'health_plans'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_id: Mapped[int] = mapped_column(Integer, ForeignKey('districts.id'), nullable=False)
    extraction_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('extractions.id'), nullable=True)

    # Core plan data
    plan_name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_type: Mapped[str] = mapped_column(String(50), nullable=False)  # Medical, Dental, Vision, etc.
    coverage_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Source metadata
    source_url: Mapped[str] = mapped_column(Text, nullable=True)
    extracted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    district: Mapped["District"] = relationship("District", back_populates="health_plans")
    extraction: Mapped[Optional["Extraction"]] = relationship("Extraction")

    __table_args__ = (
        Index('idx_health_plan_district', 'district_id'),
        Index('idx_health_plan_provider', 'provider'),
        Index('idx_health_plan_extraction', 'extraction_id'),
        UniqueConstraint('district_id', 'plan_name', 'provider', 'plan_type', name='uq_district_plan'),
    )
    def __repr__(self):
        return f"<HealthPlan(id={self.id}, plan_name='{self.plan_name}', provider='{self.provider}')>"


# Database engine and session factory
engine = create_engine(DB_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db():
    """Create all tables"""
    Base.metadata.create_all(engine)


def get_session():
    """Get a new database session"""
    return SessionLocal()