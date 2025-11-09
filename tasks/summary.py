from typing import List, Dict
from models.enums import WorkflowMode, FetchStatus


def build_summary(district_id: int, mode: WorkflowMode, results: List[Dict]) -> Dict:
    """
    Build workflow summary from results.

    Returns:
        Summary dict with counts
    """
    successful_extractions = sum(
        1 for r in results
        if r['extraction_result'] and not r['extraction_result']['is_empty']
    )

    empty_extractions = sum(
        1 for r in results
        if r['extraction_result'] and r['extraction_result']['is_empty']
    )

    errors = sum(
        1 for r in results
        if r['fetch_result']['status'] != FetchStatus.SUCCESS.value
    )

    return {
        'district_id': district_id,
        'mode': mode.value,
        'urls_checked': len(results),
        'pages_fetched': len(results),
        'successful_extractions': successful_extractions,
        'empty_extractions': empty_extractions,
        'errors': errors
    }
