# tasks/extraction.py
from prefect import task
from models.database import PageCandidate
from datetime import datetime

from utils.html_parser import clean_html_to_text
from utils.llm import llm_get_json

@task(retries=2, retry_delay_seconds=3)
def extract_contact(page_candidate: PageCandidate, session) -> PageCandidate:
    """Extract superintendent contact info from a page's HTML"""
    text = clean_html_to_text(page_candidate.html)
    system_prompt = """You are an expert at extracting superintendent contact information from school district webpages.\n\nYour task: Find ONLY the superintendent (not assistant superintendent, board members, principals, etc).\nExtract: full name, official title, email address, phone number.\n\nReply ONLY with valid JSON in this exact format:\n{\n  "name": "John Smith",\n  "title": "Superintendent",\n  "email": "jsmith@district.org",\n  "phone": "(555) 123-4567",\n  "confidence": 0.95\n}\n\nIf you cannot find the superintendent's info, return empty strings and confidence 0.0"""
    user_prompt = f"""Extract the superintendent's contact information from this school district webpage.\n\nPage content:\n{text}"""
    try:
        result = llm_get_json([system_prompt, user_prompt])
        page_candidate.extraction_name = result.get('name')
        page_candidate.extraction_title = result.get('title')
        page_candidate.extraction_email = result.get('email')
        page_candidate.extraction_phone = result.get('phone')
        page_candidate.extraction_confidence = result.get('confidence', 0.0)
        page_candidate.extracted_at = datetime.utcnow()
        session.commit()
        print(f"  ✓ Extracted from {page_candidate.url[:50]}... (confidence: {page_candidate.extraction_confidence})")
        return page_candidate
        
    except Exception as e:
        print(f"  ✗ Extraction failed for {page_candidate.url[:50]}...: {e}")
        page_candidate.extraction_confidence = 0.0
        page_candidate.extracted_at = datetime.utcnow()
        session.commit()
        return page_candidate