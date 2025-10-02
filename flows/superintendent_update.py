# flows/superintendent_update.py
from prefect import flow
from tasks.discovery import get_candidate_urls, fetch_page
from models.database import get_session, District, DiscoveryRun, PageCandidate
from datetime import datetime


@flow(name="discover-superintendent", log_prints=True)
def discover_superintendent_flow(district_name: str, domain: str):
    """Main discovery flow for finding superintendent pages"""
    print(f"\n{'='*60}")
    print(f"Starting discovery for: {district_name}")
    print(f"Domain: {domain}")
    print(f"{'='*60}\n")
    
    session = get_session()
    
    try:
        # Get or create district
        district = session.query(District).filter_by(name=district_name).first()
        if not district:
            district = District(name=district_name, domain=domain)
            session.add(district)
            session.commit()
            print(f"✓ Created new district record (ID: {district.id})")
        else:
            print(f"✓ Found existing district (ID: {district.id})")
        
        # Create discovery run
        run = DiscoveryRun(
            district_id=district.id,
            started_at=datetime.utcnow(),
            status="running"
        )
        session.add(run)
        session.commit()
        print(f"✓ Started discovery run (ID: {run.id})\n")
        
        # Step 1: Get candidate URLs
        candidates = get_candidate_urls(district_name, domain)
        print(f"\n✓ Found {len(candidates)} candidate URLs\n")
        
        run.candidates_found = len(candidates)
        session.commit()
        
        for i, url in enumerate(candidates, 1):
            print(f"  {i}. {url}")
        
        # Step 2: Fetch each candidate
        print(f"\n{'='*60}")
        print("Fetching candidate pages...")
        print(f"{'='*60}\n")
        
        results = []
        fetched_count = 0
        
        for i, url in enumerate(candidates[:5], 1):
            print(f"\n[{i}/{min(len(candidates), 5)}] ", end="")
            try:
                page_data = fetch_page(url)
                results.append(page_data)
                fetched_count += 1
                
                # Save page candidate
                page_candidate = PageCandidate(
                    discovery_run_id=run.id,
                    url=page_data['url'],
                    discovery_rank=i,
                    fetched_at=datetime.utcnow(),
                    html_length=page_data['html_length'],
                    screenshot_path=page_data.get('screenshot'),
                    fetch_method="playwright" if page_data.get('screenshot') else "http"
                )
                session.add(page_candidate)
                session.commit()
                
                print(f"✓ Success (HTML: {page_data['html_length']:,} chars)")
                if page_data['screenshot']:
                    print(f"  Screenshot: {page_data['screenshot']}")
                    
            except Exception as e:
                print(f"✗ Failed: {e}")
                
                # Save failed candidate
                page_candidate = PageCandidate(
                    discovery_run_id=run.id,
                    url=url,
                    discovery_rank=i,
                    fetched_at=datetime.utcnow()
                )
                session.add(page_candidate)
                session.commit()
        
        # Update discovery run
        run.completed_at = datetime.utcnow()
        run.status = "completed"
        run.pages_fetched = fetched_count
        district.last_checked = datetime.utcnow()
        session.commit()
        
        print(f"\n{'='*60}")
        print(f"Discovery complete: {len(results)}/{len(candidates[:5])} pages fetched")
        print(f"Discovery run ID: {run.id}")
        print(f"{'='*60}\n")
        
        return results
        
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


if __name__ == "__main__":
    # Initialize database first
    from models.database import init_db
    init_db()
    
    # Test run with a real Michigan district
    results = discover_superintendent_flow(
        district_name="Cass City Public Schools",
        domain="casscityschools.org"
    )
    
    print(f"\nFinal Results:")
    print(f"  Pages successfully fetched: {len(results)}")
    for result in results:
        print(f"    - {result['url']}")