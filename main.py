
from models.database import init_db
from queries.superintendents import get_districts_needing_check
from workflows.run import run_bulk_check


def main():
    """ Main entry point: Check all districts that need checking. """
    print("=" * 60)
    print("Superintendent Scraper - District Check")
    print("=" * 60)
    
    # Run bulk check
    print(f"\nStarting bulk check...\n")
    results = run_bulk_check([2,3,4,5,6,7,8,9,10])
    
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
    # Allow passing days as command line argument
    main()