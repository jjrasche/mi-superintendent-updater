# tasks/extraction.py
from prefect import task
from models.database import PageCandidate
from datetime import datetime
from prefect.cache_policies import NONE
from utils.html_parser import clean_html_to_text
from utils.llm import llm_get_json

# tasks/extract.py
from prefect import task
from datetime import datetime, timezone

@task(retries=2, retry_delay_seconds=3)
def extract_contact(candidate_id: int) -> dict:
    """Extract superintendent contact - returns serializable dict"""
    session = get_session()
    try:
        candidate = session.query(PageCandidate).get(candidate_id)
        text = clean_html_to_text(candidate.html)
        
        result = llm_get_json([system_prompt, user_prompt])
        
        # Update candidate
        candidate.extraction_name = result.get('name')
        candidate.extraction_email = result.get('email')
        candidate.extraction_phone = result.get('phone')
        candidate.extraction_title = result.get('title')
        candidate.extraction_confidence = result.get('confidence', 0.0)
        candidate.extracted_at = datetime.now(timezone.utc)
        session.commit()
        
        # Return serializable result
        return {
            'candidate_id': candidate_id,
            'name': result.get('name'),
            'email': result.get('email'),
            'phone': result.get('phone'),
            'title': result.get('title'),
            'confidence': result.get('confidence', 0.0)
        }
    finally:
        session.close()


@task
def save_superintendent(extraction_result: dict, district_id: int):
    """Save high-confidence extractions to superintendent history"""
    if extraction_result['confidence'] < 0.7:
        return
    
    session = get_session()
    try:
        # Your save logic here
        session.commit()
    finally:
        session.close()