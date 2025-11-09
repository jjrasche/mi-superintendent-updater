from typing import Dict, List
from repositories import HealthPlanRepository
from tasks.health_plan_processor import process_health_plans
from utils.logging import print_header


def extract_district_health_plans(district_id: int) -> Dict:
    """Extract health plans for a district"""
    with HealthPlanRepository.transaction() as repo:
        district = repo.get_district(district_id)
        if not district:
            raise ValueError(f"District {district_id} not found")

        print_header(f"HEALTH PLAN CHECK: {district.name} ({district.domain})")
        result = process_health_plans(repo, district)

        return {
            'district_id': district_id,
            'district_name': district.name,
            'transparency_url': result['transparency_url'],
            'plans_found': len(result['plans']),
            'plans': result['plans'],
            'status': result['status'],
            'error_message': result.get('error_message')
        }


def run_bulk_health_plan_check(district_ids: List[int]) -> List[Dict]:
    """Run health plan checks for multiple districts"""
    from utils.debug_logger import get_logger
    from models.enums import ExtractionStatus

    logger = get_logger()
    _print_bulk_header(len(district_ids), logger.run_dir)

    results = []
    for idx, district_id in enumerate(district_ids, 1):
        print(f"\n[{idx}/{len(district_ids)}] Processing district {district_id}...")
        try:
            results.append(extract_district_health_plans(district_id))
        except Exception as e:
            print(f"✗ Failed to check district {district_id}: {str(e)}")
            results.append({
                'district_id': district_id,
                'district_name': 'Unknown',
                'transparency_url': None,
                'plans_found': 0,
                'plans': [],
                'status': ExtractionStatus.ERROR.value,
                'error_message': str(e)
            })

    _print_bulk_summary(results, logger.run_dir)
    return results


def _print_bulk_header(count: int, log_dir: str):
    print(f"\n{'='*60}")
    print(f"BULK HEALTH PLAN CHECK - {count} districts")
    print(f"{'='*60}")
    print(f"Debug logs will be saved to: {log_dir}")
    print(f"{'='*60}\n")


def _print_bulk_summary(results: List[Dict], log_dir: str):
    from models.enums import ExtractionStatus

    print(f"\n\n{'='*60}")
    print("BULK CHECK SUMMARY")
    print(f"{'='*60}")

    successful = sum(1 for r in results if r['status'] == ExtractionStatus.SUCCESS.value and r['plans_found'] > 0)
    no_link = sum(1 for r in results if r['status'] == ExtractionStatus.NO_LINK.value)
    no_plans = sum(1 for r in results if r['status'] == ExtractionStatus.SUCCESS.value and r['plans_found'] == 0)
    errors = sum(1 for r in results if r['status'] == ExtractionStatus.ERROR.value)

    print(f"Total districts checked: {len(results)}")
    print(f"  ✓ Found plans: {successful}")
    print(f"  - No transparency link: {no_link}")
    print(f"  - Link found but no plans: {no_plans}")
    print(f"  ✗ Errors: {errors}")
    print(f"\nTotal plans extracted: {sum(r['plans_found'] for r in results)}")
    print(f"{'='*60}")
    print(f"\nDebug logs saved to: {log_dir}")
    print("Check the logs for detailed HTML and extraction information")
    print(f"{'='*60}\n")
