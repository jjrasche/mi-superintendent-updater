from typing import List, Dict
from models.database import District
from models.enums import WorkflowMode


class WorkflowObserver:
    """Base observer for workflow events"""

    def on_district_start(self, district: District):
        pass

    def on_urls_determined(self, urls: List[str], mode: WorkflowMode):
        pass

    def on_url_processing_start(self, total: int):
        pass

    def on_url_processed(self, idx: int, total: int, url: str, result: Dict):
        pass

    def on_complete(self, summary: Dict):
        pass


class ConsoleObserver(WorkflowObserver):
    """Console output observer for superintendent workflow"""

    def on_district_start(self, district: District):
        print(f"\n{'='*60}")
        print(f"Checking {district.name} ({district.domain})")
        print(f"{'='*60}")

    def on_urls_determined(self, urls: List[str], mode: WorkflowMode):
        if mode == WorkflowMode.DISCOVERY:
            print(f"URL pool is empty - running discovery")
            print(f"[DISCOVERY COMPLETE] Selected {len(urls)} URLs")
        else:
            print(f"URL pool has {len(urls)} valid URLs - running monitoring")

        print("\nURLs to check:")
        for i, url in enumerate(urls, 1):
            print(f"  {i}. {url}")

    def on_url_processing_start(self, total: int):
        print(f"\n{'='*60}")
        print("Processing URLs...")
        print(f"{'='*60}")

    def on_url_processed(self, idx: int, total: int, url: str, result: Dict):
        fetch = result['fetch_result']
        extraction = result['extraction_result']

        print(f"\n[{idx}/{total}] Processing: {url}")

        if extraction:
            if extraction['is_empty']:
                print(f"  - No superintendent found")
                if extraction['llm_reasoning']:
                    print(f"     Reason: {extraction['llm_reasoning'][:100]}")
            else:
                print(f"  + Found: {extraction['name']}")
                print(f"     Title: {extraction['title']}")
                print(f"     Email: {extraction['email']}")
        else:
            print(f"  X Fetch failed: {fetch['error_message']}")

    def on_complete(self, summary: Dict):
        print(f"\n{'='*60}")
        print("Check complete")
        print(f"{'='*60}")
        print(f"  Mode: {summary['mode']}")
        print(f"  URLs checked: {summary['urls_checked']}")
        print(f"  Pages fetched: {summary['pages_fetched']}")
        print(f"  Successful extractions: {summary['successful_extractions']}")
        print(f"  Empty extractions: {summary['empty_extractions']}")
        print(f"  Errors: {summary['errors']}")


class SilentObserver(WorkflowObserver):
    """No-op observer for silent execution"""
    pass
