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


_error_result = lambda district_id: {
    'district_id': district_id, 'mode': 'error', 'urls_checked': 0,
    'pages_fetched': 0, 'successful_extractions': 0,
    'empty_extractions': 0, 'errors': 1
}

_safe_check = lambda district_id: (
    run_district_check(district_id)
    if not (error := None)
    else (print(f"Failed to check district {district_id}: {str(error)}") or _error_result(district_id))
) if True else None  # Placeholder for try/except

def _try_check(district_id):
    """Safely run district check with error handling"""
    try:
        return run_district_check(district_id)
    except Exception as e:
        print(f"Failed to check district {district_id}: {str(e)}")
        return _error_result(district_id)

run_bulk_check = lambda district_ids: [_try_check(d_id) for d_id in district_ids]
