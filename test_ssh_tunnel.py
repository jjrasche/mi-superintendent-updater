"""Test script for SSH tunnel and LLM connection"""
import sys
from utils.llm_client import get_client
from models.extraction_results import SuperintendentExtraction

def test_connection():
    """Test SSH tunnel connection and LLM call"""
    print("=" * 60)
    print("Testing SSH Tunnel and LLM Connection")
    print("=" * 60)

    try:
        print("\n1. Initializing LLM client with SSH tunnel...")
        client = get_client()
        print(f"   [OK] Client initialized")
        print(f"   Provider: {client.provider}")
        print(f"   Model: {client.model}")
        if client.tunneled_url:
            print(f"   Tunnel URL: {client.tunneled_url}")

        print("\n2. Testing simple extraction call...")
        test_html = """
        <html>
        <body>
            <h1>District Administration</h1>
            <p>Dr. Jane Smith, Superintendent</p>
            <p>Email: jsmith@district.edu</p>
            <p>Phone: (555) 123-4567</p>
        </body>
        </html>
        """

        result = client.call(
            'superintendent_extraction',
            SuperintendentExtraction,
            text=test_html,
            district_name="Test District"
        )

        print(f"   [OK] API call successful!")
        print(f"\n3. Extraction Results:")
        print(f"   Name: {result.name}")
        print(f"   Email: {result.email}")
        print(f"   Phone: {result.phone}")
        print(f"   Title: {result.title}")
        print(f"   Reasoning: {result.reasoning}")

        print("\n" + "=" * 60)
        print("[OK] All tests passed!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\nX Error: {type(e).__name__}")
        print(f"  {str(e)}")
        print("\n" + "=" * 60)
        print("X Test failed")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
