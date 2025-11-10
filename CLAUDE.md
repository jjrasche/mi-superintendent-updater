# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MI Superintendent Updater is a web scraper that automatically extracts superintendent contact information from Michigan school district websites. It uses LLMs (via Groq API) to intelligently discover relevant pages, filter URLs, and extract structured data from HTML/PDF content.

## Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### Running the Scraper
```bash
# Check single district (default: 202)
python main.py

# Check specific districts
python main.py 202 203 204

# Check range of districts
python main.py --range 100 200

# Check all districts (TODO: not yet implemented)
python main.py --all
```

### Database
```bash
# Database is SQLite by default (district_fetch.db)
# Initialized automatically on first run via init_db() in main.py

# To use PostgreSQL, set DATABASE_URL in .env:
DATABASE_URL=postgresql://user:password@localhost/dbname
```

### Testing
```bash
# Run tests from root directory
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_health_plans.py
```

## Architecture

The codebase follows a **layered, functional architecture** with aggressive DRY principles and single-expression functions where possible. See ARCHITECTURE.md and STYLE.md for detailed guidelines.

### Layer Structure

```
Workflows (orchestration)
    ↓
Tasks (domain operations + validation)
    ↓
Services (business logic) + Repositories (data access)
    ↓
Utils (infrastructure: LLM client, HTML parser, etc.)
    ↓
Models (ORM + Pydantic validation models)
```

### Key Architectural Patterns

1. **Template-Based LLM System**: All LLM prompts are externalized to `prompts/*.txt` Jinja2 templates. The generic `utils/llm_client.py` handles template rendering, API calls, and Pydantic validation of responses.

2. **Repository Pattern**: Database access uses context managers for automatic session management:
   ```python
   with SuperintendentRepository.transaction() as repo:
       district = repo.get_district(district_id)
       page = repo.save_fetch_result(district_id, url, mode, fetch_result)
       # Auto commit/rollback/close
   ```

3. **Type Safety**: Pydantic models validate all LLM responses, enums prevent magic strings:
   ```python
   # models/extraction_results.py - Pydantic validation
   class SuperintendentExtraction(BaseModel):
       name: Optional[str] = None
       email: Optional[str] = None
       phone: Optional[str] = None

   # models/enums.py - Type-safe status/mode values
   class WorkflowMode(str, Enum):
       DISCOVERY = "discovery"
       MONITORING = "monitoring"
   ```

4. **Single-Expression Service Functions**: Business logic uses lambda-driven functional style:
   ```python
   # services/extraction.py
   extract_superintendent = lambda text, district_name: get_client().call(
       'superintendent_extraction',
       SuperintendentExtraction,
       text=text,
       district_name=district_name
   )
   ```

### Workflow Execution Flow

1. **URL Planning** (`tasks/url_planning.py`): Determines whether to use discovery mode (find new pages) or monitoring mode (check known URLs)

2. **Discovery Mode** (`tasks/discovery.py`):
   - Fetch district homepage
   - Extract all links with LLM (`link_identification.txt` prompt)
   - Filter to top N relevant URLs with LLM (`url_filtering.txt` prompt)

3. **URL Processing** (`tasks/url_processor.py`):
   - For each URL, fetch content via `tasks/fetcher.py` (tries requests, falls back to Playwright for JS-rendered pages)
   - Extract superintendent info via `tasks/extraction.py` (uses `superintendent_extraction.txt` prompt)
   - Save results to database via repositories

4. **Monitoring Mode**: Reuses existing URLs from previous successful extractions instead of running discovery

### Key Files

- `main.py` - CLI entry point with argparse
- `config.py` - Configuration (API keys, timeouts, DB URL)
- `workflows/superintendent.py` - Main orchestration logic
- `tasks/discovery.py` - URL discovery with LLM
- `tasks/extraction.py` - Data extraction with LLM
- `tasks/fetcher.py` - HTTP/Playwright page fetching (handles both HTML and PDF)
- `services/extraction.py` - Thin service layer for LLM calls
- `repositories/*.py` - Database access layer
- `utils/llm_client.py` - Generic LLM client with Jinja2 templates
- `utils/html_parser.py` - HTML parsing and text extraction
- `utils/pdf_parser.py` - PDF text extraction
- `utils/debug_logger.py` - Saves HTML/extractions to `debug_logs/{timestamp}/` for debugging
- `models/database.py` - SQLAlchemy ORM models (District, FetchedPage, SuperintendentExtraction, etc.)
- `models/extraction_results.py` - Pydantic models for LLM response validation
- `models/enums.py` - Type-safe enums (WorkflowMode, FetchStatus, etc.)
- `prompts/*.txt` - Jinja2 templates for LLM prompts

### Database Schema

**District** - School district info (id, name, URL, county)
**FetchedPage** - Tracks each URL fetch attempt (URL, status, error_message, mode, timestamp)
**SuperintendentExtraction** - Extracted contact info (name, email, phone, title, reasoning, timestamp)
**HealthPlan** - Health insurance plan data (separate workflow)

## Code Style Guidelines

This codebase follows strict **DRY, functional, lambda-driven** principles. Key rules:

1. **Single-expression functions** preferred over multi-line imperative blocks
2. **No intermediate variables** unless necessary - chain operations directly
3. **Comprehensions over loops** - use list/dict comprehensions and map/filter
4. **Ternary and logical operators** for control flow instead of if/else blocks
5. **Method chaining** for fluent APIs (SQLAlchemy queries, etc.)
6. **Self-documenting function names** - avoid comments, use descriptive names
7. **Lambda functions** for simple transformations and filters
8. **Context managers** for all resource management (DB sessions, file handles)

See STYLE.md for detailed examples and anti-patterns.

## Adding New LLM Extractions

To add a new LLM-powered extraction:

1. Create Pydantic model in `models/extraction_results.py`:
   ```python
   class NewExtraction(BaseModel):
       field1: str
       field2: Optional[int]
       reasoning: str
   ```

2. Create prompt template in `prompts/new_extraction.txt`:
   ```
   System instructions here...

   ---USER_PROMPT---

   Input: {{ input_var }}
   ```

3. Add service function in `services/extraction.py`:
   ```python
   extract_new = lambda input_var: get_client().call(
       'new_extraction',
       NewExtraction,
       input_var=input_var
   )
   ```

4. Create task in `tasks/new_extraction.py` that adds validation/post-processing

5. Integrate into workflow

## Environment Variables

- `GROQ_API_KEY` (required) - API key for Groq LLM service
- `DATABASE_URL` (optional) - Defaults to `sqlite:///district_fetch.db`

## Important Implementation Notes

- **HTML Parsing**: `utils/html_parser.py` extracts clean text from HTML, limits to MAX_TEXT_LENGTH (15000 chars) to fit in LLM context
- **PDF Handling**: `tasks/fetcher.py` detects PDF URLs, fetches as bytes, `utils/pdf_parser.py` extracts text
- **SSL Handling**: Fetcher tries HTTPS with verification first, falls back to unverified for self-signed certs
- **JavaScript Rendering**: Fetcher uses Playwright as fallback when requests fails (for JS-heavy sites)
- **Retry Logic**: LLM client uses tenacity for automatic retries on API failures
- **Debug Logging**: All HTML and extraction results saved to timestamped directories in `debug_logs/` for troubleshooting
- **Session Management**: Repositories handle commit/rollback/close automatically via context managers - never manually manage sessions in workflows
- **Mode Selection**: Workflows use enums from `models/enums.py` (WorkflowMode.DISCOVERY, FetchStatus.SUCCESS, etc.) - never use magic strings

## TODO / Future Work

See ARCHITECTURE.md "Next Steps" section:
- Implement `--all` flag in main.py to check all districts
- Add async/parallel fetching for better throughput
- Remove deprecated `utils/llm.py` if not used
- Comprehensive test coverage for repositories and workflows
