from prefect import flow
from tasks.discovery import get_candidate_urls, fetch_page


@flow(name="discover-superintendent", log_prints=True)
def discover_superintendent_flow(district_name: str, domain: str):
    """Main discovery flow for finding superintendent pages"""
    print(f"\n{'='*60}")
    print(f"Starting discovery for: {district_name}")
    print(f"Domain: {domain}")
    print(f"{'='*60}\n")
    
    # Step 1: Get candidate URLs
    candidates = get_candidate_urls(district_name, domain)
    print(f"\n✓ Found {len(candidates)} candidate URLs\n")
    for i, url in enumerate(candidates, 1):
        print(f"  {i}. {url}")
    
    # Step 2: Fetch each candidate
    print(f"\n{'='*60}")
    print("Fetching candidate pages...")
    print(f"{'='*60}\n")
    
    results = []
    for i, url in enumerate(candidates[:5], 1):
        print(f"\n[{i}/{min(len(candidates), 5)}] ", end="")
        try:
            page_data = fetch_page(url)
            results.append(page_data)
            print(f"✓ Success (HTML: {page_data['html_length']:,} chars)")
            if page_data['screenshot']:
                print(f"  Screenshot: {page_data['screenshot']}")
        except Exception as e:
            print(f"✗ Failed: {e}")
    
    print(f"\n{'='*60}")
    print(f"Discovery complete: {len(results)}/{len(candidates[:5])} pages fetched")
    print(f"{'='*60}\n")
    
    return results


if __name__ == "__main__":
    # Test run with a real Michigan district
    results = discover_superintendent_flow(
        district_name="Cass City Public Schools",
        domain="casscityschools.org"
    )
    
    print(f"\nFinal Results:")
    print(f"  Pages successfully fetched: {len(results)}")
    for result in results:
        print(f"    - {result['url']}")
