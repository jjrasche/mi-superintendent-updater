"""
Test script to verify extraction fixes.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables BEFORE importing config-dependent modules
from dotenv import load_dotenv
load_dotenv()

from utils.html_parser import parse_html_to_text
from tasks.extraction import extract_superintendent


def test_email_in_heading():
    """Test that emails in mailto links within headings are extracted."""
    html = """
    <html>
    <body>
        <h6>Superintendent<br><a href="mailto:pjankowski@abs.misd.net">Phil Jankowski</a></h6>
        <h6><strong>Assistant Superintendent</strong><br>
        <a href="mailto:trathbun@abs.misd.net">Todd Rathbun</a></h6>
    </body>
    </html>
    """
    
    print("=" * 60)
    print("TEST 1: Email extraction from heading with mailto link")
    print("=" * 60)
    
    parsed = parse_html_to_text(html)
    print("\nParsed text:")
    print(parsed)
    print("\n")
    
    # Check if email is in parsed text
    if "pjankowski@abs.misd.net" in parsed:
        print("✓ PASS: Email found in parsed text")
    else:
        print("✗ FAIL: Email NOT found in parsed text")
    
    # Test extraction
    result = extract_superintendent(html, "Test District", "http://test.com")
    print("\nExtraction result:")
    print(f"  Name: {result['name']}")
    print(f"  Title: {result['title']}")
    print(f"  Email: {result['email']}")
    print(f"  Phone: {result['phone']}")
    print(f"  Is Empty: {result['is_empty']}")
    print(f"  Reasoning: {result['llm_reasoning']}")
    
    if result['name'] and result['email']:
        print("\n✓ PASS: Extraction successful with email")
    else:
        print("\n✗ FAIL: Extraction missing name or email")


def test_empty_text():
    """Test that empty/near-empty text is handled correctly."""
    html = """
    <html>
    <head><title>Test</title></head>
    <body></body>
    </html>
    """
    
    print("\n" + "=" * 60)
    print("TEST 2: Empty text detection")
    print("=" * 60)
    
    result = extract_superintendent(html, "Test District", "http://test.com")
    print("\nExtraction result:")
    print(f"  Name: {result['name']}")
    print(f"  Is Empty: {result['is_empty']}")
    print(f"  Reasoning: {result['llm_reasoning']}")
    
    if result['is_empty'] and result['name'] is None:
        print("\n✓ PASS: Empty text correctly detected")
    else:
        print("\n✗ FAIL: Empty text NOT detected or hallucination occurred")


def test_director_rejection():
    """Test that non-superintendent titles are rejected."""
    html = """
    <html>
    <body>
        <h3>Heidi Stephenson</h3>
        <p>Director of Elementary Education</p>
        <p>586-725-2861</p>
    </body>
    </html>
    """
    
    print("\n" + "=" * 60)
    print("TEST 3: Non-superintendent title rejection")
    print("=" * 60)
    
    result = extract_superintendent(html, "Test District", "http://test.com")
    print("\nExtraction result:")
    print(f"  Name: {result['name']}")
    print(f"  Title: {result['title']}")
    print(f"  Is Empty: {result['is_empty']}")
    print(f"  Reasoning: {result['llm_reasoning']}")
    
    if result['is_empty'] or (result['name'] is None):
        print("\n✓ PASS: Director correctly rejected as non-superintendent")
    else:
        print("\n✗ FAIL: Director incorrectly accepted as superintendent")


def test_valid_superintendent():
    """Test correct extraction of valid superintendent."""
    html = """
    <html>
    <body>
        <div>
            <h3>Administration</h3>
            <p>5201 County Line Rd<br>
            Suite 100 Casco Twp, MI 48064<br>
            (586) 725-2861<br>
            (586) 727-9059 Fax</p>
            
            <h6>Superintendent<br>
            <a href="mailto:pjankowski@abs.misd.net">Phil Jankowski</a><br>
            <strong>Assistant Superintendent</strong><br>
            <a href="mailto:trathbun@abs.misd.net">Todd Rathbun</a></h6>
        </div>
    </body>
    </html>
    """
    
    print("\n" + "=" * 60)
    print("TEST 4: Valid superintendent extraction")
    print("=" * 60)
    
    result = extract_superintendent(html, "Test District", "http://test.com")
    print("\nExtraction result:")
    print(f"  Name: {result['name']}")
    print(f"  Title: {result['title']}")
    print(f"  Email: {result['email']}")
    print(f"  Phone: {result['phone']}")
    print(f"  Is Empty: {result['is_empty']}")
    print(f"  Reasoning: {result['llm_reasoning']}")
    
    if (result['name'] and 
        'jankowski' in result['name'].lower() and 
        result['email'] and 
        'pjankowski@abs.misd.net' in result['email'].lower() and
        not result['is_empty']):
        print("\n✓ PASS: Valid superintendent correctly extracted with email")
    else:
        print("\n✗ FAIL: Valid superintendent extraction incomplete")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("EXTRACTION FIX TESTS")
    print("="*60)
    print("\nTesting fixes for:")
    print("  1. Email extraction from mailto links")
    print("  2. Empty text hallucination prevention")
    print("  3. Non-superintendent title rejection")
    print("\n")
    
    test_email_in_heading()
    test_empty_text()
    test_director_rejection()
    test_valid_superintendent()
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)
    print("\nNext step: Run 'python main.py' to test on real district data")
    print("=" * 60 + "\n")