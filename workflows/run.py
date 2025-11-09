from typing import Dict, List
from repositories import SuperintendentRepository
from tasks.url_planning import determine_urls_and_mode
from tasks.url_processor import process_urls
from tasks.summary import build_summary
from utils.workflow_observer import ConsoleObserver


def run_district_check(district_id: int, observer=None) -> Dict:
    """Unified workflow: check district for superintendent info"""
    observer = observer or ConsoleObserver()

    with SuperintendentRepository.transaction() as repo:
        district = repo.get_district(district_id)
        if not district:
            raise ValueError(f"District {district_id} not found")

        observer.on_district_start(district)
        urls, mode = determine_urls_and_mode(repo, district)
        observer.on_urls_determined(urls, mode)
        results = process_urls(repo, district, urls, mode.value, observer)
        repo.update_last_checked(district)
        summary = build_summary(district_id, mode, results)
        observer.on_complete(summary)
        return summary


def run_bulk_check(district_ids: List[int]) -> List[Dict]:
    """Run district checks for multiple districts"""
    results = []
    for district_id in district_ids:
        try:
            results.append(run_district_check(district_id))
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
