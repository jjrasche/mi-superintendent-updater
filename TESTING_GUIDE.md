# LLM Prompt Testing Guide

This guide explains how to test and improve LLM prompts for the superintendent scraper using data-driven tests.

## Overview

The scraper has **two key LLM decision points**:

1. **URL Discovery/Filtering** (`prompts/url_filtering.txt`)
   - INPUT: List of all URLs found on homepage
   - OUTPUT: Top 10 URLs most likely to contain superintendent info
   - LLM REASONING: Why these URLs were selected

2. **Superintendent Extraction** (`prompts/superintendent_extraction.txt`)
   - INPUT: Parsed HTML/PDF text from a page
   - OUTPUT: Structured superintendent data (name, email, phone, title)
   - LLM REASONING: How the data was found

## Data Collection

### Run Extraction on Districts

```bash
# Collect test data from first 10 districts
PYTHONIOENCODING=utf-8 venv/Scripts/python.exe main.py --range 1 10
```

This generates:
- **Database records**: `district_fetch.db` (FetchedPage and Extraction tables)
- **Debug logs**: `debug_logs/<timestamp>/`
  - `*_discovery.json` - URL filtering inputs/outputs
  - `*_extraction.json` - Extraction results
  - `*_parsed.txt` - Text that went to LLM
  - `*_raw.html` - Original HTML

## Analysis Queries

### Find Test Candidates

```bash
python analysis_queries.py
```

This identifies:
- **Successful extractions** - Good examples to preserve
- **Empty extractions with content** - Candidates for prompt improvement
- **Partial extractions** - Missing email/phone (needs better extraction)
- **URL filtering effectiveness** - Are we selecting the right pages?

Example queries:

```python
from models.database import SessionLocal, District, FetchedPage, Extraction
from sqlalchemy import and_

# Find cases where we got name but no contact info
with SessionLocal() as session:
    partial = session.query(
        District.name,
        Extraction.name,
        Extraction.email,
        Extraction.phone,
        FetchedPage.url
    ).join(
        FetchedPage, Extraction.fetched_page_id == FetchedPage.id
    ).join(
        District, FetchedPage.district_id == District.id
    ).filter(
        and_(
            Extraction.is_empty == False,
            Extraction.name != None,
            Extraction.email == None  # Has name but missing email
        )
    ).all()
```

## Creating Test Cases

### From Debug Logs

Use the helper function to generate test cases:

```bash
python -c "from tests.test_superintendent_extraction import generate_test_case_from_debug_log; \
generate_test_case_from_debug_log(\
  'debug_logs/20251111_124231/Adams_Township_School_District/district-board_php_124302_extraction.json', \
  'debug_logs/20251111_124231/Adams_Township_School_District/district-board_php_124302_parsed.txt')"
```

Copy the output into `tests/test_superintendent_extraction.py` in the `EXTRACTION_TEST_CASES` list.

### Manual Test Case Format

```python
{
    "id": "unique_test_id",
    "description": "What this test validates",
    "district_name": "District Name",
    "input_text": """The actual HTML text...""",
    "expected": {
        "is_empty": False,
        "name": "Dr. John Doe",
        "title": "Superintendent",
        "email": "jdoe@district.edu",
        "phone": "(555) 123-4567",
    },
    "reasoning_should_mention": ["found", "superintendent", "contact"]
}
```

## Running Tests

### Run All Tests

```bash
python -m pytest tests/test_superintendent_extraction.py -v
```

### Run Specific Test

```bash
python -m pytest tests/test_superintendent_extraction.py::TestSuperintendentExtraction::test_extraction -v
```

### Run Anti-Hallucination Tests Only

```bash
python -m pytest tests/test_superintendent_extraction.py::TestSuperintendentExtraction::test_no_hallucination -v
```

## Workflow for Prompt Changes

### 1. Establish Baseline

```bash
# Run extraction on test districts
PYTHONIOENCODING=utf-8 venv/Scripts/python.exe main.py --range 1 10

# Run tests (should all pass)
python -m pytest tests/test_superintendent_extraction.py -v
```

### 2. Identify Problems

```bash
# Find cases that need improvement
python analysis_queries.py
```

Look for:
- Empty extractions with substantial content (prompt not finding data)
- Partial extractions (prompt not extracting all fields)
- Wrong URL selections (filtering prompt needs work)

### 3. Add Test Cases

For each problem case, create a test:

```python
# Add to EXTRACTION_TEST_CASES
{
    "id": "problem_case_description",
    "input_text": "...the actual text...",
    "expected": {...},
    "reasoning_should_mention": [...]
}
```

### 4. Modify Prompt

Edit `prompts/superintendent_extraction.txt` or `prompts/url_filtering.txt`

### 5. Re-run Tests

```bash
# Run extraction again on same districts
PYTHONIOENCODING=utf-8 venv/Scripts/python.exe main.py --range 1 10

# Run tests
python -m pytest tests/test_superintendent_extraction.py -v
```

### 6. Compare Results

```bash
# See before/after comparison
python analysis_queries.py
```

The `compare_before_after_prompt_changes()` function shows extraction timeline.

## Test Categories

### 1. Extraction Accuracy Tests

Validates the LLM extracts correct data:
- Finds superintendent when present
- Returns empty when not present
- Extracts all available contact fields

### 2. Anti-Hallucination Tests

Prevents the LLM from making up data:
- Verifies names appear in input
- Validates emails aren't fabricated
- Ensures phone numbers come from input
- Checks empty extractions have all None fields

### 3. URL Filtering Tests

Validates URL selection logic:
- Prioritizes contact/admin pages
- Excludes calendars, lunch menus, etc.
- Selects reasonable number of URLs

## Good Test Cases to Collect

### High Priority

1. **Clear Success** - Page with obvious superintendent contact info
2. **Board Page** - Has board members but no superintendent
3. **404 Error** - Missing or error pages
4. **Directory Page** - Staff list with superintendent
5. **Contact Page** - General contact page

### Edge Cases

6. **Assistant Superintendent Only** - No regular superintendent
7. **Interim Superintendent** - Temporary leadership
8. **Email in mailto: link** - Email not in plain text
9. **Phone in tel: link** - Phone not in plain text
10. **PDF Content** - Superintendent info in PDF

## Metrics to Track

After each prompt change, track:

```python
# Success rate
successful_extractions / total_attempts

# Field completion rate
(extractions_with_email + extractions_with_phone) / successful_extractions

# False positive rate
empty_extractions_with_substantial_content / total_attempts

# URL filtering precision
correct_urls_selected / total_urls_selected
```

## Tips

1. **Start small**: Test on 10 districts first
2. **Document examples**: Every edge case should become a test
3. **Version prompts**: Git commit before/after prompt changes
4. **Regression testing**: Always run full test suite before merging
5. **Real data**: Use actual scraped data, not synthetic examples

## Current Test Coverage

As of setup:
- ✓ Empty extraction cases (board pages, 404s)
- ✓ Anti-hallucination validation
- ✓ URL filtering logic
- ⚠ Need: Successful extraction examples
- ⚠ Need: Partial extraction examples
- ⚠ Need: PDF extraction examples
- ⚠ Need: Complex formatting examples

## Next Steps

1. Fix the workflow observer bug (`'SuperintendentContact' object is not subscriptable`)
2. Run full extraction on 10+ districts
3. Add successful extraction test cases
4. Establish baseline metrics
5. Identify top 3 prompt improvement opportunities
6. Implement and test changes iteratively
