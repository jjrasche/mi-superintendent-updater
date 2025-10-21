import os
from pathlib import Path
from datetime import datetime
import json


class DebugLogger:
    """Logger for debugging scraping process."""
    
    def __init__(self, base_dir: str = "debug_logs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # Create timestamped run directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.base_dir / timestamp
        self.run_dir.mkdir(exist_ok=True)
    
    def log_discovery(self, district_name: str, domain: str, all_urls: list, 
                     filtered_urls: list, llm_reasoning: str = None):
        """Log URL discovery and filtering."""
        district_slug = district_name.replace(' ', '_').replace('/', '_')
        log_file = self.run_dir / f"{district_slug}_discovery.json"
        
        data = {
            'district': district_name,
            'domain': domain,
            'timestamp': datetime.now().isoformat(),
            'total_urls_found': len(all_urls),
            'filtered_urls_count': len(filtered_urls),
            'all_urls': all_urls,
            'filtered_urls': filtered_urls,
            'llm_reasoning': llm_reasoning
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n[DEBUG] Discovery logged to: {log_file}")
        print(f"[DEBUG] Total URLs discovered: {len(all_urls)}")
        print(f"[DEBUG] URLs after LLM filter: {len(filtered_urls)}")
        if llm_reasoning:
            print(f"[DEBUG] LLM reasoning: {llm_reasoning[:200]}...")
    
    def log_page_fetch(self, district_name: str, url: str, raw_html: str, 
                       parsed_text: str, extraction_result: dict):
        """Log fetched page, parsing, and extraction."""
        district_slug = district_name.replace(' ', '_').replace('/', '_')
        
        # Create district folder
        district_dir = self.run_dir / district_slug
        district_dir.mkdir(exist_ok=True)
        
        # Generate filename from URL
        url_slug = url.split('/')[-1][:50] or 'homepage'
        url_slug = ''.join(c if c.isalnum() or c in '-_' else '_' for c in url_slug)
        
        base_name = f"{url_slug}_{datetime.now().strftime('%H%M%S')}"
        
        # Save raw HTML
        html_file = district_dir / f"{base_name}_raw.html"
        with open(html_file, 'w', encoding='utf-8', errors='ignore') as f:
            f.write(raw_html)
        
        # Save parsed text
        parsed_file = district_dir / f"{base_name}_parsed.txt"
        with open(parsed_file, 'w', encoding='utf-8') as f:
            f.write(parsed_text)
        
        # Save extraction result
        extraction_file = district_dir / f"{base_name}_extraction.json"
        data = {
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'raw_html_length': len(raw_html),
            'parsed_text_length': len(parsed_text),
            'extraction': extraction_result
        }
        with open(extraction_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        print(f"[DEBUG] Saved to: {district_dir}/{base_name}_*")
        print(f"[DEBUG]   → {html_file.name} ({len(raw_html)} chars)")
        print(f"[DEBUG]   → {parsed_file.name} ({len(parsed_text)} chars)")
        print(f"[DEBUG]   → {extraction_file.name}")
        print(f"[DEBUG]   Found: {extraction_result.get('name', 'None')}")
        if extraction_result.get('llm_reasoning'):
            print(f"[DEBUG]   Reasoning: {extraction_result['llm_reasoning'][:100]}...")


# Global instance
_logger = None

def get_logger():
    """Get or create debug logger."""
    global _logger
    if _logger is None:
        _logger = DebugLogger()
    return _logger