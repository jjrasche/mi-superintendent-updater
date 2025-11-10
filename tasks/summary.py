from typing import List, Dict
from models.enums import WorkflowMode, FetchStatus


is_contact_empty = lambda contact: not contact or not any([contact.name, contact.email, contact.title])

def build_summary(district_id: int, mode: WorkflowMode, results: List[Dict]) -> Dict:
    """Build workflow summary from results"""
    _count = lambda condition: sum(1 for r in results if condition(r))

    return {
        'district_id': district_id,
        'mode': mode.value,
        'urls_checked': len(results),
        'pages_fetched': len(results),
        'successful_extractions': _count(lambda r: r.get('contact') and not is_contact_empty(r['contact'])),
        'empty_extractions': _count(lambda r: r.get('contact') and is_contact_empty(r['contact'])),
        'errors': _count(lambda r: r['fetch_result']['status'] != FetchStatus.SUCCESS.value)
    }
