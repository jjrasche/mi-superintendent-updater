"""
Fast iteration test for HTML PDF link extraction.
Copies parsed output to clipboard for quick inspection.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.html_parser import parse_html_to_text
import pyperclip  # pip install pyperclip


def test_pdf_links():
    """Test PDF link extraction from transparency page."""
    
    html = """
    <html>
    <body>
        <div class="transparency-section">
            <ul>
                <li>
                    <p class="sub-content">
                        <a href="docs/budget/Medical_Plan_BCBS_1500_3000_Info_Support_Staff.pdf" target="_blank">
                        Medical Plan 
                        BCBS 
                        $1500/$3000 
                        Info Support 
                        Staff</a>
                    </p>
                </li>
                <li>
                    <p class="sub-content">
                        <a href="docs/budget/Medical_Plan_BCBS_3000_6000_Support_Staff.pdf" target="_blank">
                        Medical BCBS 
                        $3000/$6000 
                        Support 
                        Staff</a>
                    </p>
                </li>
                <li>
                    <p class="sub-content">
                        <a href="docs/budget/Medical_Plan_BCBS_3000_6000_Info_Support_Staff.pdf" target="_blank">
                        Medical BCBS 
                        $3000/$6000 
                        Info Support 
                        Staff</a>
                    </p>
                </li>
                <li>
                    <p class="sub-content">
                        <a href="docs/budget/Vision_Admin.pdf" target="_blank">Vision 
                        - Admin</a>
                    </p>
                </li>
                <li>
                    <p class="sub-content">
                        <a href="docs/budget/Dental_Plan_Info.pdf" target="_blank">Dental Plan Info</a>
                    </p>
                </li>
            </ul>
        </div>
    </body>
    </html>
    """
    
    base_url = "https://example.misd.net/transparency"
    
    print("=" * 60)
    print("PDF LINK EXTRACTION TEST")
    print("=" * 60)
    
    # Test WITHOUT preserve_document_links
    print("\n1. WITHOUT preserve_document_links:")
    print("-" * 60)
    result1 = parse_html_to_text(html, preserve_document_links=False)
    print(result1)
    
    # Test WITH preserve_document_links
    print("\n\n2. WITH preserve_document_links:")
    print("-" * 60)
    result2 = parse_html_to_text(html, preserve_document_links=True, base_url=base_url)
    print(result2)
    
    # Copy to clipboard
    try:
        pyperclip.copy(result2)
        print("\n✓ Parsed output copied to clipboard!")
    except Exception as e:
        print(f"\n✗ Failed to copy to clipboard: {e}")
    
    # Verification
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    expected_links = [
        "Medical_Plan_BCBS_1500_3000_Info_Support_Staff.pdf",
        "Medical_Plan_BCBS_3000_6000_Support_Staff.pdf",
        "Medical_Plan_BCBS_3000_6000_Info_Support_Staff.pdf",
        "Vision_Admin.pdf",
        "Dental_Plan_Info.pdf"
    ]
    
    found = 0
    missing = []
    
    for link in expected_links:
        if link in result2:
            found += 1
            print(f"✓ Found: {link}")
        else:
            missing.append(link)
            print(f"✗ Missing: {link}")
    
    print(f"\n{found}/{len(expected_links)} PDF links extracted")
    
    if missing:
        print("\nMissing links:")
        for link in missing:
            print(f"  - {link}")
    
    # Check for absolute URLs
    if "https://example.misd.net/transparency/docs/budget/" in result2:
        print("\n✓ URLs converted to absolute")
    else:
        print("\n✗ URLs still relative (not converted to absolute)")


if __name__ == "__main__":
    test_pdf_links()