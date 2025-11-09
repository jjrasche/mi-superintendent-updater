from typing import Dict, List
from datetime import datetime
from models.database import District
from models.enums import WorkflowMode, FetchStatus
from repositories import SuperintendentRepository
from tasks.discovery import discover_urls, filter_urls
from tasks.fetcher import fetch_page
from tasks.extraction import extract_superintendent


def run_district_check(district_id: int) -> Dict:
    """
    Unified workflow: check district for superintendent info.

    Returns:
        {
            'district_id': int,
            'mode': str,
            'urls_checked': int,
            'pages_fetched': int,
            'successful_extractions': int,
            'empty_extractions': int,
            'errors': int
        }
    """
    with SuperintendentRepository.transaction() as repo:
        # 1. Get district
        district = repo.session.query(District).filter_by(id=district_id).first()
        if not district:
            raise ValueError(f"District {district_id} not found")

        print(f"\n{'='*60}")
        print(f"Checking {district.name} ({district.domain})")
        print(f"{'='*60}")

        # 2. Get URL pool
        print("Getting URL pool...")
        url_pool = repo.get_monitoring_urls(district_id)

        # 3. Determine mode and get URLs to check
        if not url_pool:
            # Discovery mode
            print("URL pool is empty - running discovery")
            mode = WorkflowMode.DISCOVERY

            try:
                all_urls = discover_urls(district.domain)
                print(f"\n[DISCOVERY COMPLETE] Found {len(all_urls)} total URLs")

                print("\nSample of discovered URLs:")
                for i, url in enumerate(all_urls[:15], 1):
                    print(f"  {i}. {url}")
                if len(all_urls) > 15:
                    print(f"  ... and {len(all_urls) - 15} more")

                urls_to_check, llm_reasoning = filter_urls(all_urls, district.name, district.domain)
                print(f"\n[FILTERING COMPLETE] Selected {len(urls_to_check)} URLs")

                if llm_reasoning:
                    print(f"\nLLM Reasoning:")
                    print(f"  {llm_reasoning}")

                print("\nFinal selected URLs:")
                for i, url in enumerate(urls_to_check, 1):
                    print(f"  {i}. {url}")

            except Exception as e:
                print(f"Discovery failed: {str(e)}")
                return {
                    'district_id': district_id,
                    'mode': WorkflowMode.DISCOVERY.value,
                    'urls_checked': 0,
                    'pages_fetched': 0,
                    'successful_extractions': 0,
                    'empty_extractions': 0,
                    'errors': 1
                }
        else:
            # Monitoring mode
            print(f"URL pool has {len(url_pool)} valid URLs - running monitoring")
            mode = WorkflowMode.MONITORING
            urls_to_check = url_pool

            print("\nURLs to monitor:")
            for i, url in enumerate(urls_to_check, 1):
                print(f"  {i}. {url}")

        # Counters
        pages_fetched = successful_extractions = empty_extractions = errors = 0

        # 4. Process each URL
        print(f"\n{'='*60}")
        print("Processing URLs...")
        print(f"{'='*60}")

        for idx, url in enumerate(urls_to_check, 1):
            print(f"\n[{idx}/{len(urls_to_check)}] Processing: {url}")

            # Fetch page
            fetch_result = fetch_page(url)
            pages_fetched += 1

            # Save fetch result using repository
            fetched_page = repo.save_fetch_result(district_id, url, mode.value, fetch_result)

            # Extract if successful
            if fetch_result['status'] == FetchStatus.SUCCESS.value:
                extraction_result = extract_superintendent(fetch_result['html'], district.name, url)

                # Save extraction using repository
                repo.save_extraction_result(fetched_page.id, extraction_result)

                if extraction_result['is_empty']:
                    empty_extractions += 1
                    print(f"  → No superintendent found")
                    if extraction_result['llm_reasoning']:
                        print(f"     Reason: {extraction_result['llm_reasoning'][:100]}")
                else:
                    successful_extractions += 1
                    print(f"  → ✓ Found: {extraction_result['name']}")
                    print(f"     Title: {extraction_result['title']}")
                    print(f"     Email: {extraction_result['email']}")
            else:
                errors += 1
                print(f"  → ✗ Fetch failed: {fetch_result['error_message']}")

        # 5. Update district last checked
        district.last_checked_at = datetime.utcnow()

        print(f"\n{'='*60}")
        print(f"Check complete for {district.name}")
        print(f"{'='*60}")
        print(f"  Mode: {mode.value}")
        print(f"  URLs checked: {len(urls_to_check)}")
        print(f"  Pages fetched: {pages_fetched}")
        print(f"  Successful extractions: {successful_extractions}")
        print(f"  Empty extractions: {empty_extractions}")
        print(f"  Errors: {errors}")

        return {
            'district_id': district_id,
            'mode': mode.value,
            'urls_checked': len(urls_to_check),
            'pages_fetched': pages_fetched,
            'successful_extractions': successful_extractions,
            'empty_extractions': empty_extractions,
            'errors': errors
        }


def run_bulk_check(district_ids: List[int]) -> List[Dict]:
    """Run district checks for multiple districts."""
    results = []

    for district_id in district_ids:
        try:
            result = run_district_check(district_id)
            results.append(result)
        except Exception as e:
            print(f"Failed to check district {district_id}: {str(e)}")
            results.append({
                'district_id': district_id,
                'mode': 'error',
                'urls_checked': 0,
                'pages_fetched': 0,
                'successful_extractions': 0,
                'empty_extractions': 0,
                'errors': 1
            })

    return results
