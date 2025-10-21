
from database import init_db
from queries.superintendents import get_districts_needing_check
from workflows.run import run_bulk_check


def main(days: int = 7):
    """
    Main entry point: Check all districts that need checking.
    
    Args:
        days: Number of days threshold (default 7)
              Districts with no successful extraction in this timeframe will be checked
    """
    print("=" * 60)
    print("Superintendent Scraper - District Check")
    print("=" * 60)
    
    # Get districts that need checking
    print(f"\nFinding districts with no successful extractions in last {days} days...")
    district_ids = get_districts_needing_check(days=days)
    
    if not district_ids:
        print("✓ No districts need checking - all are up to date!")
        return
    
    print(f"Found {len(district_ids)} district(s) needing check")
    print(f"District IDs: {district_ids}")
    
    # Run bulk check
    print(f"\nStarting bulk check...\n")
    results = run_bulk_check(district_ids)
    
    # Summary
    print("\n" + "=" * 60)
    print("Bulk Check Complete - Summary")
    print("=" * 60)
    
    total_successful = sum(r['successful_extractions'] for r in results)
    total_empty = sum(r['empty_extractions'] for r in results)
    total_errors = sum(r['errors'] for r in results)
    
    discovery_count = sum(1 for r in results if r['mode'] == 'discovery')
    monitoring_count = sum(1 for r in results if r['mode'] == 'monitoring')
    
    print(f"Districts checked: {len(results)}")
    print(f"  - Discovery mode: {discovery_count}")
    print(f"  - Monitoring mode: {monitoring_count}")
    print(f"\nTotal successful extractions: {total_successful}")
    print(f"Total empty extractions: {total_empty}")
    print(f"Total errors: {total_errors}")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    init_db()
    # # Allow passing days as command line argument
    # days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    # main(days=days)