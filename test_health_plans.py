"""
Test script for health plan extraction workflow.

Usage:
    python test_health_plans.py              # Test single district (ID 1)
    python test_health_plans.py 5            # Test specific district
    python test_health_plans.py 1 2 3 4 5   # Test multiple districts
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables BEFORE importing config-dependent modules
from dotenv import load_dotenv
load_dotenv()

from models.database import init_db
from workflows.health_plans import run_health_plan_check, run_bulk_health_plan_check


def main():
    """Test health plan extraction."""
    
    print("=" * 60)
    print("HEALTH PLAN EXTRACTION TEST")
    print("=" * 60)
    
    # Parse district IDs from command line
    if len(sys.argv) > 1:
        try:
            district_ids = [int(arg) for arg in sys.argv[1:]]
        except ValueError:
            print("Error: All arguments must be district IDs (integers)")
            print("Usage: python test_health_plans.py [district_id1] [district_id2] ...")
            sys.exit(1)
    else:
        # Default to district 1
        district_ids = [1]
    
    print(f"\nTesting {len(district_ids)} district(s): {district_ids}")
    print("=" * 60 + "\n")
    
    # Initialize database
    init_db()
    
    # Run checks
    if len(district_ids) == 1:
        result = run_health_plan_check(district_ids[0])
        
        # Print detailed result
        print("\n" + "=" * 60)
        print("DETAILED RESULT")
        print("=" * 60)
        print(f"Status: {result['status']}")
        print(f"Transparency URL: {result.get('transparency_url', 'N/A')}")
        print(f"Plans found: {result['plans_found']}")
        
        if result['plans']:
            print("\nExtracted Plans:")
            for plan in result['plans']:
                print(f"\n  Plan: {plan.get('plan_name', 'N/A')}")
                print(f"  Provider: {plan.get('provider', 'N/A')}")
                print(f"  Type: {plan.get('plan_type', 'N/A')}")
                if plan.get('coverage_details'):
                    print(f"  Details: {plan['coverage_details']}")
                if plan.get('is_empty'):
                    print(f"  Empty: {plan['is_empty']}")
                if plan.get('reasoning'):
                    print(f"  Reasoning: {plan['reasoning']}")
        print("=" * 60)
    else:
        results = run_bulk_health_plan_check(district_ids)
        
        # Print detailed results for districts with plans
        print("\n" + "=" * 60)
        print("DISTRICTS WITH PLANS FOUND")
        print("=" * 60)
        
        districts_with_plans = [r for r in results if r['plans_found'] > 0]
        
        if districts_with_plans:
            for result in districts_with_plans:
                print(f"\n{result['district_name']} (ID: {result['district_id']})")
                print(f"  URL: {result['transparency_url']}")
                print(f"  Plans: {result['plans_found']}")
                for plan in result['plans']:
                    print(f"    • {plan['plan_name']} ({plan['provider']}) - {plan['plan_type']}")
        else:
            print("\nNo districts with plans found")
        
        print("\n" + "=" * 60)


if __name__ == "__main__":
    main()