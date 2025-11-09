# Architecture Overview

## New LLM Architecture (Template-Based + Pydantic)

### 🎯 Goals Achieved

1. **DRY** - Single LLM client, no duplication
2. **Type Safety** - Pydantic validates all LLM responses
3. **Maintainability** - Prompts externalized to template files
4. **Concise** - Service layer is single-expression lambdas
5. **Self-Documenting** - Clear function names, type hints, Pydantic models

---

## Layer Breakdown

### 1. **Models Layer** - Data Structures

```python
# models/extraction_results.py
class SuperintendentExtraction(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    reasoning: str
    is_empty: bool

class URLFilterResult(BaseModel):
    urls: list[str]
    reasoning: str

class HealthPlanExtraction(BaseModel):
    plans: list[HealthPlanData]
    reasoning: str
```

**Benefits:**
- Type safety - IDE autocomplete on `result.name`
- Validation - LLM responses validated automatically
- Documentation - Schema IS the contract

---

### 2. **Prompts** - External Templates

```
prompts/
├── superintendent_extraction.txt
├── url_filtering.txt
├── link_identification.txt
└── health_plan_extraction.txt
```

**Format:**
```jinja2
System instructions here...

---USER_PROMPT---

District Name: {{ district_name }}
Content: {{ text }}
```

**Benefits:**
- Version control prompts separately
- A/B test prompts easily
- Non-engineers can edit
- 400+ lines removed from Python code

---

### 3. **Utils Layer** - Generic LLM Client

```python
# utils/llm_client.py
class LLMClient:
    def call(self, template_name: str, response_model: Type[T], **variables) -> T:
        # 1. Load template from prompts/
        # 2. Render with Jinja2
        # 3. Call Groq API
        # 4. Parse JSON
        # 5. Validate with Pydantic
        # 6. Return typed object
```

**Usage:**
```python
client = get_client()
result = client.call('superintendent_extraction',
                     SuperintendentExtraction,
                     text=html,
                     district_name=name)
```

**Benefits:**
- Single place for LLM logic
- Automatic retry with tenacity
- Validation errors caught early
- Reusable across all extractions

---

### 4. **Services Layer** - Thin Business Functions

```python
# services/extraction.py

# Single-expression lambdas
extract_superintendent = lambda text, district_name: get_client().call(
    'superintendent_extraction',
    SuperintendentExtraction,
    text=text,
    district_name=district_name
)

filter_urls = lambda urls, district_name: get_client().call(
    'url_filtering',
    URLFilterResult,
    urls=urls,
    district_name=district_name
)
```

**Benefits:**
- Self-documenting function names
- No boilerplate - just delegate to client
- Easy to test (mock get_client)
- Clear API for tasks layer

---

### 5. **Tasks Layer** - Domain Operations

```python
# tasks/extraction.py
from services.extraction import extract_superintendent as llm_extract

def extract_superintendent(html: str, district_name: str, url: str) -> Dict:
    cleaned_text = parse_html_to_text(html)

    # Validation
    if len(cleaned_text) < 50:
        return empty_result(...)

    # Call service
    result = llm_extract(cleaned_text, district_name)

    # Post-processing
    if result.title and 'superintendent' not in result.title.lower():
        return empty_result(...)

    # Convert Pydantic to dict (for now, workflows still expect dicts)
    return {
        'name': result.name,
        'email': result.email,
        'phone': result.phone,
        'extracted_text': cleaned_text,
        'llm_reasoning': result.reasoning,
        'is_empty': result.is_empty
    }
```

**Benefits:**
- Uses typed Pydantic objects internally
- Validation logic stays here
- Logging stays here
- Returns dict for backward compatibility

---

### 6. **Repositories Layer** - Data Access

```python
# repositories/superintendent.py
class SuperintendentRepository(BaseRepository):
    # Single-expression queries
    get_monitoring_urls = lambda self, district_id: [
        row[0] for row in self.session.query(FetchedPage.url)
        .filter_by(district_id=district_id, mode='monitoring')
        .all()
    ]

    # Composite operations
    def save_fetch_result(self, district_id, url, mode, fetch_result):
        return self.save_page(self.create_page(
            district_id, url, mode,
            fetch_result['status'],
            fetch_result.get('error_message')
        ))
```

**Usage:**
```python
with SuperintendentRepository.transaction() as repo:
    urls = repo.get_monitoring_urls(district_id)
    page = repo.save_fetch_result(district_id, url, mode, result)
```

**Benefits:**
- Auto session management (commit/rollback/close)
- No DB boilerplate in workflows
- Chainable operations
- Type-safe queries

---

### 7. **Workflows Layer** - Orchestration

```python
# workflows/run.py (future state)
def run_district_check(district_id: int):
    with SuperintendentRepository.transaction() as repo:
        district = repo.get(district_id)
        urls = repo.get_monitoring_urls(district_id) or discover_and_filter(district)

        for url in urls:
            fetch_result = fetch_page(url)
            page = repo.save_fetch_result(district_id, url, mode, fetch_result)

            if fetch_result['status'] == 'success':
                extraction = extract_superintendent(fetch_result['html'], district.name, url)
                repo.save_extraction_result(page.id, extraction)

        repo.mark_checked(district)
```

**Benefits:**
- Clear business flow
- No DB session management
- No LLM prompt building
- Just orchestration

---

## Data Flow

```
┌─────────────┐
│  Workflow   │  Orchestrates everything
└──────┬──────┘
       │
       ├──→ Repository ─→ Database (save/load)
       │
       └──→ Task ────────→ Service ─→ LLM Client ─→ Template + API ─→ Pydantic
                                                         │
                                                    ┌────┴────┐
                                                    │ prompts/│
                                                    │  *.txt  │
                                                    └─────────┘
```

---

## Before/After Comparison

### Before (Monolithic)

```python
# workflows/run.py - 200+ lines in one function
def run_district_check(district_id):
    session = get_session()
    try:
        district = session.query(District).filter_by(id=district_id).first()

        # Build prompts inline
        system_prompt = """You are a data extraction specialist..."""
        user_prompt = f"""District: {district.name}..."""

        # Call LLM
        result = call_llm(system_prompt, user_prompt)

        # Manual dict access
        name = result.get('name')
        email = result.get('email')

        # Create DB objects manually
        page = FetchedPage(
            district_id=district_id,
            url=url,
            status=fetch_result['status'],
            # ... 10 more fields
        )
        session.add(page)
        session.flush()

        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
```

**Issues:**
- 50+ lines of boilerplate
- Prompts mixed with code
- No type safety
- Manual session management
- Repeated everywhere

### After (Layered)

```python
# workflows/run.py - Clean orchestration
def run_district_check(district_id):
    with SuperintendentRepository.transaction() as repo:
        district = repo.get(district_id)
        urls = repo.get_monitoring_urls(district_id)

        for url in urls:
            result = extract_superintendent(fetch_page(url)['html'], district.name, url)
            repo.save_extraction_result(url, result)

        repo.mark_checked(district)
```

**Benefits:**
- 15 lines (70% reduction)
- Clear intent
- Type safety
- Auto session management
- Reusable everywhere

---

## File Structure

```
mi-superintendent-updater/
├── models/
│   ├── database.py              # ORM models (District, FetchedPage, etc.)
│   └── extraction_results.py    # Pydantic models (NEW)
│
├── prompts/                     # External templates (NEW)
│   ├── superintendent_extraction.txt
│   ├── url_filtering.txt
│   ├── link_identification.txt
│   └── health_plan_extraction.txt
│
├── utils/
│   ├── llm_client.py            # Generic LLM client (NEW)
│   ├── llm.py                   # OLD - can be removed
│   ├── html_parser.py
│   └── debug_logger.py
│
├── services/                    # Business functions (NEW)
│   └── extraction.py
│
├── repositories/                # Data access (NEW)
│   ├── base.py
│   ├── district.py
│   ├── superintendent.py
│   └── health_plan.py
│
├── tasks/                       # Updated to use services
│   ├── discovery.py
│   ├── extraction.py
│   ├── health_plan_discovery.py
│   └── health_plan_extraction.py
│
└── workflows/                   # TODO: Refactor to use repos
    ├── run.py
    └── health_plans.py
```

---

## Next Steps

### ✅ Completed
1. Pydantic models for all LLM responses
2. Generic LLM client with Jinja2 templates
3. Prompt templates externalized
4. Thin service layer
5. Repository layer
6. Tasks layer refactored

### 🚧 TODO
1. Refactor workflows to use repositories
2. Remove old `utils/llm.py` (no longer needed)
3. Add enums for status/mode strings
4. Add CLI args to `main.py`
5. Consider async/parallel fetching

---

## Testing the New Architecture

```bash
# Install new dependencies
pip install jinja2>=3.1.0 pydantic>=2.0.0

# Run a test
python main.py  # Should work with new architecture
```

The new architecture is **backward compatible** - tasks still return dicts, so workflows don't need immediate changes.
