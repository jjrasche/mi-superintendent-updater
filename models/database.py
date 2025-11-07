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
    
    # Relationships
    district: Mapped["District"] = relationship("District", back_populates="fetched_pages")
    extraction: Mapped[Optional["Extraction"]] = relationship(
        "Extraction", back_populates="fetched_page", uselist=False, cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index('idx_fetched_page_district_date', 'district_id', 'fetched_at'),
        Index('idx_fetched_page_mode', 'mode'),
    )
    
    def __repr__(self):
        return f"<FetchedPage(id={self.id}, url='{self.url[:50]}...', status='{self.status}')>"


class Extraction(Base):
    """Superintendent info extracted from a page"""
    __tablename__ = 'extractions'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fetched_page_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('fetched_pages.id'), nullable=False, unique=True
    )
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    llm_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_empty: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    extracted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    fetched_page: Mapped["FetchedPage"] = relationship("FetchedPage", back_populates="extraction")
    
    __table_args__ = (
        Index('idx_extraction_name', 'name'),
    )
    
    def __repr__(self):
        return f"<Extraction(id={self.id}, name='{self.name}', is_empty={self.is_empty})>"


class HealthPlan(Base):
    """Employee health insurance plan"""
    __tablename__ = 'health_plans'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_id: Mapped[int] = mapped_column(Integer, ForeignKey('districts.id'), nullable=False)
    
    # Core plan data
    plan_name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_type: Mapped[str] = mapped_column(String(50), nullable=False)  # Medical, Dental, Vision, etc.
    coverage_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Source metadata
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    district: Mapped["District"] = relationship("District", back_populates="health_plans")
    
    __table_args__ = (
        Index('idx_health_plan_district', 'district_id'),
        Index('idx_health_plan_provider', 'provider'),
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