"""
Test script to verify LLM provider switching works correctly.
"""

import os
from utils.llm_client import get_client
from models.extraction_results import URLFilterResult

def test_llm_provider():
    """Test the currently configured LLM provider"""
    from config import LLM_PROVIDER, GROQ_MODEL, OLLAMA_MODEL, OLLAMA_URL

    print("=" * 60)
    print("LLM Provider Test")
    print("=" * 60)
    print(f"Active Provider: {LLM_PROVIDER}")

    if LLM_PROVIDER == 'groq':
        print(f"Groq Model: {GROQ_MODEL}")
    elif LLM_PROVIDER == 'ollama':
        print(f"Ollama URL: {OLLAMA_URL}")
        print(f"Ollama Model: {OLLAMA_MODEL}")

    print("\nTesting URL filtering with sample data...")
    print("-" * 60)

    # Sample test data
    test_urls = [
        "https://example.com/administration",
        "https://example.com/staff-directory",
        "https://example.com/contact-us",
        "https://example.com/calendar",
        "https://example.com/news",
    ]

    try:
        client = get_client()
        result = client.call(
            'url_filtering',
            URLFilterResult,
            urls=test_urls,
            district_name="Test District"
        )

        print(f"\nSuccess! LLM returned {len(result.urls)} URLs")
        print(f"Selected URLs: {result.urls}")
        print(f"Reasoning: {result.reasoning[:100]}...")
        print("\n" + "=" * 60)
        print(f"SUCCESS: {LLM_PROVIDER.upper()} provider is working correctly!")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR testing {LLM_PROVIDER.upper()} provider:")
        print(f"  {type(e).__name__}: {e}")
        print("=" * 60)
        return False

    return True

if __name__ == "__main__":
    test_llm_provider()
