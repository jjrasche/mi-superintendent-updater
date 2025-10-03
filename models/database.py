# models/database.py
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class District(Base):
    """The school district we're tracking"""
    __tablename__ = "districts"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    domain = Column(String, nullable=False)
    home_page = Column(String, nullable=False)
    state = Column(String, default="MI")
    
    # Current superintendent info (denormalized for quick access)
    current_superintendent_name = Column(String)
    current_superintendent_email = Column(String)
    current_superintendent_phone = Column(String)
    current_superintendent_title = Column(String)
    crm_superintendent_name = Column(String)
    crm_superintendent_email = Column(String)
    crm_superintendent_phone = Column(String)
    crm_superintendent_title = Column(String)
    
    last_checked = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    discovery_runs = relationship("DiscoveryRun", back_populates="district")
    superintendent_history = relationship("SuperintendentHistory", back_populates="district")


class DiscoveryRun(Base):
    """Each time we run discovery for a district"""
    __tablename__ = "discovery_runs"
    
    id = Column(Integer, primary_key=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    status = Column(String, default="running")  # running, completed, failed
    
    candidates_found = Column(Integer)
    pages_fetched = Column(Integer)
    extraction_successful = Column(Integer)
    
    error_message = Column(Text)
    
    # Relationships
    district = relationship("District", back_populates="discovery_runs")
    page_candidates = relationship("PageCandidate", back_populates="discovery_run")


class PageCandidate(Base):
    """Each URL we discover and fetch"""
    __tablename__ = "page_candidates"
    
    id = Column(Integer, primary_key=True)
    discovery_run_id = Column(Integer, ForeignKey("discovery_runs.id"), nullable=False)
    
    url = Column(String, nullable=False)
    html = Column(Text)
    title = Column(String)
    discovery_rank = Column(Integer)  # 1-5 from LLM ranking
    discovery_score = Column(Float)   # Confidence in URL being relevant
    
    # Fetch results
    fetched_at = Column(DateTime)
    html_length = Column(Integer)
    screenshot_path = Column(String)
    fetch_method = Column(String)  # "http" or "playwright"
    
    # Extraction results
    extracted_at = Column(DateTime)
    extraction_name = Column(String)
    extraction_title = Column(String)
    extraction_email = Column(String)
    extraction_phone = Column(String)
    extraction_confidence = Column(Float)
    
    # Relationships
    discovery_run = relationship("DiscoveryRun", back_populates="page_candidates")


class SuperintendentHistory(Base):
    """Track superintendent changes over time"""
    __tablename__ = "superintendent_history"
    
    id = Column(Integer, primary_key=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    
    name = Column(String)
    title = Column(String)
    email = Column(String)
    phone = Column(String)
    
    source_url = Column(String)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    confidence = Column(Float)
    
    # Track if this is still current
    is_current = Column(Integer, default=1)  # 1 = current, 0 = past
    replaced_at = Column(DateTime)
    
    # Relationships
    district = relationship("District", back_populates="superintendent_history")


def init_db():
    """Create all tables"""
    Base.metadata.create_all(engine)


def get_session():
    """Get a database session"""
    return SessionLocal()