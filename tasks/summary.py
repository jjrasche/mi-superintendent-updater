from typing import List, Dict
from models.enums import WorkflowMode, FetchStatus


def build_summary(district_id: int, mode: WorkflowMode, results: List[Dict]) -> Dict:
    """
    Build workflow summary from results.

    Returns:
        Summary dict with counts
    """
    def is_contact_empty(contact) -> bool:
        """Check if contact has no meaningful data"""
        if not contact:
            return True
        return not any([contact.name, contact.email, contact.title])

    successful_extractions = sum(
        1 for r in results
        if r.get('contact') and not is_contact_empty(r['contact'])
    )

    empty_extractions = sum(
        1 for r in results
        if r.get('contact') and is_contact_empty(r['contact'])
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
