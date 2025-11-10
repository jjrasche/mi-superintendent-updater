import argparse
from models.database import init_db
from workflows.superintendent import run_bulk_check
from utils.debug_logger import get_logger


def main():
    """Main entry point: Check districts for superintendent info."""

    # Parse CLI arguments
    parser = argparse.ArgumentParser(description='Extract superintendent contact info from school district websites')
    parser.add_argument('districts', nargs='*', type=int, help='District IDs to check (e.g., 202 203 204)')
    parser.add_argument('--range', nargs=2, type=int, metavar=('START', 'END'), help='Check range of districts (e.g., --range 100 200)')
    parser.add_argument('--all', action='store_true', help='Check all districts in database')
    args = parser.parse_args()

    # Determine which districts to check
    if args.all:
        # TODO: Query all district IDs from database
        district_ids = []
        print("--all flag not yet implemented")
        return
    elif args.range:
        district_ids = list(range(args.range[0], args.range[1]))
    elif args.districts:
        district_ids = args.districts
    else:
        # Default to district 202 for backward compatibility
        district_ids = [202]

    # Initialize debug logger
    logger = get_logger()

    print("=" * 60)
    print("Superintendent Scraper - District Check")
    print("=" * 60)
    print(f"Districts to check: {district_ids}")
    print(f"Debug logs will be saved to: {logger.run_dir}")
    print("=" * 60)

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
    print(f"\nDebug logs saved to: {logger.run_dir}")
    print("Check the logs for detailed HTML and extraction information")
    print("=" * 60)


if __name__ == "__main__":
    init_db()
    main()