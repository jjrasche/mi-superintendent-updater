# Repository Layer - Before/After

## Before (Direct SQLAlchemy)

```python
def run_district_check(district_id: int):
    session = get_session()
    try:
        # Get district
        district = session.query(District).filter_by(id=district_id).first()
        if not district:
            raise ValueError(f"District {district_id} not found")

        # Get URL pool
        url_pool = get_url_pool(district_id)  # Separate function with own session

        # Process each URL
        for url in urls_to_check:
            # Create FetchedPage record
            fetched_page = FetchedPage(
                district_id=district_id,
                url=fetch_result['url'],
                mode=mode,
                status=fetch_result['status'],
                error_message=fetch_result['error_message'],
                fetched_at=datetime.utcnow()
            )
            session.add(fetched_page)
            session.flush()  # Get the ID

            # Create Extraction record
            if fetch_result['status'] == 'success':
                extraction = Extraction(
                    fetched_page_id=fetched_page.id,
                    name=extraction_result['name'],
                    title=extraction_result['title'],
                    email=extraction_result['email'],
                    phone=extraction_result['phone'],
                    extracted_text=extraction_result['extracted_text'],
                    llm_reasoning=extraction_result['llm_reasoning'],
                    is_empty=extraction_result['is_empty'],
                    extracted_at=datetime.utcnow()
                )
                session.add(extraction)

        # Update district
        district.last_checked_at = datetime.utcnow()
        session.commit()

    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()
```

**Issues:**
- 50+ lines of boilerplate
- Manual session management
- Repeated field mappings
- Mixed DB operations with business logic
- Error-prone (forgot flush? rollback?)

---

## After (Repository Layer)

```python
def run_district_check(district_id: int):
    with SuperintendentRepository.transaction() as repo:
        # Get district
        district = repo.district.get(district_id)
        if not district: raise ValueError(f"District {district_id} not found")

        # Get URL pool
        url_pool = repo.get_monitoring_urls(district_id)

        # Process each URL
        for url in urls_to_check:
            page = repo.save_fetch_result(district_id, url, mode, fetch_result)
            if fetch_result['status'] == 'success':
                repo.save_extraction_result(page.id, extraction_result)

        # Update district
        repo.district.mark_checked(district)
```

**Benefits:**
- 15 lines (70% reduction)
- Auto session management
- No field mapping boilerplate
- Clear business intent
- Cannot forget rollback/close

---

## Actual Usage Examples

### Simple Queries

```python
# Get district
with DistrictRepository.transaction() as repo:
    district = repo.get(202)
    urls = repo.get_monitoring_urls(202)
```

### Chained Operations

```python
with SuperintendentRepository.transaction() as repo:
    page = repo.save_fetch_result(district_id, url, 'discovery', fetch_result)
    extraction = repo.save_extraction_result(page.id, extraction_result) if page.status == 'success' else None
```

### Bulk Operations

```python
with HealthPlanRepository.transaction() as repo:
    plans = repo.save_extracted_plans(district_id, plans_data, source_url)
    print(f"Saved {len(plans)} plans")
```

### Multiple Repositories in One Transaction

```python
with SuperintendentRepository.transaction() as super_repo:
    district = super_repo.session.query(District).filter_by(id=district_id).first()

    # Or create a helper that gives you both
    with transaction() as (district_repo, super_repo):
        district = district_repo.get(district_id)
        page = super_repo.save_fetch_result(...)
        district_repo.mark_checked(district)
```

---

## Key Design Principles

1. **Lambda for single-expression queries** - No def boilerplate
2. **Methods for multi-step operations** - When you need intermediate state
3. **Composite operations** - Common workflows pre-packaged
4. **Chainable returns** - Every save returns the object
5. **Context manager** - Automatic transaction management
