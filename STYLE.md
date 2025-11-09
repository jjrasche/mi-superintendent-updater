# Code Style Guide

## Core Principles

**DRY above all else** - Eliminate duplication ruthlessly

**Concise Functional Architecture:**
- Single-expression functions with self-documenting names
- Function composition over imperative blocks
- Comprehensions and chaining over loops
- Ternary and logical operators for control flow

**Aggressive Horizontal Compression:**
- Chain operations on single lines
- Inline unpacking and spreading
- Fluent method chaining
- Minimal vertical whitespace - functions flow together

**Functional Patterns:**
- Pure functions with clear input/output
- Method chaining and composition
- Immutable operations preferred
- No intermediate variables unless necessary

**Self-Documentation:**
- Function names eliminate need for comments
- Descriptive parameter names
- Action-oriented naming

## Python Patterns

```python
# Single-expression functions
get_url_pool = lambda district_id: session.query(FetchedPage.url).filter_by(district_id=district_id, mode='monitoring').all()
has_superintendent = lambda district: bool(get_latest_extraction(district.id))

# Chained operations
urls = (session.query(FetchedPage.url)
        .filter_by(district_id=district_id, status='success')
        .order_by(FetchedPage.created_at.desc())
        .limit(10).all())

# Comprehensions over loops
valid_urls = [url for url in urls if is_valid(url) and not is_excluded(url)]
results = {d.id: extract(d) for d in districts if should_process(d)}

# Ternary and logical operators
status = 'success' if result else 'error'
data = fetch_data() or get_cached() or default_data()
result = is_valid and process() or None

# Context managers for resources
with db_session() as s: s.add(page)

# No intermediate variables
return extract_superintendent(parse_html(fetch_page(url)))

# Method chaining for readability
return (DiscoveryStep()
        .set_district(district_id)
        .discover()
        .filter_top_urls(10))
```

## Anti-Patterns

```python
# ❌ Too verbose
def process_district(district_id):
    district = get_district(district_id)
    if district is not None:
        urls = discover_urls(district)
        if len(urls) > 0:
            return urls
        else:
            return []
    else:
        return None

# ✅ Concise
process_district = lambda d_id: discover_urls(d) if (d := get_district(d_id)) else []

# ❌ Unnecessary intermediate variables
def fetch_and_parse(url):
    html = fetch_page(url)
    text = parse_html(html)
    result = extract_data(text)
    return result

# ✅ Direct composition
fetch_and_parse = lambda url: extract_data(parse_html(fetch_page(url)))

# ❌ Imperative loop
results = []
for url in urls:
    if is_valid(url):
        results.append(process(url))

# ✅ Comprehension
results = [process(url) for url in urls if is_valid(url)]
```

## Architecture

**Clear separation:**
- Models: Data structures only
- Repositories: DB operations (pure I/O)
- Services: Business logic (pure functions)
- Workflows: Orchestration (compose services)

**Export-driven:**
- Each module exports clear public API
- Internal helpers prefixed with `_`
- Minimal public surface area

**Consistent patterns:**
- Context managers for resources
- Result objects over exceptions where appropriate
- Type hints for clarity
