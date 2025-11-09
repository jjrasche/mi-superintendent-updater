from typing import Tuple, List
from models.database import District
from models.enums import WorkflowMode
from .discovery import discover_urls, filter_urls


def determine_urls_and_mode(repo, district: District) -> Tuple[List[str], WorkflowMode]:
    """
    Determine URLs to check and workflow mode.

    Returns:
        (urls_to_check, mode)
    """
    url_pool = repo.get_monitoring_urls(district.id)

    if not url_pool:
        all_urls = discover_urls(district.domain)
        filtered_urls, _ = filter_urls(all_urls, district.name, district.domain)
        return filtered_urls, WorkflowMode.DISCOVERY

    return url_pool, WorkflowMode.MONITORING
