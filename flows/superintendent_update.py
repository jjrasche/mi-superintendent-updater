# flows/superintendent_update.py
from prefect import flow
from tasks.discovery import get_candidate_urls, getSoup
from models.database import get_session, District, DiscoveryRun, PageCandidate
from datetime import datetime

@flow(name="discover-superintendent", log_prints=True)
def discover_superintendent_flow(district: District):
    """Main discovery flow for finding superintendent pages"""
    print(f"\n{'='*60}\nStarting discovery for: {district.name}\nDomain: {district.domain}\n{'='*60}\n")
    session = get_session()    
    try:
        district = session.query(District).filter_by(name=district.name).first()
        run = DiscoveryRun( district_id=district.id, started_at=datetime.utcnow(), status="running" )
        session.add(run)
        session.commit()
        candidates = get_candidate_urls(district)        
        run.candidates_found = len(candidates)
        session.commit()
        for i, url in enumerate(candidates, 1):
            print(f"  {i}. {url}")
        collectCandidates(district, run, candidates, session)
        print(f"\n{'='*60}\nDiscovery run ID: {run.id}\n{'='*60}")
    except Exception as e:
        # Mark run as failed
        if 'run' in locals():
            run.status = "failed"
            run.error_message = str(e)
            run.completed_at = datetime.utcnow()
            session.commit()
        raise
    finally:
        session.close()


def collectCandidates(district: District, run: DiscoveryRun, url: str, session):
    """Collect candidate pages for a given district and discovery run"""
    for url in url[:5]:  # Limit to top 5 candidates
        saveCandidate(run, url, session)
    run.completed_at = datetime.utcnow()
    run.status = "completed"
    district.last_checked = datetime.utcnow()
    session.commit()

def saveCandidate(run: DiscoveryRun, url: str, session):
    """Fetch page content and save a PageCandidate object"""
    try:
        soup = getSoup(url)
        title = soup.title.string if soup.title else "No title"
        text = soup.get_text(separator="\n", strip=True)[:5000]  # Limit to first 5000 chars
        candidate = PageCandidate( discovery_run_id=run.id, url=url, title=title, content=text, fetched_at=datetime.utcnow(), status="fetched")
    except Exception as e:
        candidate = PageCandidate( discovery_run_id=run.id, url=url, title="Error", content=str(e), fetched_at=datetime.utcnow(), status="error")
    session.add(candidate)

if __name__ == "__main__":
    # Initialize database first
    from models.database import init_db
    init_db()
    
    # Test run with a real Michigan district
    results = discover_superintendent_flow(
        District(
            name="Cass City Public Schools",
            domain="casscityschools.org",
            home_page="https://casscityschools.org"
        )
    )

    print(f"\nFinal Results:")
    print(f"  Pages successfully fetched: {len(results)}")
    for result in results:
        print(f"    - {result['url']}")