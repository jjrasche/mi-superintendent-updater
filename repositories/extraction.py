from datetime import datetime
from typing import Dict, Optional
from models.database import Extraction
from models.enums import ExtractionType
from .base import BaseRepository
import json


class ExtractionRepository(BaseRepository):
    """Generic extraction data operations"""

    # Factory
    def create_extraction(
        self,
        fetched_page_id: int,
        extraction_type: str,
        parsed_text: Optional[str] = None,
        parsing_method: Optional[str] = None,
        llm_prompt_template: Optional[str] = None,
        llm_input: Optional[str] = None,
        llm_output: Optional[str] = None,
        llm_reasoning: Optional[str] = None,
        is_empty: bool = False
    ) -> Extraction:
        """
        Create extraction record for any LLM operation.

        Args:
            fetched_page_id: ID of fetched page (has raw_html)
            extraction_type: Type of extraction (from ExtractionType enum)
            parsed_text: Text extracted from HTML for LLM processing
            parsing_method: Method used to parse HTML
            llm_prompt_template: Template name used
            llm_input: Full prompt sent to LLM
            llm_output: Raw JSON from LLM
            llm_reasoning: Reasoning from LLM response
            is_empty: Whether extraction found nothing

        Returns:
            Extraction object
        """
        return Extraction(
            fetched_page_id=fetched_page_id,
            extraction_type=extraction_type,
            parsed_text=parsed_text,
            parsing_method=parsing_method,
            llm_prompt_template=llm_prompt_template,
            llm_input=llm_input,
            llm_output=json.dumps(llm_output) if llm_output and not isinstance(llm_output, str) else llm_output,
            llm_reasoning=llm_reasoning,
            is_empty=is_empty,
            extracted_at=datetime.utcnow()
        )

    def save_extraction(self, extraction: Extraction) -> Extraction:
        """Save extraction and flush to get ID"""
        self.session.add(extraction)
        self.session.flush()
        return extraction

    # Queries
    def get_by_page(self, fetched_page_id: int) -> list[Extraction]:
        """Get all extractions for a fetched page"""
        return self.session.query(Extraction).filter_by(
            fetched_page_id=fetched_page_id
        ).all()

    def get_by_type(self, extraction_type: str, limit: int = 100) -> list[Extraction]:
        """Get recent extractions by type"""
        return self.session.query(Extraction).filter_by(
            extraction_type=extraction_type
        ).order_by(Extraction.extracted_at.desc()).limit(limit).all()

    def get_failed_extractions(self, limit: int = 100) -> list[Extraction]:
        """Get recent empty/failed extractions for debugging"""
        return self.session.query(Extraction).filter_by(
            is_empty=True
        ).order_by(Extraction.extracted_at.desc()).limit(limit).all()
