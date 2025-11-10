from typing import List, Dict, Optional
from models.database import District
from models.enums import FetchStatus
from .fetcher import fetch_page
from .extraction import extract_superintendent


def _process_single_url(repo, district: District, url: str, mode: str, idx: int, total: int, observer):
    """Process single URL: fetch, save, and extract"""
    fetch_result = fetch_page(url)
    fetched_page = repo.save_fetch_result(district.id, url, mode, fetch_result)

    contact = (extract_superintendent(fetch_result['html'], district.name, url, district.id, repo, fetched_page)
               if fetch_result['status'] == FetchStatus.SUCCESS.value else None)

    result = {'fetch_result': fetch_result, 'contact': contact}
    if observer:
        observer.on_url_processed(idx, total, url, result)
    return result

def process_urls(repo, district: District, urls: List[str], mode: str, observer=None) -> List[Dict]:
    """Process URLs: fetch and extract superintendent info"""
    if observer:
        observer.on_url_processing_start(len(urls))

    return [_process_single_url(repo, district, url, mode, idx, len(urls), observer)
            for idx, url in enumerate(urls, 1)]
