"""
SQL queries to identify good test cases for LLM prompt testing.
Run with: python analysis_queries.py
"""

from models.database import SessionLocal, District, FetchedPage, Extraction
from sqlalchemy import func, and_, or_

def find_successful_extractions():
    """Find cases where we successfully extracted superintendent info"""
    with SessionLocal() as session:
        results = session.query(
            District.name,
            Extraction.name,
            Extraction.email,
            Extraction.phone,
            Extraction.llm_reasoning,
            FetchedPage.url
        ).join(
            FetchedPage, Extraction.fetched_page_id == FetchedPage.id
        ).join(
            District, FetchedPage.district_id == District.id
        ).filter(
            Extraction.is_empty == False
        ).all()

        print("\n=== SUCCESSFUL EXTRACTIONS (Good Examples) ===")
        for r in results:
            print(f"\nDistrict: {r[0]}")
            print(f"  Superintendent: {r[1]}")
            print(f"  Email: {r[2]}")
            print(f"  Phone: {r[3]}")
            print(f"  URL: {r[5]}")
            print(f"  Reasoning: {r[4][:100]}...")
        return results

def find_empty_extractions_with_content():
    """
    Find cases where LLM returned empty but the page had substantial content.
    These are candidates for prompt improvement.
    """
    with SessionLocal() as session:
        results = session.query(
            District.name,
            FetchedPage.url,
            FetchedPage.text_length,
            Extraction.llm_reasoning
        ).join(
            Extraction, Extraction.fetched_page_id == FetchedPage.id
        ).join(
            District, FetchedPage.district_id == District.id
        ).filter(
            and_(
                Extraction.is_empty == True,
                FetchedPage.text_length > 1000  # Had substantial content
            )
        ).all()

        print("\n=== EMPTY EXTRACTIONS WITH CONTENT (Prompt Improvement Candidates) ===")
        print("These pages had content but LLM didn't find superintendent info\n")
        for r in results:
            print(f"District: {r[0]}")
            print(f"  URL: {r[1]}")
            print(f"  Content length: {r[2]} chars")
            print(f"  LLM reasoning: {r[3][:100]}...")
            print()
        return results

def find_partial_extractions():
    """
    Find cases where we got name/title but missing email/phone.
    Could indicate prompt needs to emphasize contact info extraction.
    """
    with SessionLocal() as session:
        results = session.query(
            District.name,
            Extraction.name,
            Extraction.email,
            Extraction.phone,
            Extraction.llm_reasoning,
            FetchedPage.url
        ).join(
            FetchedPage, Extraction.fetched_page_id == FetchedPage.id
        ).join(
            District, FetchedPage.district_id == District.id
        ).filter(
            and_(
                Extraction.is_empty == False,
                Extraction.name != None,
                or_(Extraction.email == None, Extraction.phone == None)
            )
        ).all()

        print("\n=== PARTIAL EXTRACTIONS (Missing Contact Info) ===")
        print("Got name but missing email or phone\n")
        for r in results:
            print(f"District: {r[0]}")
            print(f"  Superintendent: {r[1]}")
            print(f"  Email: {'MISSING' if not r[2] else r[2]}")
            print(f"  Phone: {'MISSING' if not r[3] else r[3]}")
            print(f"  URL: {r[5]}")
            print(f"  Reasoning: {r[4][:100]}...")
            print()
        return results

def find_url_filtering_stats():
    """
    Stats on URL discovery/filtering to identify if we're selecting the right pages
    """
    with SessionLocal() as session:
        # Count how often first URL had the data
        first_url_hits = session.query(func.count()).join(
            Extraction, Extraction.fetched_page_id == FetchedPage.id
        ).filter(
            and_(
                Extraction.is_empty == False,
                # This would need subquery to check if it's the first URL processed
            )
        ).scalar()

        # Districts with multiple page fetches but no success
        no_success_districts = session.query(
            District.name,
            func.count(FetchedPage.id).label('pages_checked')
        ).join(
            FetchedPage, FetchedPage.district_id == District.id
        ).outerjoin(
            Extraction, Extraction.fetched_page_id == FetchedPage.id
        ).group_by(
            District.id, District.name
        ).having(
            func.sum(func.cast(~Extraction.is_empty, Integer)) == 0
        ).all()

        print("\n=== URL FILTERING EFFECTIVENESS ===")
        print("\nDistricts where we checked pages but found nothing:")
        for district, count in no_success_districts:
            print(f"  {district}: {count} pages checked")

        return no_success_districts

def compare_before_after_prompt_changes():
    """
    Template for comparing results before/after prompt changes.
    Run this after making prompt changes and re-running same districts.
    """
    with SessionLocal() as session:
        # Group extractions by district and timestamp
        # Compare success rates, field completion, etc.

        results = session.query(
            District.name,
            Extraction.created_at,
            Extraction.is_empty,
            Extraction.name,
            Extraction.email,
            Extraction.phone
        ).join(
            FetchedPage, Extraction.fetched_page_id == FetchedPage.id
        ).join(
            District, FetchedPage.district_id == District.id
        ).order_by(
            District.id, Extraction.created_at
        ).all()

        print("\n=== EXTRACTION TIMELINE (for before/after comparison) ===")
        current_district = None
        for r in results:
            if r[0] != current_district:
                print(f"\n{r[0]}:")
                current_district = r[0]
            status = "EMPTY" if r[2] else f"FOUND: {r[3]}"
            print(f"  {r[1]}: {status}")

        return results

if __name__ == "__main__":
    print("="*60)
    print("LLM PROMPT TEST CASE ANALYSIS")
    print("="*60)

    successful = find_successful_extractions()
    empty_with_content = find_empty_extractions_with_content()
    partial = find_partial_extractions()
    url_stats = find_url_filtering_stats()
    timeline = compare_before_after_prompt_changes()

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Successful extractions: {len(successful)}")
    print(f"Empty with content (candidates for improvement): {len(empty_with_content)}")
    print(f"Partial extractions (missing contact info): {len(partial)}")
    print("\nThese queries help identify:")
    print("  1. Good examples to preserve (successful extractions)")
    print("  2. Cases where prompt needs improvement (empty with content)")
    print("  3. Cases where contact extraction needs work (partial)")
    print("  4. URL filtering effectiveness")
