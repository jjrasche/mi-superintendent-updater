from typing import List, Dict, Optional
from models.database import District
from models.enums import FetchStatus
from .fetcher import fetch_page
from .extraction import extract_superintendent


def process_urls(repo, district: District, urls: List[str], mode: str, observer=None) -> List[Dict]:
    """
    Process URLs: fetch and extract superintendent info.

    Returns:
        List of {fetch_result, extraction_result} dicts
    """
    results = []

    if observer:
        observer.on_url_processing_start(len(urls))

    for idx, url in enumerate(urls, 1):
        fetch_result = fetch_page(url)
        fetched_page = repo.save_fetch_result(district.id, url, mode, fetch_result)

        extraction_result = None
        if fetch_result['status'] == FetchStatus.SUCCESS.value:
            extraction_result = extract_superintendent(fetch_result['html'], district.name, url)
            repo.save_extraction_result(fetched_page.id, extraction_result)

        result = {
            'fetch_result': fetch_result,
            'extraction_result': extraction_result
        }
        results.append(result)

        if observer:
            observer.on_url_processed(idx, len(urls), url, result)

    return results
