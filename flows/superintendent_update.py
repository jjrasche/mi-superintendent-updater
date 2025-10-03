# flows/superintendent_update.py
from prefect import flow
from tasks.discovery import get_candidate_urls, getSoup
from models.database import get_session, District, DiscoveryRun, PageCandidate
from datetime import datetime

from tasks.extract import extract_contact

@flow(name="discover-superintendent", log_prints=True)
def discover_superintendent_flow(district: District):
    """Main discovery flow for finding superintendent pages"""
    print(f"\n{'='*60}\nStarting discovery for: {district.name}\nDomain: {district.domain}\n{'='*60}\n")
    session = get_session()    
    try:
        district = session.query(District).filter_by(name=district.name).first()
        candidates = get_candidate_urls(district)
        run = startDiscoveryRun(district, session)  
        run.candidates_found = len(candidates)
        collectCandidates(district, run, candidates, session)
        print(f"\n{'='*60}\nDiscovery run ID: {run.id}\n{'='*60}")
    except Exception as e:
        handleError(run, e, session)
    finally:
        session.close()

def startDiscoveryRun(district: District, session) -> DiscoveryRun:
    run = DiscoveryRun( district_id=district.id, started_at=datetime.utcnow(), status="running" )
    session.add(run)
    session.commit()
    return run

def handleError(run: DiscoveryRun, error: Exception, session):
    if 'run' in locals():
        run.status = "failed"
        run.error_message = str(error)
        run.completed_at = datetime.utcnow()
        session.commit()
    raise

def collectCandidates(district: District, run: DiscoveryRun, candidate_contexts: list[dict], session):
    """Collect candidate pages for a given district and discovery run"""
    for context in candidate_contexts[:5]:  # Limit to top 5 candidates
        saveCandidate(run, context, session)
    run.completed_at = datetime.utcnow()
    run.status = "completed"
    district.last_checked = datetime.utcnow()
    session.commit()

def saveCandidate(run: DiscoveryRun, context: dict, session):
    """Fetch page content and save a PageCandidate object"""
    try:
        url = context['url']
        html = context.get('html')
        title = context.get('title', "No title")
        candidate = PageCandidate( discovery_run_id=run.id, url=url, title=title, html=html, fetched_at=datetime.utcnow(), status="fetched")
        extract_contact(candidate, session)
        print(f"  Fetched and saved candidate: {url} (Title: {title})")
    except Exception as e:
        candidate = PageCandidate( discovery_run_id=run.id, url=url, title="Error", html=str(e), fetched_at=datetime.utcnow(), status="error")
    session.add(candidate)

def get_districts_to_process(session, limit=5, state="MI", only_unchecked=False):
    """Get a limited set of districts for testing"""
    query = session.query(District).filter_by(state=state)
    if only_unchecked:
        query = query.filter(District.last_checked.is_(None))
    return query.limit(limit).all()

if __name__ == "__main__":
    from models.database import init_db
    init_db()
    session = get_session()
    test_districts = get_districts_to_process(session, limit=3, only_unchecked=False)
    for district in test_districts:
        discover_superintendent_flow(district)
    session.close()
    print(f"\n\n{'='*60}\nCompleted processing {len(test_districts)} districts\n{'='*60}")