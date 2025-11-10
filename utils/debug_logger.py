import os
from pathlib import Path
from datetime import datetime
import json
from functools import lru_cache

# Helper functions
_slugify = lambda name: name.replace(' ', '_').replace('/', '_')
_log_file_path = lambda run_dir, slug, suffix: run_dir / f"{slug}_{suffix}.json"

def _write_json(file_path, data):
    """Write JSON data to file"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    return file_path

@lru_cache(maxsize=1)
def get_logger():
    """Get or create debug logger (cached singleton)"""
    return DebugLogger()

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
        log_file = _write_json(
            _log_file_path(self.run_dir, _slugify(district_name), 'discovery'),
            {
                'district': district_name, 'domain': domain,
                'timestamp': datetime.now().isoformat(),
                'total_urls_found': len(all_urls),
                'filtered_urls_count': len(filtered_urls),
                'all_urls': all_urls, 'filtered_urls': filtered_urls,
                'llm_reasoning': llm_reasoning
            }
        )

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

    def log_transparency_discovery(self, district_name: str, domain: str, 
                                   found_url: str, all_links: list, 
                                   llm_reasoning: str = None):
        """Log transparency link discovery."""
        district_slug = district_name.replace(' ', '_').replace('/', '_')
        log_file = self.run_dir / f"{district_slug}_transparency_discovery.json"
        
        data = {
            'district': district_name,
            'domain': domain,
            'timestamp': datetime.now().isoformat(),
            'transparency_url': found_url,
            'total_links_found': len(all_links),
            'all_links': all_links,
            'llm_reasoning': llm_reasoning
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n[DEBUG] Transparency discovery logged to: {log_file}")
        print(f"[DEBUG] Total links found: {len(all_links)}")
        print(f"[DEBUG] Selected URL: {found_url}")
        if llm_reasoning:
            print(f"[DEBUG] LLM reasoning: {llm_reasoning[:200]}...")

    def log_health_plan_fetch(self, district_name: str, url: str, 
                             raw_content: str, parsed_text: str, 
                             extraction_result: dict, content_type: str = 'html'):
        """Log health plan page fetch and extraction."""
        district_slug = district_name.replace(' ', '_').replace('/', '_')
        
        # Create district folder
        district_dir = self.run_dir / district_slug
        district_dir.mkdir(exist_ok=True)
        
        # Generate filename
        base_name = f"transparency_{datetime.now().strftime('%H%M%S')}"
        
        # Save raw content (HTML or PDF)
        if content_type == 'pdf':
            raw_file = district_dir / f"{base_name}_raw.pdf"
            with open(raw_file, 'wb') as f:
                f.write(raw_content if isinstance(raw_content, bytes) else raw_content.encode('latin-1'))
        else:
            raw_file = district_dir / f"{base_name}_raw.html"
            with open(raw_file, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(raw_content if isinstance(raw_content, str) else raw_content.decode('utf-8', errors='ignore'))
        
        # Save parsed text
        parsed_file = district_dir / f"{base_name}_parsed.txt"
        with open(parsed_file, 'w', encoding='utf-8') as f:
            f.write(parsed_text)
        
        # Save extraction result
        extraction_file = district_dir / f"{base_name}_health_plans.json"
        data = {
            'url': url,
            'content_type': content_type,
            'timestamp': datetime.now().isoformat(),
            'raw_content_length': len(raw_content),
            'parsed_text_length': len(parsed_text),
            'extraction': extraction_result
        }
        with open(extraction_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        print(f"[DEBUG] Saved to: {district_dir}/{base_name}_*")
        print(f"[DEBUG]   → {raw_file.name} ({len(raw_content)} chars/bytes)")
        print(f"[DEBUG]   → {parsed_file.name} ({len(parsed_text)} chars)")
        print(f"[DEBUG]   → {extraction_file.name}")
        
        plans = extraction_result.get('plans', [])
        valid_plans = [p for p in plans if not p.get('is_empty', True)]
        print(f"[DEBUG]   Found: {len(valid_plans)} health plan(s)")
        
        if extraction_result.get('reasoning'):
            print(f"[DEBUG]   Reasoning: {extraction_result['reasoning'][:100]}...")

    def log_llm_call(self, district_name: str, prompt_type: str, 
                    system_prompt: str, user_prompt: str, 
                    llm_response: dict):
        """Log LLM prompt and response."""
        district_slug = district_name.replace(' ', '_').replace('/', '_')
        
        district_dir = self.run_dir / district_slug
        district_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%H%M%S')
        log_file = district_dir / f"{prompt_type}_{timestamp}_llm.json"
        
        data = {
            'prompt_type': prompt_type,
            'timestamp': datetime.now().isoformat(),
            'system_prompt': system_prompt,
            'user_prompt': user_prompt,
            'llm_response': llm_response
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        print(f"[DEBUG] LLM call logged to: {log_file}")